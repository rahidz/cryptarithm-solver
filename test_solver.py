import unittest
from solver import solve_cryptarithm

class TestCryptarithmSolver(unittest.TestCase):

    def test_send_more_money(self):
        solutions = solve_cryptarithm("SEND + MORE = MONEY")
        self.assertIn("9567 + 1085 = 10652", solutions)

    def test_abcd_puzzle(self):
        result = solve_cryptarithm("ABCD * 9 = DCBA")
        self.assertIn("1089 * 9 = 9801", result)

    def test_base_9_puzzle(self):
        result = solve_cryptarithm("ALFRED / E = NEUMAN", base=9)
        self.assertIn("704836 / 3 = 231572", result)

    def test_unsolvable_addition(self):
        self.assertEqual(["No solution found"], solve_cryptarithm("THIS + IS = WRONG"))

    def test_unsolvable_generic(self):
        self.assertEqual(["No solution found"], solve_cryptarithm("A * B = CDE"))

    def test_too_many_letters(self):
        result = solve_cryptarithm("ABCDEFGHI + J = K")
        self.assertEqual(result, ["Too many unique letters for base 10. The puzzle is unsolvable."])

    def test_leading_zero_constraint(self):
        # This puzzle requires B to be 0, but B is a first letter.
        result = solve_cryptarithm("A + B = A")
        self.assertEqual(result, ["No solution found"])

    def test_constraint_puzzle(self):
        solutions = solve_cryptarithm("WRONG + WRONG = RIGHT", constraints={'O': 3})
        self.assertIn("49306 + 49306 = 98612", solutions)
        self.assertEqual(len(solutions), 1)

    def test_constraint_puzzle_with_predefined_value(self):
        solutions = solve_cryptarithm("ABCD * 9 = DCBA", constraints={'A': 1})
        self.assertIn("1089 * 9 = 9801", solutions)

    def test_invalid_constraint_letter_not_in_puzzle(self):
        result = solve_cryptarithm("SEND + MORE = MONEY", constraints={'Z': 1})
        self.assertEqual(result, ["Invalid constraint: A letter in the constraint is not in the puzzle."])

    def test_invalid_constraint_digits_not_unique(self):
        result = solve_cryptarithm("A + B = C", constraints={'A': 1, 'B': 1})
        self.assertEqual(result, ["Invalid constraint: Digits in constraints must be unique."])

    def test_invalid_constraint_digit_ge_base(self):
        result = solve_cryptarithm("A + B = C", base=2, constraints={'A': 2})
        self.assertEqual(result, ["Invalid constraint: A digit is greater than or equal to the base 2."])

    def test_invalid_constraint_leading_zero(self):
        result = solve_cryptarithm("A + B = C", constraints={'A': 0})
        self.assertEqual(result, ["Invalid constraint: Letter 'A' cannot be zero."])

    def test_constraint_no_solution(self):
        result = solve_cryptarithm("SEND + MORE = MONEY", constraints={'M': 0})
        self.assertEqual(result, ["Invalid constraint: Letter 'M' cannot be zero."])

    def test_complex_expression(self):
        solutions = solve_cryptarithm("SIN*SIN+COS*COS=UNITE")
        self.assertIn("235*235+142*142=75389", solutions)

    def test_multiple_addends(self):
        solutions = solve_cryptarithm("THIS + ISA + GREAT + TIME = WASTER")
        self.assertIn("5628 + 280 + 97405 + 5234 = 108547", solutions)
if __name__ == '__main__':
    unittest.main()