"""Run all 92 entries without feeding published answers to the solver."""

import argparse
import json
import multiprocessing as mp
import time
from collections import Counter

from benchmarks.collection import corpus


def _solve(spec, timeout, backend, connection):
    try:
        from solver import solve_puzzle, validate_assignment
        from workbench_math import normalize_spec

        normalized = normalize_spec(spec)
        normalized.update(timeout=timeout, mode="first", backend=backend)
        result = solve_puzzle(normalized)
        solutions = result.get("solutions", [])
        verified = bool(solutions) and all(
            validate_assignment(normalized, s["assignment"]) for s in solutions
        )
        connection.send(
            {
                "outcome": "solved" if verified else result["status"],
                "verified": verified,
                "message": result.get("message", ""),
                "solutions": solutions,
                "solver_elapsed": result.get("elapsed"),
            }
        )
    except Exception as exc:
        connection.send({"outcome": "error", "message": f"{type(exc).__name__}: {exc}"})
    finally:
        connection.close()


def run(entries=None, timeout=30, backend="cp-sat"):
    """Yield each result immediately, bounding model construction as well as search."""
    context = mp.get_context("spawn")
    for entry in entries or corpus():
        start = time.monotonic()
        row = {"id": entry["id"], "source": entry["source"], "backend": backend}
        if entry.get("note"):
            row["note"] = entry["note"]
        if entry["spec"] is None:
            row.update(outcome="untranscribed", message=entry["reason"])
        else:
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(
                target=_solve, args=(entry["spec"], timeout, backend, sender)
            )
            process.start()
            sender.close()
            process.join(timeout + 3)
            if process.is_alive():
                process.terminate()
                process.join()
                row.update(
                    outcome="timeout",
                    message="Wall-clock budget exhausted, including model construction.",
                )
            elif receiver.poll():
                row.update(receiver.recv())
            else:
                row.update(
                    outcome="error",
                    message=f"Worker exited {process.exitcode} without a result.",
                )
            receiver.close()
        row["elapsed"] = round(time.monotonic() - start, 4)
        yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--backend", choices=["cp-sat", "z3"], default="cp-sat")
    parser.add_argument(
        "--ids", help="Comma-separated collection entry numbers; default all 92"
    )
    args = parser.parse_args()
    entries = corpus()
    if args.ids:
        ids = {int(i) for i in args.ids.split(",")}
        entries = [e for e in entries if e["id"] in ids]
    rows = []
    for row in run(entries, args.timeout, args.backend):
        rows.append(row)
        print(json.dumps(row), flush=True)
    counts = Counter(r["outcome"] for r in rows)
    print(
        json.dumps(
            {
                "summary": dict(counts),
                "denominator": len(rows),
                "full_collection": 92,
                "solved_fraction": counts["solved"] / len(rows) if rows else 0,
                "most_of_full_collection": counts["solved"] > 46,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
