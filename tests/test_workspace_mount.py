import runpy
import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app


def test_imported_golden_set_survives_restart_and_uses_separate_store(tmp_path):
    def workspace():
        return TestClient(create_app(tmp_path, serve_frontend=False), base_url="http://127.0.0.1")

    with workspace() as client:
        response = client.post("/api/eval/datasets/import-builtin", json={"lang": "ar"})
        assert response.is_success
        dataset = response.json()
        assert dataset["corpus"] and dataset["items"]
        assert client.get("/api/datasets").json() == []
    with workspace() as client:
        rows = client.get("/api/eval/datasets").json()
        assert [row["id"] for row in rows] == [dataset["meta"]["id"]]
        assert rows[0]["versions"][0]["items"] == len(dataset["items"])


def test_golden_sets_import_qrels_and_local_bm25(tmp_path):
    practice = Path("experiments/02-jordanian-msa-retrieval/practice.json").read_text(
        encoding="utf-8"
    )
    with TestClient(create_app(tmp_path), base_url="http://127.0.0.1") as client:
        assert client.get("/workspace").status_code == 404
        response = client.post(
            "/api/eval/datasets/import", json={"format": "json", "content": practice}
        )
        assert response.is_success, response.text
        bundle = response.json()
        assert len(bundle["items"]) == 6 and len(bundle["corpus"]) == 8
        assert bundle["items"][0]["metadata"]["pair_id"] == "p01"
        dataset_id = bundle["meta"]["id"]
        url = f"/api/eval/datasets/{dataset_id}/versions/1"
        qrels_url = url + "/qrels/import"
        assert client.post(qrels_url, json={"text": "p01_msa 0 missing 1"}).status_code == 409
        updated = client.post(qrels_url, json={"text": "p01_msa 0 d02 0\np01_jo\td02\t0"}).json()
        assert all("d02" in item["judged_nonrelevant"] for item in updated["items"][:2])
        assert client.post(url + "/freeze").is_success
        assert client.post(qrels_url, json={"text": "p01_msa 0 d02 0"}).status_code == 409
        job = client.post(
            "/api/eval/runs",
            json={"dataset_id": dataset_id, "version": 1, "variant": {"engine": "bm25"}},
        )
        assert job.is_success, job.text
        for _ in range(100):
            state = client.get("/api/eval/jobs/" + job.json()["id"]).json()
            if state["status"] == "done":
                break
            time.sleep(0.02)
        assert state["status"] == "done", state
        run = client.get("/api/eval/runs/" + state["result"]["run_id"]).json()
        assert run["engine_version"] == "bm25-ar-v1"
        assert sum(row["metrics"]["hit_rate"] for row in run["results"]) == 4
        exporter = runpy.run_path("experiments/02-jordanian-msa-retrieval/export_pairs.py")
        pairs, summary = exporter["summarize"](run, client.get(url).json())
        assert len(pairs) == 3
        assert summary["msa_hit_at_5"] == 1
        assert summary["jo_hit_at_5"] == 1 / 3
