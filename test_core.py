import itertools
import unittest
from solver import (
    solve_puzzle,
    validate_assignment,
    validate_assignment_strict,
    inspect_puzzle,
)


class CoreTests(unittest.TestCase):
    def solve(self, equation, **kwargs):
        return solve_puzzle(dict(equations=[equation], mode="all", **kwargs))

    def test_precedence_and_rational_arithmetic(self):
        for text in [
            "-2^2=-4",
            "2**3^2=512",
            "1/2+1/3=5/6",
            "1/(2/3)=3/2",
            "(2+3)*4=20",
        ]:
            with self.subTest(text=text):
                r = self.solve(text)
                self.assertEqual(r["status"], "satisfiable", r)
                self.assertTrue(r["complete"])

    def test_denominator_restrictions(self):
        for text in ["1/0=2", "0/0=0/0", "1/(A-A)=B", "A/(B-B)=0"]:
            self.assertEqual(self.solve(text)["status"], "unsatisfiable", text)

    def test_zero_and_fixed_digits(self):
        r = self.solve("A+B=A")
        self.assertEqual(len(r["solutions"]), 9)
        self.assertTrue(all(s["assignment"]["B"] == 0 for s in r["solutions"]))
        self.assertEqual(self.solve("AB=10", assignments={"A": 0})["status"], "invalid")
        self.assertEqual(self.solve("A=2", base=2)["status"], "invalid")
        self.assertEqual(
            self.solve("A=[15]", base=16)["solutions"][0]["assignment"], {"A": 15}
        )

    def test_anon_and_domains(self):
        spec = dict(equations=["?1+?2=?1"], base=3, mode="all")
        r = solve_puzzle(spec)
        self.assertEqual(len(r["solutions"]), 3)
        self.assertTrue(
            all(validate_assignment(spec, s["assignment"]) for s in r["solutions"])
        )
        self.assertEqual(
            inspect_puzzle({"equations": ["?+?=A"]})["variables"], ["?1", "?2", "A"]
        )
        self.assertEqual(
            self.solve("A+B=C", domains={"A": [1], "B": [2]})["solutions"][0][
                "assignment"
            ],
            {"A": 1, "B": 2, "C": 3},
        )

    def test_statuses(self):
        self.assertEqual(self.solve("A+=B")["status"], "invalid")
        self.assertEqual(self.solve("A^99=B")["status"], "unsupported")
        self.assertEqual(self.solve("1234567890123456/A=2")["status"], "unsupported")
        r = solve_puzzle({"equations": ["A+B=C"], "mode": "first"})
        self.assertEqual(len(r["solutions"]), 1)
        self.assertIsNone(r["unique"])
        self.assertFalse(r["complete"])
        r = solve_puzzle({"equations": ["A=1"], "mode": "unique"})
        self.assertTrue(r["unique"])

    def test_predicates(self):
        cases = [
            ({"kind": "prime", "expr": "A"}, {2, 3, 5, 7}),
            ({"kind": "square", "expr": "A"}, {0, 1, 4, 9}),
            ({"kind": "factorial", "expr": "A"}, {1, 2, 6}),
            ({"kind": "modular", "expr": "A", "modulus": 3, "remainder": 1}, {1, 4, 7}),
            ({"kind": "inequality", "expr": "A", "op": ">", "value": 6}, {7, 8, 9}),
        ]
        for constraint, expected in cases:
            r = self.solve("A=A", constraints=[constraint])
            self.assertEqual(
                {s["assignment"]["A"] for s in r["solutions"]}, expected, r
            )
        r = self.solve("A=A", constraints=[{"kind": "prime", "expr": "A/2"}])
        self.assertEqual({s["assignment"]["A"] for s in r["solutions"]}, {4, 6})

    def test_small_independent_oracle(self):
        # Deliberately no parser/evaluator reuse: enumerate the equations directly.
        for base in range(2, 7):
            for text, condition in [
                ("A+B=C", lambda a, b, c: a + b == c),
                ("A*B=C", lambda a, b, c: a * b == c),
                ("A/B=C", lambda a, b, c: b != 0 and a == b * c),
                ("A-B=C", lambda a, b, c: a - b == c),
                ("A/B+C=1", lambda a, b, c: b != 0 and a + b * c == b),
            ]:
                expected = {
                    t for t in itertools.permutations(range(base), 3) if condition(*t)
                }
                r = self.solve(text, base=base)
                self.assertIn(r["status"], ("satisfiable", "unsatisfiable"), r)
                actual = {
                    tuple(s["assignment"][v] for v in "ABC") for s in r["solutions"]
                }
                self.assertEqual(actual, expected, (base, text, r))

    def test_z3_differential(self):
        for equation in ("A+B=C", "A/B+C=1", "A^2=B", "0/(A-A)=0"):
            cp = self.solve(equation, base=5)
            z3 = self.solve(equation, base=5, backend="z3")
            self.assertIn(z3["status"], ("satisfiable", "unsatisfiable"), z3)
            assignments = lambda r: {
                tuple(sorted(s["assignment"].items())) for s in r["solutions"]
            }
            self.assertEqual(assignments(cp), assignments(z3))

    def test_large_column_models(self):
        for equation in [
            "99999999999999999999+1=100000000000000000000",
            "100000000000000000000-1=99999999999999999999",
            "1234567890^2=1524157875019052100",
            "99999999999999999999*A=199999999999999999998",
        ]:
            r = self.solve(equation)
            self.assertEqual(r["status"], "satisfiable", r)
            self.assertTrue(r["complete"])
            self.assertGreater(r["statistics"]["column_equations"], 0)

    def test_constraint_parameter_expressions(self):
        r = self.solve(
            "A=A",
            constraints=[dict(kind="modular", expr="A", modulus=3, remainder="1")],
        )
        self.assertEqual({s["assignment"]["A"] for s in r["solutions"]}, {1, 4, 7})
        self.assertEqual(
            self.solve(
                "?=0", constraints=[dict(kind="inequality", expr="?", op="=", value=1)]
            )["status"],
            "invalid",
        )
        r = self.solve(
            "A=A",
            constraints=[dict(kind="modular", expr="A", modulus=3, remainder="B")],
        )
        self.assertIn(r["status"], ("satisfiable", "unsatisfiable"), r)

    def test_deferred_prime_is_exact(self):
        for value, expected in ((100001, "unsatisfiable"), (100003, "satisfiable")):
            r = self.solve(
                f"ABCDEF={value}",
                distinct=False,
                constraints=[dict(kind="prime", expr="ABCDEF")],
            )
            self.assertEqual(r["status"], expected, r)
            self.assertTrue(r["complete"])
            self.assertEqual(r["statistics"]["deferred_predicates"], 1)

    def test_variable_power_columns_oracle(self):
        for base in (2, 3, 4):
            r = self.solve("A^B*C^D=ABCD", base=base, distinct=False)
            expected = {
                t
                for t in itertools.product(range(base), repeat=4)
                if t[0] != 0
                and t[0] ** t[1] * t[2] ** t[3]
                == ((t[0] * base + t[1]) * base + t[2]) * base + t[3]
            }
            self.assertTrue(r["complete"], r)
            actual = {tuple(s["assignment"][v] for v in "ABCD") for s in r["solutions"]}
            self.assertEqual(actual, expected, (base, r))
        r = solve_puzzle(
            dict(equations=["A^B*C^D=ABCD"], distinct=False, mode="first", timeout=3)
        )
        self.assertEqual(r["status"], "satisfiable", r)
        self.assertTrue(
            validate_assignment(
                dict(equations=["A^B*C^D=ABCD"], distinct=False),
                r["solutions"][0]["assignment"],
            )
        )


class ConstraintSchemaTests(unittest.TestCase):
    def test_strict_checker_preserves_unsupported_and_invalid(self):
        with self.assertRaises(ValueError):
            validate_assignment_strict(dict(equations=["1^99=1"]), {})
        with self.assertRaises(ValueError):
            validate_assignment_strict(
                dict(
                    equations=["1=1"],
                    constraints=[dict(kind="modular", expr="1", modulus="0")],
                ),
                {},
            )
        self.assertFalse(
            validate_assignment_strict(dict(equations=["1/A=2"]), {"A": 0})
        )
        self.assertFalse(validate_assignment(dict(equations=["1^99=1"]), {}))

    def test_inspection_and_solving_reject_invalid_schema(self):
        for constraint in [
            dict(kind="unknown", expr="A"),
            dict(kind=[], expr="A"),
            dict(kind="prime", expr=[]),
            dict(kind="inequality", expr="A", op="~"),
            dict(kind="inequality", expr="A", value=0.5),
            dict(kind="modular", expr="A", modulus=0),
            dict(kind="modular", expr="A", modulus=-2),
            dict(kind="modular", expr="A", modulus=True),
            dict(kind="modular", expr="A", modulus=2, remainder=[]),
            dict(kind="power", expr="A", degree=True),
            dict(kind="root", expr="A", degree=17),
            dict(kind="consecutive_primes", expr="A"),
        ]:
            spec = dict(
                equations=["A=1"], assignments={"A": 1}, constraints=[constraint]
            )
            with self.subTest(constraint=constraint):
                with self.assertRaises(ValueError):
                    inspect_puzzle(spec)
                self.assertEqual(solve_puzzle(spec)["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
