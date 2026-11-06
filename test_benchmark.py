import unittest

from benchmarks.collection import corpus
from workbench_math import normalize_spec


class BenchmarkTests(unittest.TestCase):
    def test_full_denominator(self):
        entries = corpus()
        self.assertEqual([e["id"] for e in entries], list(range(1, 93)))
        self.assertGreater(sum(e["spec"] is not None for e in entries), 46)
        self.assertTrue(all(e["spec"] is not None or e.get("reason") for e in entries))

    def test_answer_free(self):
        for entry in corpus():
            if entry["spec"]:
                self.assertEqual(
                    entry["spec"].get("assignments", {}),
                    {"A": 3} if entry["id"] == 1 else {},
                )

    def test_root_reconstruction(self):
        from solver import solve_puzzle

        result = solve_puzzle(
            normalize_spec(
                {
                    "layout": {
                        "kind": "root",
                        "rows": ["12", "144", "0", "1", "44", "44"],
                    }
                }
            )
        )
        self.assertTrue(result["solutions"], result)

    def test_wrong_root_step_rejected(self):
        from solver import solve_puzzle

        result = solve_puzzle(
            normalize_spec(
                {
                    "layout": {
                        "kind": "root",
                        "rows": ["12", "144", "0", "1", "44", "43"],
                    }
                }
            )
        )
        self.assertEqual(result["status"], "unsatisfiable")
