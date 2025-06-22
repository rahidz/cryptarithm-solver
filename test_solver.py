import unittest
from solver import solve_cryptarithm

class TestCryptarithmSolver(unittest.TestCase):

    def test_send_more_money(self):
        solutions = solve_cryptarithm("SEND + MORE = MONEY")
        self.assertIn("9567 + 1085 = 10652\nD=7 E=5 M=1 N=6 O=0 R=8 S=9 Y=2", solutions)

    def test_abcd_puzzle(self):
        result = solve_cryptarithm("ABCD * 9 = DCBA")
        self.assertIn("1089 * 9 = 9801\nA=1 B=0 C=8 D=9", result)

    def test_base_9_puzzle(self):
        result = solve_cryptarithm("ALFRED / E = NEUMAN", base=9)
        self.assertIn("704836 / 3 = 231572\nA=7 D=6 E=3 F=4 L=0 M=5 N=2 R=8 U=1", result)

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
        self.assertIn("49306 + 49306 = 98612\nG=6 H=1 I=8 N=0 O=3 R=9 T=2 W=4", solutions)
        self.assertEqual(len(solutions), 1)

    def test_constraint_puzzle_with_predefined_value(self):
        solutions = solve_cryptarithm("ABCD * 9 = DCBA", constraints={'A': 1})
        self.assertIn("1089 * 9 = 9801\nA=1 B=0 C=8 D=9", solutions)

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
        self.assertIn("235*235+142*142=75389\nC=1 E=9 I=3 N=5 O=4 S=2 T=8 U=7", solutions)

    def test_multiple_addends(self):
        solutions = solve_cryptarithm("THIS + ISA + GREAT + TIME = WASTER")
        self.assertIn("5628 + 280 + 97405 + 5234 = 108547\nA=0 E=4 G=9 H=6 I=2 M=3 R=7 S=8 T=5 W=1", solutions)
        
    def test_cross_multiplication(self):
        solutions = solve_cryptarithm("EVE/DID=TALK/9999")
        self.assertIn("212/606=3498/9999\nA=4 D=6 E=2 I=0 K=8 L=9 T=3 V=1", solutions)
        self.assertIn("242/303=7986/9999\nA=9 D=3 E=2 I=0 K=6 L=8 T=7 V=4", solutions)
if __name__ == '__main__':
    unittest.main()