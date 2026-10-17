import math
import unittest

from riot_model.diagnostics import review_report


def profile(metric="early_cs_15", n=100, p25=80, median=100, p75=120):
    return {"Ashe|BOTTOM|EARLY": {"metrics": {metric: {"n": n, "p25": p25, "median": median, "p75": p75}}}}


def match(start, value, **extra):
    row = {"gameStartMs": start, "matchRef": f"m{start}", "champion": "Ashe", "position": "BOTTOM",
           "durationMin": 30, "patch": "16.17", "win": bool(start % 2), "early_cs_15": value}
    row.update(extra)
    return row


class ReviewReportTests(unittest.TestCase):
    def test_recurring_gap_keeps_wins_and_losses_as_evidence(self):
        report = review_report([match(i, value) for i, value in enumerate([70, 75, 79, 110, 115], 1)], profile())
        finding = report["findings"][0]
        self.assertTrue(finding["recurring"])
        self.assertEqual(finding["weakCount"], 3)
        self.assertEqual({row["win"] for row in finding["evidence"]}, {True, False})

    def test_duplicate_missing_nonfinite_and_incomplete_phase_are_excluded(self):
        rows = [match(1, 70), match(1, 60), match(2, None), match(3, math.nan), match(4, 50, durationMin=10)]
        report = review_report(rows, profile())
        finding = report["findings"][0]
        self.assertEqual(report["games"], 4)
        self.assertEqual(finding["eligible"], 1)

    def test_boundary_tie_is_not_weak_and_no_hero_fallback(self):
        rows = [match(1, 80), {**match(2, 40), "champion": "Jinx"}]
        finding = review_report(rows, profile())["findings"][0]
        self.assertEqual(finding["eligible"], 1)
        self.assertEqual(finding["weakCount"], 0)

    def test_sparse_baseline_and_team_metrics_do_not_create_diagnosis(self):
        sparse = profile(n=19)
        sparse["Ashe|BOTTOM|EARLY"]["metrics"]["team_dragons"] = {"n": 100, "p25": 0, "median": 1, "p75": 2}
        self.assertEqual(review_report([match(1, 10, team_dragons=0)], sparse)["findings"], [])


if __name__ == "__main__":
    unittest.main()
