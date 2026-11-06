# Cryptarithm Workbench

Execution deadline: 2026-11-06 05:00 America/New_York. Check items only after implementation and relevant verification. Public-repository push authorized by Rahid. Finish with the requested anti-bloat refactor and commit/push.

## Goal and defaults

Build a trustworthy exact cryptarithm solver and a polished local browser workbench for solving, understanding, and exploring ordinary alphametics and visual skeleton arithmetic. Personal use; localhost only; no accounts, deployment, external AI, or initial image recognition.

Additional acceptance criterion: solve most of the puzzles at http://cryptarithms.awardspace.us/collection.html with minimal hardcoding. Preserve source references and a reproducible benchmark, report the actual denominator and unsupported cases, and never feed published solutions to the solver. Improve general representations and algorithms in response to failures.

## 1. Reliable mathematics

- [x] Replace string splitting with a tokenized precedence parser, source-position errors, unary signs, parentheses, simultaneous equations, exact rational division, and right-associative `^` / `**` powers.
- [x] Support bases 2–36, explicit fixed digits `[15]` above nine, assignments, digit domains, optional distinctness groups, independent anonymous cells, and shared named variables.
- [x] Ban leading zero only for multi-digit numerals. Interpret numeral constants in the chosen base. Require nonzero denominators. Support finite nonnegative powers with explicit resource/range limits rather than silent truncation.
- [x] Share one puzzle model across CLI, API, and UI; retain a compatibility adapter for `solve_cryptarithm`.
- [x] Keep CP-SAT primary, compute expression bounds, use column/carry models for layouts, preserve denominator restrictions, and distinguish unsupported ranges from inconsistency.
- [x] Independently check returned assignments with Python integers and `Fraction`. Structured results separate satisfiable, unsatisfiable, incomplete/cancelled, invalid, unsupported, and backend error states.
- [x] Offer first solution, uniqueness, bounded enumeration, and full enumeration. Never imply uniqueness or completeness from one result.

## 2. Local workbench

- [x] React/TypeScript/Vite frontend, FastAPI Python API, SQLite saved puzzles. One launch command; built frontend served by Python.
- [x] Separate cancellable job processes, one active job, visible queue, default 30-second interactive budget, HTTP job endpoints and server-sent status events.
- [ ] Equation editor plus visual addition, subtraction, multiplication with partial products, and long division with remainder/intermediate rows. Explicit alignment, keyboard editing, undo/redo, and distinct styling for letters, fixed digits, and blank cells.
- [ ] Original/completed puzzles, mappings, carries/intermediates, solution differences, proven/unknown candidate states, hints, and assumptions.
- [ ] Searchable saved library, autosaved drafts, titles/tags/notes, examples, versioned JSON import/export. Imported results never count as proof.
- [ ] Responsive desktop-first accessible UI; contextual errors and honest elapsed-time progress. Preserve arbitrary equations when visual conversion is unavailable.
- [x] Keep CLI interactive mode and add file/JSON input and explicit limits.

## 3. Teaching and advanced math

- [ ] Verified deduction rules: domain elimination, distinctness, leading digits, column sums/carries/borrows, parity, final digits, modular arithmetic, intervals, divisibility.
- [ ] Record rule/premises; test independently. Search-derived deductions require proving the negation inconsistent and are labelled solver-proved. Timeouts are inconclusive.
- [x] Reveal hints incrementally and acknowledge when elementary reasoning stalls; never fabricate a human solution.
- [ ] Add modular/divisibility/inequality/digit-domain constraints, bounded prime/composite/square/perfect-power predicates, finite unknown-base sweeps, bounded factorials, exact integer roots, and richer rational expressions.
- [ ] Use SymPy for exact predicate preparation, Z3 as an explicit experimental backend and small-case cross-check, Sage for focused research, and cvc5 only for concrete independent checks. No unrestricted eval or default redundant solving.

## 4. Generation and experiments

- [x] Deterministic seeded generator: construct valid arithmetic, replace digits, remove clues while checking uniqueness, and export settings/outcomes.
- [x] Check uniqueness on original variables (and base), not auxiliary carry assignments. Describe difficulty by deduction/search metrics rather than claiming runtime measures human difficulty.
- [ ] Finite parameter/base sweeps and exportable experiment tables.
- [ ] Moonshots are bounded experiments, not promised production features: replayable human-proof search; certified minimal clues on small templates; adversarial generators targeting missing rules; parametric constructions/proofs with SymPy/Sage; screenshot-to-layout with mandatory correction; independent formal certificate checking for a small encoding.
- [ ] Promote experiments only on demonstrated success; negative evidence applies only to the tested scope.

## Delivery and verification

1. Correctness release: parser, semantics, results, bounds, checker, CLI, docs.
2. Workbench release: complete UI, four layouts, persistence, jobs, comparison, uniqueness.
3. Teaching release: rules, candidates, hints, assumptions.
4. Advanced release: exact constraints, base sweeps, symbolic features, generation, experiments.
5. Independent research track: test moonshots and integrate demonstrated wins.

Preserve valid existing examples; correct obsolete zero tests. Add malformed input, precedence, invalid digits, negative intermediates, division/zero denominators, powers and overflow tests. Compare small cases against independent brute force. Check layouts and intermediate arithmetic, unique/multiple solutions, cancellation/timeouts/errors, persistence/import round trips, and browser entry/edit/solve/hint/save/export flows. Run a fixed corpus including the linked collection and report unresolved failures honestly.

Release bar: every displayed solution passes independent checking; incomplete search never masquerades as proof; ordinary and skeleton puzzles can be entered, solved, inspected, saved, and reopened entirely in the UI.
