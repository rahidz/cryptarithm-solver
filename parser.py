"""Position-aware parser for digit arithmetic, without Python evaluation."""

import re
from dataclasses import dataclass


@dataclass
class Number:
    digits: list


@dataclass
class Word:
    letters: list


@dataclass
class Operation:
    op: str
    left: object
    right: object


ATOM = r"(?:[A-Z0-9]|\?\d*|\[\d+\])+"


class Parser:
    def __init__(self, text, counter=None):
        self.counter = counter if counter is not None else [0]
        self.tokens, self.i = [], 0
        pos = 0
        while pos < len(text):
            if text[pos].isspace():
                pos += 1
                continue
            m = re.match(ATOM + r"|\*\*|[+*/^()=\-]", text[pos:].upper())
            if not m:
                raise ValueError(f"Unexpected character at column {pos + 1}")
            self.tokens.append((m.group(), pos))
            pos += len(m.group())
        self.tokens.append(("", len(text)))

    def peek(self):
        return self.tokens[self.i][0]

    def take(self):
        result = self.peek()
        self.i += 1
        return result

    def fail(self, message):
        raise ValueError(f"{message} at column {self.tokens[self.i][1] + 1}")

    def expression(self, minimum=0):
        token = self.peek()
        if token in ("+", "-"):
            self.take()
            left = Operation(token, Number([0]), self.expression(25))
        elif token == "(":
            self.take()
            left = self.expression()
            if self.peek() != ")":
                self.fail("Expected ')'")
            self.take()
        elif token and re.fullmatch(ATOM, token):
            self.take()
            digits = []
            for digit in re.findall(r"\[\d+\]|\?\d*|[A-Z0-9]", token):
                if digit == "?":
                    self.counter[0] += 1
                    digits.append(f"?{self.counter[0]}")
                elif digit.startswith("?"):
                    digits.append(digit)
                elif digit.startswith("["):
                    digits.append(int(digit[1:-1]))
                else:
                    digits.append(int(digit) if digit.isdigit() else digit)
            left = (
                Word(digits)
                if any(isinstance(d, str) for d in digits)
                else Number(digits)
            )
        else:
            self.fail("Expected a numeral or expression")
        priority = {"+": 10, "-": 10, "*": 20, "/": 20, "^": 30, "**": 30}
        while self.peek() in priority and priority[self.peek()] >= minimum:
            op = self.take()
            right = self.expression(
                priority[op] if op in ("^", "**") else priority[op] + 1
            )
            left = Operation("^" if op == "**" else op, left, right)
        return left


def _parse_expression(text, counter=None):
    parser = Parser(text, counter)
    result = parser.expression()
    if parser.peek():
        parser.fail("Unexpected token")
    return result


def parse_puzzle(text, counter=None):
    parser = Parser(text, counter)
    left = parser.expression()
    if parser.peek() != "=":
        parser.fail("Expected exactly one '='")
    parser.take()
    right = parser.expression()
    if parser.peek():
        parser.fail("Unexpected token")
    return Operation("=", left, right)


def parse_multi_puzzle(lines):
    explicit = [int(x) for line in lines for x in re.findall(r"\?(\d+)", line)]
    counter = [max(explicit, default=0)]
    return [parse_puzzle(line, counter) for line in lines]
