import json
import os

import pytest

os.environ["RAGAS_DO_NOT_TRACK"] = "true"
pytest.importorskip("ragas")
from backend.ragas_evaluation import evaluate_faithfulness


def test_actual_ragas_scorer_and_evidence(monkeypatch, client):
    replies = [
        {"statements": ["الدعم متاح صباحا.", "الدعم مجاني."]},
        {
            "statements": [
                {"statement": "الدعم متاح صباحا.", "reason": "Supported", "verdict": 1},
                {"statement": "الدعم مجاني.", "reason": "Not supported", "verdict": 0},
            ]
        },
    ]

    def fake_complete(system, payload, **kwargs):
        assert kwargs["response_schema"]["type"] == "object"
        return {
            "raw": json.dumps(replies.pop(0)),
            "input": payload,
            "system_prompt": system,
            "config": {"model": "fixture"},
            "model_identity": {"digest": "fixture-only"},
        }

    monkeypatch.setattr("backend.ragas_evaluation.complete", fake_complete)
    result = evaluate_faithfulness(
        "الدعم", "الدعم متاح صباحا ومجاني.", [{"text": "الدعم متاح صباحا."}]
    )
    assert result["ragas_metrics"]["faithfulness"] == 0.5
    assert result["scores"] is None
    assert len(result["traces"]) == 2
    assert result["ragas_version"] == "0.4.4"
    assert os.environ["RAGAS_DO_NOT_TRACK"] == "true"
    demo = client.post("/api/demo").json()
    monkeypatch.setattr("backend.main.evaluate_faithfulness", lambda *a: result)
    saved = client.post(
        "/api/judgments",
        json={
            "engine": "ragas",
            "experiment_id": demo["candidate_id"],
            "query_id": "q-support",
            "answer": "الدعم",
        },
    ).json()
    assert saved["ragas_metrics"]["faithfulness"] == 0.5
    bundle = client.get(
        "/api/report", params={"baseline": demo["baseline_id"], "candidate": demo["candidate_id"]}
    ).json()
    assert bundle["judgments"][0]["traces"] == result["traces"]


@pytest.mark.parametrize("raw", ['{"statements":[]}', "not-json"])
def test_invalid_or_empty_claims_are_not_zero(monkeypatch, raw):
    monkeypatch.setattr("backend.ragas_evaluation.complete", lambda *a, **k: {"raw": raw})
    result = evaluate_faithfulness("question", "answer", [{"text": "context"}])
    assert result["ragas_metrics"]["faithfulness"] is None
    assert result["validation_error"]
    assert result["traces"][0]["raw"] == raw


def test_nonbinary_verdict_rejected(monkeypatch):
    replies = iter(
        [
            '{"statements":["claim"]}',
            '{"statements":[{"statement":"claim","reason":"test","verdict":2}]}',
        ]
    )
    monkeypatch.setattr("backend.ragas_evaluation.complete", lambda *a, **k: {"raw": next(replies)})
    result = evaluate_faithfulness("question", "claim", [{"text": "context"}])
    assert result["ragas_metrics"]["faithfulness"] is None
    assert "0 or 1" in result["validation_error"]


def test_remote_endpoint_rejected_before_scoring(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_URL", "https://api.example.com")
    with pytest.raises(ValueError, match="loopback"):
        evaluate_faithfulness("q", "a", [{"text": "c"}])
