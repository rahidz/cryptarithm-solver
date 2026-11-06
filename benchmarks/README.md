# Sphinx collection benchmark

Source: [The Sphinx Collection](http://cryptarithms.awardspace.us/collection.html), fetched over HTTP on 2026-11-06. The page contains **92 numbered entries**. These include multiplication and division skeletons, digit-by-digit root extractions, prime and power constraints, and several research or historically contextual puzzles.

`collection.py` contains mathematical transcriptions, not copied explanatory prose. Every entry remains in the denominator. Currently 70 entries have specs; the remaining 22 have explicit reasons rather than disappearing from the score. No published answer is supplied to the solver. Entry 1's `A=3` is given in the question itself. Partial products, place values, visible root-extraction steps, given-digit exclusions, and extra textual mathematical conditions are retained.

Run from the repository root:

```sh
python -m benchmarks.run --timeout 10
python -m benchmarks.run --timeout 30 --ids 58,62,68
```

The runner uses a fresh process per case, budgets model construction as well as search, and checks returned assignments with the exact evaluator. It reports individual outcomes followed by a summary. A verified first solution counts as solved, **not** as proven unique or fully enumerated. Source transcription correctness is a separate requirement from satisfying the encoded puzzle; these fixtures received a targeted independent source audit.

The recorded CP-SAT run in `results.json` solved **67/92 (72.8%)** at a ten-second solver budget per entry. All 70 transcribed puzzles were either solved or proved unsatisfiable under the three literal-source inconsistencies below. The remaining 22 entries are untranscribed. The all-entry denominator is deliberately conservative, including puzzles outside the implemented representation.

## Literal-source inconsistencies

- **28:** the question says `ABCB` is square; its answer instead refers to `ABCD`. The fixture retains `ABCB`.
- **43:** the stated `ECD` cube condition conflicts with the published answer, whose mapping makes `ECD=516`. The fixture retains the condition.
- **75:** the wording says each letter is a prime number, but the published answer uses digit 1. The fixture uses modern prime digits and does not silently treat 1 as prime.

These are reported as unsatisfiable under the literal modern interpretation, not counted as solved. Historical or corrected variants could be separate fixtures later.

Cases #58 (long multiplication with equal digit sums), #62 (variable divisibility), and #68 (variable powers) now solve through general constraints rather than puzzle-specific answers. Run results depend on hardware, backend version, and budget. `results.json` records outcome evidence without treating solver timing as human difficulty.
