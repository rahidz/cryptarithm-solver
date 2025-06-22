import re
from itertools import permutations
import re
from evaluator import safe_eval
from parser import parse_puzzle, Operation, Word, Number
from columns import ColumnEngine

def _solve_generic_puzzle(ast: Operation, puzzle_string: str, base=10, constraints=None):
    if constraints is None:
        constraints = {}

    # This is a simplified letter collection, assuming the column engine handles the main logic.
    # For generic puzzles, we still need to know all letters.
    letters = set()
    def collect_letters(node):
        if isinstance(node, Word):
            letters.update(node.letters)
        elif isinstance(node, Operation):
            collect_letters(node.left)
            collect_letters(node.right)
    collect_letters(ast)
    unique_letters = sorted(list(letters))
    
    # A simple way to get first letters for the generic solver.
    first_letters = set()
    words_in_puzzle = re.findall('[A-Z]+', puzzle_string.upper())
    for word in words_in_puzzle:
        if word:
            first_letters.add(word[0])

    if any(l not in unique_letters for l in constraints.keys()):
        return ["Invalid constraint: A letter in the constraint is not in the puzzle."]
    if len(set(constraints.values())) != len(constraints.values()):
        return ["Invalid constraint: Digits in constraints must be unique."]
    if any(d >= base for d in constraints.values()):
        return [f"Invalid constraint: A digit is greater than or equal to the base {base}."]

    if len(unique_letters) > base:
        return [f"Too many unique letters for base {base}. The puzzle is unsolvable."]

    letters_to_solve = [l for l in unique_letters if l not in constraints]
    used_digits = set(constraints.values())
    available_digits = [d for d in range(base) if d not in used_digits]

    if len(letters_to_solve) > len(available_digits):
        return ["Not enough available digits for the remaining letters after applying constraints."]

    solutions = []
    for p in permutations(available_digits, len(letters_to_solve)):
        mapping = constraints.copy()
        mapping.update(dict(zip(letters_to_solve, p)))

        if any(mapping[letter] == 0 for letter in first_letters if letter in letters_to_solve):
            continue

        from_str = "".join(unique_letters)
        to_str = "".join([str(mapping[l]) for l in unique_letters])
        table = str.maketrans(from_str, to_str)
        
        equation = puzzle_string.upper().replace("=", "==")
        
        # This part remains similar, as it handles generic expressions.
        eval_equation = equation
        for word in sorted(words_in_puzzle, key=len, reverse=True):
            digit_word = "".join([str(mapping[l]) for l in word])
            eval_equation = re.sub(r'\b' + word + r'\b', f'int("{digit_word}", {base})', eval_equation)

        if safe_eval(eval_equation):
            solutions.append(puzzle_string.upper().translate(table))

    if not solutions:
        return ["No solution found"]
    return solutions


def solve_cryptarithm(puzzle_string, base=10, constraints=None):
    if constraints is None:
        constraints = {}

    try:
        ast = parse_puzzle(puzzle_string)
    except ValueError as e:
        return [str(e)]

    # Collect all letters and first letters from the AST for validation
    all_letters = set()
    first_letters = set()
    def _collect_letters_for_validation(node):
        if isinstance(node, Word):
            all_letters.update(node.letters)
            if node.letters:
                first_letters.add(node.letters[0])
        elif isinstance(node, Operation):
            _collect_letters_for_validation(node.left)
            _collect_letters_for_validation(node.right)
    _collect_letters_for_validation(ast)
    
    # Perform all constraint validations upfront
    if any(l not in all_letters for l in constraints.keys()):
        return ["Invalid constraint: A letter in the constraint is not in the puzzle."]
    if len(set(constraints.values())) != len(constraints.values()):
        return ["Invalid constraint: Digits in constraints must be unique."]
    if any(d >= base for d in constraints.values()):
        return [f"Invalid constraint: A digit is greater than or equal to the base {base}."]
    if len(all_letters) > base:
        return [f"Too many unique letters for base {base}. The puzzle is unsolvable."]
    for letter, digit in constraints.items():
        if letter in first_letters and digit == 0:
            return [f"Invalid constraint: Letter '{letter}' cannot be zero."]

    # Decide which solver to use.
    # The column engine is only for simple `Word + Word = Word` puzzles.
    def _is_simple_addition_chain(node):
        if isinstance(node, Operation) and node.op == '+':
            return _is_simple_addition_chain(node.left) and _is_simple_addition_chain(node.right)
        elif isinstance(node, Word):
            return True
        return False

    is_simple_addition = (
        _is_simple_addition_chain(ast.left) and
        isinstance(ast.right, Word)
    )

    if is_simple_addition:
        engine = ColumnEngine(ast)
        return engine.solve(puzzle_string, base=base, constraints=constraints)
    else:
        # All other cases (multiplication, complex expressions, etc.) go to the generic solver.
        return _solve_generic_puzzle(ast, puzzle_string, base=base, constraints=constraints)