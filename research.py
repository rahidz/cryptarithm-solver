"""Bounded symbolic families and independently replayed finite certificates."""

from copy import deepcopy
import itertools
import math
import re
import time


def parametric(spec, options=None):
    """Fix digit values and analyze the resulting exact rational functions of base."""
    import sympy as sp
    from parser import Number, Word, parse_multi_puzzle

    options = options or {}
    if spec.get("constraints") or spec.get("layout"):
        raise ValueError(
            "Families require equations without extra predicates or layouts."
        )
    lines = spec.get("equations", [])
    if isinstance(lines, str):
        lines = lines.splitlines()
    if not lines or sum(map(len, lines)) > 2000:
        raise ValueError(
            "Families require equations totaling at most 2,000 characters."
        )
    assignments = spec.get("assignments", {})
    if any(type(d) is not int or not 0 <= d < 36 for d in assignments.values()):
        raise ValueError("Fixed digits must be integers in 0..35.")
    b = sp.Symbol("base", integer=True, positive=True)
    variables, fixed_digits, denominators = set(), [], []

    def bounded(value):
        value = sp.cancel(value)
        for part in sp.fraction(value):
            poly = sp.Poly(part, b)
            if poly.degree() > 128 or any(
                abs(int(c)).bit_length() > 8192 for c in poly.all_coeffs()
            ):
                raise ValueError(
                    "Symbolic family exceeds degree 128 or 8,192-bit coefficients."
                )
        return value

    def expression(node):
        if isinstance(node, (Number, Word)):
            digits = node.digits if isinstance(node, Number) else node.letters
            values = []
            for digit in digits:
                if isinstance(digit, str):
                    variables.add(digit)
                    if digit not in assignments:
                        raise ValueError(
                            f"Fix every variable before family analysis; missing {digit}."
                        )
                    digit = assignments[digit]
                fixed_digits.append(digit)
                values.append(digit)
            if len(values) > 1 and values[0] == 0:
                raise ValueError("Multi-digit numerals cannot begin with zero.")
            if len(values) > 64:
                raise ValueError("Family numerals support at most 64 digits.")
            return bounded(
                sum(digit * b**i for i, digit in enumerate(reversed(values)))
            )
        left, right = expression(node.left), expression(node.right)
        if node.op == "+":
            return bounded(left + right)
        if node.op == "-":
            return bounded(left - right)
        if node.op == "*":
            return bounded(left * right)
        if node.op == "/":
            denominators.append(right)
            return bounded(left / right) if right != 0 else sp.Integer(0)
        if node.op == "^":
            if not right.is_Integer or not 0 <= right <= 16:
                raise ValueError(
                    "Family powers require a base-independent exponent in 0..16."
                )
            return bounded(left ** int(right))
        raise ValueError("Unsupported family operator.")

    identities = []
    for ast in parse_multi_puzzle(lines):
        numerator, denominator = sp.fraction(
            sp.cancel(expression(ast.left) - expression(ast.right))
        )
        identities.append(sp.Poly(numerator, b).as_expr())
        denominators.append(denominator)
    if set(assignments) - variables:
        raise ValueError("Assignments contain variables absent from the equations.")
    groups = (
        [sorted(v for v in variables if not v.startswith("?"))]
        if spec.get("distinct", True)
        else []
    ) + spec.get("distinct_groups", [])
    for group in groups:
        if any(v not in variables for v in group):
            raise ValueError("Distinctness group contains an unknown variable.")
        if len({assignments[v] for v in group}) != len(group):
            raise ValueError("Fixed assignments violate distinctness.")
    for variable, domain in spec.get("domains", {}).items():
        if variable not in variables or assignments[variable] not in domain:
            raise ValueError("Fixed assignments violate a supplied digit domain.")
    minimum = max(2, max(fixed_digits, default=0) + 1)
    lo, hi = int(options.get("min_base", 2)), int(options.get("max_base", 36))
    if not 2 <= lo <= hi <= 36:
        raise ValueError("Family inspection bases must lie within 2..36.")
    rows = []
    for base in range(lo, hi + 1):
        legal = base >= minimum
        defined = legal and all(d.subs(b, base) != 0 for d in denominators)
        holds = defined and all(n.subs(b, base) == 0 for n in identities)
        rows.append(
            {
                "base": base,
                "legal_digits": legal,
                "defined": bool(defined),
                "satisfies": bool(holds),
            }
        )
    universal = all(n == 0 for n in identities) and all(d != 0 for d in denominators)
    conditions = list(
        dict.fromkeys(str(sp.factor(d)) + " != 0" for d in denominators if d != 1)
    )
    return {
        "kind": "families",
        "rows": rows,
        "complete": True,
        "polynomials": [str(sp.factor(n)) for n in identities],
        "denominator_conditions": conditions,
        "minimum_base": minimum,
        "identity": universal,
        "message": (
            "An original denominator is identically zero; there are no defined bases."
            if any(d == 0 for d in denominators)
            else "Polynomial identity proved for every base with legal digits and all listed nonzero-denominator conditions."
            if universal
            else "Not an identity. Displayed base solutions were tested by exact polynomial substitution."
        ),
    }


class FinitePuzzle:
    """Independent grammar and arithmetic: no imports from the solver or its parser."""

    def __init__(self, spec):
        if not isinstance(spec, dict) or spec.get("constraints") or spec.get("layout"):
            raise ValueError(
                "Finite certificates support equations without extra predicates or layouts."
            )
        self.base = spec.get("base", 10)
        if type(self.base) is not int or not 2 <= self.base <= 10:
            raise ValueError("Finite certificate bases must lie within 2..10.")
        equations = spec.get("equations", [])
        if (
            not isinstance(equations, list)
            or len(equations) != 1
            or not isinstance(equations[0], str)
        ):
            raise ValueError("Finite certificates require exactly one equation.")
        source = equations[0].upper()
        if len(source) > 500 or not re.fullmatch(r"[A-Z0-9+*()=\s\-]+", source):
            raise ValueError(
                "Finite certificates accept letters, decimal digits, +, -, *, and parentheses only."
            )
        self.tokens = re.findall(r"[A-Z0-9]+|[+*()=\-]", source) + [""]
        self.position = 0
        self.variables, self.leading = set(), set()
        self.left = self.parse_sum()
        self.expect("=")
        self.right = self.parse_sum()
        self.expect("")
        self.variables = sorted(self.variables)
        if len(self.variables) > 6:
            raise ValueError(
                "Finite certificates support at most six letter variables."
            )
        self.groups = (
            [self.variables] if spec.get("distinct", True) else []
        ) + spec.get("distinct_groups", [])
        if any(
            not isinstance(group, list) or any(v not in self.variables for v in group)
            for group in self.groups
        ):
            raise ValueError("Distinctness groups must contain puzzle variables.")
        assignments, restrictions = spec.get("assignments", {}), spec.get("domains", {})
        if set(assignments) - set(self.variables) or set(restrictions) - set(
            self.variables
        ):
            raise ValueError("Unknown variable in assignment or domain.")
        self.domains = {}
        for variable in self.variables:
            domain = list(range(1 if variable in self.leading else 0, self.base))
            if variable in restrictions:
                values = restrictions[variable]
                if not isinstance(values, list) or any(
                    type(d) is not int or not 0 <= d < self.base for d in values
                ):
                    raise ValueError("Invalid digit domain.")
                domain = [d for d in domain if d in values]
            if variable in assignments:
                digit = assignments[variable]
                if type(digit) is not int or not 0 <= digit < self.base:
                    raise ValueError("Invalid fixed digit.")
                domain = [digit] if digit in domain else []
            self.domains[variable] = domain
        self.possibilities = math.prod(map(len, self.domains.values()))
        if self.possibilities > 100_000:
            raise ValueError(
                "Finite certificate domain exceeds 100,000 assignments; restrict digits."
            )

    def expect(self, token):
        if self.tokens[self.position] != token:
            raise ValueError(
                f"Expected {token or 'end of equation'} in certificate expression."
            )
        self.position += 1

    def parse_sum(self):
        left = self.parse_product()
        while self.tokens[self.position] in {"+", "-"}:
            op = self.tokens[self.position]
            self.position += 1
            left = (op, left, self.parse_product())
        return left

    def parse_product(self):
        left = self.parse_atom()
        while self.tokens[self.position] == "*":
            self.position += 1
            left = ("*", left, self.parse_atom())
        return left

    def parse_atom(self):
        token = self.tokens[self.position]
        if token in {"+", "-"}:
            self.position += 1
            return (token, ("word", "0"), self.parse_atom())
        if token == "(":
            self.position += 1
            result = self.parse_sum()
            self.expect(")")
            return result
        if not token or not token.isalnum():
            raise ValueError("Expected a numeral in certificate expression.")
        self.position += 1
        for character in token:
            if character.isalpha():
                self.variables.add(character)
            elif int(character) >= self.base:
                raise ValueError("Fixed digit is outside the base.")
        if len(token) > 1:
            if token[0] == "0":
                raise ValueError("Multi-digit numerals cannot begin with zero.")
            if token[0].isalpha():
                self.leading.add(token[0])
        return ("word", token)

    def value(self, node, assignment):
        if node[0] == "word":
            value = 0
            for character in node[1]:
                digit = assignment[character] if character.isalpha() else int(character)
                value = self.base * value + digit
            return value
        left, right = self.value(node[1], assignment), self.value(node[2], assignment)
        return (
            left + right
            if node[0] == "+"
            else left - right
            if node[0] == "-"
            else left * right
        )

    def enumerate(self, deadline):
        solutions, examined = [], 0
        for digits in itertools.product(*(self.domains[v] for v in self.variables)):
            if time.monotonic() >= deadline:
                return solutions, examined, False
            examined += 1
            assignment = dict(zip(self.variables, digits))
            if any(
                len({assignment[v] for v in group}) != len(group)
                for group in self.groups
            ):
                continue
            if self.value(self.left, assignment) == self.value(self.right, assignment):
                solutions.append(assignment)
        return solutions, examined, True


def verify_certificate(evidence, timeout=30):
    """Recompute finite coverage; an assignment list alone is not a proof."""
    try:
        if evidence.get("version") != 1:
            raise ValueError("Unknown certificate version.")
        puzzle = FinitePuzzle(evidence["spec"])
        actual, examined, complete = puzzle.enumerate(
            time.monotonic() + max(0.001, float(timeout))
        )
        claimed = evidence["solutions"]
        if not isinstance(claimed, list) or any(
            not isinstance(s, dict) for s in claimed
        ):
            raise ValueError("Invalid certificate solution list.")
        # Require canonical digit types as JSON booleans compare equal to integers.
        if any(
            set(s) != set(puzzle.variables)
            or any(type(v) is not int for v in s.values())
            for s in claimed
        ):
            raise ValueError(
                "Certificate assignments require exactly the puzzle's integer digits."
            )
        normalize = lambda values: sorted(tuple(sorted(s.items())) for s in values)
        valid = complete and normalize(actual) == normalize(claimed)
        return {
            "valid": valid,
            "complete": complete,
            "examined": examined,
            "solution_count": len(actual),
            "unique": len(actual) == 1 if complete else None,
            "message": "Exhaustive finite replay matches."
            if valid
            else "Replay incomplete or solution list does not match.",
        }
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        return {"valid": False, "complete": False, "message": str(exc)}


def certificate(spec, options=None):
    """Create then independently replay a small complete assignment certificate."""
    options = options or {}
    budget = max(
        0.001, min(float(options.get("timeout", spec.get("timeout", 30))), 300)
    )
    deadline = time.monotonic() + budget
    puzzle = FinitePuzzle(spec)
    solutions, examined, complete = puzzle.enumerate(deadline)
    evidence = {"version": 1, "spec": deepcopy(spec), "solutions": solutions}
    verification = (
        verify_certificate(evidence, max(0.001, deadline - time.monotonic()))
        if complete
        else {"valid": False, "complete": False, "message": "Creation exceeded budget."}
    )
    return {
        "kind": "certificate",
        "certificate": evidence if complete else None,
        "verification": verification,
        "complete": bool(verification["valid"]),
        "rows": [
            {
                "assignments_checked": examined,
                "solutions": len(solutions),
                "creation_complete": complete,
                "replay_valid": verification["valid"],
            }
        ],
        "message": "Independent finite arithmetic enumeration and replay; not a general formal proof certificate.",
    }
