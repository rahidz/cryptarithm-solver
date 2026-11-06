# Cryptarithm Workbench

Solve alphametics and missing-digit arithmetic in a local browser UI or from Python/the terminal. Includes visual addition, subtraction, multiplication, long division, and square-root extraction; exact solutions; uniqueness checks; hints; and bounded puzzle-generation experiments.

## Run

Requires Python 3.11+, Node.js 22+, npm, and [uv](https://docs.astral.sh/uv/).

```sh
./run.sh
# Open http://127.0.0.1:8010
```

The launcher creates `.venv`, installs Python dependencies, builds the UI, and starts the local server. Use `./run.sh --port 8011` to choose another port. Puzzles are stored in `.workbench/puzzles.sqlite3`; set `CRYPTARITHM_DB` to use another database. Browser drafts use local storage. No accounts or external services are required.

For frontend development, run `.venv/bin/python main.py --serve` and `cd frontend && npm run dev` in separate terminals.

## Use

- Type equations, one per line, or select **Visual skeleton** and fill the labelled rows.
- Choose a base, optional assignments, and search mode. **Find a solution** stops at one result; **Check uniqueness** searches for a second assignment.
- Inspect solutions, digit mappings, column carries/borrows, hints, and candidate digits. Unknown candidates are not exclusions.
- Save puzzles to the library or export/import versioned JSON. The library also contains transcribed puzzles from the Sphinx collection, with source links and explicit gaps.
- The research lab generates seeded puzzles, checks clue minimality within a bounded template, and compares bases/backends. A partial count is not an exhaustive count.

### Arithmetic notation

Named letters represent shared digits and are distinct by default. Disable distinctness or specify `distinct_groups` for other conventions. A multi-digit numeral cannot start with zero; a standalone digit can.

Supported operators: `+ - * / ^ **`, unary signs, parentheses, and `=`. Division is exact rational arithmetic, with zero denominators forbidden. Powers associate rightward. Numeral digits are interpreted in the selected base, not automatically decimal.

Use `[15]` for a fixed digit fifteen. Alphabetic characters always name variables. In equations, `?` creates an independent digit and `?12` references a shared anonymous digit numbered twelve; write `?[3]` for a blank followed by fixed digit three. In the visual editor, `?3` naturally means a blank followed by three.

Multiplication partials are entered **unshifted**, rightmost multiplier digit first. Division optional steps alternate product and difference for each quotient digit, left to right. Root extraction rows are root, radicand, remainder, initial square, then current/product pairs. The UI labels these rows.

### CLI

```sh
.venv/bin/python main.py 'SEND + MORE = MONEY' --mode unique
.venv/bin/python main.py 'ALFRED / E = NEUMAN' --base 9 --json
.venv/bin/python main.py --file puzzle.json --timeout 30
.venv/bin/python main.py --file equations.txt --assign M=1 --mode limit --limit 20
```

With no arguments the CLI accepts equations until a blank line. JSON input accepts a bare spec, a puzzle containing `spec`, or a version-1 UI export.

### Python

```python
from solver import solve_puzzle

result = solve_puzzle({
    'equations': ['SEND + MORE = MONEY'],
    'base': 10,
    'assignments': {'M': 1},
    'mode': 'unique',
    'timeout': 30,
})
print(result['solutions'])
```

For layouts, call `workbench_math.normalize_spec(spec)` first. The legacy `solve_cryptarithm(puzzles, base=10, constraints=None)` still returns formatted strings; new callers should use structured results.

Optional spec fields: `domains` (digit lists per variable), `distinct` (default true), `distinct_groups`, `constraints`, `backend` (`cp-sat` or experimental `z3`), `mode` (`first`, `unique`, `limit`, `all`), `limit`, and `timeout` in seconds.

Constraints use `kind` and `expr`, for example:

```json
[
  {"kind": "prime", "expr": "ABC"},
  {"kind": "modular", "expr": "ABC", "modulus": 7, "remainder": 2},
  {"kind": "inequality", "expr": "A", "op": ">", "value": "B"},
  {"kind": "power", "expr": "DEFG", "degree": 3}
]
```

Also supported: `composite`, `square`, `root` (perfect integer power of the given degree), `factorial` (membership in bounded factorial values), `divisible`, and `consecutive_primes`. See tests for exact examples. Constraint metadata integers are decimal; expression strings use the puzzle base.

Results distinguish satisfiable, unsatisfiable, incomplete, invalid, unsupported, and error. `complete` records exhaustive search; `unique` is true only with a proof, false after two assignments, and null when unresolved. Every returned assignment is independently evaluated with Python integers and fractions. Backend limits are explicit errors, not mathematical impossibility claims.

## Tests and benchmark

```sh
uv pip install --python .venv/bin/python pytest httpx
.venv/bin/python -m pytest -q
cd frontend && npm run build
cd ..
.venv/bin/python -m benchmarks.run --timeout 2
```

The recorded benchmark solves **67/92 (72.8%)** entries of the [Sphinx collection](http://cryptarithms.awardspace.us/collection.html) at ten seconds per case. The denominator includes 22 untranscribed puzzles and three literal-source inconsistencies. Inputs contain mathematical clues, not published answers. See `benchmarks/README.md` for evidence and source ambiguities.

API documentation is available at `/docs`. Jobs run in isolated processes with cancellation and one active job at a time. The server enforces a whole-job time budget; direct Python callers should use process isolation when bounding model-building time matters.

Research experiments include replayable elementary case-split proofs, adversarial generation, fixed-assignment polynomial identities across bases, and independent exhaustive certificates for a small arithmetic grammar. Certificates are rechecked without the solver's parser/evaluator; they are not general theorem-prover certificates. Screenshot import and unrestricted family discovery remain future ideas.

`plan.md` tracks implementation and verification.
