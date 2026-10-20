"""Contract checks for the public frozen example; no API calls."""
import json
import unittest
from pathlib import Path


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / "portfolio"
        self.demo = json.loads((self.root / "demo.json").read_text(encoding="utf-8"))

    def test_export_excludes_identifiers_and_credentials(self):
        forbidden = {"puuid", "summonerid", "riotid", "gamename", "tagline", "matchid", "matchref", "gamestartms", "apikey"}
        def check(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(key.lower(), forbidden)
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
            elif isinstance(value, str):
                self.assertNotIn("RGAPI-", value)
        check(self.demo)

    def test_evidence_and_benchmarks_are_inspectable(self):
        episode = self.demo["episode"]
        facts = {fact["id"] for fact in episode["facts"]}
        primary = next(item for item in episode["hypotheses"] if item["id"] == episode["primaryHypothesisId"])
        self.assertTrue(primary["evidenceIds"])
        self.assertTrue(set(primary["evidenceIds"]).issubset(facts))
        self.assertTrue(self.demo["metrics"])
        for metric in self.demo["metrics"]:
            self.assertGreaterEqual(metric["n"], 20)
            self.assertAlmostEqual(metric["gap"], metric["value"] - metric["baseline"])
        times = [frame["timestamp"] for frame in self.demo["frames"]]
        self.assertEqual(times, sorted(times))
        self.assertLessEqual(episode["eventSecond"] * 1000, times[-1])

    def test_guide_is_sixty_seconds(self):
        from PIL import Image
        with Image.open(self.root / "walkthrough.gif") as image:
            duration = 0
            for index in range(image.n_frames):
                image.seek(index)
                duration += image.info["duration"]
            self.assertEqual(duration, 60000)


if __name__ == "__main__":
    unittest.main()
