from __future__ import annotations

import hashlib
import json
import logging
import re
import tempfile
import threading
import time
import uuid
from argparse import Namespace
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from tools.annotate_web_replays import annotate
from tools.build_player_case import build
from tools.player_case_server import PLAYER_CASE_PREFIX, load_window_payload, parse_riot_id


LOG = logging.getLogger("riftscale.backend")
JOB_ID_RE = re.compile(r"^ana_[0-9a-f]{24}$")
ALLOWED_PLATFORMS = {"oc1"}
PRIVATE_OUTPUT_FIELDS = {"puuid", "summonerId", "accountId", "matchId"}


def sanitize_public_payload(value):
    """Defence in depth for fields that must never cross the public API."""
    if isinstance(value, dict):
        return {
            key: sanitize_public_payload(item)
            for key, item in value.items()
            if key not in PRIVATE_OUTPUT_FIELDS
        }
    if isinstance(value, list):
        return [sanitize_public_payload(item) for item in value]
    return value


@dataclass(frozen=True)
class AnalysisRequest:
    riot_id: str
    platform: str = "oc1"
    match_count: int = 10

    def normalized(self) -> "AnalysisRequest":
        game_name, tag_line = parse_riot_id(self.riot_id)
        platform = self.platform.strip().lower()
        if platform not in ALLOWED_PLATFORMS:
            raise ValueError("The public beta currently supports OCE (oc1) only")
        if not 1 <= int(self.match_count) <= 20:
            raise ValueError("matchCount must be between 1 and 20")
        return AnalysisRequest(f"{game_name}#{tag_line}", platform, int(self.match_count))

    @property
    def cache_key(self) -> str:
        value = f"{self.platform}|{self.riot_id.casefold()}|{self.match_count}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class JobRecord:
    job_id: str
    request: AnalysisRequest
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: dict | None = None
    error: str | None = None

    def public(self) -> dict:
        payload = {
            "jobId": self.job_id,
            "status": self.status,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.result is not None:
            payload["result"] = self.result
        if self.error:
            payload["error"] = self.error
        return payload


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        timestamp = time.time() if now is None else now
        cutoff = timestamp - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(timestamp)
            return True


class AnalysisEngine:
    """Run existing deterministic extraction without exporting Riot identifiers."""

    def __init__(self, root: Path, api_key: str, cache_dir: Path):
        self.root = root.resolve()
        self.api_key = api_key.strip()
        self.cache_dir = cache_dir.resolve()

    def __call__(self, request: AnalysisRequest) -> dict:
        game_name, tag_line = parse_riot_id(request.riot_id)
        with tempfile.TemporaryDirectory(prefix="riftscale-analysis-") as temporary:
            work = Path(temporary)
            player_case_path = work / "player-case.js"
            replay_path = work / "player-replays.json"
            args = Namespace(
                config=str(self.root / "config" / "model-parameters.json"),
                platform=request.platform,
                riot_id=game_name,
                tag_line=tag_line,
                matches=request.match_count,
                cache_dir=str(self.cache_dir),
                output=str(player_case_path),
                replay_output=str(replay_path),
                api_key=self.api_key,
            )
            build(args)
            annotate(player_case_path, replay_path, replay_path)
            player_case = load_window_payload(player_case_path, PLAYER_CASE_PREFIX)
            replays = json.loads(replay_path.read_text(encoding="utf-8"))
        return sanitize_public_payload({
            "playerCase": player_case,
            "replays": replays,
            "precision": {
                "positions": "approximately 60-second Timeline samples",
                "events": "millisecond timestamps where Riot Timeline provides them",
                "causality": "candidate causes only; temporal order is not proof of causation",
            },
        })


class JobManager:
    def __init__(
        self,
        analyzer: Callable[[AnalysisRequest], dict],
        *,
        cache_ttl_seconds: int = 300,
        job_ttl_seconds: int = 3600,
    ):
        self.analyzer = analyzer
        self.cache_ttl_seconds = max(1, int(cache_ttl_seconds))
        self.job_ttl_seconds = max(self.cache_ttl_seconds, int(job_ttl_seconds))
        self._jobs: dict[str, JobRecord] = {}
        self._cache: dict[str, tuple[float, dict]] = {}
        self._active_by_key: dict[str, str] = {}
        self._lock = threading.Lock()
        # One worker protects the shared Riot application quota and cache files.
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="riot-analysis")

    def submit(self, raw_request: AnalysisRequest) -> tuple[JobRecord, bool]:
        request = raw_request.normalized()
        now = time.time()
        with self._lock:
            self._prune(now)
            cached = self._cache.get(request.cache_key)
            if cached and cached[0] > now:
                record = JobRecord(
                    job_id=self._new_job_id(), request=request, status="completed",
                    created_at=now, updated_at=now, result=cached[1],
                )
                self._jobs[record.job_id] = record
                return record, True
            active_id = self._active_by_key.get(request.cache_key)
            if active_id and active_id in self._jobs:
                return self._jobs[active_id], False
            record = JobRecord(job_id=self._new_job_id(), request=request)
            self._jobs[record.job_id] = record
            self._active_by_key[request.cache_key] = record.job_id
            self._executor.submit(self._run, record.job_id)
            return record, False

    def get(self, job_id: str) -> JobRecord | None:
        if not JOB_ID_RE.fullmatch(job_id):
            return None
        with self._lock:
            self._prune(time.time())
            return self._jobs.get(job_id)

    def _run(self, job_id: str) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = "running"
            record.updated_at = time.time()
        try:
            result = self.analyzer(record.request)
        except Exception as exc:
            # Riot response bodies and infrastructure details are intentionally
            # excluded from logs as well as from the public response.
            LOG.error("Analysis failed for job %s (%s)", job_id, type(exc).__name__)
            with self._lock:
                record.status = "failed"
                record.error = "Analysis failed. Check the Riot ID or try again later."
                record.updated_at = time.time()
                self._active_by_key.pop(record.request.cache_key, None)
            return
        with self._lock:
            now = time.time()
            record.status = "completed"
            record.result = result
            record.updated_at = now
            self._cache[record.request.cache_key] = (now + self.cache_ttl_seconds, result)
            self._active_by_key.pop(record.request.cache_key, None)

    def _prune(self, now: float) -> None:
        expired_jobs = [
            job_id for job_id, record in self._jobs.items()
            if record.status in {"completed", "failed"} and now - record.updated_at > self.job_ttl_seconds
        ]
        for job_id in expired_jobs:
            self._jobs.pop(job_id, None)
        expired_cache = [key for key, (expires_at, _) in self._cache.items() if expires_at <= now]
        for key in expired_cache:
            self._cache.pop(key, None)

    @staticmethod
    def _new_job_id() -> str:
        return f"ana_{uuid.uuid4().hex[:24]}"
