import time
import json
import subprocess
import sys
from fastapi.testclient import TestClient
from app import create_app


def await_job(client, key):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{key}").json()
        if job["state"] not in {"queued", "running"}:
            return job
        time.sleep(0.05)
    raise AssertionError("Job did not finish")


def test_persistence(tmp_path):
    path = tmp_path / "puzzles.db"
    puzzle = {
        "title": "Classic",
        "tags": ["addition"],
        "notes": "saved",
        "spec": {"equations": ["SEND+MORE=MONEY"]},
    }
    with TestClient(create_app(path)) as client:
        assert client.put("/api/puzzles/example", json=puzzle).status_code == 200
        assert client.get("/api/puzzles").json() == [{"id": "example", **puzzle}]
    with TestClient(create_app(path)) as client:
        assert client.get("/api/puzzles").json()[0]["spec"] == puzzle["spec"]
        assert client.delete("/api/puzzles/example").status_code == 200
        assert client.get("/api/puzzles").json() == []


def test_jobs_validation_and_events(tmp_path):
    with TestClient(create_app(tmp_path / "db")) as client:
        assert (
            client.post("/api/validate", json={"equations": ["A+=B"]}).json()["valid"]
            is False
        )
        spec = {"equations": ["SEND+MORE=MONEY"], "mode": "unique"}
        assert client.post("/api/validate", json=spec).json()["valid"] is True
        key = client.post("/api/jobs", json={"spec": spec}).json()["id"]
        job = await_job(client, key)
        assert job["state"] == "done", job
        assert job["result"]["unique"] is True
        assert job["result"]["solutions"][0]["assignment"]["S"] == 9
        events = client.get(f"/api/jobs/{key}/events")
        assert "data: " in events.text and '"done"' in events.text
        assert (
            client.post("/api/jobs", json={"spec": {"timeout": -1}}).status_code == 422
        )
        assert (
            client.post("/api/jobs", json={"action": "bad", "spec": {}}).status_code
            == 422
        )
        assert client.get("/api/jobs/missing").status_code == 404


def test_cancel_and_error(tmp_path):
    with TestClient(create_app(tmp_path / "db")) as client:
        spec = {"equations": ["ABCDEFGHIJ=ABCDEFGHIJ"], "mode": "all", "timeout": 30}
        key = client.post("/api/jobs", json={"spec": spec}).json()["id"]
        job = client.post(f"/api/jobs/{key}/cancel").json()
        assert job["state"] == "cancelled"
        assert not job["result"]["complete"]
        bad = client.post(
            "/api/jobs", json={"spec": {"layout": {"kind": "invalid", "rows": []}}}
        ).json()["id"]
        assert await_job(client, bad)["state"] == "error"


def test_cross_site_write_rejected(tmp_path):
    with TestClient(create_app(tmp_path / "db")) as client:
        response = client.put(
            "/api/puzzles/x",
            json={"spec": {}},
            headers={"Origin": "https://unrelated.example"},
        )
        assert response.status_code == 403


def test_running_cancel_releases_queue(tmp_path):
    with TestClient(create_app(tmp_path / "db")) as client:
        spec = {"equations": ["ABCDEFGHIJ=ABCDEFGHIJ"], "mode": "all", "timeout": 30}
        first = client.post("/api/jobs", json={"spec": spec}).json()["id"]
        deadline = time.monotonic() + 5
        while client.get(f"/api/jobs/{first}").json()["state"] == "queued":
            assert time.monotonic() < deadline
            time.sleep(0.02)
        second = client.post("/api/jobs", json={"spec": {"equations": ["A=1"]}}).json()[
            "id"
        ]
        assert client.post(f"/api/jobs/{first}/cancel").json()["state"] == "cancelled"
        job = await_job(client, second)
        assert job["state"] == "done"
        assert job["result"]["solutions"][0]["assignment"] == {"A": 1}


def test_layout_conversion_preserves_constraints(tmp_path):
    with TestClient(create_app(tmp_path / "db")) as client:
        spec = {"layout": {"kind": "division", "rows": ["15", "3", "4", "3"]}}
        normalized = client.post("/api/validate", json=spec).json()["normalized_spec"]
        assert normalized["constraints"]
        key = client.post("/api/jobs", json={"spec": normalized}).json()["id"]
        assert await_job(client, key)["result"]["status"] == "unsatisfiable"


def test_cli_reads_ui_export(tmp_path):
    path = tmp_path / "export.json"
    path.write_text(
        json.dumps({"version": 1, "puzzle": {"spec": {"equations": ["A+1=2"]}}})
    )
    command = subprocess.run(
        [sys.executable, "main.py", "--file", str(path), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(command.stdout)["solutions"][0]["assignment"] == {"A": 1}
