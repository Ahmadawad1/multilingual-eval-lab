"""Check study contrasts with hand-computed paired outcomes."""

import copy
import runpy

import pytest

EXPORT = runpy.run_path("experiments/02-jordanian-msa-retrieval/export_pairs.py")


def fixture():
    bundle = {"current_hash": "fixed", "items": []}
    runs = []
    # BM25: MSA 100%, JO 0%. Dense: MSA 50%, JO 100%.
    for engine, hits in [("bm25", [1, 0, 1, 0]), ("knowhub", [1, 1, 0, 1])]:
        run = {
            "id": engine,
            "status": "done",
            "dataset_id": "study",
            "dataset_version": 1,
            "dataset_hash": "fixed",
            "engine_version": "test",
            "split": "dev",
            "k": 5,
            "variant": {
                "engine": engine,
                "level": "document",
                "hybrid": False,
                "corpus_index": "off",
                "query_normalization": "off",
                "fetch": 50,
                "min_score": 0,
            },
            "results": [],
        }
        for i, hit in enumerate(hits):
            form = "msa" if i % 2 == 0 else "jo"
            item = {
                "id": str(i),
                "split": "dev",
                "metadata": {"pair_id": str(i // 2), "form": form},
            }
            if engine == "bm25":
                bundle["items"].append(item)
            run["results"].append(
                {
                    "item_id": str(i),
                    "query": str(i),
                    "query_sent": str(i),
                    "relevant_units": {"answer": 1},
                    "error": None,
                    "ranked": [{"doc_id": "answer" if hit else "wrong", "rank": 1}],
                }
            )
        runs.append(run)
    return *runs, bundle


def test_four_cells_and_paired_contrasts():
    bm25, dense, bundle = fixture()
    result = EXPORT["compare_engines"](bm25, dense, bundle)
    assert result["bm25"]["jo_minus_msa_pp"] == -100
    assert result["dense"]["jo_minus_msa_pp"] == 50
    contrasts = result["contrasts"]
    assert contrasts["dense_gain_jo_pp"]["estimate"] == 100
    assert contrasts["dense_gain_msa_pp"]["estimate"] == -50
    assert contrasts["gap_change_pp"]["estimate"] == 150
    assert contrasts["gap_change_pp"]["paired_bootstrap_95_pp"] == [100, 200]


@pytest.mark.parametrize("key,value", [("hybrid", True), ("level", "chunk")])
def test_rejects_incomparable_dense_modes(key, value):
    _, dense, bundle = fixture()
    dense["variant"][key] = value
    with pytest.raises(ValueError):
        EXPORT["summarize"](dense, bundle)


def test_rejects_different_versions_and_changed_labels():
    bm25, dense, bundle = fixture()
    changed = copy.deepcopy(dense)
    changed["dataset_version"] = 2
    with pytest.raises(ValueError, match="dataset_version"):
        EXPORT["compare_engines"](bm25, changed, bundle)
    for row in dense["results"]:
        row["relevant_units"] = {"other": 1}
    with pytest.raises(ValueError, match="labels changed"):
        EXPORT["compare_engines"](bm25, dense, bundle)
