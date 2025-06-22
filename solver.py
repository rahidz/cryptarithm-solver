import re
from itertools import permutations
from parser import parse_puzzle

def solve_cryptarithm(puzzle_string):
    """
    Solves a cryptarithmetic puzzle.

    Args:
        puzzle_string (str): The puzzle to solve (e.g., "SEND + MORE = MONEY").

    Returns:
        str: The solved puzzle as a string, or an error message.
    """
    words, unique_letters = parse_puzzle(puzzle_string)

    if unique_letters is None or words is None:
        return "Invalid puzzle"

    first_letters = {word[0] for word in words}
    sorted_letters = sorted(list(unique_letters))
    
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
        
        try:
            # Replace '=' with '==' for evaluation and check for validity
            if eval(re.sub(r'([A-Z0-9]+)', r'int(\1)', equation).replace('=', '==')):
                return equation
        except (SyntaxError, TypeError):
            # If the translated equation is not valid Python, skip it
            continue
            
    return "No solution found"