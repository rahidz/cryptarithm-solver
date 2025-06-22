import unittest
from solver import solve_cryptarithm

class TestCryptarithmSolver(unittest.TestCase):

    def test_send_more_money(self):
        # This should use the fast addition solver
        solutions = solve_cryptarithm("SEND + MORE = MONEY")
        self.assertIn("9567 + 1085 = 10652", solutions)

    def test_abcd_puzzle(self):
        # This should use the generic solver
        result = solve_cryptarithm("ABCD * 9 = DCBA")
        self.assertIn("1089 * 9 = 9801", result)

    def test_base_9_puzzle(self):
        # This should use the solver with a different base
        result = solve_cryptarithm("ALFRED / E = NEUMAN", base=9)
        self.assertIn("704836 / 3 = 231572", result)

    def test_unsolvable_addition(self):
        # This should use the fast addition solver
        self.assertEqual(["No solution found"], solve_cryptarithm("THIS + IS = WRONG"))

    def test_unsolvable_generic(self):
        # This should use the generic solver
        self.assertEqual(["No solution found"], solve_cryptarithm("A * B = CDE"))

    def test_too_many_letters_addition(self):
        # This should use the fast addition solver
        result = solve_cryptarithm("ABCDEFGHI + J = K")
        self.assertEqual(result, ["Too many unique letters for base 10. The puzzle is unsolvable."])

    def test_too_many_letters_generic(self):
        # This should use the generic solver
        result = solve_cryptarithm("ABCDEFGHI * J = K")
        self.assertEqual(result, ["Too many unique letters for base 10. The puzzle is unsolvable."])

    def test_leading_zero_addition(self):
        # This should use the fast addition solver
        # This puzzle requires B to be 0, but B is a first letter.
        result = solve_cryptarithm("A + B = A")
        self.assertEqual(result, ["No solution found"])

    def test_leading_zero_generic(self):
        # This should use the generic solver
        # This puzzle requires B to be 0, but B is a leading letter of a two-digit number.
        result = solve_cryptarithm("A * B = C")
        self.assertNotIn("1 * 0 = 0", result)

if __name__ == '__main__':
    unittest.main()