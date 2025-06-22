import re

def parse_puzzle(puzzle_string):
    """
    Parses the puzzle string to extract words and unique letters.

    Args:
        puzzle_string (str): The cryptarithmetic puzzle.

    Returns:
        tuple: A tuple containing the list of words and a set of unique letters.
               Returns (None, None) if the puzzle is invalid.
    """
    # Find all sequences of letters and numbers
    words = re.findall('[A-Z]+', puzzle_string.upper())
    
    # Get all unique letters from the words
    unique_letters = set(''.join(words))

    # Validate the number of unique letters
    if len(unique_letters) > 10:
        return (None, None)

    return (words, unique_letters)