"""Local HTTP workbench with durable puzzles and isolated, cancellable jobs."""

from contextlib import asynccontextmanager
from collections import deque
from pathlib import Path
import asyncio
import json
import multiprocessing as mp
import os
import sqlite3
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


def execute(action, spec, options):
    from solver import solve_puzzle
    from workbench_math import (
        candidates,
        describe_solution,
        experiment,
        generate,
        hints,
        normalize_spec,
    )

    if action == "solve":
        result = solve_puzzle(normalize_spec(spec))
        for solution in result.get("solutions", []):
            solution["detail"] = describe_solution(spec, solution["assignment"])
        return result
    return {
        "hint": hints,
        "candidates": candidates,
        "generate": generate,
        "experiment": experiment,
    }[action](spec, options)


def worker(connection, action, spec, options):
    try:
        connection.send({"result": execute(action, spec, options)})
    except Exception as exc:
        connection.send({"error": f"{type(exc).__name__}: {exc}"})
    finally:
        connection.close()


class Jobs:
    def __init__(self):
        self.jobs = {}
        self.queue = deque()
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def submit(self, action, spec, options):
        with self.lock:
            if (
                sum(j["state"] in {"queued", "running"} for j in self.jobs.values())
                >= 20
            ):
                raise HTTPException(429, "Job queue is full.")
            finished = [
                key
                for key, job in self.jobs.items()
                if job["state"] not in {"queued", "running"}
            ]
            for key in finished[:-99]:
                del self.jobs[key]
            key = uuid.uuid4().hex
            self.jobs[key] = {
                "id": key,
                "state": "queued",
                "action": action,
                "spec": spec,
                "options": options,
                "elapsed": 0,
            }
            self.queue.append(key)
            return key

    def get(self, key):
        with self.lock:
            if key not in self.jobs:
                raise HTTPException(404, "Job not found.")
            job = self.jobs[key]
            result = {
                k: v
                for k, v in job.items()
                if k not in {"spec", "options", "process", "started"}
            }
            if job["state"] == "running":
                result["elapsed"] = round(time.monotonic() - job["started"], 3)
            return result

    def cancel(self, key):
        with self.lock:
            self.get(key)
            job = self.jobs[key]
            if job["state"] in {"queued", "running"}:
                job["state"] = "cancelled"
                if "process" in job:
                    job["process"].terminate()
                    job["elapsed"] = time.monotonic() - job["started"]
                job["result"] = {
                    "status": "incomplete",
                    "complete": False,
                    "unique": None,
                    "solutions": [],
                    "message": "Cancelled.",
                }
            return self.get(key)

    def run(self):
        context = mp.get_context("spawn")
        while not self.stop.wait(0.05):
            with self.lock:
                if not self.queue:
                    continue
                job = self.jobs[self.queue.popleft()]
                if job["state"] == "cancelled":
                    continue
                parent, child = context.Pipe(duplex=False)
                process = context.Process(
                    target=worker,
                    args=(child, job["action"], job["spec"], job["options"]),
                )
                process.start()
                child.close()
                job.update(state="running", started=time.monotonic(), process=process)
            message = None
            budget = float(job["spec"].get("timeout", 30))
            while not self.stop.is_set() and job["state"] == "running":
                if parent.poll(0.05):
                    try:
                        message = parent.recv()
                    except EOFError:
                        message = {"error": "Solver process exited without a result."}
                    break
                if not process.is_alive():
                    message = {"error": f"Solver process exited ({process.exitcode})."}
                    break
                if time.monotonic() - job["started"] > budget + 2:
                    message = {
                        "result": {
                            "status": "incomplete",
                            "complete": False,
                            "unique": None,
                            "solutions": [],
                            "message": "Job time budget reached; no completeness claim.",
                        }
                    }
                    break
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join()
            parent.close()
            with self.lock:
                job.pop("process", None)
                job["elapsed"] = time.monotonic() - job["started"]
                if job["state"] != "cancelled":
                    job.update(message or {"error": "Workbench stopped."})
                    job["state"] = "error" if "error" in job else "done"

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)


class Puzzle(BaseModel):
    title: str = Field(default="Untitled puzzle", max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=30)
    notes: str = Field(default="", max_length=20000)
    spec: dict


class JobRequest(BaseModel):
    action: str = "solve"
    spec: dict
    options: dict = Field(default_factory=dict)


def create_app(data_path=None):
    db_path = Path(
        data_path or os.environ.get("CRYPTARITHM_DB", ".workbench/puzzles.sqlite3")
    )

    @asynccontextmanager
    async def lifespan(app):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS puzzles (id TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)"
            )
        app.state.jobs = Jobs()
        yield
        app.state.jobs.close()

    app = FastAPI(title="Cryptarithm Workbench", lifespan=lifespan)

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse(
                {"detail": "Cross-origin requests are not allowed."}, 403
            )
        return await call_next(request)

    @app.get("/api/puzzles")
    def list_puzzles():
        with sqlite3.connect(db_path) as db:
            return [
                {"id": key, **json.loads(data)}
                for key, data in db.execute(
                    "SELECT id,data FROM puzzles ORDER BY updated DESC"
                )
            ]

    @app.get("/api/benchmarks")
    def benchmark_puzzles():
        from benchmarks.collection import corpus

        return corpus()

    @app.put("/api/puzzles/{key}")
    def save_puzzle(key: str, puzzle: Puzzle):
        data = puzzle.model_dump()
        with sqlite3.connect(db_path) as db:
            db.execute(
                "INSERT INTO puzzles VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,updated=excluded.updated",
                (key, json.dumps(data), time.time()),
            )
        return {"id": key, **data}

    @app.delete("/api/puzzles/{key}")
    def delete_puzzle(key: str):
        with sqlite3.connect(db_path) as db:
            db.execute("DELETE FROM puzzles WHERE id=?", (key,))
        return {"deleted": key}

    @app.post("/api/validate")
    def validate(spec: dict):
        from solver import inspect_puzzle
        from workbench_math import normalize_spec

        try:
            normalized = normalize_spec(spec)
            info = inspect_puzzle(normalized)
            return {
                "valid": True,
                "errors": [],
                "normalized_spec": normalized,
                "equations": normalized.get("equations", []),
                **info,
            }
        except (ValueError, TypeError, KeyError) as exc:
            return {"valid": False, "errors": [str(exc)]}

    @app.post("/api/jobs")
    def submit(request: JobRequest):
        if request.action not in {
            "solve",
            "hint",
            "candidates",
            "generate",
            "experiment",
        }:
            raise HTTPException(422, "Unknown action.")
        timeout = request.spec.get("timeout", 30)
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
            raise HTTPException(422, "Timeout must be between 0 and 3600 seconds.")
        return {
            "id": app.state.jobs.submit(request.action, request.spec, request.options)
        }

    @app.get("/api/jobs/{key}")
    def job(key: str):
        return app.state.jobs.get(key)

    @app.post("/api/jobs/{key}/cancel")
    def cancel(key: str):
        return app.state.jobs.cancel(key)

    @app.get("/api/jobs/{key}/events")
    async def events(key: str, request: Request):
        app.state.jobs.get(key)

        async def stream():
            while not await request.is_disconnected():
                state = app.state.jobs.get(key)
                yield f"data: {json.dumps(state)}\n\n"
                if state["state"] not in {"queued", "running"}:
                    break
                await asyncio.sleep(0.25)

        return StreamingResponse(stream(), media_type="text/event-stream")

    frontend = Path(__file__).parent / "frontend" / "dist"
    if (frontend / "assets").exists():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/")
    def index():
        if not (frontend / "index.html").exists():
            raise HTTPException(
                503, "Build the UI with: cd frontend && npm ci && npm run build"
            )
        return FileResponse(frontend / "index.html")

    return app


app = create_app()
