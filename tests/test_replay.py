import copy

import pytest

from backend.replay import verify_bundle


def test_report_replays_and_detects_tampering(client):
    demo = client.post("/api/demo").json()
    report = client.get(
        "/api/report", params={"baseline": demo["baseline_id"], "candidate": demo["candidate_id"]}
    ).json()
    assert verify_bundle(report)["candidate"]["verified"] is True
    altered = copy.deepcopy(report)
    altered["dataset"]["data"]["documents"][0]["text"] = "changed"
    with pytest.raises(ValueError, match="hash"):
        verify_bundle(altered)
    altered = copy.deepcopy(report)
    altered["comparison"]["candidate"]["metrics"]["ndcg"] = 0.123
    with pytest.raises(ValueError, match="differ"):
        verify_bundle(altered)
    altered = copy.deepcopy(report)
    altered["comparison"]["summary"]["ndcg"]["bootstrap"]["interval"] = [0.5, 0.9]
    with pytest.raises(ValueError, match="summary differs"):
        verify_bundle(altered)
