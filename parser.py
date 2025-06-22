import re
from dataclasses import dataclass
from typing import List, Union

@dataclass
class Number:
    digits: List[int]

@dataclass
class Word:
    letters: List[str]

@dataclass
class Operation:
    op: str
    left: Union[Number, Word, 'Operation']
    right: Union[Number, Word, 'Operation']

def _parse_operand(s: str) -> Union[Word, Number, Operation]:
    s = s.strip()
    if s.isdigit():
        return Number(digits=[int(d) for d in s])
    elif s.isalpha():
        return Word(letters=list(s))
    # This is where we handle nested expressions by recursively calling the expression parser.
    elif s.startswith('(') and s.endswith(')'):
        return _parse_expression(s[1:-1])
    else:
        # If it's not a simple word/number or a parenthesis block, it must be a complex expression.
        return _parse_expression(s)

def _find_rightmost_operator(s: str, operators: List[str]) -> int:
    """Find the rightmost operator at the top level of an expression."""
    level = 0
    for i in range(len(s) - 1, -1, -1):
        if s[i] == ')':
            level += 1
        elif s[i] == '(':
            level -= 1
        elif level == 0 and s[i] in operators:
            return i
    return -1

def _parse_expression(s: str) -> Union[Operation, Word, Number]:
    """Recursively parse an expression respecting operator precedence."""
    # Addition and Subtraction (lowest precedence)
    pos = _find_rightmost_operator(s, ['+', '-'])
    if pos != -1:
        op = s[pos]
        left = _parse_expression(s[:pos])
        right = _parse_expression(s[pos+1:])
        return Operation(op=op, left=left, right=right)

    # Multiplication and Division (higher precedence)
    pos = _find_rightmost_operator(s, ['*', '/'])
    if pos != -1:
        op = s[pos]
        left = _parse_expression(s[:pos])
        right = _parse_expression(s[pos+1:])
        return Operation(op=op, left=left, right=right)
        
    # If no operators, it's a simple operand (Word or Number)
    return _parse_operand(s)

def parse_puzzle(puzzle_string: str) -> Operation:
    """
    Parses the puzzle string into a full AST.
    """
    puzzle_string = puzzle_string.upper().replace(" ", "")
    
    parts = puzzle_string.split('=')
    if len(parts) != 2:
        raise ValueError("Puzzle must contain exactly one '='.")
        
    left_str, right_str = parts
    
    left_expr = _parse_expression(left_str)
    right_expr = _parse_operand(right_str) # The result is always a single word/number.

    return Operation(op='=', left=left_expr, right=right_expr)