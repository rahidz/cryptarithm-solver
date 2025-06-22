"""
This module provides a cryptarithm solver using Google's OR-Tools CP-SAT solver.
"""
import re
from ortools.sat.python import cp_model
from parser import parse_multi_puzzle, Operation, Word, Number, _parse_expression
from typing import Dict, Union, Set, List

def _int_to_base_digit_char(digit: int) -> str:
    """Converts a digit to its character representation for bases > 10."""
    if digit < 10:
        return str(digit)
    return chr(ord('A') + digit - 10)

def _get_all_letters(node: Union[Operation, Word, Number]) -> Set[str]:
    """Recursively traverses the AST to collect all unique letters."""
    if isinstance(node, Word):
        return set(l for l in node.letters if isinstance(l, str))
    if isinstance(node, Operation):
        return _get_all_letters(node.left) | _get_all_letters(node.right)
    return set()

def _build_expression(model: cp_model.CpModel, node: Union[Operation, Word, Number], letter_vars: Dict[str, cp_model.IntVar], base: int, bound: int, to_var_func):
    """Recursively builds a CP-SAT expression from an AST node."""
    if isinstance(node, Number):
        return int("".join(map(str, node.digits)))

    if isinstance(node, Word):
        linear_expr = 0
        for element in node.letters:
            if isinstance(element, str):
                linear_expr = linear_expr * base + letter_vars[element]
            else: # is an int
                linear_expr = linear_expr * base + element
        
        max_word_val = (base ** len(node.letters)) - 1
        word_var = model.NewIntVar(0, max_word_val if max_word_val > 0 else 0, "".join(map(str, node.letters)))
        model.Add(word_var == linear_expr)
        return word_var

    if isinstance(node, Operation):
        left_expr = _build_expression(model, node.left, letter_vars, base, bound, to_var_func)
        right_expr = _build_expression(model, node.right, letter_vars, base, bound, to_var_func)

        op_map = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
        }

        if node.op in op_map:
            return op_map[node.op](left_expr, right_expr)

        if node.op == '*':
            l_var = to_var_func(left_expr, 'l_mul')
            r_var = to_var_func(right_expr, 'r_mul')
            prod_var = model.NewIntVar(-bound * bound, bound * bound, 'prod')
            model.AddMultiplicationEquality(prod_var, [l_var, r_var])
            return prod_var
        
        if node.op == '^':
            base_var = to_var_func(left_expr, 'base_pow')
            exponent_var = to_var_func(right_expr, 'exponent')
            pow_var = model.NewIntVar(-bound, bound, 'pow')
            # CP-SAT does not have a direct power function, so we use a workaround.
            # This can be slow if the domain of variables is large.
            _add_pow_constraint(model, pow_var, base_var, exponent_var, bound)
            return pow_var

        raise ValueError(f"Unsupported operator: {node.op}")

    raise TypeError(f"Unsupported node type: {type(node).__name__}")

def _add_pow_constraint(model: cp_model.CpModel, result_var, base_var, exp_var, bound):
    """
    Adds a constraint result_var == base_var ** exp_var to the model.
    This is a workaround as CP-SAT doesn't directly support exponentiation.
    """
    possible_values = []
    # This is a simple implementation. A more optimized version might be needed
    # for larger domains or bounds.
    for b in range(bound):
        for e in range(10): # Limit exponent to prevent excessive computation
            try:
                res = b ** e
                if res < bound:
                    possible_values.append((res, b, e))
                # Early exit if result exceeds bound, assuming exp is non-negative
                elif e > 1 and b > 1:
                    break
            except OverflowError:
                break # Exit if power calculation results in an overflow
    
    model.AddAllowedAssignments([result_var, base_var, exp_var], possible_values)

class CryptarithmSolutionCallback(cp_model.CpSolverSolutionCallback):
    """Callback to store all solutions."""
    def __init__(self, letter_vars, puzzles):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._letter_vars = letter_vars
        self._puzzles = puzzles
        self.solutions = []

    def on_solution_callback(self):
        solution_map = {letter: self.Value(var) for letter, var in self._letter_vars.items()}
        
        # Create the solved puzzle string
        from_str = "".join(solution_map.keys())
        to_str = "".join(map(_int_to_base_digit_char, solution_map.values()))
        table = str.maketrans(from_str, to_str)
        solved_puzzle = "\n".join([p.upper().translate(table) for p in self._puzzles])
        
        # Create the letter-to-digit mapping string
        letter_mapping_str = " ".join(sorted([f"{l}={v}" for l, v in solution_map.items()]))
        
        # Combine and store the solution
        self.solutions.append(f"{solved_puzzle}\n{letter_mapping_str}")

def solve_with_cp_sat(puzzles: Union[str, List[str]], base=10, constraints=None):
    """
    Solves a cryptarithm puzzle using the CP-SAT solver.
    Can handle a single puzzle string or a list of puzzle strings for simultaneous equations.
    """
    if constraints is None:
        constraints = {}

    if isinstance(puzzles, str):
        puzzles = [puzzles]

    try:
        asts = parse_multi_puzzle(puzzles)
    except ValueError as e:
        return [str(e)]

    # --- 1. Collect letters and identify leading letters from all puzzles ---
    all_letters = set()
    for ast in asts:
        all_letters.update(_get_all_letters(ast))
    all_letters = sorted(list(all_letters))

    first_letters = set()
    for puzzle_string in puzzles:
        words_in_puzzle = re.findall('[A-Z0-9]+', puzzle_string.upper())
        for word in words_in_puzzle:
            if word:
                if word and word[0].isalpha():
                    first_letters.add(word[0])

    # --- 2. Perform validations ---
    if any(l not in all_letters for l in constraints.keys()):
        return ["Invalid constraint: A letter in the constraint is not in the puzzle."]
    if len(set(constraints.values())) != len(constraints.values()):
        return ["Invalid constraint: Digits in constraints must be unique."]
    if any(d >= base for d in constraints.values()):
        return [f"Invalid constraint: A digit is greater than or equal to the base {base}."]
    for letter, digit in constraints.items():
        if letter in first_letters and digit == 0:
            return [f"Invalid constraint: Letter '{letter}' cannot be zero."]
    if len(all_letters) > base:
        return [f"Too many unique letters for base {base}. The puzzle is unsolvable."]

    # --- 3. Create the CP-SAT model and variables ---
    model = cp_model.CpModel()
    letter_vars = {letter: model.NewIntVar(0, base - 1, letter) for letter in all_letters}

    # --- 4. Add constraints ---
    if all_letters:
        model.AddAllDifferent([letter_vars[l] for l in all_letters])

    for letter in first_letters:
        model.Add(letter_vars[letter] != 0)

    for letter, digit in constraints.items():
        model.Add(letter_vars[letter] == digit)

    # --- 5. Build and add the main arithmetic constraint from the AST ---
    all_words = []
    all_numbers = []
    for puzzle_string in puzzles:
        all_words.extend(re.findall('[A-Z0-9]+', puzzle_string.upper()))
        all_numbers.extend(re.findall(r'\d+', puzzle_string))
    
    max_word_len = max(len(w) for w in all_words) if all_words else 0
    max_num_len = max(len(n) for n in all_numbers) if all_numbers else 0
    max_len = max(max_word_len, max_num_len)
    bound = base ** (max_len if max_len > 0 else 10)

    def to_var(expr, name):
        if isinstance(expr, int):
            const_var = model.NewIntVar(expr, expr, name)
            return const_var
        if hasattr(expr, 'Index'):  # It's an IntVar
            return expr
        
        helper_var = model.NewIntVar(-bound, bound, name)
        model.Add(helper_var == expr)
        return helper_var

    for i, ast in enumerate(asts):
        if isinstance(ast.left, Operation) and ast.left.op == '/':
            # Case: A/B = C or A/B = C/D
            if isinstance(ast.right, Operation) and ast.right.op == '/':
                # Equation is of the form A/B = C/D, so we solve A*D = B*C
                a_expr = _build_expression(model, ast.left.left, letter_vars, base, bound, to_var)
                b_expr = _build_expression(model, ast.left.right, letter_vars, base, bound, to_var)
                c_expr = _build_expression(model, ast.right.left, letter_vars, base, bound, to_var)
                d_expr = _build_expression(model, ast.right.right, letter_vars, base, bound, to_var)

                a_var = to_var(a_expr, f'a_{i}')
                b_var = to_var(b_expr, f'b_{i}')
                c_var = to_var(c_expr, f'c_{i}')
                d_var = to_var(d_expr, f'd_{i}')

                prod_bound = bound * bound
                prod1_var = model.NewIntVar(-prod_bound, prod_bound, f'prod1_{i}')
                prod2_var = model.NewIntVar(-prod_bound, prod_bound, f'prod2_{i}')
                
                model.AddMultiplicationEquality(prod1_var, [a_var, d_var])
                model.AddMultiplicationEquality(prod2_var, [b_var, c_var])
                model.Add(prod1_var == prod2_var)
            else:
                # Equation is of the form A/B = C, so we solve A = B*C
                dividend_node = ast.left.left
                divisor_node = ast.left.right
                quotient_node = ast.right
                
                dividend_expr = _build_expression(model, dividend_node, letter_vars, base, bound, to_var)
                divisor_expr = _build_expression(model, divisor_node, letter_vars, base, bound, to_var)
                quotient_expr = _build_expression(model, quotient_node, letter_vars, base, bound, to_var)

                dividend_var = to_var(dividend_expr, f'dividend_{i}')
                divisor_var = to_var(divisor_expr, f'divisor_{i}')
                quotient_var = to_var(quotient_expr, f'quotient_{i}')

                model.AddMultiplicationEquality(dividend_var, [divisor_var, quotient_var])
        else:
            left_side_expr = _build_expression(model, ast.left, letter_vars, base, bound, to_var)
            right_side_expr = _build_expression(model, ast.right, letter_vars, base, bound, to_var)
            model.Add(left_side_expr == right_side_expr)

    # --- 6. Solve the model ---
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solution_callback = CryptarithmSolutionCallback(letter_vars, puzzles)
    status = solver.Solve(model, solution_callback)

    # --- 7. Process and return the solution ---
    if solution_callback.solutions:
        return sorted(list(set(solution_callback.solutions)))

    if status == cp_model.INFEASIBLE:
         return ["No solution found"]
    
    # Check for validation errors that lead to no solution
    for letter, digit in constraints.items():
        if letter in first_letters and digit == 0:
            return [f"Invalid constraint: Letter '{letter}' cannot be zero."]

    return ["No solution found"]