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
