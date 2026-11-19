import json

from fastapi.testclient import TestClient

from backend.main import create_app


def test_full_demo_comparison_reports_and_persistence(client, tmp_path):
    assert client.get("/api/health").json()["local_only"] is True
    demo = client.post("/api/demo").json()
    assert client.post("/api/demo").json()["experiment_ids"] == demo["experiment_ids"]
    assert len(client.get("/api/experiments").json()) == 3
    params = {"baseline": demo["baseline_id"], "candidate": demo["candidate_id"]}
    result = client.get("/api/comparison", params=params)
    assert result.status_code == 200
    comparison = result.json()
    assert comparison["counts"] == {"improved": 10, "regressed": 4, "unchanged": 4, "excluded": 0}
    assert comparison["baseline"]["metrics"]["recall"] == 8 / 18
    assert comparison["candidate"]["metrics"]["recall"] == 1
    assert comparison["summary"]["ndcg"]["bootstrap"]["n"] == 18
    for row in comparison["rows"]:
        for variant in ["baseline", "candidate"]:
            assert len(row[variant]["ranking"]) <= 5
    report = client.get("/api/report", params=params)
    assert report.status_code == 200
    assert report.json()["dataset"]["hash"] == comparison["baseline"]["dataset_hash"]
    assert len(report.json()["dataset"]["data"]["documents"]) == 22
    assert "attachment" in report.headers["content-disposition"]
    markdown = client.get("/api/report", params={**params, "format": "markdown"})
    assert "q-entity-hiba" in markdown.text
    assert "Synthetic" in markdown.text
    assert "## Limitations" in markdown.text
    with TestClient(create_app(tmp_path, False), base_url="http://localhost") as restarted:
        assert len(restarted.get("/api/experiments").json()) == 3


def test_import_run_mismatches_and_excluded_queries(client, tiny_data):
    data = client.post(
        "/api/datasets/import", json={"format": "json", "content": json.dumps(tiny_data)}
    )
    assert data.status_code == 200
    dataset_id = data.json()["id"]
    assert (
        client.post(
            "/api/datasets/import", json={"format": "json", "content": json.dumps(tiny_data)}
        ).json()["id"]
        == dataset_id
    )
    first = client.post("/api/experiments", json={"dataset_id": dataset_id, "name": "one"}).json()
    second = client.post(
        "/api/experiments", json={"dataset_id": dataset_id, "name": "two", "config": {"k": 1}}
    ).json()
    assert (
        client.get(
            "/api/comparison", params={"baseline": first["id"], "candidate": second["id"]}
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/comparison", params={"baseline": first["id"], "candidate": first["id"]}
        ).status_code
        == 422
    )
    tiny_data["queries"][0]["qrels"] = {"d1": 0}
    new_id = client.post(
        "/api/datasets/import", json={"format": "json", "content": json.dumps(tiny_data)}
    ).json()["id"]
    excluded = client.post(
        "/api/experiments", json={"dataset_id": new_id, "name": "excluded"}
    ).json()
    assert excluded["excluded_queries"] == 1
    assert excluded["metrics"]["recall"] is None
    assert (
        client.get(
            "/api/comparison", params={"baseline": first["id"], "candidate": excluded["id"]}
        ).status_code
        == 422
    )


def test_playground_no_model_and_errors(client):
    demo = client.post("/api/demo").json()
    response = client.post(
        "/api/playground",
        json={
            "dataset_id": demo["dataset_id"],
            "question": "اجراءات",
            "config": {"query_normalization": "aggressive", "corpus_normalization": "aggressive"},
        },
    )
    assert response.status_code == 200
    assert response.json()["generation"] is None
    assert response.json()["passages"][0]["doc_id"] == "doc-hamza"
    assert client.get("/api/datasets/unknown").status_code == 404
    assert (
        client.post("/api/datasets/import", json={"format": "json", "content": "{"}).status_code
        == 422
    )
    assert (
        client.post("/api/experiments", json={"dataset_id": "missing", "name": "test"}).status_code
        == 404
    )
    assert (
        client.post(
            "/api/experiments",
            json={"dataset_id": demo["dataset_id"], "name": "test", "config": {"k": 0}},
        ).status_code
        == 422
    )


def test_local_security_and_body_limit(client):
    assert client.post("/api/demo", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/demo", headers={"Origin": "null"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/api/health", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.post("/api/demo", headers={"Origin": "http://127.0.0.1:8000"}).status_code == 200
    assert client.post("/api/datasets/import", content=b"x" * 12_000_001).status_code == 413


def test_judge_validation_human_review_and_export(client, monkeypatch):
    demo = client.post("/api/demo").json()

    def fake_complete(*args, **kwargs):
        return {
            "raw": '{"correctness":3,"faithfulness":2,"relevance":4,"rationale":"Test only"}',
            "config": {"model": "mock-model"},
            "model_identity": {"digest": "test"},
        }

    monkeypatch.setattr("backend.main.complete", fake_complete)
    payload = {"experiment_id": demo["candidate_id"], "query_id": "q-hamza", "answer": "test"}
    result = client.post("/api/judgments", json=payload)
    assert result.status_code == 200
    judgment = result.json()
    assert judgment["scores"]["correctness"] == 3
    assert judgment["calibrated"] is False
    review = {
        "correctness": 1,
        "faithfulness": 1,
        "relevance": 2,
        "notes": "Independent test review",
    }
    assert client.post(f"/api/judgments/{judgment['id']}/reviews", json=review).status_code == 200
    monkeypatch.setattr("backend.main.complete", lambda *a, **k: {"raw": '{"correctness":99}'})
    invalid = client.post("/api/judgments", json=payload).json()
    assert invalid["scores"] is None
    assert invalid["validation_error"]
    assert len(client.get("/api/judgments").json()["judgments"]) == 2
    bundle = client.get(
        "/api/report", params={"baseline": demo["baseline_id"], "candidate": demo["candidate_id"]}
    ).json()
    assert len(bundle["human_reviews"]) == 1
    assert len(bundle["judgments"]) == 2
