import unittest

from desktop.lol_high_rank_comparator import (
    approximate_percentile,
    comparison_rows,
    estimated_minion_waves,
    format_clock,
    map_coordinates,
    objective_snapshot,
    parse_riot_id,
    replay_event_lines,
    tab_snapshot,
    timeline_second_at_x,
)


class DesktopAppTests(unittest.TestCase):
    def test_parse_riot_id(self):
        self.assertEqual(parse_riot_id("Geolonwe#OC"), ("Geolonwe", "OC"))
        self.assertEqual(
            parse_riot_id("https://op.gg/lol/summoners/oce/Addy%20The%20Great-OC"),
            ("Addy The Great", "OC"),
        )

    def test_percentile_and_four_way_comparison(self):
        stats = {"p10": 10, "p25": 20, "median": 30, "p75": 40, "p90": 50}
        self.assertEqual(approximate_percentile(30, stats), 50)
        baselines = {
            "XinZhao|JUNGLE|EARLY": {"sampleSize": 100, "metrics": {"early_gold_15": stats}},
            "Vi|JUNGLE|EARLY": {"sampleSize": 80, "metrics": {"early_gold_15": {**stats, "median": 25}}},
        }
        match = {
            "champion": "XinZhao", "position": "JUNGLE",
            "opponentChampion": "Vi", "opponentPosition": "JUNGLE",
            "early_gold_15": 35, "opponent_early_gold_15": 20,
        }
        row = comparison_rows(match, "EARLY", baselines)[0]
        self.assertEqual(row[1], "35")
        self.assertEqual(row[2], "20")
        self.assertEqual(row[5], "+15")
        self.assertEqual(row[6], "+5")
        self.assertEqual(row[7], "-5")

    def test_map_coordinates_flip_vertical_axis(self):
        self.assertEqual(map_coordinates(0, 0, 600, 600), (0.0, 600.0))
        self.assertEqual(map_coordinates(15000, 15000, 600, 600), (600.0, 0.0))
        self.assertEqual(map_coordinates(7500, 7500, 600, 600), (300.0, 300.0))
        self.assertIsNone(map_coordinates(None, 100, 600, 600))

    def test_replay_event_lines_use_champion_names(self):
        players = [
            {"participantId": 1, "champion": "XinZhao"},
            {"participantId": 6, "champion": "Vi"},
            {"participantId": 2, "champion": "Ashe"},
        ]
        frame = {"events": [{
            "type": "CHAMPION_KILL", "killerId": 1, "victimId": 6,
            "assistingParticipantIds": [2],
        }]}
        self.assertEqual(replay_event_lines(frame, players), ["击杀：XinZhao → Vi（助攻：Ashe）"])

    def test_second_precision_objectives_and_tab_state(self):
        replay = {
            "players": [
                {"participantId": 1, "teamId": 100, "champion": "Ashe"},
                {"participantId": 6, "teamId": 200, "champion": "Vi"},
            ],
            "frames": [{"events": [
                {"type": "ITEM_PURCHASED", "timestamp": 1000, "participantId": 1, "itemId": 1055},
                {"type": "CHAMPION_KILL", "timestamp": 12_500, "killerId": 1, "victimId": 6},
                {"type": "BUILDING_KILL", "timestamp": 20_000, "teamId": 200, "buildingType": "TOWER_BUILDING", "position": {"x": 100, "y": 100}},
                {"type": "ELITE_MONSTER_KILL", "timestamp": 25_000, "killerTeamId": 100, "monsterType": "DRAGON", "monsterSubType": "FIRE_DRAGON"},
                {"type": "DRAGON_SOUL_GIVEN", "timestamp": 30_000, "teamId": 100, "name": "Infernal"},
                {"type": "ITEM_DESTROYED", "timestamp": 40_000, "participantId": 1, "itemId": 1055},
            ]}],
        }
        self.assertEqual(format_clock(125), "02:05")
        self.assertEqual(timeline_second_at_x(500, 1000, 1800), 900)
        self.assertEqual(timeline_second_at_x(0, 1000, 1800), 0)
        self.assertEqual(timeline_second_at_x(1000, 1000, 1800), 1800)
        at_35 = objective_snapshot(replay, 35)["teams"][100]
        self.assertEqual(at_35["towers"], 1)
        self.assertEqual(at_35["dragons"], ["火龙"])
        self.assertEqual(at_35["soul"], "火龙魂")
        self.assertEqual(tab_snapshot(replay, 35)[1]["items"], [1055])
        self.assertEqual(tab_snapshot(replay, 35)[1]["kills"], 1)
        self.assertEqual(tab_snapshot(replay, 35)[6]["deaths"], 1)
        self.assertEqual(tab_snapshot(replay, 45)[1]["items"], [])

    def test_minion_wave_estimate_uses_spawn_cadence(self):
        self.assertEqual(estimated_minion_waves(64), [])
        spawn = estimated_minion_waves(65)
        self.assertEqual(len(spawn), 6)
        self.assertTrue(all(wave["estimated"] for wave in spawn))
        self.assertTrue(all(wave["spawnSecond"] == 65 for wave in spawn))
        moved = estimated_minion_waves(75)
        blue_mid_spawn = next(wave for wave in spawn if wave["teamId"] == 100 and wave["lane"] == "MIDDLE")
        blue_mid_moved = next(wave for wave in moved if wave["teamId"] == 100 and wave["lane"] == "MIDDLE")
        self.assertGreater(blue_mid_moved["x"], blue_mid_spawn["x"])


if __name__ == "__main__":
    unittest.main()
