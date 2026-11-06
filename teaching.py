"""Small replayable finite-domain arithmetic rules, independent of solver search."""

from copy import deepcopy
from fractions import Fraction
from itertools import product
from math import prod
import time

from parser import Number, Word, Operation, parse_multi_puzzle, _parse_expression


def variables(node):
    if isinstance(node, (Word, Number)):
        return {
            d
            for d in (node.letters if isinstance(node, Word) else node.digits)
            if isinstance(d, str)
        }
    return variables(node.left) | variables(node.right)


def interval(node, domains, base):
    if isinstance(node, (Word, Number)):
        lo = hi = 0
        for digit in node.letters if isinstance(node, Word) else node.digits:
            values = domains[digit] if isinstance(digit, str) else [digit]
            if not values:
                return None
            lo, hi = lo * base + min(values), hi * base + max(values)
        return Fraction(lo), Fraction(hi)
    a, b = interval(node.left, domains, base), interval(node.right, domains, base)
    if a is None or b is None:
        return None
    if node.op == "+":
        return a[0] + b[0], a[1] + b[1]
    if node.op == "-":
        return a[0] - b[1], a[1] - b[0]
    if node.op == "*":
        values = [x * y for x in a for y in b]
        return min(values), max(values)
    if node.op == "/" and not b[0] <= 0 <= b[1]:
        values = [x / y for x in a for y in b]
        return min(values), max(values)
    if node.op == "^" and b[0] == b[1] and b[0].denominator == 1 and 0 <= b[0] <= 16:
        e = int(b[0])
        values = [a[0] ** e, a[1] ** e]
        if a[0] <= 0 <= a[1] and e > 0:
            values.append(Fraction(0))
        return min(values), max(values)
    return None


def residues(node, domains, base, modulus):
    if isinstance(node, (Word, Number)):
        possible = {0}
        for digit in node.letters if isinstance(node, Word) else node.digits:
            values = domains[digit] if isinstance(digit, str) else [digit]
            possible = {(x * base + d) % modulus for x in possible for d in values}
        return possible
    a, b = (
        residues(node.left, domains, base, modulus),
        residues(node.right, domains, base, modulus),
    )
    if a is None or b is None:
        return None
    if node.op == "+":
        return {(x + y) % modulus for x in a for y in b}
    if node.op == "-":
        return {(x - y) % modulus for x in a for y in b}
    if node.op == "*":
        return {(x * y) % modulus for x in a for y in b}
    if node.op == "^":
        exp = interval(node.right, domains, base)
        if exp and exp[0] == exp[1] and exp[0].denominator == 1 and 0 <= exp[0] <= 64:
            return {pow(x, int(exp[0]), modulus) for x in a}
    return None


class Rule:
    def __init__(self, name, source, involved, possible):
        self.name, self.source, self.involved, self.possible = (
            name,
            source,
            sorted(involved),
            possible,
        )


def _linear_rule(name, source, terms, domains):
    coefficients, constant = {}, 0
    for coefficient, digit in terms:
        if isinstance(digit, str):
            coefficients[digit] = coefficients.get(digit, 0) + coefficient
        else:
            constant += coefficient * digit
    coefficients = {v: c for v, c in coefficients.items() if c}
    names = sorted(coefficients)

    def possible(ds):
        support = {v: set() for v in names}
        if prod(len(ds[v]) for v in names) <= 20_000:
            for values in product(*(ds[v] for v in names)):
                if (
                    sum(coefficients[v] * d for v, d in zip(names, values)) + constant
                    == 0
                ):
                    for v, d in zip(names, values):
                        support[v].add(d)
        else:
            for v in names:
                lo = sum(
                    min(coefficients[w] * min(ds[w]), coefficients[w] * max(ds[w]))
                    for w in names
                    if w != v
                )
                hi = sum(
                    max(coefficients[w] * min(ds[w]), coefficients[w] * max(ds[w]))
                    for w in names
                    if w != v
                )
                support[v] = {
                    d for d in ds[v] if lo <= -constant - coefficients[v] * d <= hi
                }
        return support

    return Rule(name, source, names, possible)


def build_rules(spec):
    from solver import inspect_puzzle

    info = inspect_puzzle(spec)
    domains = deepcopy(info["domains"])
    base, rules = info["base"], []
    named = [v for v in info["variables"] if not v.startswith("?")]
    groups = ([named] if spec.get("distinct", True) else []) + spec.get(
        "distinct_groups", []
    )
    for i, group in enumerate(groups):

        def distinct(ds, group=group):
            return {
                v: {
                    d
                    for d in ds[v]
                    if all(w == v or len(ds[w]) != 1 or ds[w][0] != d for w in group)
                }
                for v in group
            }

        rules.append(
            Rule("distinctness", f"Distinctness group {i + 1}", group, distinct)
        )

    for i, equation in enumerate(parse_multi_puzzle(spec["equations"])):
        involved = variables(equation)
        source = spec["equations"][i]

        def bound_possible(ds, equation=equation, involved=involved):
            support = {v: set() for v in involved}
            for v in involved:
                for d in ds[v]:
                    probe = dict(ds, **{v: [d]})
                    a, b = (
                        interval(equation.left, probe, base),
                        interval(equation.right, probe, base),
                    )
                    if a is None or b is None or max(a[0], b[0]) <= min(a[1], b[1]):
                        support[v].add(d)
            return support

        rules.append(Rule("interval", source, involved, bound_possible))
        for modulus, name in [(2, "parity"), (base, "final-digit")]:

            def modular(ds, equation=equation, involved=involved, modulus=modulus):
                support = {v: set() for v in involved}
                for v in involved:
                    for d in ds[v]:
                        probe = dict(ds, **{v: [d]})
                        a, b = (
                            residues(equation.left, probe, base, modulus),
                            residues(equation.right, probe, base, modulus),
                        )
                        if a is None or b is None or a & b:
                            support[v].add(d)
                return support

            rules.append(Rule(name, f"{source} modulo {modulus}", involved, modular))

        def summands(node):
            if isinstance(node, (Word, Number)):
                return [node]
            if node.op == "+":
                a, b = summands(node.left), summands(node.right)
                return None if a is None or b is None else a + b
            return None

        def digit_list(node):
            return node.letters if isinstance(node, Word) else node.digits

        addends = summands(equation.left)
        is_subtract = (
            isinstance(equation.left, Operation)
            and equation.left.op == "-"
            and all(
                isinstance(n, (Word, Number))
                for n in [equation.left.left, equation.left.right]
            )
        )
        if isinstance(equation.right, (Word, Number)) and (addends or is_subtract):
            operands = (
                [equation.left.left, equation.left.right] if is_subtract else addends
            )
            arrays = [digit_list(n) for n in [*operands, equation.right]]
            width = max(map(len, arrays))
            carries = [f"$carry:{i}:{c}" for c in range(width + 1)]
            for c, name in enumerate(carries):
                domains[name] = (
                    [0]
                    if c in (0, width)
                    else list(range(2 if is_subtract else len(operands)))
                )
            for c in range(width):
                column = [a[-1 - c] if c < len(a) else 0 for a in arrays]
                if is_subtract:
                    terms = [
                        (1, column[0]),
                        (-1, column[1]),
                        (-1, carries[c]),
                        (base, carries[c + 1]),
                        (-1, column[-1]),
                    ]
                    rule_name = "column-borrow"
                else:
                    terms = [(1, d) for d in column[:-1]] + [
                        (1, carries[c]),
                        (-base, carries[c + 1]),
                        (-1, column[-1]),
                    ]
                    rule_name = "column-carry"
                rules.append(
                    _linear_rule(rule_name, f"{source}; column {c + 1}", terms, domains)
                )

    for constraint in spec.get("constraints", []):
        kind = constraint["kind"]
        expr = _parse_expression(constraint["expr"])
        involved = variables(expr)
        if kind in ("modular", "divisible"):
            modulus = constraint.get("modulus", constraint.get("divisor"))
            remainder = constraint.get("remainder", 0)
            if (
                type(modulus) is not int
                or not 1 <= modulus <= 100
                or type(remainder) is not int
            ):
                continue

            def divisible(
                ds, expr=expr, involved=involved, modulus=modulus, remainder=remainder
            ):
                support = {v: set() for v in involved}
                for v in involved:
                    for d in ds[v]:
                        r = residues(expr, dict(ds, **{v: [d]}), base, modulus)
                        if r is None or remainder % modulus in r:
                            support[v].add(d)
                return support

            rules.append(
                Rule(
                    "divisibility" if kind == "divisible" else "modular",
                    str(constraint),
                    involved,
                    divisible,
                )
            )
        elif kind == "inequality":
            comparison = constraint.get("value", 0)
            rhs = (
                _parse_expression(comparison)
                if isinstance(comparison, str)
                else Number([comparison])
                if 0 <= comparison < base
                else None
            )
            if rhs is None:
                # Decimal-valued API integers are not radix numerals.
                rhs_interval = (Fraction(comparison), Fraction(comparison))
            involved |= variables(rhs) if rhs else set()
            op = constraint.get("op", "<")

            def inequality(
                ds,
                expr=expr,
                rhs=rhs,
                rhs_interval=None if rhs else rhs_interval,
                involved=involved,
                op=op,
            ):
                support = {v: set() for v in involved}
                for v in involved:
                    for d in ds[v]:
                        probe = dict(ds, **{v: [d]})
                        a, b = (
                            interval(expr, probe, base),
                            interval(rhs, probe, base) if rhs else rhs_interval,
                        )
                        possible = a is None or b is None
                        if not possible:
                            possible = {
                                "<": a[0] < b[1],
                                "<=": a[0] <= b[1],
                                ">": a[1] > b[0],
                                ">=": a[1] >= b[0],
                                "=": max(a[0], b[0]) <= min(a[1], b[1]),
                                "!=": not (a[0] == a[1] == b[0] == b[1]),
                            }.get(op, True)
                        if possible:
                            support[v].add(d)
                return support

            rules.append(
                Rule("inequality-interval", str(constraint), involved, inequality)
            )
    return info, domains, rules


def propagate(spec, timeout=2, max_steps=500):
    info, domains, rules = build_rules(spec)
    steps, deadline, changed = [], time.monotonic() + max(0.01, min(timeout, 30)), True
    exhausted = False
    while changed and not any(not d for d in domains.values()):
        changed = False
        for index, rule in enumerate(rules):
            if time.monotonic() >= deadline or len(steps) >= max_steps:
                exhausted = True
                break
            premises = {v: list(domains[v]) for v in rule.involved}
            support = rule.possible(domains)
            for v in rule.involved:
                remaining = sorted(set(domains[v]) & support[v])
                if remaining != domains[v]:
                    removed = sorted(set(domains[v]) - set(remaining))
                    steps.append(
                        {
                            "id": len(steps) + 1,
                            "rule": rule.name,
                            "rule_index": index,
                            "source": rule.source,
                            "premises": premises,
                            "variable": v,
                            "removed": removed,
                            "remaining": remaining,
                            "text": f"{rule.name}: {v} cannot be {', '.join(map(str, removed))}; remaining {remaining}.",
                        }
                    )
                    domains[v] = remaining
                    changed = True
            if any(not d for d in domains.values()):
                break
        if exhausted:
            break
    visible = {v: domains[v] for v in info["variables"]}
    contradiction = any(not d for d in domains.values())
    solved = not contradiction and all(len(d) == 1 for d in visible.values())
    checked = False
    verification_error, verification_status = None, None
    if solved:
        from solver import validate_assignment_strict

        try:
            checked = validate_assignment_strict(
                spec, {v: d[0] for v, d in visible.items()}
            )
            contradiction = not checked
        except ValueError as exc:
            verification_error = str(exc)
            verification_status = (
                "unsupported" if type(exc).__name__ == "Unsupported" else "invalid"
            )
            contradiction = False
    return {
        "steps": steps,
        "domains": visible,
        "carry_domains": {v: d for v, d in domains.items() if v.startswith("$carry:")},
        "solved": bool(solved and checked),
        "contradiction": contradiction,
        "exhausted": exhausted,
        "verification_error": verification_error,
        "verification_status": verification_status,
        "message": "Finite elementary-rule propagation; stalled domains are not proof that other digits are feasible.",
    }


def _replay_domains(spec, steps):
    _, domains, rules = build_rules(spec)
    for step in steps:
        try:
            rule = rules[step["rule_index"]]
            if step["rule"] != rule.name or step["source"] != rule.source:
                return None
            premises = step["premises"]
            # A rule may produce several simultaneous reductions from one snapshot.
            if any(not set(domains[v]).issubset(premises[v]) for v in rule.involved):
                return None
            support = rule.possible(dict(domains, **premises))
            v = step["variable"]
            if (
                v not in rule.involved
                or sorted(set(premises[v]) - support[v]) != step["removed"]
            ):
                return None
            remaining = sorted(set(premises[v]) & support[v])
            if remaining != step["remaining"]:
                return None
            domains[v] = sorted(set(domains[v]) & set(remaining))
        except (KeyError, IndexError, TypeError, ValueError):
            return None
    return domains


def replay_steps(spec, steps):
    """Recompute each rule from its recorded premises; reject changed deductions."""
    return _replay_domains(spec, steps) is not None


def replay_proof(spec, proof):
    """Check branch coverage and every saved local deduction, without solver search."""
    from solver import validate_assignment_strict

    try:
        rows = proof["rows"]
        if not rows or any(row["node"] != i for i, row in enumerate(rows)):
            return False
        children, verified, found = {}, {}, []
        for i, row in enumerate(rows):
            parent = row["parent"]
            if i == 0:
                if (
                    parent is not None
                    or row["assumptions"]
                    or row["input_domains"] != spec.get("domains", {})
                ):
                    return False
            else:
                if type(parent) is not int or not 0 <= parent < i:
                    return False
                ancestor = rows[parent]
                if (
                    ancestor["outcome"] != "case-split"
                    or row["assumptions"][:-1] != ancestor["assumptions"]
                ):
                    return False
                assumption = row["assumptions"][-1]
                var, digit = assumption["variable"], assumption["digit"]
                if (
                    var != ancestor["split_variable"]
                    or digit not in ancestor["split_digits"]
                ):
                    return False
                expected = dict(ancestor["domains"], **{var: [digit]})
                if row["input_domains"] != expected:
                    return False
                children.setdefault(parent, []).append((digit, i))
            case = dict(spec, domains=row["input_domains"])
            ds = _replay_domains(case, row["steps"])
            if ds is None:
                return False
            visible = {v: d for v, d in ds.items() if not v.startswith("$carry:")}
            carries = {v: d for v, d in ds.items() if v.startswith("$carry:")}
            if row["domains"] != visible or row["carry_domains"] != carries:
                return False
            outcome = row["outcome"]
            all_fixed = all(len(d) == 1 for d in visible.values())
            assignment = {v: d[0] for v, d in visible.items()} if all_fixed else None
            if outcome == "checked-solution":
                if not all_fixed or not validate_assignment_strict(case, assignment):
                    return False
                found.append(assignment)
                verified[i] = True
            elif outcome in {"rule-contradiction", "exact-arithmetic-rejection"}:
                if not any(not d for d in ds.values()) and not (
                    all_fixed and not validate_assignment_strict(case, assignment)
                ):
                    return False
                verified[i] = True
            elif outcome == "case-split":
                if (
                    row["split_digits"] != visible[row["split_variable"]]
                    or len(row["split_digits"]) < 2
                ):
                    return False
            elif outcome == "stalled":
                verified[i] = False
            else:
                return False
        for i in reversed(range(len(rows))):
            if rows[i]["outcome"] != "case-split":
                continue
            descendants = children.get(i, [])
            digits = [digit for digit, _ in descendants]
            covered = sorted(digits) == sorted(rows[i]["split_digits"]) and len(
                digits
            ) == len(set(digits))
            verified[i] = covered and all(verified[child] for _, child in descendants)
            if rows[i].get("branches_complete") and not verified[i]:
                return False
        if proof["complete"] and not verified[0]:
            return False
        if proof.get("status") == "exhaustive" and not verified[0]:
            return False
        return found == [s["assignment"] for s in proof["solutions"]]
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def proof_search(spec, options=None):
    """Explicit finite case splits over elementary propagation, never hidden CP search."""
    options = options or {}
    deadline = time.monotonic() + max(0.01, min(float(options.get("timeout", 10)), 30))
    max_depth = max(0, min(int(options.get("depth", 2)), 5))
    max_nodes = max(1, min(int(options.get("max_nodes", 32)), 128))
    rows, solutions = [], []

    def visit(case, assumptions, depth, parent=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or len(rows) >= max_nodes:
            return False
        deduction = propagate(case, timeout=min(1, remaining))
        node = {
            "node": len(rows),
            "parent": parent,
            "depth": depth,
            "assumptions": assumptions,
            "input_domains": deepcopy(case.get("domains", {})),
            **deduction,
        }
        rows.append(node)
        if deduction["contradiction"]:
            node["outcome"] = "rule-contradiction"
            return True
        if deduction["solved"]:
            assignment = {v: ds[0] for v, ds in deduction["domains"].items()}
            solutions.append({"assignment": assignment, "rendered": []})
            node["outcome"] = "checked-solution"
            return True
        choices = [
            (len(ds), v) for v, ds in deduction["domains"].items() if len(ds) > 1
        ]
        if not choices:
            # A fixed assignment with unsupported evaluation is not a contradiction.
            node["outcome"] = "stalled"
            return False
        if depth >= max_depth or deduction["exhausted"]:
            node["outcome"] = "stalled"
            return False
        _, variable = min(choices)
        node["outcome"], node["split_variable"] = "case-split", variable
        node["split_digits"] = deduction["domains"][variable]
        complete = True
        for digit in deduction["domains"][variable]:
            child = dict(
                case, domains=dict(deduction["domains"], **{variable: [digit]})
            )
            if not visit(
                child,
                [*assumptions, {"variable": variable, "digit": digit}],
                depth + 1,
                node["node"],
            ):
                complete = False
        node["branches_complete"] = complete
        return complete

    complete = visit(spec, [], 0)
    return {
        "rows": rows,
        "solutions": solutions,
        "complete": complete,
        "status": "exhaustive" if complete else "inconclusive",
        "message": "Replayable local rules plus explicit digit case splits. Exhaustive means every branch was closed or exactly checked; depth, node, and time limits otherwise leave the result inconclusive.",
    }
