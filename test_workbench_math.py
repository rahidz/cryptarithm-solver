import unittest
from copy import deepcopy
from itertools import product
from unittest.mock import patch

from workbench_math import (
    normalize_spec,
    candidates,
    hints,
    generate,
    minimal_clues,
    experiment,
    describe_solution,
)


class LayoutTests(unittest.TestCase):
    def solve_layout(self, kind, rows, **extra):
        from solver import solve_puzzle

        return solve_puzzle(
            normalize_spec({"layout": {"kind": kind, "rows": rows}, **extra})
        )

    def test_addition(self):
        self.assertEqual(
            self.solve_layout("addition", ["12", "34", "46"])["status"], "satisfiable"
        )
        self.assertEqual(
            self.solve_layout("addition", ["12", "34", "47"])["status"], "unsatisfiable"
        )

    def test_blank_cells_reused(self):
        spec = normalize_spec(
            {"layout": {"kind": "multiplication", "rows": ["1?", "2", "2?", "2?"]}}
        )
        self.assertIn("1?1 * 2 = 2?3", spec["equations"])
        self.assertIn("1?1 * 2 = 2?2", spec["equations"])
        self.assertNotIn("layout", spec)
        self.assertEqual(normalize_spec(spec), spec)

    def test_blank_followed_by_fixed_digit(self):
        compiled = normalize_spec(
            {"layout": {"kind": "addition", "rows": ["?3", "1", "24"]}}
        )
        self.assertIn("?1[3]", compiled["equations"][0])
        answer = self.solve_layout("addition", ["?3", "1", "24"])
        self.assertEqual(answer["solutions"][0]["assignment"]["?1"], 2)

    def test_multiplication_shift(self):
        answer = self.solve_layout("multiplication", ["12", "34", "48", "36", "408"])
        self.assertEqual(answer["status"], "satisfiable")
        wrong = self.solve_layout("multiplication", ["12", "34", "48", "35", "408"])
        self.assertEqual(wrong["status"], "unsatisfiable")

    def test_division_steps(self):
        answer = self.solve_layout(
            "division", ["157", "12", "13", "1", "12", "3", "36", "1"]
        )
        self.assertEqual(answer["status"], "satisfiable")
        wrong = self.solve_layout(
            "division", ["157", "12", "13", "1", "12", "4", "36", "1"]
        )
        self.assertEqual(wrong["status"], "unsatisfiable")

    def test_remainder_bound(self):
        self.assertEqual(
            self.solve_layout("division", ["15", "3", "4", "3"])["status"],
            "unsatisfiable",
        )
        self.assertEqual(
            self.solve_layout("division", ["15", "0", "4", "3"])["status"],
            "unsatisfiable",
        )

    def test_nondecimal_division(self):
        self.assertEqual(
            self.solve_layout(
                "division", ["111", "10", "11", "1", "10", "1", "10", "1"], base=2
            )["status"],
            "satisfiable",
        )

    def test_wrong_partial_count(self):
        with self.assertRaises(ValueError):
            normalize_spec(
                {
                    "layout": {
                        "kind": "multiplication",
                        "rows": ["12", "34", "48", "408"],
                    }
                }
            )

    def test_forbidden_blank_digits(self):
        spec = normalize_spec(
            {
                "layout": {"kind": "addition", "rows": ["1?", "?", "2?"]},
                "forbidden_blank_digits": [0, 3],
            }
        )
        self.assertEqual(spec["domains"]["?1"], [1, 2, 4, 5, 6, 7, 8, 9])
        self.assertEqual(set(spec["domains"]), {"?1", "?2", "?3"})

    def test_square_root_extraction(self):
        # sqrt(1521): take 3² from 15, then (20*3+9)*9 from 621.
        answer = self.solve_layout("root", ["39", "1521", "0", "9", "621", "621"])
        self.assertEqual(answer["status"], "satisfiable")
        wrong = self.solve_layout("root", ["39", "1521", "0", "9", "621", "620"])
        self.assertEqual(wrong["status"], "unsatisfiable")

    def test_root_must_be_floor(self):
        self.assertEqual(
            self.solve_layout("root", ["2", "15", "11", "4"])["status"], "unsatisfiable"
        )
        self.assertEqual(
            self.solve_layout("root", ["3", "15", "6", "9"])["status"], "satisfiable"
        )

    def test_binary_root(self):
        self.assertEqual(
            self.solve_layout("root", ["11", "1001", "0", "1", "101", "101"], base=2)[
                "status"
            ],
            "satisfiable",
        )


class TeachingTests(unittest.TestCase):
    def test_declared_domain_exclusions(self):
        values = candidates({"equations": ["A=A"], "base": 3, "domains": {"A": [1]}})[
            "candidates"
        ]["A"]
        self.assertEqual(values, {"possible": [1], "excluded": [0, 2], "unknown": []})

    def test_unsupported_exact_leaf_not_a_contradiction(self):
        from teaching import propagate, proof_search, replay_proof

        for spec in [
            {"equations": ["1^99=1"]},
            {
                "equations": ["1=1"],
                "constraints": [{"kind": "divisible", "expr": "1", "modulus": "0"}],
            },
        ]:
            result = propagate(spec)
            self.assertFalse(result["contradiction"])
            self.assertFalse(result["solved"])
            self.assertTrue(result["verification_error"])
            proof = proof_search(spec)
            self.assertFalse(proof["complete"])
            self.assertNotEqual(proof["status"], "exhaustive")
            self.assertTrue(replay_proof(spec, proof))

    def test_ordinary_false_exact_leaf_is_contradiction(self):
        from teaching import propagate, proof_search

        for spec in [{"equations": ["1=2"]}, {"equations": ["1/0=1"]}]:
            self.assertTrue(propagate(spec)["contradiction"])
            proof = proof_search(spec)
            self.assertTrue(proof["complete"])
            self.assertEqual(proof["solutions"], [])

    def test_expression_remainder_skips_unsupported_local_rule(self):
        from teaching import propagate

        result = propagate(
            {
                "equations": ["A=A"],
                "assignments": {"A": 1},
                "constraints": [
                    {"kind": "modular", "expr": "A", "modulus": 3, "remainder": "A"}
                ],
            }
        )
        self.assertTrue(result["solved"])
        self.assertFalse(result["contradiction"])

    def test_invalid_predicate_not_a_proof_of_contradiction(self):
        from teaching import propagate, proof_search

        spec = {
            "equations": ["1=1"],
            "constraints": [{"kind": "nonsense", "expr": "1"}],
        }
        with self.assertRaises(ValueError):
            propagate(spec)
        with self.assertRaises(ValueError):
            proof_search(spec)

    def test_proof_replay_requires_every_branch(self):
        from teaching import proof_search, replay_proof

        spec = {"equations": ["A+B=2"], "base": 3, "distinct": False}
        proof = proof_search(spec)
        self.assertTrue(replay_proof(spec, proof))
        missing = deepcopy(proof)
        missing["rows"].pop()
        self.assertFalse(replay_proof(spec, missing))
        repeated = deepcopy(proof)
        repeated["rows"][-1] = deepcopy(repeated["rows"][-2])
        self.assertFalse(replay_proof(spec, repeated))
        forged = proof_search(spec, {"depth": 0})
        forged["complete"], forged["status"] = True, "exhaustive"
        self.assertFalse(replay_proof(spec, forged))

    def test_elementary_parity(self):
        from teaching import propagate

        result = propagate({"equations": ["2*A=B"]})
        self.assertEqual(result["domains"]["B"], [0, 2, 4, 6, 8])
        self.assertTrue(any(s["rule"] == "parity" for s in result["steps"]))

    def test_elementary_last_digit(self):
        from teaching import propagate

        result = propagate({"equations": ["AB*5=CD"]})
        self.assertEqual(result["domains"]["D"], [0, 5])
        self.assertTrue(any(s["rule"] == "final-digit" for s in result["steps"]))

    def test_elementary_divisibility_and_modular(self):
        from teaching import propagate

        for kind, remainder, expected in [
            ("divisible", 0, [0, 3, 6, 9]),
            ("modular", 1, [1, 4, 7]),
        ]:
            result = propagate(
                {
                    "equations": ["A=A"],
                    "constraints": [
                        {
                            "kind": kind,
                            "expr": "A",
                            "modulus": 3,
                            "remainder": remainder,
                        }
                    ],
                }
            )
            self.assertEqual(result["domains"]["A"], expected)

    def test_elementary_intervals(self):
        from teaching import propagate

        result = propagate({"equations": ["A+B=2"], "distinct": False})
        self.assertEqual(result["domains"], {"A": [0, 1, 2], "B": [0, 1, 2]})
        self.assertTrue(any(s["rule"] == "interval" for s in result["steps"]))

    def test_rule_replay_and_tampering(self):
        from teaching import propagate, replay_steps

        spec = {"equations": ["SEND+MORE=MONEY"]}
        result = propagate(spec)
        self.assertTrue(replay_steps(spec, result["steps"]))
        self.assertTrue(any(s["rule"] == "column-carry" for s in result["steps"]))
        changed = deepcopy(result["steps"])
        changed[0]["remaining"] = [42]
        self.assertFalse(replay_steps(spec, changed))

    def test_elementary_rules_preserve_all_independent_solutions(self):
        from teaching import propagate

        tests = [
            (
                {"equations": ["AB+C=BA"], "base": 4},
                lambda a, b, c: a * 4 + b + c == b * 4 + a,
                ["A", "B"],
            ),
            (
                {"equations": ["AB-C=BA"], "base": 4},
                lambda a, b, c: a * 4 + b - c == b * 4 + a,
                ["A", "B"],
            ),
            ({"equations": ["A*B=C"], "base": 4}, lambda a, b, c: a * b == c, []),
        ]
        for spec, condition, leading in tests:
            result = propagate(spec)
            for a, b, c in product(range(4), repeat=3):
                assignment = dict(A=a, B=b, C=c)
                if (
                    len({a, b, c}) != 3
                    or any(assignment[v] == 0 for v in leading)
                    or not condition(a, b, c)
                ):
                    continue
                self.assertFalse(result["contradiction"])
                for v, d in assignment.items():
                    self.assertIn(d, result["domains"][v])

    def test_borrow_rule_and_inequality(self):
        from teaching import propagate

        result = propagate({"equations": ["A0-B=19"]})
        self.assertTrue(any(s["rule"] == "column-borrow" for s in result["steps"]))
        result = propagate(
            {
                "equations": ["A=A"],
                "constraints": [
                    {"kind": "inequality", "expr": "A", "op": "<", "value": 3}
                ],
            }
        )
        self.assertEqual(result["domains"]["A"], [0, 1, 2])

    def test_proof_search_explicit_complete_and_stalled(self):
        spec = {"equations": ["A+B=2"], "base": 3, "distinct": False}
        limited = experiment(spec, {"kind": "proof-search", "depth": 0})
        self.assertFalse(limited["complete"])
        complete = experiment(spec, {"kind": "proof-search", "depth": 2})
        self.assertTrue(complete["complete"])
        self.assertEqual(len(complete["solutions"]), 3)
        self.assertEqual(complete["rows"][0]["split_digits"], [0, 1, 2])

    def test_adversarial_bounded_unique(self):
        answer = experiment(
            {"base": 4},
            {"kind": "adversarial", "width": 1, "count": 2, "seed": 13, "timeout": 5},
        )
        self.assertTrue(answer["complete"])
        self.assertEqual(len(answer["rows"]), 2)
        self.assertTrue(all(r["unique"] for r in answer["rows"] if r["accepted"]))

    def test_base_sweep_recompiles_layout(self):
        spec = {
            "layout": {"kind": "addition", "rows": ["?", "?", "?"]},
            "forbidden_blank_digits": [0],
        }
        cases = []

        def solved(case, **kwargs):
            cases.append(case)
            return {
                "status": "satisfiable",
                "solutions": [],
                "complete": True,
                "elapsed": 0,
                "message": "",
            }

        with patch("workbench_math._solve", side_effect=solved):
            experiment(spec, {"min_base": 2, "max_base": 3})
        self.assertEqual(cases[0]["domains"]["?1"], [1])
        self.assertEqual(cases[1]["domains"]["?1"], [1, 2])

    def test_addition_carries(self):
        spec = {"equations": ["SEND+MORE=MONEY"]}
        assignment = dict(S=9, E=5, N=6, D=7, M=1, O=0, R=8, Y=2)
        detail = describe_solution(spec, assignment)
        self.assertEqual([c["carry_out"] for c in detail["columns"]], [1, 1, 0, 1, 0])

    def test_subtraction_borrows(self):
        detail = describe_solution(
            {"layout": {"kind": "subtraction", "rows": ["1000", "1", "999"]}}, {}
        )
        self.assertEqual([c["carry_out"] for c in detail["columns"]], [1, 1, 1, 0])
        self.assertEqual(detail["rows"][-1]["solved"], "999")

    def test_multiplication_column_carries(self):
        detail = describe_solution(
            {
                "layout": {
                    "kind": "multiplication",
                    "rows": ["12", "34", "48", "36", "408"],
                }
            },
            {},
        )
        self.assertEqual(len(detail["columns"]), 7)
        self.assertEqual(detail["columns"][-1]["result"], 4)

    def test_division_columns(self):
        detail = describe_solution(
            {"layout": {"kind": "division", "rows": ["157", "12", "13", "1"]}}, {}
        )
        self.assertTrue(any(c["operation"] == "subtraction" for c in detail["columns"]))
        self.assertEqual(detail["rows"][-1]["value"], "1")

    def test_probe_timeout_unknown(self):
        with (
            patch(
                "workbench_math._inspect",
                return_value={"variables": ["A"], "domains": {"A": [0, 1]}},
            ),
            patch(
                "workbench_math._solve",
                return_value={"solutions": [], "status": "incomplete"},
            ),
        ):
            self.assertEqual(
                candidates({"equations": ["A=A"], "base": 2})["candidates"]["A"],
                {"possible": [], "excluded": [], "unknown": [0, 1]},
            )

    def test_candidates_witness_and_exclusion(self):
        values = candidates({"equations": ["A+1=2"], "base": 3})["candidates"]["A"]
        self.assertEqual(values["possible"], [1])
        self.assertEqual(values["excluded"], [0, 2])

    def test_hints_checked(self):
        answer = hints({"equations": ["A+1=2"], "base": 3})
        self.assertTrue(
            any(
                h["kind"] == "solver-proved" and "A = 1" in h["text"]
                for h in answer["hints"]
            )
        )

    def test_generator_unique_reproducible(self):
        a = generate({"base": 5}, {"seed": 10, "width": 1})
        b = generate({"base": 5}, {"seed": 10, "width": 1})
        self.assertEqual(a["spec"], b["spec"])
        self.assertTrue(a["verification"]["unique"])

    def test_minimal_clues(self):
        answer = minimal_clues(
            {"equations": ["A+B=2"], "base": 3, "assignments": {"A": 0, "B": 2}}
        )
        self.assertEqual(answer["minimal"], 1)
        self.assertTrue(answer["complete"])


if __name__ == "__main__":
    unittest.main()
