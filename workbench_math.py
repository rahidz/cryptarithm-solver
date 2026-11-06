"""Visual arithmetic, checked hints, and bounded research experiments."""

from copy import deepcopy
import itertools
import random
import re
import time


def _digits(text, raw=False):
    pattern = r"\[\d+\]|[A-Z0-9?]" if raw else r"\[\d+\]|\?\d+|[A-Z0-9?]"
    tokens = re.findall(pattern, text.upper())
    if not tokens or "".join(tokens) != text.upper():
        raise ValueError(
            "A layout row must contain only digits, letters, [digit] tokens, or ? cells."
        )
    return tokens


def _numeral(value, base):
    if value < 0:
        raise ValueError("A visual numeral cannot be negative.")
    if value == 0:
        return "0"
    out = []
    while value:
        value, digit = divmod(value, base)
        out.append(str(digit) if digit < 10 else f"[{digit}]")
    return "".join(reversed(out))


def normalize_spec(spec):
    """Compile a visual layout, sharing cells across all derived equations."""
    out = deepcopy(spec)
    layout = out.pop("layout", None)
    if not layout:
        return out
    base = out.get("base", 10)
    if not isinstance(base, int) or not 2 <= base <= 36:
        raise ValueError("Base must be an integer from 2 to 36.")
    kind = layout.get("kind")
    raw_rows = layout.get("rows", [])
    if not isinstance(raw_rows, list) or not all(isinstance(r, str) for r in raw_rows):
        raise ValueError("Layout rows must be a list of numeral strings.")
    rows = []
    next_id = 0
    for row in raw_rows:
        digits = _digits(row.strip(), raw=True)
        for i, digit in enumerate(digits):
            if digit == "?":
                next_id += 1
                digits[i] = f"?{next_id}"
            elif digit.isdigit() and i and digits[i - 1].startswith("?"):
                # ?13 is one explicit variable, not ?1 followed by fixed digit 3.
                digits[i] = f"[{digit}]"
        rows.append("".join(digits))
    forbidden = out.get("forbidden_blank_digits", [])
    if forbidden:
        if not isinstance(forbidden, list) or any(
            type(d) is not int or not 0 <= d < base for d in forbidden
        ):
            raise ValueError(
                "Forbidden blank digits must be digits in the selected base."
            )
        domains = out.setdefault("domains", {})
        for row in rows:
            for digit in _digits(row):
                if digit.startswith("?"):
                    domains[digit] = [
                        d for d in domains.get(digit, range(base)) if d not in forbidden
                    ]
    equations = []
    constraints = out.setdefault("constraints", [])
    if kind == "addition":
        if len(rows) < 3:
            raise ValueError("Addition needs at least two addends and a result.")
        equations.append(" + ".join(rows[:-1]) + " = " + rows[-1])
    elif kind == "subtraction":
        if len(rows) != 3:
            raise ValueError("Subtraction needs minuend, subtrahend, and result.")
        equations.append(f"{rows[0]} - {rows[1]} = {rows[2]}")
    elif kind == "multiplication":
        if len(rows) < 3:
            raise ValueError("Multiplication needs two factors and a result.")
        a, b = rows[:2]
        partials = rows[2:-1]
        multiplier = _digits(b)
        if partials and len(partials) != len(multiplier):
            raise ValueError(
                "Provide one unshifted partial product per multiplier digit, right to left."
            )
        equations.append(f"{a} * {b} = {rows[-1]}")
        for digit, partial in zip(reversed(multiplier), partials):
            equations.append(f"{a} * {digit} = {partial}")
        if partials:
            terms = [
                f"({p}) * {_numeral(base**i, base)}" for i, p in enumerate(partials)
            ]
            equations.append(" + ".join(terms) + " = " + rows[-1])
    elif kind == "division":
        if len(rows) < 4:
            raise ValueError(
                "Division needs dividend, divisor, quotient, and remainder."
            )
        dividend, divisor, quotient, remainder = rows[:4]
        equations.append(f"{dividend} = {divisor} * {quotient} + {remainder}")
        constraints.extend(
            [
                {"kind": "inequality", "expr": divisor, "op": ">", "value": 0},
                {"kind": "inequality", "expr": remainder, "op": ">=", "value": 0},
                {
                    "kind": "inequality",
                    "expr": f"({remainder}) - ({divisor})",
                    "op": "<",
                    "value": 0,
                },
            ]
        )
        steps = rows[4:]
        qdigits, ndigits = _digits(quotient), _digits(dividend)
        start = len(ndigits) - len(qdigits) + 1
        if start < 1:
            raise ValueError("Quotient cannot have more digits than the dividend.")
        if steps and len(steps) != 2 * len(qdigits):
            raise ValueError(
                "Provide a product and difference row for each quotient digit, left to right."
            )
        current = "".join(ndigits[:start])
        for i, qdigit in enumerate(qdigits):
            if not steps:
                break
            product, difference = steps[2 * i : 2 * i + 2]
            equations.extend(
                [
                    f"{divisor} * {qdigit} = {product}",
                    f"({current}) - ({product}) = {difference}",
                ]
            )
            constraints.append(
                {
                    "kind": "inequality",
                    "expr": f"({difference}) - ({divisor})",
                    "op": "<",
                    "value": 0,
                }
            )
            if i + 1 < len(qdigits):
                current = f"({difference}) * 10 + {ndigits[start + i]}"
        if steps:
            equations.append(f"{steps[-1]} = {remainder}")
    elif kind == "root":
        if len(rows) < 4:
            raise ValueError(
                "Root extraction needs root, radicand, remainder, and the initial square row."
            )
        root, radicand, remainder = rows[:3]
        shown = rows[3:]
        rd, nd = _digits(root), _digits(radicand)
        two = _numeral(2, base)
        if (
            len(nd) not in (2 * len(rd) - 1, 2 * len(rd))
            or len(shown) != 2 * len(rd) - 1
        ):
            raise ValueError(
                "Root extraction needs one initial square and a current/product pair for each subsequent root digit."
            )
        equations.append(f"({root}) * ({root}) + ({remainder}) = {radicand}")
        constraints.extend(
            [
                {"kind": "inequality", "expr": remainder, "op": ">=", "value": 0},
                {
                    "kind": "inequality",
                    "expr": f"({remainder}) - ({two}*({root})+1)",
                    "op": "<",
                    "value": 0,
                },
            ]
        )
        prefix, rest, cursor = "0", "0", 0
        # Square-root extraction brings down two radix digits at a time.
        twice_base = _numeral(2 * base, base)
        for i, digit in enumerate(rd):
            width = len(nd) - 2 * (len(rd) - 1) if i == 0 else 2
            group_digits = nd[cursor : cursor + width]
            group = (
                group_digits[0]
                if width == 1
                else f"({group_digits[0]}*10+{group_digits[1]})"
            )
            cursor += width
            current = f"(({rest})*100+({group}))"
            product = shown[0 if i == 0 else 2 * i]
            if i:
                equations.append(f"{shown[2 * i - 1]} = {current}")
            equations.append(f"{product} = ({twice_base}*({prefix})+{digit})*{digit}")
            rest = f"({current}-({product}))"
            prefix = f"(({prefix})*10+{digit})"
            constraints.extend(
                [
                    {"kind": "inequality", "expr": rest, "op": ">=", "value": 0},
                    {
                        "kind": "inequality",
                        "expr": f"({rest})-({two}*({prefix})+1)",
                        "op": "<",
                        "value": 0,
                    },
                ]
            )
        equations.append(f"{rest} = {remainder}")
    else:
        raise ValueError("Unknown layout kind.")
    out["equations"] = equations
    out["source_layout"] = {"kind": kind, "rows": rows}
    return out


def _solve(spec, **changes):
    from solver import solve_puzzle

    return solve_puzzle(dict(spec, **changes))


def _inspect(spec):
    from solver import inspect_puzzle

    return inspect_puzzle(spec)


def candidates(spec, options=None):
    """A witness proves possibility; only UNSAT proves an exclusion."""
    options = options or {}
    spec = normalize_spec(spec)
    info = _inspect(spec)
    if not info.get("variables"):
        return {"candidates": {}, "message": "No variable digits to inspect."}
    budget = max(0.01, min(float(options.get("timeout", spec.get("timeout", 30))), 300))
    deadline = time.monotonic() + budget
    probe_timeout = max(0.01, min(float(options.get("probe_timeout", 1)), budget))
    requested = options.get("variables", info["variables"])
    result = {}
    for letter in requested:
        if letter not in info["variables"]:
            raise ValueError(f"Unknown digit variable: {letter}")
        domain = list(info["domains"][letter])
        entry = {"possible": [], "excluded": [], "unknown": []}
        for digit in domain:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                entry["unknown"].append(digit)
                continue
            domains = dict(spec.get("domains", {}), **{letter: [digit]})
            answer = _solve(
                spec,
                domains=domains,
                mode="first",
                timeout=min(probe_timeout, remaining),
            )
            if answer["solutions"]:
                entry["possible"].append(digit)
            elif answer["status"] == "unsatisfiable":
                entry["excluded"].append(digit)
            else:
                entry["unknown"].append(digit)
        result[letter] = entry
    return {
        "candidates": result,
        "message": "Possible digits have exact checked witnesses; exclusions are solver-proved. Unchecked or timed-out probes remain unknown.",
    }


def hints(spec, options=None):
    options = options or {}
    spec = normalize_spec(spec)
    started = time.monotonic()
    budget = max(0.01, min(float(options.get("timeout", spec.get("timeout", 30))), 30))
    from teaching import propagate

    deductions = propagate(spec, timeout=min(3, budget))
    info = _inspect(spec)
    steps = []
    for letter in info.get("leading", []):
        steps.append(
            {
                "rule": "leading-digit",
                "kind": "elementary",
                "text": f"{letter} cannot be zero: it begins a multi-digit numeral.",
            }
        )
    for letter, digit in spec.get("assignments", {}).items():
        if spec.get("distinct", True) and not letter.startswith("?"):
            steps.append(
                {
                    "rule": "distinctness",
                    "kind": "elementary",
                    "text": f"{letter} is fixed to {digit}; no other named letter may use {digit}.",
                }
            )
    for equation in spec.get("equations", []):
        # Only plain sums of numerals qualify for this elementary column rule.
        parts = equation.replace(" ", "").upper().split("=")
        if len(parts) != 2 or "+" not in parts[0]:
            continue
        try:
            addends = [_digits(p) for p in parts[0].split("+")]
            result = _digits(parts[1])
        except ValueError:
            continue
        units = " + ".join(a[-1] for a in addends)
        base = spec.get("base", 10)
        steps.append(
            {
                "rule": "units-column",
                "kind": "elementary",
                "text": f"In the units column, {units} = {result[-1]} + {base} × carry. The outgoing carry is between 0 and {len(addends) - 1}.",
            }
        )
    steps.extend(
        {
            "rule": step["rule"],
            "kind": "elementary",
            "text": step["text"],
            "source": step["source"],
            "premises": step["premises"],
        }
        for step in deductions["steps"]
    )
    remaining = budget - (time.monotonic() - started)
    if (
        options.get("search", True)
        and not options.get("elementary_only", False)
        and remaining > 0
    ):
        found = candidates(spec, dict(options, timeout=remaining))
        for letter, values in found["candidates"].items():
            if len(values["possible"]) == 1 and not values["unknown"]:
                digit = values["possible"][0]
                if spec.get("assignments", {}).get(letter) != digit:
                    steps.append(
                        {
                            "rule": "excluded-alternatives",
                            "kind": "solver-proved",
                            "text": f"{letter} = {digit}. A checked solution uses it, and every other allowed digit makes the puzzle inconsistent.",
                        }
                    )
    return {
        **deductions,
        "hints": steps,
        "message": "Elementary rules have replayable domain premises. Solver-proved claims are explicitly search-assisted; stalled domains are not feasibility claims.",
    }


def generate(spec=None, options=None):
    """Generate one deterministic bounded arithmetic instance and prove uniqueness."""
    spec, options = spec or {}, options or {}
    base = spec.get("base", 10)
    if not isinstance(base, int) or not 2 <= base <= 36:
        raise ValueError("Base must be between 2 and 36.")
    seed = int(options.get("seed", 1))
    rng = random.Random(seed)
    kind = options.get("kind", "addition")
    width = int(options.get("width", 2))
    if width not in range(1, 4) or kind not in {
        "addition",
        "subtraction",
        "multiplication",
        "division",
    }:
        raise ValueError(
            "Generation supports widths 1–3 and the four arithmetic operations."
        )
    deadline = time.monotonic() + max(
        0.1, min(float(options.get("timeout", spec.get("timeout", 30))), 300)
    )
    a, b = (
        rng.randrange(base ** (width - 1), base**width),
        rng.randrange(1, base**width),
    )
    if kind == "addition":
        numbers, op = [a, b, a + b], "+"
    elif kind == "subtraction":
        a, b = max(a, b), min(a, b)
        numbers, op = [a, b, a - b], "-"
    elif kind == "multiplication":
        numbers, op = [a, b, a * b], "*"
    else:
        numbers, op = [a * b, b, a], "/"
    numerals = [_numeral(n, base) for n in numbers]
    values = sorted(
        {
            int(t[1:-1]) if t.startswith("[") else int(t)
            for n in numerals
            for t in _digits(n)
        }
    )
    rng.shuffle(values)
    mapping = {v: chr(65 + i) for i, v in enumerate(values)}
    words = [
        "".join(
            mapping[int(t[1:-1]) if t.startswith("[") else int(t)] for t in _digits(n)
        )
        for n in numerals
    ]
    puzzle = {
        "equations": [f"{words[0]} {op} {words[1]} = {words[2]}"],
        "base": base,
        "distinct": True,
        "assignments": {mapping[v]: v for v in values},
        "mode": "unique",
        "timeout": 1,
    }
    order = list(puzzle["assignments"])
    rng.shuffle(order)
    checks, removed = 0, 0
    # Monotonicity makes a single deletion pass sufficient for inclusion-minimality.
    all_decided = True
    for letter in order:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            all_decided = False
            break
        trial = deepcopy(puzzle)
        del trial["assignments"][letter]
        answer = _solve(trial, mode="unique", timeout=min(2, remaining))
        checks += 1
        if answer.get("unique") is True:
            puzzle = trial
            removed += 1
        elif answer.get("unique") is not False:
            all_decided = False
    remaining = deadline - time.monotonic()
    verification = _solve(puzzle, mode="unique", timeout=max(0.01, min(2, remaining)))
    return {
        "spec": puzzle,
        "verification": verification,
        "seed": seed,
        "checks": checks,
        "removed_clues": removed,
        "inclusion_minimal": all_decided and verification.get("unique") is True,
        "message": "Seeded arithmetic with verified clue deletion. Inclusion-minimal means no remaining assignment clue can be removed, not globally fewest clues. No universal human-difficulty rating is claimed.",
    }


def experiment(spec, options=None):
    options = options or {}
    action = options.get("kind", "bases")
    if action in {"families", "certificate"}:
        from research import parametric, certificate

        return {"families": parametric, "certificate": certificate}[action](
            spec, options
        )
    if action == "proof-search":
        from teaching import proof_search

        return proof_search(normalize_spec(spec), options)
    if action == "adversarial":
        return adversarial(spec, options)
    if action == "minimal-clues":
        return minimal_clues(spec, options)
    if action not in {"bases", "backends"}:
        raise ValueError("Experiment kind must be bases, backends, or minimal-clues.")
    deadline = time.monotonic() + max(0.1, min(float(options.get("timeout", 30)), 300))
    rows = []
    if action == "bases":
        lo, hi = int(options.get("min_base", 2)), int(options.get("max_base", 16))
        if not 2 <= lo <= hi <= 36:
            raise ValueError("Base sweep must lie between 2 and 36.")
        variants = [{"base": base} for base in range(lo, hi + 1)]
    else:
        variants = [{"backend": backend} for backend in ["cp-sat", "z3"]]
    complete = True
    for variant in variants:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            complete = False
            break
        case = normalize_spec(dict(spec, **variant))
        answer = _solve(case, mode="all", timeout=min(2, remaining))
        rows.append(
            {
                **variant,
                "status": answer["status"],
                "solutions": len(answer["solutions"]),
                "complete": answer["complete"],
                "elapsed": answer["elapsed"],
                "message": answer["message"],
            }
        )
        if not answer["complete"]:
            complete = False
    return {
        "rows": rows,
        "complete": complete,
        "message": "Finite sweep. Solution counts are exact only for complete rows; different bases are distinct cases.",
    }


def adversarial(spec, options=None):
    """Rank seeded unique puzzles by what the current elementary rules leave open."""
    from teaching import propagate

    options = options or {}
    seed = int(options.get("seed", 1))
    count = max(1, min(int(options.get("count", 3)), 8))
    deadline = time.monotonic() + max(0.1, min(float(options.get("timeout", 30)), 30))
    rows = []
    for i in range(count):
        remaining = deadline - time.monotonic()
        if remaining <= 0.05:
            break
        generated = generate(
            spec,
            dict(
                options,
                kind=options.get("arithmetic_kind", "multiplication"),
                seed=seed + i,
                timeout=min(remaining / 2, 3),
            ),
        )
        if generated["verification"].get("unique") is not True:
            rows.append(
                {
                    "seed": seed + i,
                    "accepted": False,
                    "message": "Uniqueness not established within the generation budget.",
                }
            )
            continue
        remaining = deadline - time.monotonic()
        deduction = propagate(generated["spec"], timeout=max(0.01, min(1, remaining)))
        alternatives = sum(max(0, len(ds) - 1) for ds in deduction["domains"].values())
        rows.append(
            {
                "seed": seed + i,
                "accepted": True,
                "spec": generated["spec"],
                "unique": True,
                "remaining_alternatives": alternatives,
                "elementary_solved": deduction["solved"],
                "rule_steps": len(deduction["steps"]),
                "domains": deduction["domains"],
                "exhausted": deduction["exhausted"],
            }
        )
    rows.sort(key=lambda r: (-r.get("remaining_alternatives", -1), r["seed"]))
    return {
        "rows": rows,
        "complete": len(rows) == count,
        "message": "Seeded unique puzzles ranked by residual digit alternatives under this elementary rule set. This exposes rule gaps, not a universal human-difficulty measure; timed-out propagation is flagged.",
    }


def describe_solution(spec, assignment):
    """Replay ordinary column arithmetic on a checked digit assignment."""
    spec = normalize_spec(spec)
    base = spec.get("base", 10)
    layout = spec.get("source_layout")
    columns, rendered_rows = [], []

    def digits(numeral):
        return [
            int(t[1:-1])
            if t.startswith("[")
            else int(t)
            if t.isdigit()
            else assignment[t]
            for t in _digits(numeral)
        ]

    def value(ds):
        total = 0
        for digit in ds:
            total = total * base + digit
        return total

    def add_rows(stage, operands, result):
        carry = 0
        for col in range(max([len(result), *map(len, operands)])):
            inputs = [a[-1 - col] if col < len(a) else 0 for a in operands]
            total = sum(inputs) + carry
            outgoing, digit = divmod(total, base)
            expected = result[-1 - col] if col < len(result) else 0
            if digit != expected:
                raise ValueError(
                    "Solution does not satisfy a displayed addition column."
                )
            columns.append(
                {
                    "stage": stage,
                    "operation": "addition",
                    "column": col,
                    "inputs": inputs,
                    "carry_in": carry,
                    "carry_out": outgoing,
                    "result": digit,
                    "text": f"Column {col + 1}: {' + '.join(map(str, inputs))} + carry {carry} = {digit} + {base} × {outgoing}.",
                }
            )
            carry = outgoing
        if carry:
            raise ValueError("Addition result is missing a leading carry.")

    def subtract(stage, a, b, result):
        borrow = 0
        for col in range(max(len(a), len(b), len(result))):
            x, y = (
                a[-1 - col] if col < len(a) else 0,
                b[-1 - col] if col < len(b) else 0,
            )
            total = x - y - borrow
            outgoing = int(total < 0)
            digit = total + base * outgoing
            expected = result[-1 - col] if col < len(result) else 0
            if digit != expected:
                raise ValueError(
                    "Solution does not satisfy a displayed subtraction column."
                )
            columns.append(
                {
                    "stage": stage,
                    "operation": "subtraction",
                    "column": col,
                    "inputs": [x, y],
                    "carry_in": borrow,
                    "carry_out": outgoing,
                    "result": digit,
                    "text": f"Column {col + 1}: {x} − {y} − borrow {borrow} + {base} × new borrow {outgoing} = {digit}.",
                }
            )
            borrow = outgoing
        if borrow:
            raise ValueError("Subtraction has a negative result.")

    def multiply(stage, a, digit, result):
        carry = 0
        for col in range(max(len(a), len(result))):
            x = a[-1 - col] if col < len(a) else 0
            outgoing, answer = divmod(x * digit + carry, base)
            expected = result[-1 - col] if col < len(result) else 0
            if answer != expected:
                raise ValueError(
                    "Solution does not satisfy a displayed multiplication column."
                )
            columns.append(
                {
                    "stage": stage,
                    "operation": "multiplication",
                    "column": col,
                    "inputs": [x, digit],
                    "carry_in": carry,
                    "carry_out": outgoing,
                    "result": answer,
                    "text": f"Column {col + 1}: {x} × {digit} + carry {carry} = {answer} + {base} × {outgoing}.",
                }
            )
            carry = outgoing
        if carry:
            raise ValueError("Partial product is missing a leading carry.")

    def numeral_digits(n):
        return [
            int(t[1:-1]) if t.startswith("[") else int(t)
            for t in _digits(_numeral(n, base))
        ]

    if not layout:
        for i, equation in enumerate(spec.get("equations", [])):
            parts = equation.replace(" ", "").upper().split("=")
            if len(parts) != 2:
                continue
            try:
                result = digits(parts[1])
                if "+" in parts[0]:
                    operands = [digits(p) for p in parts[0].split("+")]
                    add_rows(f"Equation {i + 1}", operands, result)
                elif parts[0].count("-") == 1 and not parts[0].startswith("-"):
                    a, b = [digits(p) for p in parts[0].split("-")]
                    subtract(f"Equation {i + 1}", a, b, result)
            except (ValueError, KeyError):
                continue
        return {"kind": "equations", "rows": [], "columns": columns}

    kind, rows = layout["kind"], layout["rows"]
    ds = [digits(row) for row in rows]
    vals = [value(d) for d in ds]
    labels = {
        "addition": [*[f"Addend {i + 1}" for i in range(len(rows) - 1)], "Result"],
        "subtraction": ["Minuend", "Subtrahend", "Difference"],
        "multiplication": [
            "Multiplicand",
            "Multiplier",
            *[f"Partial {i + 1}" for i in range(len(rows) - 3)],
            "Product",
        ],
        "division": [
            "Dividend",
            "Divisor",
            "Quotient",
            "Remainder",
            *[
                f"{'Product' if i % 2 == 0 else 'Difference'} {i // 2 + 1}"
                for i in range(len(rows) - 4)
            ],
        ],
        "root": [
            "Root",
            "Radicand",
            "Remainder",
            "Initial square",
            *[
                f"{'Current' if i % 2 == 0 else 'Product'} {i // 2 + 2}"
                for i in range(len(rows) - 4)
            ],
        ],
    }[kind]
    for label, original, d, n in zip(labels, rows, ds, vals):
        solved = "".join(str(x) if x < 10 else f"[{x}]" for x in d)
        rendered_rows.append(
            {"label": label, "original": original, "solved": solved, "value": str(n)}
        )
    if kind == "addition":
        add_rows("Addition", ds[:-1], ds[-1])
    elif kind == "subtraction":
        subtract("Subtraction", *ds)
    elif kind == "multiplication":
        partials = ds[2:-1] or [numeral_digits(vals[0] * d) for d in reversed(ds[1])]
        for i, (digit, partial) in enumerate(zip(reversed(ds[1]), partials)):
            multiply(f"Partial product {i + 1}", ds[0], digit, partial)
        add_rows(
            "Sum of shifted partials",
            [p + [0] * i for i, p in enumerate(partials)],
            ds[-1],
        )
    elif kind == "division":
        cursor = len(ds[0]) - len(ds[2]) + 1
        current = value(ds[0][:cursor])
        for i, digit in enumerate(ds[2]):
            product = vals[1] * digit
            difference = current - product
            multiply(f"Division product {i + 1}", ds[1], digit, numeral_digits(product))
            subtract(
                f"Division subtraction {i + 1}",
                numeral_digits(current),
                numeral_digits(product),
                numeral_digits(difference),
            )
            if i + 1 < len(ds[2]):
                current = difference * base + ds[0][cursor + i]
    return {"kind": kind, "rows": rendered_rows, "columns": columns}


def minimal_clues(spec, options=None):
    """Exhaust all subsets of up to eight assignment clues, within a budget."""
    options = options or {}
    spec = normalize_spec(spec)
    clues = list(spec.get("assignments", {}).items())
    if len(clues) > 8:
        raise ValueError(
            "The exhaustive minimal-clue experiment supports at most eight assignment clues."
        )
    deadline = time.monotonic() + max(0.1, min(float(options.get("timeout", 30)), 300))
    rows, winners = [], []
    unresolved_smaller = False
    for size in range(len(clues) + 1):
        for subset in itertools.combinations(clues, size):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {
                    "rows": rows,
                    "complete": False,
                    "minimal": None,
                    "message": "Budget exhausted; global minimality is not established.",
                }
            answer = _solve(
                spec, assignments=dict(subset), mode="unique", timeout=min(2, remaining)
            )
            rows.append(
                {
                    "clues": dict(subset),
                    "size": size,
                    "unique": answer.get("unique"),
                    "status": answer["status"],
                }
            )
            if answer.get("unique") is True:
                winners.append(dict(subset))
            elif answer.get("unique") is None:
                unresolved_smaller = True
        if winners:
            return {
                "rows": rows,
                "complete": not unresolved_smaller,
                "minimal": None if unresolved_smaller else size,
                "winners": winners,
                "message": "Minimality is certified only within subsets of the supplied assignment clues and only if all smaller subsets were decided.",
            }
    return {
        "rows": rows,
        "complete": not unresolved_smaller,
        "minimal": None,
        "winners": [],
        "message": "No unique subset was established.",
    }
