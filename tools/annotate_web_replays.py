"""Attach deterministic objective-loss evidence to browser replay payloads."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from desktop.lol_high_rank_comparator import objective_loss_analysis, objective_loss_events
from tools.player_case_server import PLAYER_CASE_PREFIX, load_window_payload


def annotate(player_case: Path, replays_path: Path, output: Path) -> None:
    case = load_window_payload(player_case, PLAYER_CASE_PREFIX)
    replays = json.loads(replays_path.read_text(encoding="utf-8"))
    matches = {match.get("matchRef"): match for match in case.get("matches", [])}
    for match_ref, replay in replays.items():
        match = matches.get(match_ref)
        if not match:
            continue
        replay["objectiveAnalyses"] = [
            objective_loss_analysis(replay, match, event)
            for event in objective_loss_events(replay, match)
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(replays, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-case", required=True)
    parser.add_argument("--replays", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    annotate(Path(args.player_case), Path(args.replays), Path(args.output))


if __name__ == "__main__":
    main()
