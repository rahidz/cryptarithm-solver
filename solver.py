import re
from itertools import permutations
from evaluator import safe_eval
from parser import parse_puzzle

def _to_base_char(n):
    if n < 10:
        return str(n)
    return chr(ord('A') + n - 10)

def _solve_addition_puzzle(puzzle_string, base=10, constraints=None):
    if constraints is None:
        constraints = {}
    """
    Solves addition-based cryptarithmetic puzzles using a column-wise backtracking algorithm.
    """
    try:
        left, right = puzzle_string.upper().split('=')
        result_word = right.strip()
        addend_words = [a.strip() for a in left.split('+')]
    except ValueError:
        return ["Invalid puzzle format. Expected 'WORD + ... = WORD'."]

    words = addend_words + [result_word]
    if any(not re.match('^[A-Z]+$', word) for word in words):
        return ["Invalid characters in puzzle. Only letters are allowed."]

    all_letters = sorted(list(set("".join(words))))

    if any(l not in all_letters for l in constraints.keys()):
        return ["Invalid constraint: A letter in the constraint is not in the puzzle."]
    if len(set(constraints.values())) != len(constraints.values()):
        return ["Invalid constraint: Digits in constraints must be unique."]
    if any(d >= base for d in constraints.values()):
        return [f"Invalid constraint: A digit is greater than or equal to the base {base}."]

    if len(all_letters) > base:
        return [f"Too many unique letters for base {base}. The puzzle is unsolvable."]

    first_letters = {word[0] for word in words if word}
    for letter, digit in constraints.items():
        if letter in first_letters and digit == 0:
            return [f"Invalid constraint: Letter '{letter}' cannot be zero."]
    
    max_len = max(len(w) for w in words)
    if len(result_word) > max_len:
        max_len = len(result_word)
        
    addends_padded = [w.rjust(max_len, ' ') for w in addend_words]
    result_padded = result_word.rjust(max_len, ' ')
    
    solutions = []

    def backtrack(col, carry, mapping, all_letters):
        if col < 0:
            if carry == 0:
                # Ensure all letters are mapped before creating the solution
                if all(l in mapping for l in all_letters):
                    solution_str = "".join([_to_base_char(mapping[c]) if c in mapping else c for c in puzzle_string.upper()])
                    solutions.append(solution_str)
            return

        current_col_letters = set(w[col] for w in addends_padded if w[col] != ' ')
        if result_padded[col] != ' ':
            current_col_letters.add(result_padded[col])
        
        unassigned_letters = sorted([l for l in current_col_letters if l not in mapping])
        
        available_digits = [d for d in range(base) if d not in mapping.values()]
        
        for p in permutations(available_digits, len(unassigned_letters)):
            temp_mapping = dict(zip(unassigned_letters, p))

            if any(temp_mapping.get(l) == 0 and l in first_letters for l in unassigned_letters):
                continue

            full_col_mapping = mapping.copy()
            full_col_mapping.update(temp_mapping)
            
            try:
                col_sum = carry + sum(full_col_mapping[w[col]] for w in addends_padded if w[col] != ' ')
                result_digit = full_col_mapping[result_padded[col]]
            except KeyError:
                continue

            if col_sum % base == result_digit:
                new_carry = col_sum // base
                backtrack(col - 1, new_carry, full_col_mapping, all_letters)

    backtrack(max_len - 1, 0, constraints.copy(), all_letters)
    
    if not solutions:
        return ["No solution found"]
    return sorted(list(set(solutions)))

def _solve_generic_puzzle(puzzle_string, base=10, constraints=None):
    if constraints is None:
        constraints = {}
    """
    Solves a cryptarithmetic puzzle using a brute-force permutation approach.
    """
    words, unique_letters = parse_puzzle(puzzle_string)

    if any(l not in unique_letters for l in constraints.keys()):
        return ["Invalid constraint: A letter in the constraint is not in the puzzle."]
    if len(set(constraints.values())) != len(constraints.values()):
        return ["Invalid constraint: Digits in constraints must be unique."]
    if any(d >= base for d in constraints.values()):
        return [f"Invalid constraint: A digit is greater than or equal to the base {base}."]

    first_letters = {word[0] for word in words}
    for letter, digit in constraints.items():
        if letter in first_letters and digit == 0:
            return [f"Invalid constraint: Letter '{letter}' cannot be zero."]

    if len(unique_letters) > base:
        return [f"Too many unique letters for base {base}. The puzzle is unsolvable."]

    letters_to_solve = sorted([l for l in unique_letters if l not in constraints])
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

        sorted_unique_letters = sorted(list(unique_letters))
        from_str = "".join(sorted_unique_letters)
        to_str = "".join([_to_base_char(mapping[l]) for l in sorted_unique_letters])
        table = str.maketrans(from_str, to_str)

        equation = puzzle_string.upper().replace("=", "==")

        # To handle different bases, we replace each word with an explicit
        # base conversion, so `safe_eval` can process it correctly.
        # Sorting words by length descending prevents substring replacement issues (e.g., 'IN' in 'JOIN').
        sorted_words = sorted(words, key=len, reverse=True)
        
        eval_equation = equation
        for word in sorted_words:
            digit_word = "".join([_to_base_char(mapping[l]) for l in word])
            eval_equation = re.sub(r'\b' + word + r'\b', f'int("{digit_word}", {base})', eval_equation)

        if safe_eval(eval_equation):
            solutions.append(puzzle_string.upper().translate(table))
            
    if not solutions:
        return ["No solution found"]
    return solutions

def solve_cryptarithm(puzzle_string, base=10, constraints=None):
    if constraints is None:
        constraints = {}
    """
    Solves a cryptarithmetic puzzle.
    Delegates to the appropriate solver based on the operator.
    """
    if '+' in puzzle_string and all(op not in puzzle_string for op in '*/-'):
        return _solve_addition_puzzle(puzzle_string, base=base, constraints=constraints)
    else:
        return _solve_generic_puzzle(puzzle_string, base=base, constraints=constraints)