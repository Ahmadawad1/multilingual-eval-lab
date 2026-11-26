"""End-to-end integrity checks for paired language × retrieval studies."""

import copy
import io
import json
import time
import zipfile

import numpy as np
import pytest
from fastapi.testclient import TestClient

from agent_hub.eval.lab import routes_paired
from agent_hub.eval.lab.api import create_app
from agent_hub.eval.lab.models import CorpusDoc, DatasetMeta, GoldenItem
from agent_hub.eval.lab.paired_data import adapt_wana, assign_pairs, clusters, pair_groups
from agent_hub.eval.lab.paired_engine import LocalEmbeddings, report
from agent_hub.eval.lab.store import Conflict, LabStore
from scripts.replay_paired import verify


class FakeEmbeddings:
    changed = False
    fail = False

    def identity(self, name):
        return {
            "name": name,
            "digest": "changed" if self.changed else "abc",
            "query_prefix": "",
            "passage_prefix": "",
        }

    def models(self):
        return [self.identity("bge-m3:latest")]

    def encode(self, name, texts):
        if self.fail:
            raise RuntimeError("test embedding failure")
        result = []
        for text in texts:
            vector = np.zeros(6)
            vector[int(text[-1])] = 1
            result.append(vector)
        return np.asarray(result)

    def runtime(self):
        return {"device": "test double"}


@pytest.fixture
def environment(tmp_path, monkeypatch):
    store = LabStore(tmp_path)
    docs = [CorpusDoc(doc_id=f"d{i}", body=f"topic{i}", source=f"article:{i}") for i in range(6)]
    items = [
        GoldenItem(
            id=f"p{i}_{form}",
            query=f"{form}{i}",
            relevant={f"d{i}": 1},
            metadata={
                "pair_id": f"p{i}",
                "form": form,
                "pair_reviewed": True,
                "reviewer": "human",
                "source_article": str(i),
            },
        )
        for i in range(6)
        for form in ("msa", "jo")
    ]
    store.create_dataset(DatasetMeta(id="study", name="Test study"), docs, items)
    fake = FakeEmbeddings()
    monkeypatch.setattr(routes_paired, "LocalEmbeddings", lambda: fake)
    with TestClient(create_app(store)) as client:
        yield client, store, fake


def design():
    return {
        "name": "Paired study",
        "dataset_id": "study",
        "dataset_version": 1,
        "hypothesis": "BM25 will show a Jordanian deficit of at least five points.",
        "rationale": "Lexical overlap differs while paired meaning remains fixed.",
        "model_name": "bge-m3:latest",
        "k": 1,
    }


def prepare(client):
    response = client.post("/api/eval/paired/datasets/study/1/split", json={"seed": 42})
    assert response.status_code == 200, response.text
    assert client.post("/api/eval/datasets/study/versions/1/freeze").status_code == 200
    response = client.post("/api/eval/paired/studies", json=design())
    assert response.status_code == 200, response.text
    return response.json()["id"]


def finish(client, response):
    assert response.status_code == 200, response.text
    jid = response.json()["id"]
    for _ in range(200):
        job = client.get("/api/eval/jobs/" + jid).json()
        if job["status"] != "running":
            return job
        time.sleep(0.01)
    pytest.fail("Job did not finish")


def test_registration_holdout_repeat_export_and_replay(environment, tmp_path):
    client, store, _ = environment
    sid = prepare(client)
    base = "/api/eval/paired/studies/" + sid
    assert client.post(base + "/runs", json={"split": "holdout"}).status_code == 409
    assert client.post(base + "/register").status_code == 200
    assert client.post(base + "/register").status_code == 409
    job = finish(client, client.post(base + "/runs", json={"split": "holdout"}))
    assert job["status"] == "done", job
    result = client.get(base).json()
    run = result["run_records"][0]
    assert run["confirmatory"]
    assert run["report"]["metrics"]["dense_jo"]["mean"] == 1
    assert run["index"]["chunking"] == "none"
    assert run["index"]["dimension"] == 6
    assert client.post(base + "/runs", json={"split": "holdout"}).status_code == 409
    repeated = finish(
        client,
        client.post(
            base + "/runs",
            json={"split": "holdout", "reason": "Reproduction check after first access"},
        ),
    )
    assert repeated["status"] == "done"
    assert not client.get(base).json()["run_records"][-1]["confirmatory"]
    archive = client.get(base + "/export")
    assert archive.status_code == 200
    path = tmp_path / "export.zip"
    path.write_bytes(archive.content)
    assert verify(path)["verified_completed_runs"] == 2
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        assert {"import.json", "dataset.json", "protocol.json", "replay_paired.py"} <= set(
            z.namelist()
        )
    # A new study on the same snapshot cannot silently reset holdout history.
    other = client.post("/api/eval/paired/studies", json=design()).json()["id"]
    other_url = "/api/eval/paired/studies/" + other
    assert client.post(other_url + "/register").status_code == 200
    assert client.post(other_url + "/runs", json={"split": "holdout"}).status_code == 409


def test_pair_edit_review_and_frozen_guards(environment):
    client, _, _ = environment
    url = "/api/eval/paired/datasets/study/1/pair"
    body = {
        "pair_id": "p0",
        "msa_id": "p0_msa",
        "jo_id": "p0_jo",
        "msa": "msa0",
        "jo": "jo0",
        "qrels": {"d0": 1},
        "reviewed": True,
        "reviewer": "reviewer",
    }
    assert client.put(url, json={**body, "qrels": {"missing": 1}}).status_code == 409
    assert client.put(url, json={**body, "reviewer": ""}).status_code == 409
    assert client.put(url, json={**body, "msa": "[MSA review required]"}).status_code == 409
    assert client.put(url, json=body).status_code == 200
    prepare(client)
    assert client.put(url, json=body).status_code == 409


def test_model_change_and_failures_preserve_traces(environment):
    client, _, fake = environment
    sid = prepare(client)
    base = "/api/eval/paired/studies/" + sid
    fake.changed = True
    assert client.post(base + "/register").status_code == 409
    fake.changed = False
    fake.fail = True
    job = finish(client, client.post(base + "/runs", json={"split": "dev"}))
    assert job["status"] == "failed"
    record = client.get(base).json()["run_records"][0]
    assert record["status"] == "failed" and "embedding failure" in record["error"]
    assert "report" not in record


def test_groups_connect_all_relevant_passages(environment):
    _, store, _ = environment
    bundle = store.bundle("study", 1)
    # Two pairs share a secondary relevant passage, which must link their groups.
    for item in bundle.items[:4]:
        item.relevant["d5"] = 1
    pairs, errors = pair_groups(bundle)
    assert not errors
    mapping = clusters(bundle, pairs)
    assert mapping["p0"] == mapping["p1"] == mapping["p5"]
    first = assign_pairs(bundle, 42, 0.3)
    second = assign_pairs(bundle, 42, 0.3)
    assert [i.split for i in first] == [i.split for i in second]
    linked = {i.split for i in first if i.metadata["pair_id"] in {"p0", "p1", "p5"}}
    assert len(linked) == 1


def test_report_hand_computed_four_cells():
    rows = []
    for i, values in enumerate([(1, 0, 1, 1), (1, 0, 0, 1)]):
        rows.append(
            {
                "cluster": str(i),
                **{
                    n: {"hit": v}
                    for n, v in zip(
                        ["bm25_msa", "bm25_jo", "dense_msa", "dense_jo"], values, strict=True
                    )
                },
            }
        )
    result = report(rows, "gap_change", "increase", 0.05, 0.95, 42)
    assert result["metrics"]["bm25_gap"]["mean"] == -1
    assert result["metrics"]["dense_gap"]["mean"] == 0.5
    assert result["metrics"]["gap_change"] == {"mean": 1.5, "low": 1, "high": 2}
    rows[1]["cluster"] = "0"
    assert (
        report(rows, "gap_change", "increase", 0.05, 0.95, 42)["metrics"]["gap_change"]["low"]
        is None
    )


def wana_row():
    text = "هذا جواب عربي.\n\nنص آخر."
    raw = text.encode()
    end = len("هذا جواب عربي.".encode())
    return {
        "example_id": "123",
        "language": "Jordanian Arabic",
        "question_text": "شو الجواب؟",
        "document_plaintext": text,
        "document_url": "https://example.org/article",
        "annotations": [{"minimal_answer": {"plaintext_start_byte": 0, "plaintext_end_byte": end}}],
        "passage_answer_candidates": [
            {"plaintext_start_byte": 0, "plaintext_end_byte": end},
            {"plaintext_start_byte": end + 2, "plaintext_end_byte": len(raw)},
        ],
    }


def test_wana_byte_offsets_and_exclusions(environment):
    client, _, _ = environment
    valid = wana_row()
    broken = copy.deepcopy(valid)
    broken["example_id"] = "bad"
    broken["passage_answer_candidates"][0]["plaintext_start_byte"] = 1
    docs, items, excluded = adapt_wana([valid, broken])
    assert len(docs) == 2 and len(items) == 2 and len(excluded) == 1
    assert docs[0].body == "هذا جواب عربي."
    assert items[0].relevant == items[1].relevant
    assert items[1].query == "[MSA review required]"
    result = client.post(
        "/api/eval/paired/wana", json={"text": json.dumps([valid]), "confirm": True}
    )
    assert result.status_code == 200, result.text
    did = result.json()["dataset_id"]
    issues = client.get(f"/api/eval/paired/datasets/{did}/1").json()["issues"]
    assert any("review" in issue for issue in issues)


def test_embedding_contract_rejects_zero_vectors():
    embed = LocalEmbeddings()
    embed.request = lambda path, data=None: {"embeddings": [[0, 0]]}
    with pytest.raises(Conflict, match="zero vector"):
        embed.encode("bge-m3", ["query"])


def test_official_wana_parallel_arrays_and_review_requirement():
    text = "هذا جواب عربي " + "كلمة " * 300
    row = {
        "language": "Arabic_Jordanian",
        "article_plaintext": text,
        "question": "شو الجواب؟",
        "answer_types": ["minimal_span"],
        "answer_start_byte_indices": [0],
        "answer_end_byte_indices": [len("هذا جواب".encode())],
        "answer_texts": ["هذا جواب"],
    }
    docs, items, excluded = adapt_wana([row])
    assert not excluded and len(docs) == 2 and len(items) == 2
    assert not items[0].metadata["pair_reviewed"]
    row["answer_texts"] = ["incorrect answer"]
    assert "does not match" in adapt_wana([row])[2][0]["reason"]


def test_prior_dev_exposure_cannot_become_clean_holdout_in_a_fork(environment):
    client, store, _ = environment
    sid = prepare(client)
    base = "/api/eval/paired/studies/" + sid
    assert finish(client, client.post(base + "/runs", json={"split": "dev"}))["status"] == "done"
    store.fork("study", 1)
    bundle = store.bundle("study", 2)
    store.replace_items(
        "study",
        2,
        [
            i.model_copy(update={"split": "holdout" if i.split == "dev" else "dev"})
            for i in bundle.items
        ],
    )
    store.freeze("study", 2)
    new = client.post("/api/eval/paired/studies", json={**design(), "dataset_version": 2}).json()
    new_url = "/api/eval/paired/studies/" + new["id"]
    assert client.post(new_url + "/register").status_code == 200
    denied = client.post(new_url + "/runs", json={"split": "holdout"})
    assert denied.status_code == 409 and "already evaluated" in denied.text
