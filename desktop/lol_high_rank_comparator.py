from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

if not getattr(sys, "frozen", False):
    source_root = Path(__file__).resolve().parents[1]
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from riot_model.client import RiotClient
from riot_model.features import extract_match_replay, extract_player_match
from riot_model.settings import load_settings
from tools.build_conditional_model import PHASE_METRICS, number, phase_metrics
from tools.build_player_case import case_payload


APP_NAME = "LOLHighRankComparator"
APP_TITLE = "峡谷天平 · 高分段赛后对比"
DDRAGON_VERSION = "16.15.1"
PHASE_NAMES = {"EARLY": "前期 0–15", "MID": "中期 15–25", "LATE": "后期 25+"}
POSITION_NAMES = {"TOP": "上路", "JUNGLE": "打野", "MIDDLE": "中路", "BOTTOM": "下路", "UTILITY": "辅助"}
CONFIDENCE_NAMES = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}
DRAGON_NAMES = {
    "FIRE_DRAGON": "火龙", "EARTH_DRAGON": "土龙", "WATER_DRAGON": "水龙",
    "AIR_DRAGON": "风龙", "HEXTECH_DRAGON": "海克斯龙", "CHEMTECH_DRAGON": "炼金龙",
    "ELDER_DRAGON": "远古龙", "Infernal": "火龙魂", "Mountain": "土龙魂",
    "Ocean": "水龙魂", "Cloud": "风龙魂", "Hextech": "海克斯龙魂", "Chemtech": "炼金龙魂",
}
LANE_PATHS = {
    "TOP": [(1450, 1450), (1100, 3600), (1100, 12100), (3300, 13700), (13500, 13500)],
    "MIDDLE": [(1450, 1450), (7500, 7500), (13500, 13500)],
    "BOTTOM": [(1450, 1450), (3600, 1100), (12100, 1100), (13700, 3300), (13500, 13500)],
}
METRIC_NAMES = {
    "early_gold_15": "15 分钟经济", "early_xp_15": "15 分钟经验", "early_cs_15": "15 分钟 CS",
    "early_kills": "前期击杀", "early_deaths": "前期死亡", "early_assists": "前期助攻",
    "mid_gold_gain": "15–25 经济增长", "mid_cs_gain": "15–25 CS 增长", "mid_champion_damage": "15–25 英雄伤害",
    "mid_kills": "中期击杀", "mid_deaths": "中期死亡", "mid_assists": "中期助攻",
    "mid_team_turrets": "中期团队推塔", "mid_team_dragons": "中期团队小龙",
    "late_champion_damage_per_min": "25+ 每分钟英雄伤害", "late_damage_taken_per_min": "25+ 每分钟承伤",
    "late_kills": "后期击杀", "late_deaths": "后期死亡", "late_assists": "后期助攻",
    "late_teamfight_participation_rate": "后期团战参与率", "late_first_target_deaths": "后期首个阵亡",
    "early_gold_diff_vs_enemy_jungle": "15 分钟对位经济差", "early_xp_diff_vs_enemy_jungle": "15 分钟对位经验差",
    "early_cs_diff_vs_enemy_jungle": "15 分钟对位 CS 差", "early_gank_takedowns": "前 15 分钟有效 Gank",
    "early_gank_lanes": "前 15 分钟影响路线数", "early_first_gank_minute": "首次有效 Gank 分钟",
    "early_enemy_jungle_takedowns": "前期对敌方打野击杀参与", "early_kill_participation_rate": "前期团队击杀参与率",
    "early_team_dragons": "前期团队小龙", "early_team_void_grubs": "前期团队虚空巢虫",
    "early_team_rift_heralds": "前期团队峡谷先锋", "early_personal_epic_secures": "前期个人史诗野怪击杀",
    "early_gank_takedown_diff_vs_enemy_jungle": "前期有效 Gank 对位差",
    "early_epic_monster_diff_vs_enemy_jungle": "前期史诗野怪对位差",
    "mid_gank_takedowns": "中期有效 Gank", "mid_gank_lanes": "中期影响路线数",
    "mid_first_gank_minute": "中期首次有效 Gank 分钟", "mid_enemy_jungle_takedowns": "中期对敌方打野击杀参与",
    "mid_kill_participation_rate": "中期团队击杀参与率", "mid_team_void_grubs": "中期团队虚空巢虫",
    "mid_team_rift_heralds": "中期团队峡谷先锋", "mid_personal_epic_secures": "中期个人史诗野怪击杀",
    "mid_gank_takedown_diff_vs_enemy_jungle": "中期有效 Gank 对位差",
    "mid_epic_monster_diff_vs_enemy_jungle": "中期史诗野怪对位差",
}


def resource_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root / relative


def app_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_riot_id(value: str) -> tuple[str, str]:
    candidate = urllib.parse.unquote(str(value or "").strip())
    if "/summoners/" in candidate:
        candidate = urllib.parse.urlparse(candidate).path.rstrip("/").split("/")[-1]
        candidate = urllib.parse.unquote(candidate)
        if "#" not in candidate and "-" in candidate:
            left, right = candidate.rsplit("-", 1)
            candidate = f"{left}#{right}"
    if "#" not in candidate:
        raise ValueError("Riot ID 必须包含 #TAG，例如 Geolonwe#OC")
    game_name, tag_line = (part.strip() for part in candidate.rsplit("#", 1))
    if not game_name or not tag_line:
        raise ValueError("玩家名和 TAG 不能为空")
    return game_name, tag_line


def load_bootstrap_case(path: Path) -> dict:
    source = path.read_text(encoding="utf-8").strip()
    if source.startswith("window.PLAYER_CASE="):
        source = source[len("window.PLAYER_CASE="):].removesuffix(";")
    return json.loads(source)


def approximate_percentile(value, stats) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not stats:
        return None
    points = [(stats["p10"], 10), (stats["p25"], 25), (stats["median"], 50), (stats["p75"], 75), (stats["p90"], 90)]
    if numeric < points[0][0]:
        return max(0, 10 - 10 * (points[0][0] - numeric) / (abs(points[0][0]) or 1))
    if numeric >= points[-1][0]:
        return min(100, 90 + 10 * (numeric - points[-1][0]) / (abs(points[-1][0]) + 1))
    for index in range(1, len(points)):
        if numeric <= points[index][0]:
            low_value, low_pct = points[index - 1]
            high_value, high_pct = points[index]
            ratio = (numeric - low_value) / (high_value - low_value or 1)
            return low_pct + ratio * (high_pct - low_pct)
    return None


def format_metric(metric: str, value) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(numeric):
        return "—"
    if "rate" in metric:
        return f"{numeric * 100:.1f}%"
    if abs(numeric) >= 1000:
        return f"{numeric:,.0f}"
    if abs(numeric - round(numeric)) < 1e-9:
        return f"{int(numeric)}"
    return f"{numeric:.2f}".rstrip("0").rstrip(".")


def format_gap(metric: str, value) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"
    sign = "+" if numeric > 0 else ""
    if "rate" in metric:
        return f"{sign}{numeric * 100:.1f}pp"
    return f"{sign}{format_metric(metric, numeric)}"


def comparison_rows(match: dict, phase: str, baselines: dict) -> list[tuple[str, ...]]:
    position = match.get("position")
    player_profile = baselines.get(f"{match.get('champion')}|{position}|{phase}", {})
    opponent_profile = baselines.get(f"{match.get('opponentChampion')}|{match.get('opponentPosition')}|{phase}", {})
    rows = []
    for metric in phase_metrics(phase, position):
        player_value = number(match.get(metric))
        opponent_value = number(match.get(f"opponent_{metric}"))
        player_stats = player_profile.get("metrics", {}).get(metric)
        opponent_stats = opponent_profile.get("metrics", {}).get(metric)
        player_base = number(player_stats.get("median")) if player_stats else None
        opponent_base = number(opponent_stats.get("median")) if opponent_stats else None
        player_pct = approximate_percentile(player_value, player_stats)
        opponent_pct = approximate_percentile(opponent_value, opponent_stats)
        rows.append((
            METRIC_NAMES.get(metric, metric),
            format_metric(metric, player_value),
            format_metric(metric, opponent_value),
            f"{format_metric(metric, player_base)}  n={player_profile.get('sampleSize', 0)}" if player_stats else "—",
            f"{format_metric(metric, opponent_base)}  n={opponent_profile.get('sampleSize', 0)}" if opponent_stats else "—",
            format_gap(metric, player_value - opponent_value) if player_value is not None and opponent_value is not None else "—",
            format_gap(metric, player_value - player_base) if player_value is not None and player_base is not None else "—",
            format_gap(metric, opponent_value - opponent_base) if opponent_value is not None and opponent_base is not None else "—",
            f"P{round(player_pct)}" if player_pct is not None else "—",
            f"P{round(opponent_pct)}" if opponent_pct is not None else "—",
        ))
    return rows


def map_coordinates(x, y, width: int, height: int) -> tuple[float, float] | None:
    """Convert Riot's bottom-left map coordinates to Tk's top-left canvas."""
    try:
        map_x = min(15000.0, max(0.0, float(x)))
        map_y = min(15000.0, max(0.0, float(y)))
    except (TypeError, ValueError):
        return None
    return map_x / 15000.0 * width, height - map_y / 15000.0 * height


def point_along_path(path: list[tuple[float, float]], distance: float) -> tuple[float, float]:
    remaining = max(0.0, float(distance))
    for start, end in zip(path, path[1:]):
        segment = math.dist(start, end)
        if remaining <= segment:
            ratio = remaining / segment if segment else 0.0
            return start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio
        remaining -= segment
    return path[-1]


def estimated_minion_waves(second: int) -> list[dict]:
    """Estimate the newest wave from public SR spawn rules; Riot does not expose minion positions."""
    current = max(0, int(second))
    first_spawn = 65
    if current < first_spawn:
        return []
    spawn_second = first_spawn + ((current - first_spawn) // 30) * 30
    age = current - spawn_second
    output = []
    for lane, path in LANE_PATHS.items():
        total_distance = sum(math.dist(start, end) for start, end in zip(path, path[1:]))
        travel = min(325.0 * age, total_distance / 2)
        output.append({"teamId": 100, "lane": lane, "x": point_along_path(path, travel)[0], "y": point_along_path(path, travel)[1], "spawnSecond": spawn_second, "estimated": True})
        reversed_path = list(reversed(path))
        red_position = point_along_path(reversed_path, travel)
        output.append({"teamId": 200, "lane": lane, "x": red_position[0], "y": red_position[1], "spawnSecond": spawn_second, "estimated": True})
    return output


def replay_event_lines(frame: dict, players: list[dict]) -> list[str]:
    champions = {player.get("participantId"): player.get("champion", "未知") for player in players}

    def champion(participant_id) -> str:
        return champions.get(participant_id, f"玩家 {participant_id}")

    lines = []
    for event in frame.get("events", []):
        event_type = event.get("type")
        if event_type == "CHAMPION_KILL":
            assists = [champion(pid) for pid in event.get("assistingParticipantIds", [])]
            suffix = f"（助攻：{'、'.join(assists)}）" if assists else ""
            lines.append(f"击杀：{champion(event.get('killerId'))} → {champion(event.get('victimId'))}{suffix}")
        elif event_type == "ELITE_MONSTER_KILL":
            monster_key = event.get("monsterSubType") or event.get("monsterType") or "史诗野怪"
            monster = DRAGON_NAMES.get(monster_key, monster_key)
            lines.append(f"资源：{champion(event.get('killerId'))} 击杀 {monster}")
        elif event_type == "DRAGON_SOUL_GIVEN" and event.get("teamId") in {100, 200}:
            team_name = "蓝方" if event.get("teamId") == 100 else "红方"
            soul = DRAGON_NAMES.get(event.get("name"), event.get("name") or "龙魂")
            lines.append(f"龙魂：{team_name} 获得 {soul}")
        elif event_type == "BUILDING_KILL":
            building = event.get("towerType") or event.get("buildingType") or "防御建筑"
            lane = event.get("laneType") or ""
            lines.append(f"推塔：{champion(event.get('killerId'))} · {lane} {building}".strip())
        elif event_type == "WARD_PLACED":
            lines.append(f"视野：{champion(event.get('creatorId'))} 放置 {event.get('wardType') or '守卫'}")
        elif event_type == "WARD_KILL":
            lines.append(f"排眼：{champion(event.get('killerId'))} 清除 {event.get('wardType') or '守卫'}")
    return lines


def format_clock(seconds) -> str:
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        total = 0
    return f"{total // 60:02d}:{total % 60:02d}"


def timeline_second_at_x(x: float, width: float, total_seconds: int, slider_length: int = 22) -> int:
    usable = max(1.0, float(width) - slider_length)
    ratio = (float(x) - slider_length / 2) / usable
    return round(min(1.0, max(0.0, ratio)) * max(0, int(total_seconds)))


def replay_events(replay: dict) -> list[dict]:
    return sorted(
        (event for frame in replay.get("frames", []) for event in frame.get("events", [])),
        key=lambda event: int(number(event.get("timestamp")) or 0),
    )


def objective_snapshot(replay: dict, second: int) -> dict:
    """Return objective totals and map markers through an exact event timestamp."""
    cutoff_ms = max(0, int(second)) * 1000
    teams = {
        100: {"towers": 0, "inhibitors": 0, "dragons": [], "elders": 0, "barons": 0, "heralds": 0, "grubs": 0, "soul": None},
        200: {"towers": 0, "inhibitors": 0, "dragons": [], "elders": 0, "barons": 0, "heralds": 0, "grubs": 0, "soul": None},
    }
    markers = []
    soul_type = None
    for event in replay_events(replay):
        timestamp = int(number(event.get("timestamp")) or 0)
        if timestamp > cutoff_ms:
            break
        event_type = event.get("type")
        if event_type == "BUILDING_KILL":
            destroyed_team = int(number(event.get("teamId")) or 0)
            scoring_team = 300 - destroyed_team if destroyed_team in {100, 200} else 0
            building = event.get("buildingType")
            if scoring_team in teams:
                if building == "TOWER_BUILDING":
                    teams[scoring_team]["towers"] += 1
                elif building == "INHIBITOR_BUILDING":
                    teams[scoring_team]["inhibitors"] += 1
            markers.append({**event, "kind": "inhibitor" if building == "INHIBITOR_BUILDING" else "tower", "scoringTeam": scoring_team})
        elif event_type == "ELITE_MONSTER_KILL":
            scoring_team = int(number(event.get("killerTeamId")) or 0)
            if scoring_team not in teams:
                continue
            monster = event.get("monsterType")
            subtype = event.get("monsterSubType")
            if monster == "DRAGON":
                if subtype == "ELDER_DRAGON":
                    teams[scoring_team]["elders"] += 1
                else:
                    teams[scoring_team]["dragons"].append(DRAGON_NAMES.get(subtype, subtype or "龙"))
            elif monster == "BARON_NASHOR":
                teams[scoring_team]["barons"] += 1
            elif monster == "RIFTHERALD":
                teams[scoring_team]["heralds"] += 1
            elif monster == "HORDE":
                teams[scoring_team]["grubs"] += 1
            markers.append({**event, "kind": "monster", "scoringTeam": scoring_team})
        elif event_type == "DRAGON_SOUL_GIVEN":
            team_id = int(number(event.get("teamId")) or 0)
            soul = DRAGON_NAMES.get(event.get("name"), event.get("name") or "龙魂")
            if team_id in teams:
                teams[team_id]["soul"] = soul
                markers.append({**event, "kind": "soul", "scoringTeam": team_id, "position": {"x": 9850, "y": 4400}})
            elif team_id == 0:
                soul_type = soul
    return {"teams": teams, "markers": markers, "soulType": soul_type}


def tab_snapshot(replay: dict, second: int) -> dict[int, dict]:
    """Rebuild current K/D/A and inventory from exact timestamped events."""
    cutoff_ms = max(0, int(second)) * 1000
    state = {
        int(player.get("participantId")): {"kills": 0, "deaths": 0, "assists": 0, "items": []}
        for player in replay.get("players", []) if player.get("participantId")
    }

    def remove_item(participant_state: dict, item_id) -> None:
        item_id = int(number(item_id) or 0)
        if item_id in participant_state["items"]:
            participant_state["items"].remove(item_id)

    for event in replay_events(replay):
        if int(number(event.get("timestamp")) or 0) > cutoff_ms:
            break
        event_type = event.get("type")
        if event_type == "CHAMPION_KILL":
            killer_id = int(number(event.get("killerId")) or 0)
            victim_id = int(number(event.get("victimId")) or 0)
            if killer_id in state:
                state[killer_id]["kills"] += 1
            if victim_id in state:
                state[victim_id]["deaths"] += 1
            for participant_id in event.get("assistingParticipantIds", []):
                participant_id = int(number(participant_id) or 0)
                if participant_id in state:
                    state[participant_id]["assists"] += 1
        elif event_type in {"ITEM_PURCHASED", "ITEM_SOLD", "ITEM_DESTROYED", "ITEM_UNDO"}:
            participant_id = int(number(event.get("participantId")) or 0)
            participant_state = state.get(participant_id)
            if not participant_state:
                continue
            if event_type == "ITEM_PURCHASED":
                item_id = int(number(event.get("itemId")) or 0)
                if item_id:
                    participant_state["items"].append(item_id)
            elif event_type in {"ITEM_SOLD", "ITEM_DESTROYED"}:
                remove_item(participant_state, event.get("itemId"))
            else:
                remove_item(participant_state, event.get("beforeId"))
                after_id = int(number(event.get("afterId")) or 0)
                if after_id:
                    participant_state["items"].append(after_id)
    return state


class ComparatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1500x900")
        self.minsize(1120, 680)
        self.configure(bg="#070b0f")
        self.data_dir = app_data_dir()
        self.key_path = self.data_dir / "riot_api_key.txt"
        self.case_path = self.data_dir / "player_case.json"
        self.settings = load_settings(resource_path("config/model-parameters.json"))
        self.baseline_payload = json.loads(resource_path("desktop/all-champion-baselines.json").read_text(encoding="utf-8"))
        self.baselines = self.baseline_payload.get("profiles", {})
        item_payload = json.loads(resource_path("assets/item-data.json").read_text(encoding="utf-8"))
        self.item_entries = {int(item_id): item for item_id, item in item_payload.get("data", {}).items()}
        self.item_names = {
            int(item_id): item.get("name") or str(item_id)
            for item_id, item in item_payload.get("data", {}).items()
        }
        spell_payload = json.loads(resource_path("assets/summoner-spells.json").read_text(encoding="utf-8"))
        self.spell_entries = {
            int(spell.get("key")): spell for spell in spell_payload.get("data", {}).values()
            if str(spell.get("key") or "").isdigit()
        }
        champion_manifest = resource_path(f"assets/ddragon/{DDRAGON_VERSION}/champion.json")
        champion_payload = json.loads(champion_manifest.read_text(encoding="utf-8")) if champion_manifest.exists() else {"data": {}}
        self.champion_files = {
            str(champion.get("id") or "").lower(): champion.get("image", {}).get("full")
            for champion in champion_payload.get("data", {}).values()
        }
        self.icon_cache = {}
        self.sprite_cache = {}
        self.tooltip_window = None
        replay_path = resource_path("desktop/bootstrap-replays.json")
        self.bootstrap_replays = json.loads(replay_path.read_text(encoding="utf-8")) if replay_path.exists() else {}
        self.case = self._load_case()
        self.refreshing = False
        self.replay_data = None
        self.replay_playing = False
        self.replay_job = None
        self.replay_second = tk.IntVar(value=0)
        self.selected_phase = tk.StringVar(value="EARLY")
        self.riot_id = tk.StringVar(value=self.case.get("meta", {}).get("riotId", "Geolonwe#OC"))
        self.api_key = tk.StringVar()
        self.auto_refresh = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value="程序已就绪")
        self._configure_style()
        self._build_ui()
        self._populate_matches()
        self.after(5000, self._auto_tick)

    def _load_case(self) -> dict:
        if self.case_path.exists():
            try:
                return json.loads(self.case_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return load_bootstrap_case(resource_path("assets/player-case.js"))

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#070b0f")
        style.configure("Panel.TFrame", background="#0c1319")
        style.configure("TLabel", background="#070b0f", foreground="#dbe8ed", font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", foreground="#e9bd59", font=("Microsoft YaHei UI", 21, "bold"))
        style.configure("Muted.TLabel", foreground="#78909a", font=("Microsoft YaHei UI", 9))
        style.configure("Card.TLabel", background="#0c1319", foreground="#e9bd59", font=("Microsoft YaHei UI", 15, "bold"))
        style.configure("TButton", background="#17242c", foreground="#dbe8ed", borderwidth=0, padding=(14, 9), font=("Microsoft YaHei UI", 10, "bold"))
        style.map("TButton", background=[("active", "#203740")], foreground=[("active", "#6de1dc")])
        style.configure("Accent.TButton", background="#c69438", foreground="#071015")
        style.map("Accent.TButton", background=[("active", "#e9bd59")])
        style.configure("Timeline.TButton", background="#17242c", foreground="#dbe8ed", padding=(9, 6), font=("Microsoft YaHei UI", 9, "bold"))
        style.map("Timeline.TButton", background=[("active", "#203740")], foreground=[("active", "#6de1dc")])
        style.configure("TRadiobutton", background="#0c1319", foreground="#a9bbc2", padding=(10, 7), font=("Microsoft YaHei UI", 10, "bold"))
        style.map("TRadiobutton", foreground=[("selected", "#6de1dc")], background=[("selected", "#13252b")])
        style.configure("Treeview", background="#0b1217", fieldbackground="#0b1217", foreground="#d7e4e9", borderwidth=0, rowheight=31, font=("Microsoft YaHei UI", 9))
        style.map("Treeview", background=[("selected", "#18313a")], foreground=[("selected", "#f6d27b")])
        style.configure("Treeview.Heading", background="#111d23", foreground="#91a8b1", relief="flat", font=("Microsoft YaHei UI", 9, "bold"), padding=(6, 9))
        style.map("Treeview.Heading", background=[("active", "#182a32")])
        style.configure("Score.Treeview", background="#0b1217", fieldbackground="#0b1217", foreground="#d7e4e9", borderwidth=0, rowheight=18, font=("Microsoft YaHei UI", 8))
        style.map("Score.Treeview", background=[("selected", "#18313a")], foreground=[("selected", "#f6d27b")])
        style.configure("Score.Treeview.Heading", background="#111d23", foreground="#91a8b1", relief="flat", font=("Microsoft YaHei UI", 8, "bold"), padding=(3, 2))
        style.configure("TEntry", fieldbackground="#111b21", foreground="#e4edf0", insertcolor="#6de1dc", borderwidth=1, padding=8)
        style.configure("TCheckbutton", background="#070b0f", foreground="#9db0b8", font=("Microsoft YaHei UI", 9))
        style.configure("TNotebook", background="#0c1319", borderwidth=0)
        style.configure("TNotebook.Tab", background="#111d23", foreground="#93a8b0", padding=(16, 8), font=("Microsoft YaHei UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#18313a")], foreground=[("selected", "#e9bd59")])

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(22, 16))
        header.pack(fill="x")
        title_box = ttk.Frame(header)
        title_box.pack(side="left")
        ttk.Label(title_box, text="峡谷天平", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="D4+ 赛后逐局对比 · Python 桌面版", style="Muted.TLabel").pack(anchor="w")

        controls = ttk.Frame(header)
        controls.pack(side="right", fill="x")
        ttk.Label(controls, text="Riot ID").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(controls, textvariable=self.riot_id, width=25).grid(row=1, column=0, padx=(0, 10))
        ttk.Label(controls, text="API Key（可随时粘贴新值）").grid(row=0, column=1, sticky="w", padx=(0, 6))
        ttk.Entry(controls, textvariable=self.api_key, show="●", width=31).grid(row=1, column=1, padx=(0, 10))
        ttk.Button(controls, text="仅保存 Key", command=self._save_key).grid(row=1, column=2, padx=(0, 8))
        ttk.Button(controls, text="应用输入并刷新", style="Accent.TButton", command=self.refresh_player).grid(row=1, column=3)

        cards = ttk.Frame(self, padding=(22, 0, 22, 14))
        cards.pack(fill="x")
        meta = self.case.get("meta", {})
        card_values = [
            ("D4+ 玩家单局", f"{self.baseline_payload.get('meta', {}).get('sourceRows', 0):,}"),
            ("英雄阶段基准", f"{self.baseline_payload.get('meta', {}).get('profileCount', 0):,}"),
            ("当前玩家比赛", str(meta.get("rankedSoloMatches", 0))),
            ("自动检查", "每 1 分钟"),
        ]
        for index, (label, value) in enumerate(card_values):
            card = ttk.Frame(cards, style="Panel.TFrame", padding=(15, 10))
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0))
            cards.columnconfigure(index, weight=1)
            ttk.Label(card, text=label, style="Muted.TLabel", background="#0c1319").pack(anchor="w")
            ttk.Label(card, text=value, style="Card.TLabel").pack(anchor="w")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=22, pady=(0, 10))
        left = ttk.Frame(body, style="Panel.TFrame", padding=10)
        right = ttk.Frame(body, style="Panel.TFrame", padding=10)
        body.add(left, weight=1)
        body.add(right, weight=4)

        ttk.Label(left, text="最近单双排", background="#0c1319", foreground="#e9bd59", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        self.match_tree = ttk.Treeview(left, columns=("result", "matchup", "duration"), show="headings", selectmode="browse")
        self.match_tree.heading("result", text="结果")
        self.match_tree.heading("matchup", text="你 vs 对位")
        self.match_tree.heading("duration", text="时长")
        self.match_tree.column("result", width=48, anchor="center", stretch=False)
        self.match_tree.column("matchup", width=210, anchor="w")
        self.match_tree.column("duration", width=60, anchor="center", stretch=False)
        left_scroll = ttk.Scrollbar(left, orient="vertical", command=self.match_tree.yview)
        self.match_tree.configure(yscrollcommand=left_scroll.set)
        self.match_tree.pack(side="left", fill="both", expand=True)
        left_scroll.pack(side="right", fill="y")
        self.match_tree.bind("<<TreeviewSelect>>", self._on_match_selected)

        top_line = ttk.Frame(right, style="Panel.TFrame")
        top_line.pack(fill="x", pady=(0, 8))
        self.match_title = ttk.Label(top_line, text="请选择比赛", background="#0c1319", foreground="#e9bd59", font=("Microsoft YaHei UI", 13, "bold"))
        self.match_title.pack(side="left")
        phase_box = ttk.Frame(top_line, style="Panel.TFrame")
        phase_box.pack(side="right")
        for phase in ("EARLY", "MID", "LATE"):
            ttk.Radiobutton(phase_box, text=PHASE_NAMES[phase], value=phase, variable=self.selected_phase, command=self._render_comparison).pack(side="left")

        self.explanation = ttk.Label(
            right,
            text="正负号只表示数值方向，不自动判断好坏。双方基准分别按各自英雄＋位置匹配。",
            style="Muted.TLabel",
            background="#0c1319",
        )
        self.explanation.pack(anchor="w", pady=(0, 8))

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        compare_tab = ttk.Frame(self.notebook, style="Panel.TFrame")
        replay_tab = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.notebook.add(compare_tab, text="数据对比")
        self.notebook.add(replay_tab, text="整场小地图")

        columns = ("metric", "player", "opponent", "player_base", "opponent_base", "head_gap", "player_gap", "opponent_gap", "player_pct", "opponent_pct")
        self.comparison_tree = ttk.Treeview(compare_tab, columns=columns, show="headings")
        headings = {
            "metric": "指标", "player": "你本局", "opponent": "对手本局", "player_base": "你英雄基准",
            "opponent_base": "对手英雄基准", "head_gap": "你−对手", "player_gap": "你−基准",
            "opponent_gap": "对手−基准", "player_pct": "你分位", "opponent_pct": "对手分位",
        }
        widths = {"metric": 190, "player": 82, "opponent": 82, "player_base": 125, "opponent_base": 125, "head_gap": 90, "player_gap": 90, "opponent_gap": 100, "player_pct": 65, "opponent_pct": 70}
        for column in columns:
            self.comparison_tree.heading(column, text=headings[column])
            self.comparison_tree.column(column, width=widths[column], anchor="w" if column == "metric" else "center", stretch=column in {"metric", "player_base", "opponent_base"})
        right_vscroll = ttk.Scrollbar(compare_tab, orient="vertical", command=self.comparison_tree.yview)
        right_hscroll = ttk.Scrollbar(compare_tab, orient="horizontal", command=self.comparison_tree.xview)
        self.comparison_tree.configure(yscrollcommand=right_vscroll.set, xscrollcommand=right_hscroll.set)
        compare_tab.columnconfigure(0, weight=1)
        compare_tab.rowconfigure(0, weight=1)
        self.comparison_tree.grid(row=0, column=0, sticky="nsew")
        right_vscroll.grid(row=0, column=1, sticky="ns")
        right_hscroll.grid(row=1, column=0, sticky="ew")

        timeline = ttk.Frame(replay_tab, style="Panel.TFrame", padding=(10, 7, 10, 5))
        timeline.pack(fill="x")
        timeline.columnconfigure(1, weight=1)
        ttk.Label(
            timeline, text="复盘时间线（拖动滑块即可跳转）", background="#0c1319",
            foreground="#e9bd59", font=("Microsoft YaHei UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.timeline_value_text = tk.StringVar(value="00:00 / --:--")
        ttk.Label(
            timeline, textvariable=self.timeline_value_text, background="#0c1319",
            foreground="#6de1dc", font=("Consolas", 11, "bold"),
        ).grid(row=0, column=1, sticky="e", pady=(0, 2))

        jump_buttons = ttk.Frame(timeline, style="Panel.TFrame")
        jump_buttons.grid(row=1, column=0, sticky="w", padx=(0, 10))
        ttk.Button(jump_buttons, text="|◀", width=4, style="Timeline.TButton", command=lambda: self._jump_replay_edge(False)).pack(side="left", padx=(0, 4))
        ttk.Button(jump_buttons, text="−60s", width=5, style="Timeline.TButton", command=lambda: self._jump_replay(-60)).pack(side="left", padx=(0, 4))
        ttk.Button(jump_buttons, text="−10s", width=5, style="Timeline.TButton", command=lambda: self._jump_replay(-10)).pack(side="left", padx=(0, 4))
        self.replay_button = ttk.Button(jump_buttons, text="播放", width=6, style="Timeline.TButton", command=self._toggle_replay)
        self.replay_button.pack(side="left", padx=(0, 4))
        ttk.Button(jump_buttons, text="+10s", width=5, style="Timeline.TButton", command=lambda: self._jump_replay(10)).pack(side="left", padx=(0, 4))
        ttk.Button(jump_buttons, text="+60s", width=5, style="Timeline.TButton", command=lambda: self._jump_replay(60)).pack(side="left", padx=(0, 4))
        ttk.Button(jump_buttons, text="▶|", width=4, style="Timeline.TButton", command=lambda: self._jump_replay_edge(True)).pack(side="left")

        self.replay_scale = tk.Scale(
            timeline, orient="horizontal", variable=self.replay_second, command=self._seek_replay,
            from_=0, to=1, resolution=1, showvalue=False,
            bg="#0c1319", fg="#8fa6af", troughcolor="#203740", activebackground="#e9bd59",
            highlightthickness=0, bd=0, sliderlength=22, width=13, font=("Microsoft YaHei UI", 8),
        )
        self.replay_scale.grid(row=1, column=1, sticky="ew")
        self.replay_scale.bind("<ButtonPress-1>", self._timeline_pointer)
        self.replay_scale.bind("<B1-Motion>", self._timeline_pointer)
        timeline_ticks = ttk.Frame(timeline, style="Panel.TFrame")
        timeline_ticks.grid(row=2, column=1, sticky="ew", padx=(7, 7))
        self.timeline_tick_texts = [tk.StringVar(value="--:--") for _ in range(5)]
        for index, tick_text in enumerate(self.timeline_tick_texts):
            timeline_ticks.columnconfigure(index, weight=1)
            ttk.Label(
                timeline_ticks, textvariable=tick_text, style="Muted.TLabel", background="#0c1319",
            ).grid(row=0, column=index, sticky="w" if index == 0 else "e" if index == 4 else "")

        replay_body = ttk.Frame(replay_tab, style="Panel.TFrame", padding=(8, 3, 8, 4))
        replay_body.pack(fill="x")
        replay_body.columnconfigure(1, weight=1)
        self.map_source_photo = tk.PhotoImage(file=str(resource_path("assets/map11.png")))
        self.map_photo = self.map_source_photo.zoom(3, 3).subsample(5, 5)
        self.map_width = self.map_photo.width()
        self.map_height = self.map_photo.height()
        self.map_canvas = tk.Canvas(
            replay_body, width=self.map_width, height=self.map_height, bg="#05090c",
            highlightthickness=1, highlightbackground="#29404a",
        )
        self.map_canvas.grid(row=0, column=0, sticky="nw", padx=(0, 14))
        self.map_canvas.create_image(0, 0, image=self.map_photo, anchor="nw", tags=("map",))

        replay_side = ttk.Frame(replay_body, style="Panel.TFrame")
        replay_side.grid(row=0, column=1, sticky="nsew")
        replay_side.columnconfigure(0, weight=1)
        replay_side.rowconfigure(7, weight=1)
        self.replay_time_text = tk.StringVar(value="请选择一场比赛")
        ttk.Label(
            replay_side, textvariable=self.replay_time_text, background="#0c1319",
            foreground="#e9bd59", font=("Microsoft YaHei UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(
            replay_side, text="人物坐标约每 60 秒采样；目标事件按毫秒；三路兵线为规则推算（API 不提供小兵坐标）",
            style="Muted.TLabel", background="#0c1319",
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))

        ttk.Label(replay_side, text="关键目标状态", background="#0c1319", foreground="#e9bd59", font=("Microsoft YaHei UI", 10, "bold")).grid(row=2, column=0, sticky="w")
        self.objective_canvas = tk.Canvas(replay_side, height=78, bg="#0c1319", highlightthickness=0, bd=0)
        self.objective_canvas.grid(row=3, column=0, rowspan=3, sticky="ew", pady=(2, 5))

        ttk.Label(replay_side, text="最近 30 秒关键事件", style="Muted.TLabel", background="#0c1319").grid(row=6, column=0, sticky="nw", pady=(0, 4))
        self.event_canvas = tk.Canvas(replay_side, height=92, bg="#081015", highlightthickness=0, bd=0)
        self.event_canvas.grid(row=7, column=0, sticky="nsew")

        scoreboard = ttk.Frame(replay_tab, style="Panel.TFrame", padding=(8, 2, 8, 5))
        scoreboard.pack(fill="both", expand=True)
        scoreboard.columnconfigure(0, weight=1)
        scoreboard.columnconfigure(1, weight=1)
        ttk.Label(
            scoreboard, text="TAB 对局面板 · 当前时刻", background="#0c1319", foreground="#e9bd59",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 3))
        self.scoreboard_canvases = {}
        for column_index, (team_id, team_name, color) in enumerate(((100, "蓝方", "#63dcff"), (200, "红方", "#ff8577"))):
            panel = ttk.Frame(scoreboard, style="Panel.TFrame")
            panel.grid(row=1, column=column_index, sticky="nsew", padx=(0, 5) if column_index == 0 else (5, 0))
            canvas = tk.Canvas(panel, height=104, bg="#091116", highlightthickness=1, highlightbackground=color, bd=0)
            canvas.pack(fill="both", expand=True)
            self.scoreboard_canvases[team_id] = canvas

        footer = ttk.Frame(self, padding=(22, 6, 22, 12))
        footer.pack(fill="x")
        ttk.Checkbutton(footer, text="每 1 分钟自动检查新比赛", variable=self.auto_refresh).pack(side="left")
        ttk.Label(footer, text=" · 对局进行中无法读取实时坐标", style="Muted.TLabel").pack(side="left")
        ttk.Label(footer, textvariable=self.status_text, style="Muted.TLabel").pack(side="right")

    def _fit_photo(self, photo: tk.PhotoImage, target: int) -> tk.PhotoImage:
        factor = max(1, round(max(photo.width(), photo.height()) / max(1, target)))
        return photo.subsample(factor, factor)

    def _champion_icon(self, champion: str, target: int = 18) -> tk.PhotoImage | None:
        cache_key = ("champion", champion, target)
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        filename = self.champion_files.get(str(champion or "").lower()) or f"{champion}.png"
        candidates = [
            resource_path(f"assets/ddragon/{DDRAGON_VERSION}/champion/{filename}"),
            resource_path(f"assets/champions/{filename}"),
        ]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if not path:
            self.icon_cache[cache_key] = None
            return None
        icon = self._fit_photo(tk.PhotoImage(file=str(path)), target)
        self.icon_cache[cache_key] = icon
        return icon

    def _sprite_icon(self, category: str, entry: dict | None, target: int) -> tk.PhotoImage | None:
        image = (entry or {}).get("image", {})
        sprite = image.get("sprite")
        if not sprite:
            return None
        cache_key = (category, image.get("full"), target)
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        sprite_path = resource_path(f"assets/ddragon/{DDRAGON_VERSION}/sprite/{sprite}")
        if not sprite_path.exists():
            self.icon_cache[cache_key] = None
            return None
        if sprite not in self.sprite_cache:
            self.sprite_cache[sprite] = tk.PhotoImage(file=str(sprite_path))
        source = self.sprite_cache[sprite]
        width = int(image.get("w") or 48)
        height = int(image.get("h") or 48)
        cropped = tk.PhotoImage(width=width, height=height)
        cropped.tk.call(
            str(cropped), "copy", str(source), "-from",
            int(image.get("x") or 0), int(image.get("y") or 0),
            int(image.get("x") or 0) + width, int(image.get("y") or 0) + height,
            "-to", 0, 0,
        )
        icon = self._fit_photo(cropped, target)
        self.icon_cache[cache_key] = icon
        return icon

    def _item_icon(self, item_id: int, target: int = 16) -> tk.PhotoImage | None:
        return self._sprite_icon("item", self.item_entries.get(int(item_id)), target)

    def _spell_icon(self, spell_id, target: int = 9) -> tk.PhotoImage | None:
        return self._sprite_icon("spell", self.spell_entries.get(int(number(spell_id) or 0)), target)

    def _show_tooltip(self, event, text: str) -> None:
        self._hide_tooltip()
        if not text:
            return
        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        tk.Label(
            tip, text=text, bg="#111d23", fg="#e4edf0", relief="solid", borderwidth=1,
            font=("Microsoft YaHei UI", 9), padx=7, pady=4,
        ).pack()
        self.tooltip_window = tip

    def _hide_tooltip(self, _event=None) -> None:
        if self.tooltip_window is not None:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def _bind_tooltip(self, canvas: tk.Canvas, item_or_tag, text: str) -> None:
        canvas.tag_bind(item_or_tag, "<Enter>", lambda event, value=text: self._show_tooltip(event, value))
        canvas.tag_bind(item_or_tag, "<Leave>", self._hide_tooltip)

    def _draw_objective_icon(self, canvas: tk.Canvas, x: float, y: float, kind: str, color: str, size: int = 8, tooltip: str = "") -> None:
        tag = f"objective_{id(canvas)}_{len(canvas.find_all())}_{kind}"
        if kind == "tower":
            canvas.create_polygon(x - size, y - size, x + size, y - size, x + size * 0.6, y - size * 0.4, x - size * 0.6, y - size * 0.4, fill=color, outline="#dce9ed", tags=(tag, "replay_marker"))
            canvas.create_rectangle(x - size * 0.55, y - size * 0.4, x + size * 0.55, y + size, fill="#0a1217", outline=color, width=2, tags=(tag, "replay_marker"))
        elif kind == "inhibitor":
            canvas.create_polygon(x, y - size, x + size, y, x, y + size, x - size, y, fill="#0a1217", outline=color, width=2, tags=(tag, "replay_marker"))
            canvas.create_oval(x - size * 0.35, y - size * 0.35, x + size * 0.35, y + size * 0.35, fill=color, outline="", tags=(tag, "replay_marker"))
        elif kind == "dragon":
            canvas.create_polygon(x - size, y, x - size * 0.2, y - size * 0.75, x, y - size * 0.15, x + size * 0.2, y - size * 0.75, x + size, y, x, y + size, fill=color, outline="#f5d37f", tags=(tag, "replay_marker"))
        elif kind == "soul":
            canvas.create_oval(x - size, y - size, x + size, y + size, outline=color, width=3, tags=(tag, "replay_marker"))
            canvas.create_oval(x - size * 0.35, y - size * 0.35, x + size * 0.35, y + size * 0.35, fill=color, outline="", tags=(tag, "replay_marker"))
        elif kind == "baron":
            canvas.create_oval(x - size, y - size * 0.65, x + size, y + size * 0.65, fill="#271b35", outline=color, width=2, tags=(tag, "replay_marker"))
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#f5d37f", outline="", tags=(tag, "replay_marker"))
        elif kind == "herald":
            canvas.create_polygon(x, y - size, x + size, y - size * 0.2, x + size * 0.55, y + size, x - size * 0.55, y + size, x - size, y - size * 0.2, fill="#34244b", outline=color, width=2, tags=(tag, "replay_marker"))
        else:
            for offset_x, offset_y in ((-size * 0.55, 0), (0, -size * 0.35), (size * 0.55, 0)):
                canvas.create_oval(x + offset_x - 3, y + offset_y - 3, x + offset_x + 3, y + offset_y + 3, fill=color, outline="#dce9ed", tags=(tag, "replay_marker"))
        if tooltip:
            self._bind_tooltip(canvas, tag, tooltip)

    def _draw_minion_wave(self, canvas: tk.Canvas, x: float, y: float, team_id: int, lane: str, spawn_second: int) -> None:
        color = "#45c9ff" if team_id == 100 else "#ff675d"
        tag = f"wave_{team_id}_{lane}_{spawn_second}"
        for offset_x, offset_y in ((-4, 2), (0, -3), (4, 2)):
            canvas.create_oval(x + offset_x - 2, y + offset_y - 2, x + offset_x + 2, y + offset_y + 2, fill=color, outline="#e6f2f5", tags=(tag, "replay_marker"))
        lane_name = {"TOP": "上路", "MIDDLE": "中路", "BOTTOM": "下路"}.get(lane, lane)
        self._bind_tooltip(canvas, tag, f"{lane_name}推算兵线 · {format_clock(spawn_second)} 出生\nRiot API 不提供小兵实时坐标")

    def _draw_cs_icon(self, canvas: tk.Canvas, x: float, y: float, color: str) -> None:
        tag = f"cs_{id(canvas)}_{len(canvas.find_all())}"
        canvas.create_polygon(x - 6, y + 5, x - 5, y - 3, x, y - 7, x + 5, y - 3, x + 6, y + 5, fill="#17242c", outline=color, tags=(tag,))
        canvas.create_oval(x - 2, y - 1, x + 2, y + 3, fill=color, outline="", tags=(tag,))
        self._bind_tooltip(canvas, tag, "当前总补刀（线上小兵＋野怪）")

    def _render_objective_panel(self, objectives: dict) -> None:
        canvas = self.objective_canvas
        canvas.delete("all")
        for row_index, team_id in enumerate((100, 200)):
            team = objectives["teams"][team_id]
            color = "#45c9ff" if team_id == 100 else "#ff675d"
            y = 20 + row_index * 34
            canvas.create_rectangle(2, y - 11, 9, y + 11, fill=color, outline="")
            entries = [
                ("tower", team["towers"], "已摧毁防御塔"),
                ("inhibitor", team["inhibitors"], "已摧毁召唤水晶"),
                ("dragon", len(team["dragons"]), "小龙：" + (" / ".join(team["dragons"]) or "无")),
                ("soul", 1 if team["soul"] else 0, team["soul"] or f"龙魂属性：{objectives['soulType'] or '未确定'}"),
                ("baron", team["barons"], "纳什男爵"),
                ("herald", team["heralds"], "峡谷先锋"),
                ("grubs", team["grubs"], "虚空巢虫"),
            ]
            for index, (kind, count, tooltip) in enumerate(entries):
                x = 27 + index * 70
                self._draw_objective_icon(canvas, x, y, kind, color, size=8, tooltip=tooltip)
                canvas.create_text(x + 16, y, text=str(count), fill="#dce9ed", font=("Consolas", 10, "bold"), anchor="w")

    def _render_scoreboard(self, team_rows: dict[int, list[dict]]) -> None:
        for team_id, canvas in self.scoreboard_canvases.items():
            canvas.delete("all")
            color = "#45c9ff" if team_id == 100 else "#ff675d"
            for row_index, row in enumerate(team_rows.get(team_id, [])):
                y = 11 + row_index * 19
                canvas.create_rectangle(0, y - 9, max(520, canvas.winfo_width()), y + 9, fill="#0c161c" if row_index % 2 == 0 else "#091116", outline="")
                champion_icon = self._champion_icon(row["champion"], 18)
                if champion_icon:
                    image_id = canvas.create_image(13, y, image=champion_icon)
                    self._bind_tooltip(canvas, image_id, f"{row['champion']} · {POSITION_NAMES.get(row['position'], row['position'])}")
                for spell_index, spell_id in enumerate((row.get("summoner1Id"), row.get("summoner2Id"))):
                    spell_icon = self._spell_icon(spell_id, 9)
                    if spell_icon:
                        spell_entry = self.spell_entries.get(int(number(spell_id) or 0), {})
                        image_id = canvas.create_image(29, y - 5 + spell_index * 10, image=spell_icon)
                        self._bind_tooltip(canvas, image_id, spell_entry.get("name") or str(spell_id))
                canvas.create_oval(40, y - 7, 54, y + 7, fill="#17242c", outline=color)
                canvas.create_text(47, y, text=str(row["level"]), fill="#e6f2f5", font=("Consolas", 8, "bold"))
                canvas.create_text(67, y, text=row["kda"], fill="#dce9ed", font=("Consolas", 9, "bold"), anchor="w")
                self._draw_cs_icon(canvas, 145, y, color)
                canvas.create_text(157, y, text=str(row["cs"]), fill="#dce9ed", font=("Consolas", 9, "bold"), anchor="w")
                canvas.create_oval(196, y - 5, 206, y + 5, fill="#d7a93c", outline="#f5d37f")
                canvas.create_text(212, y, text=f"{row['gold']:,}", fill="#f5d37f", font=("Consolas", 9, "bold"), anchor="w")
                item_x = 270
                for slot in range(7):
                    canvas.create_rectangle(item_x + slot * 20 - 8, y - 8, item_x + slot * 20 + 8, y + 8, fill="#101a20", outline="#263941")
                for item_index, item_id in enumerate(row["items"][:7]):
                    item_icon = self._item_icon(item_id, 16)
                    if item_icon:
                        image_id = canvas.create_image(item_x + item_index * 20, y, image=item_icon)
                        self._bind_tooltip(canvas, image_id, self.item_names.get(item_id, str(item_id)))

    def _render_recent_events(self, events: list[dict], public_players: dict[int, dict]) -> None:
        canvas = self.event_canvas
        canvas.delete("all")
        if not events:
            canvas.create_line(15, 46, 95, 46, fill="#263941", width=2)
            canvas.create_oval(102, 41, 112, 51, outline="#526973", width=2)
            return

        def champion_icon(participant_id, x, y):
            player = public_players.get(int(number(participant_id) or 0), {})
            icon = self._champion_icon(player.get("champion"), 16)
            if icon:
                image_id = canvas.create_image(x, y, image=icon)
                self._bind_tooltip(canvas, image_id, player.get("champion") or "未知英雄")
            else:
                canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#526973", outline="#dce9ed")

        for row_index, event in enumerate(events[-4:]):
            y = 13 + row_index * 21
            canvas.create_text(7, y, text=format_clock(int(number(event.get("timestamp")) or 0) / 1000), fill="#78909a", font=("Consolas", 8), anchor="w")
            event_type = event.get("type")
            if event_type == "CHAMPION_KILL":
                champion_icon(event.get("killerId"), 60, y)
                canvas.create_line(72, y, 88, y, fill="#e98273", width=2, arrow="last")
                champion_icon(event.get("victimId"), 101, y)
                for assist_index, participant_id in enumerate(event.get("assistingParticipantIds", [])[:4]):
                    champion_icon(participant_id, 127 + assist_index * 18, y)
            elif event_type == "ELITE_MONSTER_KILL":
                champion_icon(event.get("killerId"), 60, y)
                canvas.create_line(72, y, 88, y, fill="#e9bd59", width=2, arrow="last")
                monster = event.get("monsterSubType") or event.get("monsterType")
                kind = "dragon" if event.get("monsterType") == "DRAGON" else "baron" if monster == "BARON_NASHOR" else "herald" if monster == "RIFTHERALD" else "grubs"
                self._draw_objective_icon(canvas, 102, y, kind, "#e9bd59", size=7, tooltip=DRAGON_NAMES.get(monster, monster or "史诗野怪"))
            elif event_type == "BUILDING_KILL":
                champion_icon(event.get("killerId"), 60, y)
                canvas.create_line(72, y, 88, y, fill="#e9bd59", width=2, arrow="last")
                kind = "inhibitor" if event.get("buildingType") == "INHIBITOR_BUILDING" else "tower"
                self._draw_objective_icon(canvas, 102, y, kind, "#e9bd59", size=7, tooltip="召唤水晶" if kind == "inhibitor" else "防御塔")
            elif event_type == "DRAGON_SOUL_GIVEN":
                team_id = int(number(event.get("teamId")) or 0)
                color = "#45c9ff" if team_id == 100 else "#ff675d"
                canvas.create_rectangle(52, y - 7, 67, y + 7, fill=color, outline="#dce9ed")
                canvas.create_line(72, y, 88, y, fill="#e9bd59", width=2, arrow="last")
                self._draw_objective_icon(canvas, 102, y, "soul", color, size=7, tooltip=DRAGON_NAMES.get(event.get("name"), event.get("name") or "龙魂"))

    def _populate_matches(self) -> None:
        for item in self.match_tree.get_children():
            self.match_tree.delete(item)
        for index, match in enumerate(self.case.get("matches", [])):
            result = "胜" if match.get("win") else "负"
            matchup = f"{match.get('champion', '—')} vs {match.get('opponentChampion') or '未知'}"
            duration = f"{number(match.get('durationMin')) or 0:.1f}m"
            self.match_tree.insert("", "end", iid=str(index), values=(result, matchup, duration), tags=("win" if match.get("win") else "loss",))
        self.match_tree.tag_configure("win", foreground="#68ddd5")
        self.match_tree.tag_configure("loss", foreground="#e98273")
        if self.match_tree.get_children():
            self.match_tree.selection_set(self.match_tree.get_children()[0])
            self.match_tree.focus(self.match_tree.get_children()[0])
            self._on_match_selected()

    def _selected_match(self) -> dict | None:
        selected = self.match_tree.selection()
        if not selected:
            return None
        try:
            return self.case.get("matches", [])[int(selected[0])]
        except (IndexError, ValueError):
            return None

    def _on_match_selected(self, _event=None) -> None:
        self._stop_replay()
        self._render_comparison()
        self._load_selected_replay()

    def _load_selected_replay(self) -> None:
        self.replay_data = None
        match = self._selected_match()
        if not match:
            self._render_replay_unavailable("请选择一场比赛")
            return
        replay_ref = match.get("replayRef")
        if replay_ref:
            replay_file = self.data_dir / "replays" / f"{Path(str(replay_ref)).name}.json"
            if replay_file.exists():
                try:
                    self.replay_data = json.loads(replay_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    self.replay_data = None
        if self.replay_data is None:
            self.replay_data = self.bootstrap_replays.get(match.get("matchRef"))
        if not self.replay_data or not self.replay_data.get("frames"):
            self.replay_scale.configure(to=1, state="disabled")
            self.replay_second.set(0)
            self._render_replay_unavailable("这场比赛还没有分钟复盘数据；使用 API 刷新后会自动生成")
            return
        final_second = self._replay_final_second()
        self.replay_scale.configure(to=final_second, state="normal")
        for variable, value in zip(self.timeline_tick_texts, (0, final_second * 0.25, final_second * 0.5, final_second * 0.75, final_second)):
            variable.set(format_clock(value))
        self.replay_second.set(0)
        self._render_replay(0)

    def _replay_final_second(self) -> int:
        if not self.replay_data:
            return 0
        duration = int(number(self.replay_data.get("durationSeconds")) or 0)
        if duration:
            return duration
        return max(0, len(self.replay_data.get("frames", [])) - 1) * 60

    def _render_replay_unavailable(self, message: str) -> None:
        self.map_canvas.delete("replay_marker")
        self.map_canvas.create_text(
            self.map_width / 2, self.map_height / 2, text=message, width=self.map_width * 0.7,
            fill="#e9bd59", font=("Microsoft YaHei UI", 12, "bold"), justify="center",
            tags=("replay_marker",),
        )
        self.replay_time_text.set(message)
        self.timeline_value_text.set("00:00 / --:--")
        for variable in self.timeline_tick_texts:
            variable.set("--:--")
        for canvas in self.scoreboard_canvases.values():
            canvas.delete("all")
        self.objective_canvas.delete("all")
        self._render_recent_events([], {})
        self.replay_button.configure(text="播放")

    def _render_replay(self, second: int) -> None:
        if not self.replay_data or not self.replay_data.get("frames"):
            return
        frames = self.replay_data["frames"]
        final_second = self._replay_final_second()
        current_second = min(max(0, int(second)), final_second)
        frame_index = min(current_second // 60, len(frames) - 1)
        frame = frames[frame_index]
        sample_second = int(number(frame.get("timestamp")) or frame_index * 60_000) // 1000
        self.replay_second.set(current_second)
        self.replay_time_text.set(f"当前 {format_clock(current_second)} · 人物坐标采样 {format_clock(sample_second)}")
        self.timeline_value_text.set(f"{format_clock(current_second)} / {format_clock(final_second)}")
        self.map_canvas.delete("replay_marker")
        public_players = {player.get("participantId"): player for player in self.replay_data.get("players", [])}
        objectives = objective_snapshot(self.replay_data, current_second)
        tab_state = tab_snapshot(self.replay_data, current_second)

        for marker in objectives["markers"]:
            location = map_coordinates(
                (marker.get("position") or {}).get("x"), (marker.get("position") or {}).get("y"),
                self.map_width, self.map_height,
            )
            if not location:
                continue
            x, y = location
            team_id = marker.get("scoringTeam")
            color = "#45c9ff" if team_id == 100 else "#ff675d"
            kind = marker.get("kind")
            if kind in {"tower", "inhibitor"}:
                target_name = "召唤水晶" if kind == "inhibitor" else "防御塔"
                self._draw_objective_icon(self.map_canvas, x, y, kind, color, size=7, tooltip=f"{format_clock(int(marker.get('timestamp', 0)) / 1000)} 摧毁{target_name}")
            elif kind == "soul" or current_second * 1000 - int(number(marker.get("timestamp")) or 0) <= 90_000:
                monster = marker.get("monsterSubType") or marker.get("monsterType") or "魂"
                icon_kind = "soul" if kind == "soul" else "dragon" if marker.get("monsterType") == "DRAGON" else "baron" if monster == "BARON_NASHOR" else "herald" if monster == "RIFTHERALD" else "grubs"
                objective_name = DRAGON_NAMES.get(monster, monster)
                self._draw_objective_icon(self.map_canvas, x, y, icon_kind, color, size=8, tooltip=f"{format_clock(int(marker.get('timestamp', 0)) / 1000)} · {objective_name}")

        for wave in estimated_minion_waves(current_second):
            location = map_coordinates(wave["x"], wave["y"], self.map_width, self.map_height)
            if location:
                self._draw_minion_wave(self.map_canvas, location[0], location[1], wave["teamId"], wave["lane"], wave["spawnSecond"])

        team_rows = {100: [], 200: []}
        for player_frame in sorted(frame.get("players", []), key=lambda item: int(item.get("participantId") or 0)):
            participant_id = int(number(player_frame.get("participantId")) or 0)
            player = public_players.get(participant_id, {})
            team_id = int(player.get("teamId") or 0)
            color = "#45c9ff" if team_id == 100 else "#ff675d"
            outline = "#d7f6ff" if team_id == 100 else "#ffe0dc"
            location = map_coordinates(player_frame.get("x"), player_frame.get("y"), self.map_width, self.map_height)
            if location:
                x, y = location
                champion_icon = self._champion_icon(player.get("champion"), 24)
                if champion_icon:
                    image_id = self.map_canvas.create_image(x, y, image=champion_icon, tags=("replay_marker",))
                    self.map_canvas.create_oval(x - 12, y - 12, x + 12, y + 12, outline=outline, width=2, tags=("replay_marker",))
                    self._bind_tooltip(self.map_canvas, image_id, f"{player.get('champion')} · {POSITION_NAMES.get(player.get('position'), player.get('position'))}")
                else:
                    self.map_canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, outline=outline, width=2, tags=("replay_marker",))
            lane_cs = int(number(player_frame.get("minions")) or 0)
            jungle_cs = int(number(player_frame.get("jungleMinions")) or 0)
            player_tab = tab_state.get(participant_id, {"kills": 0, "deaths": 0, "assists": 0, "items": []})
            if team_id not in team_rows:
                continue
            team_rows[team_id].append({
                "champion": player.get("champion") or "未知", "position": player.get("position") or "UNKNOWN",
                "summoner1Id": player.get("summoner1Id"), "summoner2Id": player.get("summoner2Id"),
                "level": int(number(player_frame.get("level")) or 0),
                "kda": f"{player_tab['kills']}/{player_tab['deaths']}/{player_tab['assists']}",
                "cs": lane_cs + jungle_cs, "gold": int(number(player_frame.get("totalGold")) or 0),
                "items": player_tab["items"],
            })

        self._render_scoreboard(team_rows)
        self._render_objective_panel(objectives)
        recent_events = [
            event for event in replay_events(self.replay_data)
            if max(0, current_second - 30) * 1000 <= int(number(event.get("timestamp")) or 0) <= current_second * 1000
            and event.get("type") in {"CHAMPION_KILL", "ELITE_MONSTER_KILL", "BUILDING_KILL", "DRAGON_SOUL_GIVEN"}
        ]
        self._render_recent_events(recent_events, public_players)

    def _seek_replay(self, value) -> None:
        if self.replay_data:
            self._render_replay(round(float(value)))

    def _timeline_pointer(self, event):
        if not self.replay_data:
            return "break"
        self._stop_replay()
        target_second = timeline_second_at_x(
            event.x, event.widget.winfo_width(), self._replay_final_second(),
        )
        self._render_replay(target_second)
        return "break"

    def _jump_replay(self, delta: int) -> None:
        if not self.replay_data:
            return
        self._stop_replay()
        self._render_replay(self.replay_second.get() + int(delta))

    def _jump_replay_edge(self, to_end: bool) -> None:
        if not self.replay_data:
            return
        self._stop_replay()
        final_second = self._replay_final_second()
        self._render_replay(final_second if to_end else 0)

    def _toggle_replay(self) -> None:
        if not self.replay_data:
            return
        if self.replay_playing:
            self._stop_replay()
            return
        final_second = self._replay_final_second()
        if self.replay_second.get() >= final_second:
            self._render_replay(0)
        self.replay_playing = True
        self.replay_button.configure(text="暂停")
        self.replay_job = self.after(250, self._advance_replay)

    def _advance_replay(self) -> None:
        self.replay_job = None
        if not self.replay_playing or not self.replay_data:
            return
        next_second = self.replay_second.get() + 5
        final_second = self._replay_final_second()
        if next_second > final_second:
            self._render_replay(final_second)
            self._stop_replay()
            return
        self._render_replay(next_second)
        self.replay_job = self.after(250, self._advance_replay)

    def _stop_replay(self) -> None:
        self.replay_playing = False
        if self.replay_job is not None:
            self.after_cancel(self.replay_job)
            self.replay_job = None
        if hasattr(self, "replay_button"):
            self.replay_button.configure(text="播放")

    def _render_comparison(self) -> None:
        for item in self.comparison_tree.get_children():
            self.comparison_tree.delete(item)
        match = self._selected_match()
        if not match:
            return
        phase = self.selected_phase.get()
        start_ms = int(match.get("gameStartMs") or 0)
        played = datetime.fromtimestamp(start_ms / 1000).strftime("%Y-%m-%d %H:%M") if start_ms else "未知时间"
        self.match_title.configure(text=f"{played} · {match.get('champion')} vs {match.get('opponentChampion') or '未知'} · {'胜' if match.get('win') else '负'} · {match.get('durationMin')} 分钟")
        if phase == "LATE" and (number(match.get("durationMin")) or 0) < 25:
            self.comparison_tree.insert("", "end", values=("该局未达到 25 分钟", "—", "—", "—", "—", "—", "—", "—", "—", "—"))
            return
        for row in comparison_rows(match, phase, self.baselines):
            self.comparison_tree.insert("", "end", values=row)

    def _saved_key(self) -> str:
        return self.key_path.read_text(encoding="ascii").strip() if self.key_path.exists() else ""

    def _save_key(self) -> bool:
        candidate = self.api_key.get().strip()
        if not candidate:
            if self._saved_key():
                self.status_text.set("本机已经保存了一个 API Key")
                return True
            messagebox.showwarning(APP_TITLE, "请输入以 RGAPI- 开头的 Riot Development API Key。")
            return False
        if not candidate.startswith("RGAPI-") or len(candidate) < 20:
            messagebox.showerror(APP_TITLE, "API Key 格式不正确。")
            return False
        self.key_path.write_text(candidate, encoding="ascii")
        self.api_key.set("")
        self.status_text.set("API Key 已只保存在本机应用数据目录")
        return True

    def refresh_player(self, silent: bool = False) -> None:
        if self.refreshing:
            return
        if self.api_key.get().strip() and not self._save_key():
            return
        key = self._saved_key()
        if not key:
            if not silent:
                messagebox.showwarning(APP_TITLE, "请先输入并保存 Riot API Key。")
            self.status_text.set("等待 Riot API Key")
            return
        try:
            game_name, tag_line = parse_riot_id(self.riot_id.get())
        except ValueError as exc:
            if not silent:
                messagebox.showerror(APP_TITLE, str(exc))
            return
        self.refreshing = True
        self.status_text.set("正在检查 Riot 最近比赛…")
        threading.Thread(target=self._refresh_worker, args=(key, game_name, tag_line, silent), daemon=True).start()

    def _refresh_worker(self, key: str, game_name: str, tag_line: str, silent: bool) -> None:
        try:
            platform = self.settings.get("collection", {}).get("platform", "oc1")
            matches = int(self.settings.get("player_case", {}).get("matches", 20))
            split_minute = int(self.settings["conditional_model"]["late_phase_start_minute"])
            client = RiotClient(key, platform, self.data_dir / "cache")
            account = client.account_by_riot_id(game_name, tag_line)
            requested_ids = client.match_ids(account["puuid"], matches)
            rows = []
            replays = {}
            for match_id in requested_ids:
                match_data = client.match(match_id)
                timeline_data = client.timeline(match_id)
                row = extract_player_match(
                    match_data, timeline_data, account["puuid"],
                    {"tier": "LOCAL_CASE", "rank": "", "leaguePoints": 0}, late_start_minute=split_minute,
                )
                if not row:
                    continue
                fights = number(row.get("late_teamfights")) or 0
                participations = number(row.get("late_teamfight_participations")) or 0
                row["late_teamfight_participation_rate"] = participations / fights if fights else None
                rows.append(row)
                replay = extract_match_replay(match_data, timeline_data)
                if replay:
                    replays[match_id] = replay
            payload = case_payload(
                rows,
                riot_id=f"{account.get('gameName', game_name)}#{account.get('tagLine', tag_line)}",
                platform=platform,
                requested_matches=len(requested_ids),
                conditional_parameters=self.settings["conditional_model"],
            )
            replay_dir = self.data_dir / "replays"
            replay_dir.mkdir(parents=True, exist_ok=True)
            for public_match, row in zip(payload.get("matches", []), rows):
                replay_ref = str(row.get("match_id") or "")
                if not replay_ref or replay_ref not in replays:
                    continue
                public_match["replayRef"] = replay_ref
                replay_file = replay_dir / f"{Path(replay_ref).name}.json"
                replay_next = replay_file.with_suffix(".next")
                replay_next.write_text(json.dumps(replays[replay_ref], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                os.replace(replay_next, replay_file)
            old_starts = {match.get("gameStartMs") for match in self.case.get("matches", [])}
            new_count = sum(match.get("gameStartMs") not in old_starts for match in payload.get("matches", []))
            temporary = self.case_path.with_suffix(".next")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, self.case_path)
            self.after(0, self._apply_refresh, payload, new_count)
        except Exception as exc:
            self.after(0, self._refresh_failed, str(exc), silent)

    def _apply_refresh(self, payload: dict, new_count: int) -> None:
        self.case = payload
        self.riot_id.set(payload.get("meta", {}).get("riotId", self.riot_id.get()))
        self.refreshing = False
        self._populate_matches()
        self.status_text.set(f"更新完成 · 新增 {new_count} 场 · {datetime.now().strftime('%H:%M:%S')}")

    def _refresh_failed(self, error: str, silent: bool) -> None:
        self.refreshing = False
        friendly = "Riot API Key 已失效，请粘贴新 Key" if "401" in error or "apikey" in error.lower() else f"更新失败：{error}"
        self.status_text.set(friendly)
        if not silent:
            messagebox.showerror(APP_TITLE, friendly)

    def _auto_tick(self) -> None:
        if self.auto_refresh.get() and not self.refreshing:
            self.refresh_player(silent=True)
        self.after(60_000, self._auto_tick)


def main() -> None:
    app = ComparatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
