"""Export one frozen, allowlisted replay and a 60-second animated data guide."""
import json
from pathlib import Path

from desktop.lol_high_rank_comparator import objective_loss_analysis, objective_loss_events
from tools.player_case_server import PLAYER_CASE_PREFIX, load_window_payload


def build():
    root = Path(__file__).resolve().parents[1]
    case = load_window_payload(root / "assets/player-case.js", PLAYER_CASE_PREFIX)
    replays = json.loads((root / "desktop/bootstrap-replays.json").read_text(encoding="utf-8"))
    selected = None
    for match in case["matches"]:
        replay = replays.get(match["matchRef"], {})
        for event in objective_loss_events(replay, match):
            analysis = objective_loss_analysis(replay, match, event)
            if analysis["primaryHypothesisId"]:
                selected = match, replay, analysis
                break
        if selected:
            break
    if selected is None:
        raise ValueError("No evidence-supported objective loss episode available")
    match, replay, analysis = selected
    pick = lambda row, keys: {key: row[key] for key in keys if key in row}
    demo = {
        "schemaVersion": 1,
        "match": pick(match, ("champion", "position", "opponentChampion", "durationMin", "win", "patch")),
        "focusId": analysis["focusId"],
        "focusTeam": analysis["focusTeam"],
        "players": [pick(player, ("participantId", "teamId", "champion", "position")) for player in replay["players"]],
        "frames": [
            {"timestamp": frame["timestamp"], "players": [pick(player, ("participantId", "x", "y", "level", "totalGold")) for player in frame.get("players", [])]}
            for frame in replay["frames"]
        ],
        "episode": pick(analysis, ("eventSecond", "windowStartSecond", "objectiveName", "position", "primaryHypothesisId", "facts", "hypotheses", "edges")),
        "sourceRows": case.get("diagnosis", {}).get("benchmarkMeta", {}).get("sourceRows"),
        "metrics": [
            {"label": finding["label"], "lowerIsBetter": finding["lowerIsBetter"], **pick(row, ("value", "baseline", "gap", "n", "weak"))}
            for finding in case.get("diagnosis", {}).get("findings", [])
            for row in finding["evidence"] if row["gameStartMs"] == match["gameStartMs"]
        ],
        "notes": "Frozen post-game sample. Coordinates are minute snapshots. Hypothesis confidence is a heuristic, not a calibrated probability.",
    }
    demo["episode"]["facts"] = [
        pick(fact, ("id", "type", "label", "source", "timestamp", "sampleTimestamp", "confidence"))
        for fact in analysis["facts"]
    ]
    output = root / "portfolio"
    output.mkdir(exist_ok=True)
    (output / "demo.json").write_text(json.dumps(demo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    animate(demo, output, root)
    print(f"Exported 1 anonymous match, {len(demo['frames'])} position snapshots, {len(demo['episode']['facts'])} evidence facts")


def animate(demo, output, root):
    from PIL import Image, ImageDraw
    background = Image.open(root / "assets/map11.png").convert("RGB").resize((480, 480))
    images = []
    end = demo["episode"]["eventSecond"]
    start = max(0, end - 120)
    for index in range(30):
        second = round(start + (end - start) * index / 29)
        frame = max((item for item in demo["frames"] if item["timestamp"] <= second * 1000), key=lambda item: item["timestamp"], default=demo["frames"][0])
        image = Image.new("RGB", (560, 600), "#09151e")
        image.paste(background, (40, 60))
        draw = ImageDraw.Draw(image)
        draw.text((20, 18), "RIFTSCALE | FROZEN REPLAY WALKTHROUGH", fill="#e9bd59")
        teams = {player["participantId"]: player["teamId"] for player in demo["players"]}
        for player in frame["players"]:
            if player.get("x") is None or player.get("y") is None:
                continue
            x, y = 40 + player["x"] / 15000 * 480, 540 - player["y"] / 15000 * 480
            color = "#67ded7" if teams[player["participantId"]] == demo["focusTeam"] else "#ef7b70"
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="white" if player["participantId"] == demo["focusId"] else color, width=2)
        position = demo["episode"].get("position")
        if position:
            x, y = 40 + position["x"] / 15000 * 480, 540 - position["y"] / 15000 * 480
            draw.ellipse((x - 15, y - 15, x + 15, y + 15), outline="#e9bd59", width=3)
        draw.text((20, 552), f"{second // 60:02}:{second % 60:02} | snapshot {frame['timestamp'] // 60000:02}:00 | objective {end // 60:02}:{end % 60:02}", fill="white")
        draw.text((20, 575), "Position samples, not live motion. Gold ring: objective area.", fill="#a0b4bf")
        images.append(image)
    images[0].save(output / "walkthrough.gif", save_all=True, append_images=images[1:], duration=2000, loop=0)
    images[-1].save(output / "replay-still.png")


if __name__ == "__main__":
    build()
