from itertools import permutations
from evaluator import safe_eval
from parser import parse_puzzle

def solve_cryptarithm(puzzle_string):
    """
    Solves a cryptarithmetic puzzle.

    Args:
        puzzle_string (str): The puzzle to solve (e.g., "SEND + MORE = MONEY").

    Returns:
        list[str]: A list of solutions, or an error message inside a list.
    """
    words, unique_letters = parse_puzzle(puzzle_string)

    if unique_letters is None or words is None:
        return ["Invalid puzzle"]

    first_letters = {word[0] for word in words}
    sorted_letters = sorted(list(unique_letters))
    
    solutions = []
    digits = range(10)
    for p in permutations(digits, len(sorted_letters)):
        # Create the mapping from letters to digits
        mapping = dict(zip(sorted_letters, p))

        # Leading zero check
        if any(mapping[letter] == 0 for letter in first_letters):
            continue

        # Create the equation to evaluate
        # str.maketrans requires string arguments for mapping
        from_str = ''.join(sorted_letters)
        to_str = ''.join(map(str, p))
        table = str.maketrans(from_str, to_str)
        
        # Translate the original puzzle string into a numeric equation
        equation = puzzle_string.upper().translate(table)
        
        # Replace '=' with '==' for evaluation and check for validity
        if safe_eval(equation.replace("=", "==")):
            solutions.append(equation)
            
    if not solutions:
        return ["No solution found"]
    return solutions