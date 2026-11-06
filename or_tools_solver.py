"""Exact bounded compilation of rational digit equations to CP-SAT."""

from dataclasses import dataclass
from fractions import Fraction
from math import factorial
import re
import time
from ortools.sat.python import cp_model
from parser import Number, Word, Operation, parse_multi_puzzle, _parse_expression

MAX_INT = 10**15
TABLE_LIMIT = 100_000


class Unsupported(ValueError):
    pass


def walk(node):
    yield node
    if isinstance(node, Operation):
        yield from walk(node.left)
        yield from walk(node.right)


def prepare(spec):
    base = spec.get("base", 10)
    if type(base) is not int or not 2 <= base <= 36:
        raise ValueError("Base must be an integer between 2 and 36.")
    lines = spec.get("equations", [])
    if isinstance(lines, str):
        lines = lines.splitlines()
    if (
        not isinstance(lines, list)
        or not lines
        or not all(isinstance(x, str) and x.strip() for x in lines)
    ):
        raise ValueError("Enter at least one nonempty equation.")
    if sum(map(len, lines)) > 10_000:
        raise Unsupported("Puzzle exceeds 10,000 characters.")
    asts = parse_multi_puzzle(lines)
    constraints = spec.get("constraints", [])
    if not isinstance(constraints, list):
        raise ValueError("Constraints must be a list.")
    extra = []
    for c in constraints:
        if not isinstance(c, dict) or "kind" not in c or "expr" not in c:
            raise ValueError("Each constraint requires kind and expr.")
        if re.search(r"\?(?!\d)", c["expr"]):
            raise ValueError(
                "Constraint expressions require explicit anonymous references such as ?1, not raw ?."
            )
        extra.append(_parse_expression(c["expr"]))
        for key in ("value", "modulus", "divisor", "other", "remainder"):
            if isinstance(c.get(key), str):
                if re.search(r"\?(?!\d)", c[key]):
                    raise ValueError(
                        "Use explicit anonymous references in constraint parameters."
                    )
                extra.append(_parse_expression(c[key]))
    variables, leading = set(), set()
    for root in asts + extra:
        for node in walk(root):
            if isinstance(node, (Word, Number)):
                digits = node.letters if isinstance(node, Word) else node.digits
                for d in digits:
                    if isinstance(d, str):
                        variables.add(d)
                    elif d >= base:
                        raise ValueError(f"Fixed digit {d} is invalid in base {base}.")
                if len(digits) > 1:
                    if isinstance(digits[0], str):
                        leading.add(digits[0])
                    elif digits[0] == 0:
                        raise ValueError("Multi-digit numerals cannot begin with zero.")
    domains = {
        v: list(range(1 if v in leading else 0, base)) for v in sorted(variables)
    }
    for v, values in spec.get("domains", {}).items():
        if v not in domains or not isinstance(values, list) or not values:
            raise ValueError(f"Invalid domain for {v}.")
        if any(type(x) is not int or not 0 <= x < base for x in values):
            raise ValueError("Domain digits must be within the base.")
        domains[v] = sorted(set(values) & set(domains[v]))
    for v, d in spec.get("assignments", {}).items():
        if v not in domains:
            raise ValueError(
                "Invalid constraint: A letter in the constraint is not in the puzzle."
            )
        if type(d) is not int or not 0 <= d < base:
            raise ValueError(
                f"Invalid constraint: A digit is greater than or equal to the base {base}."
            )
        if v in leading and d == 0:
            raise ValueError(f"Invalid constraint: Letter '{v}' cannot be zero.")
        domains[v] = [d] if d in domains[v] else []
    named = sorted(v for v in variables if not v.startswith("?"))
    groups = ([named] if spec.get("distinct", True) else []) + spec.get(
        "distinct_groups", []
    )
    for group in groups:
        if not isinstance(group, list) or any(v not in variables for v in group):
            raise ValueError("Distinctness groups must contain puzzle variables.")
    return dict(
        base=base,
        equations=lines,
        asts=asts,
        extra=[_parse_expression(c["expr"]) for c in constraints],
        variables=sorted(variables),
        leading=sorted(leading),
        domains=domains,
        groups=groups,
    )


def inspect_puzzle(spec):
    p = prepare(spec)
    return {k: p[k] for k in ("base", "equations", "variables", "leading", "domains")}


def evaluate(node, assignment, base):
    if isinstance(node, (Number, Word)):
        value = 0
        for d in node.digits if isinstance(node, Number) else node.letters:
            value = value * base + (assignment[d] if isinstance(d, str) else d)
        return Fraction(value)
    a, b = evaluate(node.left, assignment, base), evaluate(node.right, assignment, base)
    if node.op == "+":
        return a + b
    if node.op == "-":
        return a - b
    if node.op == "*":
        return a * b
    if node.op == "/":
        return a / b
    if node.op == "=":
        return a == b
    if node.op == "^":
        if b.denominator != 1 or not 0 <= b <= 64:
            raise Unsupported("Exponent must be an integer within 0..64.")
        return a ** int(b)
    raise ValueError(f"Unknown operation {node.op}")


def predicate(value, c):
    if value.denominator != 1:
        return False
    n, kind = int(value), c["kind"]
    if kind in ("divisible", "modular"):
        modulus = c.get("modulus", c.get("divisor", 0))
        if type(modulus) is not int or modulus <= 0:
            raise ValueError("Modulus must be a positive integer.")
        return n % modulus == c.get("remainder", 0)
    if kind in ("prime", "composite"):
        from sympy import isprime

        return bool(isprime(n)) if kind == "prime" else n > 1 and not isprime(n)
    if kind == "consecutive_primes":
        from sympy import isprime, nextprime

        other = c.get("other", 0)
        return bool(
            isprime(n) and isprime(other) and nextprime(min(n, other)) == max(n, other)
        )
    if kind in ("square", "power", "root"):
        degree = 2 if kind == "square" else c.get("degree", 2)
        if type(degree) is not int or not 2 <= degree <= 16:
            raise ValueError("Degree must be within 2..16.")
        if n < 0 and degree % 2 == 0:
            return False
        from sympy import integer_nthroot

        return bool(integer_nthroot(abs(n), degree)[1])
    if kind == "factorial":
        return n in {factorial(i) for i in range(19)}
    if kind == "inequality":
        op, v = c.get("op", "<"), c.get("value", 0)
        if type(v) is not int:
            raise ValueError("Comparison value must be an integer.")
        ops = {
            "<": n < v,
            "<=": n <= v,
            ">": n > v,
            ">=": n >= v,
            "!=": n != v,
            "=": n == v,
        }
        if op not in ops:
            raise ValueError("Unsupported comparison operator.")
        return ops[op]
    raise ValueError(f"Unsupported constraint kind: {kind}")


def validate_assignment(spec, assignment):
    try:
        p = prepare(spec)
        if any(
            v not in assignment
            or type(assignment[v]) is not int
            or assignment[v] not in d
            for v, d in p["domains"].items()
        ):
            return False
        if any(len({assignment[v] for v in g}) != len(g) for g in p["groups"]):
            return False
        if not all(evaluate(a, assignment, p["base"]) for a in p["asts"]):
            return False
        for e, c in zip(p["extra"], spec.get("constraints", [])):
            resolved = dict(c)
            for key in ("value", "modulus", "divisor", "other", "remainder"):
                if isinstance(c.get(key), str):
                    value = evaluate(_parse_expression(c[key]), assignment, p["base"])
                    if value.denominator != 1:
                        return False
                    resolved[key] = int(value)
            if not predicate(evaluate(e, assignment, p["base"]), resolved):
                return False
        return True
    except (ValueError, ZeroDivisionError, KeyError, OverflowError):
        return False


@dataclass
class Term:
    expr: object
    lo: int
    hi: int


class Compiler:
    def __init__(self, p):
        self.p, self.model, self.vars = p, cp_model.CpModel(), {}
        self.deferred = []
        self.column_equations = 0
        for v, domain in p["domains"].items():
            self.vars[v] = (
                self.model.new_int_var_from_domain(
                    cp_model.Domain.from_values(domain), v
                )
                if domain
                else self.model.new_int_var(0, 0, v)
            )
            if not domain:
                self.model.add(False)
        for g in p["groups"]:
            self.model.add_all_different([self.vars[v] for v in g])

    def term(self, expr, lo, hi):
        if max(abs(lo), abs(hi)) > MAX_INT:
            raise Unsupported(
                "Intermediate arithmetic exceeds exact integer range (10^15)."
            )
        if lo == hi:
            return Term(lo, lo, hi)
        var = self.model.new_int_var(lo, hi, "arithmetic")
        self.model.add(var == expr)
        return Term(var, lo, hi)

    def add(self, a, b, sign=1):
        return self.term(
            a.expr + sign * b.expr,
            a.lo + (b.lo if sign == 1 else -b.hi),
            a.hi + (b.hi if sign == 1 else -b.lo),
        )

    def mul(self, a, b):
        if a.lo == a.hi == 0 or b.lo == b.hi == 0:
            return Term(0, 0, 0)
        bounds = [x * y for x in (a.lo, a.hi) for y in (b.lo, b.hi)]
        lo, hi = min(bounds), max(bounds)
        if max(abs(lo), abs(hi)) > MAX_INT:
            raise Unsupported("Product exceeds exact integer range (10^15).")
        if a.lo == a.hi:
            return self.term(a.lo * b.expr, lo, hi)
        if b.lo == b.hi:
            return self.term(b.lo * a.expr, lo, hi)
        var = self.model.new_int_var(lo, hi, "product")
        self.model.add_multiplication_equality(var, [a.expr, b.expr])
        return Term(var, lo, hi)

    def power(self, a, e):
        if e.lo < 0 or e.hi > 64:
            raise Unsupported("Restrict exponent domain to integers within 0..64.")
        if e.lo == e.hi:
            result = Term(1, 1, 1)
            for _ in range(e.lo):
                result = self.mul(result, a)
            return result
        if (a.hi - a.lo + 1) * (e.hi - e.lo + 1) > TABLE_LIMIT:
            raise Unsupported(
                "Variable-power table exceeds 100,000 entries; restrict domains."
            )
        rows = []
        for b in range(a.lo, a.hi + 1):
            for exponent in range(e.lo, e.hi + 1):
                v = b**exponent
                if abs(v) > MAX_INT:
                    raise Unsupported("Power exceeds exact integer range (10^15).")
                rows.append((b, exponent, v))
        lo, hi = min(r[2] for r in rows), max(r[2] for r in rows)
        var = self.model.new_int_var(lo, hi, "power")
        self.model.add_allowed_assignments([a.expr, e.expr, var], rows)
        return Term(var, lo, hi)

    def expression(self, node):
        one = Term(1, 1, 1)
        if isinstance(node, (Word, Number)):
            value = Term(0, 0, 0)
            for d in node.letters if isinstance(node, Word) else node.digits:
                if isinstance(d, str):
                    domain = self.p["domains"][d] or [0]
                    digit = Term(self.vars[d], min(domain), max(domain))
                else:
                    digit = Term(d, d, d)
                value = self.add(
                    self.mul(
                        value, Term(self.p["base"], self.p["base"], self.p["base"])
                    ),
                    digit,
                )
            return value, one
        a, ad = self.expression(node.left)
        b, bd = self.expression(node.right)
        if node.op in ("+", "-"):
            return self.add(
                self.mul(a, bd), self.mul(b, ad), 1 if node.op == "+" else -1
            ), self.mul(ad, bd)
        if node.op == "*":
            return self.mul(a, b), self.mul(ad, bd)
        if node.op == "/":
            self.model.add(b.expr != 0)
            return self.mul(a, bd), self.mul(ad, b)
        if node.op == "^":
            if not (bd.lo == bd.hi == 1):
                raise Unsupported("Exponent expressions must not contain division.")
            return self.power(a, b), self.power(ad, b)
        raise ValueError(f"Unsupported operation {node.op}")

    def equation(self, ast):
        if self.column_compatible(ast.left) and self.column_compatible(ast.right):
            self.column_equation(ast)
            return
        a, ad = self.expression(ast.left)
        b, bd = self.expression(ast.right)
        self.model.add(self.mul(a, bd).expr == self.mul(b, ad).expr)

    def column_compatible(self, node):
        if isinstance(node, (Word, Number)):
            return True
        if node.op in ("+", "-", "*"):
            return self.column_compatible(node.left) and self.column_compatible(
                node.right
            )
        if node.op == "^":
            try:
                exponent = evaluate(node.right, {}, self.p["base"])
            except (KeyError, ValueError, ZeroDivisionError):
                return False
            return (
                exponent.denominator == 1
                and 0 <= exponent <= 8
                and self.column_compatible(node.left)
            )
        return False

    def columns(self, node):
        zero = Term(0, 0, 0)
        if isinstance(node, (Word, Number)):
            result = []
            for d in reversed(node.letters if isinstance(node, Word) else node.digits):
                if isinstance(d, str):
                    domain = self.p["domains"][d] or [0]
                    result.append(Term(self.vars[d], min(domain), max(domain)))
                else:
                    result.append(Term(d, d, d))
            return result
        a = self.columns(node.left)
        if node.op == "^":
            exponent = int(evaluate(node.right, {}, self.p["base"]))
            result = [Term(1, 1, 1)]
            for _ in range(exponent):
                result = self.convolve(result, a)
            return result
        b = self.columns(node.right)
        if node.op == "*":
            return self.convolve(a, b)
        return [
            self.add(
                a[i] if i < len(a) else zero,
                b[i] if i < len(b) else zero,
                1 if node.op == "+" else -1,
            )
            for i in range(max(len(a), len(b)))
        ]

    def convolve(self, a, b):
        if len(a) + len(b) > 512:
            raise Unsupported("Column expression exceeds 512 digit positions.")
        result = [Term(0, 0, 0) for _ in range(len(a) + len(b) - 1)]
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                result[i + j] = self.add(result[i + j], self.mul(x, y))
        return result

    def column_equation(self, ast):
        a, b = self.columns(ast.left), self.columns(ast.right)
        carry, zero = Term(0, 0, 0), Term(0, 0, 0)
        base = self.p["base"]
        for i in range(max(len(a), len(b))):
            coefficient = self.add(
                a[i] if i < len(a) else zero, b[i] if i < len(b) else zero, -1
            )
            total = self.add(coefficient, carry)
            if i == max(len(a), len(b)) - 1:
                self.model.add(total.expr == 0)
            else:
                lo, hi = total.lo // base, total.hi // base
                carry = Term(
                    self.model.new_int_var(
                        lo, hi, f"carry_{self.column_equations}_{i + 1}"
                    ),
                    lo,
                    hi,
                )
                self.model.add(total.expr == base * carry.expr)
        self.column_equations += 1

    def integer_expression(self, node):
        n, d = self.expression(node)
        if d.lo == d.hi == 1:
            return n
        if d.lo == d.hi and d.lo != 0:
            values = [Fraction(n.lo, d.lo), Fraction(n.hi, d.lo)]
            lo, hi = min(values).__ceil__(), max(values).__floor__()
        else:
            bound = max(abs(n.lo), abs(n.hi))
            lo, hi = -bound, bound
        if lo > hi:
            self.model.add(False)
            return Term(0, 0, 0)
        q = self.model.new_int_var(lo, hi, "exact_quotient")
        self.model.add(self.mul(Term(q, lo, hi), d).expr == n.expr)
        return Term(q, lo, hi)

    def parameter(self, c, key, default=0):
        value = c.get(key, default)
        if isinstance(value, str):
            return self.integer_expression(_parse_expression(value))
        if type(value) is not int:
            raise ValueError(f"{key} must be an integer or expression.")
        return Term(value, value, value)

    def constraint(self, node, c):
        n = self.integer_expression(node)
        kind = c["kind"]
        if kind == "inequality":
            other = self.parameter(c, "value")
            op = c.get("op", "<")
            if op == "<":
                relation = n.expr < other.expr
            elif op == "<=":
                relation = n.expr <= other.expr
            elif op == ">":
                relation = n.expr > other.expr
            elif op == ">=":
                relation = n.expr >= other.expr
            elif op == "=":
                relation = n.expr == other.expr
            elif op == "!=":
                relation = n.expr != other.expr
            else:
                raise ValueError("Unsupported comparison operator.")
            self.model.add(relation)
            return
        if kind in ("divisible", "modular"):
            modulus = self.parameter(c, "modulus", c.get("divisor", 0))
            remainder = self.parameter(c, "remainder")
            if modulus.lo == modulus.hi and modulus.lo <= 0:
                raise ValueError("Modulus must be a positive integer.")
            self.model.add(modulus.expr > 0)
            self.model.add(remainder.expr >= 0)
            self.model.add(remainder.expr < modulus.expr)
            if modulus.hi < 1:
                self.model.add(False)
                return
            bounds = [
                Fraction(x, m)
                for x in (n.lo - remainder.hi, n.hi - remainder.lo)
                for m in (max(1, modulus.lo), modulus.hi)
            ]
            lo, hi = min(bounds).__floor__(), max(bounds).__floor__()
            q = Term(self.model.new_int_var(lo, hi, "modular_quotient"), lo, hi)
            self.model.add(self.add(self.mul(modulus, q), remainder).expr == n.expr)
            return
        if kind in ("square", "power", "root"):
            degree = 2 if kind == "square" else c.get("degree", 2)
            if type(degree) is not int or not 2 <= degree <= 16:
                raise ValueError("Degree must be within 2..16.")
            from sympy import integer_nthroot

            bound = int(integer_nthroot(max(abs(n.lo), abs(n.hi)), degree)[0])
            lo = -bound if degree % 2 else 0
            root = Term(self.model.new_int_var(lo, bound, "exact_root"), lo, bound)
            self.model.add(
                self.power(root, Term(degree, degree, degree)).expr == n.expr
            )
            return
        if kind == "factorial":
            values = sorted(
                {factorial(i) for i in range(19) if n.lo <= factorial(i) <= n.hi}
            )
            self.model.add_allowed_assignments([n.expr], [(v,) for v in values])
            return
        if kind == "consecutive_primes":
            other = self.parameter(c, "other")
            if max(n.hi, other.hi) - min(n.lo, other.lo) > TABLE_LIMIT:
                raise Unsupported("Consecutive-prime domain exceeds 100,000 values.")
            from sympy import primerange, nextprime

            rows = []
            for a in primerange(max(2, min(n.lo, other.lo)), max(n.hi, other.hi) + 1):
                b = int(nextprime(a))
                if n.lo <= a <= n.hi and other.lo <= b <= other.hi:
                    rows.append((int(a), b))
                if n.lo <= b <= n.hi and other.lo <= a <= other.hi:
                    rows.append((b, int(a)))
            self.model.add_allowed_assignments([n.expr, other.expr], rows)
            return
        if n.hi - n.lo + 1 > TABLE_LIMIT:
            if kind in ("prime", "composite"):
                self.deferred.append((node, c))
                return
            raise Unsupported(
                "Predicate domain exceeds 100,000 values; restrict domains."
            )
        values = [v for v in range(n.lo, n.hi + 1) if predicate(Fraction(v), c)]
        self.model.add_allowed_assignments([n.expr], [(v,) for v in values])


def render(lines, assignment):
    explicit = [int(x) for line in lines for x in re.findall(r"\?(\d+)", line)]
    counter = [max(explicit, default=0)]

    def replace(match):
        t = match.group()
        if t.startswith("["):
            return t
        if t == "?":
            counter[0] += 1
            t = f"?{counter[0]}"
        digit = assignment[t]
        return str(digit) if digit < 10 else chr(55 + digit)

    return [re.sub(r"\[\d+\]|\?\d*|[A-Z]", replace, line.upper()) for line in lines]


def solve_z3(spec, p, result, started, cap, timeout):
    """Experimental independently encoded equation-only backend."""
    try:
        import z3
    except ImportError as exc:
        raise Unsupported(
            "Install z3-solver to use the experimental Z3 backend."
        ) from exc
    if spec.get("constraints"):
        raise Unsupported(
            "Experimental Z3 currently supports equations, domains and distinctness only."
        )
    engine = z3.Solver()
    variables = {v: z3.Int(v) for v in p["variables"]}
    for v, domain in p["domains"].items():
        engine.add(z3.Or([variables[v] == d for d in domain]))
    for group in p["groups"]:
        if group:
            engine.add(z3.Distinct([variables[v] for v in group]))

    def expression(node):
        if isinstance(node, (Number, Word)):
            value = 0
            for d in node.digits if isinstance(node, Number) else node.letters:
                value = value * p["base"] + (variables[d] if isinstance(d, str) else d)
            return value, 1
        a, ad = expression(node.left)
        b, bd = expression(node.right)
        if node.op == "+":
            return a * bd + b * ad, ad * bd
        if node.op == "-":
            return a * bd - b * ad, ad * bd
        if node.op == "*":
            return a * b, ad * bd
        if node.op == "/":
            engine.add(b != 0)
            return a * bd, ad * b
        if node.op == "^":
            try:
                exponent = evaluate(node.right, {}, p["base"])
            except KeyError as exc:
                raise Unsupported(
                    "Z3 backend currently requires constant exponents."
                ) from exc
            if exponent.denominator != 1 or not 0 <= exponent <= 64:
                raise Unsupported("Exponent must be within 0..64.")
            # Repeated multiplication remains in exact integer arithmetic.
            n, d = 1, 1
            for _ in range(int(exponent)):
                n, d = n * a, d * ad
            return n, d
        raise ValueError("Unsupported Z3 operation.")

    for ast in p["asts"]:
        a, ad = expression(ast.left)
        b, bd = expression(ast.right)
        engine.add(a * bd == b * ad)
    complete = False
    while cap is None or len(result["solutions"]) < cap:
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            break
        engine.set(timeout=max(1, int(remaining * 1000)))
        status = engine.check()
        if status == z3.unsat:
            complete = True
            break
        if status == z3.unknown:
            result["message"] = "Z3 returned unknown: " + engine.reason_unknown()
            break
        assignment = {
            v: engine.model().eval(x, model_completion=True).as_long()
            for v, x in variables.items()
        }
        if not validate_assignment(spec, assignment):
            raise RuntimeError("Independent exact checker rejected a Z3 solution.")
        result["solutions"].append(
            dict(assignment=assignment, rendered=render(p["equations"], assignment))
        )
        engine.add(z3.Or([x != assignment[v] for v, x in variables.items()]))
    count = len(result["solutions"])
    result.update(
        complete=complete,
        unique=False if count > 1 else True if complete and count == 1 else None,
        status="satisfiable"
        if count
        else "unsatisfiable"
        if complete
        else "incomplete",
    )
    if not result["message"]:
        result["message"] = (
            "Search complete."
            if complete
            else "Z3 search stopped; completeness is not established."
        )
    result["elapsed"] = time.monotonic() - started
    return result


def solve_puzzle(spec):
    started = time.monotonic()
    backend = spec.get("backend", "cp-sat") if isinstance(spec, dict) else "cp-sat"
    result = dict(
        status="invalid",
        solutions=[],
        complete=False,
        unique=None,
        elapsed=0.0,
        backend=backend,
        message="",
    )
    try:
        if not isinstance(spec, dict):
            raise ValueError("Puzzle must be an object.")
        mode, limit, timeout = (
            spec.get("mode", "first"),
            spec.get("limit", 100),
            spec.get("timeout", 30),
        )
        if mode not in ("first", "unique", "limit", "all"):
            raise ValueError("Unknown search mode.")
        if type(limit) is not int or limit < 1:
            raise ValueError("Solution limit must be positive.")
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 86400:
            raise ValueError("Time limit must be within (0,86400] seconds.")
        p = prepare(spec)
        cap = (
            1
            if mode == "first"
            else 2
            if mode == "unique"
            else limit
            if mode == "limit"
            else None
        )
        if backend == "z3":
            return solve_z3(spec, p, result, started, cap, timeout)
        if backend != "cp-sat":
            raise Unsupported(f"Backend '{backend}' is not available; select cp-sat.")
        compiler = Compiler(p)
        for a in p["asts"]:
            compiler.equation(a)
        for e, c in zip(p["extra"], spec.get("constraints", [])):
            compiler.constraint(e, c)
        invalid = compiler.model.validate()
        if invalid:
            raise Unsupported("CP-SAT cannot represent this model: " + invalid)

        class Callback(cp_model.CpSolverSolutionCallback):
            def __init__(self):
                super().__init__()
                self.failed, self.seen = False, set()

            def on_solution_callback(self):
                assignment = {v: self.value(x) for v, x in compiler.vars.items()}
                key = tuple(assignment.items())
                if key in self.seen:
                    return
                self.seen.add(key)
                if any(
                    not predicate(evaluate(node, assignment, p["base"]), c)
                    for node, c in compiler.deferred
                ):
                    return
                if not validate_assignment(spec, assignment):
                    self.failed = True
                    self.stop_search()
                    return
                result["solutions"].append(
                    dict(
                        assignment=assignment,
                        rendered=render(p["equations"], assignment),
                    )
                )
                if cap is not None and len(result["solutions"]) >= cap:
                    self.stop_search()

        callback, solver = Callback(), cp_model.CpSolver()
        solver.parameters.enumerate_all_solutions = True
        solver.parameters.max_time_in_seconds = max(
            0.001, timeout - (time.monotonic() - started)
        )
        status = solver.solve(compiler.model, callback)
        if callback.failed:
            raise RuntimeError(
                "Independent exact arithmetic check rejected a solver assignment."
            )
        if status == cp_model.MODEL_INVALID:
            raise RuntimeError("Solver rejected compiled model.")
        complete = status in (cp_model.OPTIMAL, cp_model.INFEASIBLE)
        count = len(result["solutions"])
        result.update(
            complete=complete,
            unique=False if count > 1 else True if complete and count == 1 else None,
            status="satisfiable"
            if count
            else "unsatisfiable"
            if complete
            else "incomplete",
            message="Search complete."
            if complete
            else "Stopped at solution or time limit; completeness is not established.",
        )
        result["statistics"] = dict(
            branches=solver.num_branches,
            conflicts=solver.num_conflicts,
            wall_time=solver.wall_time,
            column_equations=compiler.column_equations,
            deferred_predicates=len(compiler.deferred),
        )
    except Unsupported as exc:
        result.update(status="unsupported", message=str(exc))
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        result.update(status="invalid", message=str(exc))
    except Exception as exc:
        result.update(status="error", message=str(exc))
    result["elapsed"] = time.monotonic() - started
    return result


def solve_with_cp_sat(puzzles, base=10, constraints=None):
    assignments = constraints or {}
    if len(set(assignments.values())) != len(assignments.values()):
        return ["Invalid constraint: Digits in constraints must be unique."]
    spec = dict(
        equations=[puzzles] if isinstance(puzzles, str) else puzzles,
        base=base,
        assignments=assignments,
        mode="all",
    )
    r = solve_puzzle(spec)
    if r["solutions"]:
        return sorted(
            "\n".join(s["rendered"])
            + "\n"
            + " ".join(f"{k}={v}" for k, v in sorted(s["assignment"].items()))
            for s in r["solutions"]
        )
    if r["status"] == "unsatisfiable":
        if (
            len([v for v in inspect_puzzle(spec)["variables"] if not v.startswith("?")])
            > base
        ):
            return [
                f"Too many unique letters for base {base}. The puzzle is unsolvable."
            ]
        return ["No solution found"]
    return [r["message"]]
