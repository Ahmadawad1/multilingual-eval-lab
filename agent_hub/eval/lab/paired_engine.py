"""Local exact-vector retrieval and cluster-paired four-cell analysis."""

import hashlib
import json
import platform
from pathlib import Path

import httpx
import numpy as np

from backend.retrieval import BM25
from backend.schemas import Document, RetrievalConfig

from .models import now_iso
from .paired_data import clusters, pair_groups
from .store import Conflict

ENGINE_VERSION = "paired-retrieval-v1"
PROFILES = {
    "bge-m3": ("", ""),
    "nomic-embed-text": ("search_query: ", "search_document: "),
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class LocalEmbeddings:
    """No user-controlled hosts, redirects, cloud models or executable model code."""

    def request(self, path, data=None):
        with httpx.Client(
            base_url="http://127.0.0.1:11434", timeout=120, trust_env=False, follow_redirects=False
        ) as client:
            response = client.get(path) if data is None else client.post(path, json=data)
            if response.is_error:
                try:
                    detail = response.json().get("error", response.text[:500])
                except ValueError:
                    detail = response.text[:500]
                raise Conflict(f"Local Ollama {path}: {detail}")
            response.raise_for_status()
            return response.json()

    def models(self):
        result = []
        for model in self.request("/api/tags").get("models", []):
            name = model.get("name", "")
            if name.split(":")[0] not in PROFILES or "cloud" in name.lower():
                continue
            info = self.request("/api/show", {"model": name})
            if info.get("remote_host") or info.get("remote_model"):
                continue
            if "embedding" not in info.get("capabilities", []):
                continue
            result.append(
                {
                    "name": name,
                    "digest": model["digest"],
                    "details": model.get("details", {}),
                    "model_info": info.get("model_info", {}),
                    "query_prefix": PROFILES[name.split(":")[0]][0],
                    "passage_prefix": PROFILES[name.split(":")[0]][1],
                }
            )
        return result

    def identity(self, name):
        found = next((m for m in self.models() if m["name"] == name), None)
        if not found:
            raise Conflict("Select an installed local embedding model: bge-m3 or nomic-embed-text")
        return found

    def encode(self, name, texts):
        response = self.request(
            "/api/embed",
            {
                "model": name,
                "input": texts,
                "truncate": False,
                "keep_alive": "5m",
            },
        )
        array = np.asarray(response.get("embeddings"), dtype=np.float64)
        if (
            array.ndim != 2
            or array.shape[0] != len(texts)
            or not 1 <= array.shape[1] <= 8192
            or not np.isfinite(array).all()
        ):
            raise Conflict("Embedding response has invalid dimensions or nonfinite values")
        norms = np.linalg.norm(array, axis=1, keepdims=True)
        if (norms <= 0).any():
            raise Conflict("Embedding model returned a zero vector")
        return array / norms

    def runtime(self):
        try:
            return {
                "ollama": self.request("/api/version"),
                "loaded_models": self.request("/api/ps"),
            }
        except (httpx.HTTPError, ValueError):
            return {"device": "unavailable; do not assume GPU use"}


def report(rows, primary, direction, threshold, confidence, seed):
    """Pair-weighted mean with resampling of connected source clusters."""
    if not rows:
        raise Conflict("No complete pairs in the selected split")
    names = ["bm25_msa", "bm25_jo", "dense_msa", "dense_jo"]
    values = np.asarray([[r[n]["hit"] for n in names] for r in rows], dtype=float)
    contrasts = np.column_stack(
        [
            values[:, 1] - values[:, 0],
            values[:, 3] - values[:, 2],
            values[:, 3] - values[:, 1],
            values[:, 2] - values[:, 0],
            (values[:, 3] - values[:, 2]) - (values[:, 1] - values[:, 0]),
        ]
    )
    names += ["bm25_gap", "dense_gap", "jo_gain", "msa_gain", "gap_change"]
    matrix = np.column_stack([values, contrasts])
    group_ids = sorted({r["cluster"] for r in rows})
    groups = [np.asarray([i for i, r in enumerate(rows) if r["cluster"] == g]) for g in group_ids]
    estimates = matrix.mean(axis=0)
    intervals = None
    if len(groups) >= 2:
        rng = np.random.default_rng(seed)
        sums = np.asarray([matrix[g].sum(axis=0) for g in groups])
        sizes = np.asarray([len(g) for g in groups])
        draws = []
        for _ in range(2000):
            selected = rng.integers(len(groups), size=len(groups))
            draws.append(sums[selected].sum(axis=0) / sizes[selected].sum())
        alpha = (1 - confidence) / 2
        intervals = np.quantile(draws, [alpha, 1 - alpha], axis=0)
    metrics = {
        n: {
            "mean": float(estimates[i]),
            "low": float(intervals[0, i]) if intervals is not None else None,
            "high": float(intervals[1, i]) if intervals is not None else None,
        }
        for i, n in enumerate(names)
    }
    endpoint = metrics[primary]
    supported = False
    if intervals is not None:
        supported = (
            endpoint["low"] >= threshold
            if direction == "increase"
            else endpoint["high"] <= -threshold
        )
    return {
        "metrics": metrics,
        "pairs": len(rows),
        "clusters": len(groups),
        "primary": primary,
        "threshold_supported": supported,
        "confidence": confidence,
        "resamples": 2000,
        "seed": seed,
        "warnings": [
            "Secondary intervals are exploratory and not multiplicity-adjusted.",
            "A positive gap change can reflect worse MSA performance; inspect all cells.",
            "Unjudged passages are scored as nonrelevant.",
        ]
        + (["Too few source clusters for an uncertainty interval."] if len(groups) < 2 else []),
    }


def evaluate(study, bundle, split, embedder, root: Path, job, save_partial):
    pairs, errors = pair_groups(bundle)
    if errors:
        raise Conflict("; ".join(errors[:12]))
    selected = {p: forms for p, forms in pairs.items() if forms["msa"].split == split}
    if not selected:
        raise Conflict("No pairs in this split")
    identity = embedder.identity(study["model"]["name"])
    if identity != study["model"]:
        raise Conflict("Embedding model identity changed. Create a new study and index.")
    docs = sorted(bundle.corpus.values(), key=lambda d: d.doc_id)
    ids = [d.doc_id for d in docs]
    spec = {
        "model": identity,
        "passages": [[d.doc_id, d.body] for d in docs],
        "normalization": "off",
        "truncation": False,
        "chunking": "none",
        "similarity": "cosine",
        "engine": ENGINE_VERSION,
    }
    key = digest(spec)
    directory = root / "paired_indexes"
    directory.mkdir(exist_ok=True, parents=True)
    path = directory / f"{key}.npz"
    job.progress(0, len(docs) + 2 * len(selected), "Preparing dense passage index")
    if path.exists():
        with np.load(path, allow_pickle=False) as archive:
            vectors = archive["vectors"]
            expected = str(archive["vector_sha256"].item())
        if hashlib.sha256(vectors.tobytes()).hexdigest() != expected:
            raise Conflict("Dense index checksum mismatch; remove this cache and rebuild")
    else:
        batches = []
        for start in range(0, len(docs), 8):
            batches.append(
                embedder.encode(
                    identity["name"],
                    [identity["passage_prefix"] + d.body for d in docs[start : start + 8]],
                )
            )
            job.progress(min(start + 8, len(docs)))
        vectors = np.concatenate(batches)
        if embedder.identity(identity["name"]) != identity:
            raise Conflict("Model changed while indexing")
        tmp = path.with_suffix(".tmp")
        with tmp.open("wb") as output:
            np.savez_compressed(
                output, vectors=vectors, vector_sha256=hashlib.sha256(vectors.tobytes()).hexdigest()
            )
        tmp.replace(path)
    if (
        vectors.ndim != 2
        or vectors.shape[0] != len(docs)
        or not np.isfinite(vectors).all()
        or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-6)
    ):
        raise Conflict("Invalid cached index; remove this local cache and retry")
    index_meta = {
        "identity": key,
        "model": identity,
        "dimension": int(vectors.shape[1]),
        "passages": len(docs),
        "vector_sha256": hashlib.sha256(vectors.tobytes()).hexdigest(),
        "chunking": "none",
        "normalization": "off",
        "truncate": False,
        "batch_size": 8,
        "similarity": "exact cosine",
        "tie_break": "passage ID",
    }
    k = study["k"]
    bm25 = BM25(
        [Document(id=d.doc_id, text=d.body) for d in docs],
        RetrievalConfig(k=k, corpus_normalization="none", query_normalization="none"),
    )
    group_map = clusters(bundle, pairs)
    rows = []
    save_partial(rows, index_meta)
    for pair, forms in sorted(selected.items()):
        row = {"pair_id": pair, "cluster": group_map[pair], "qrels": forms["msa"].relevant}
        for form, item in sorted(forms.items()):
            query_vector = embedder.encode(
                identity["name"], [identity["query_prefix"] + item.query]
            )[0]
            if query_vector.shape[0] != vectors.shape[1]:
                raise Conflict("Query and corpus embedding dimensions differ")
            scores = vectors @ query_vector
            order = np.argsort(-scores, kind="stable")[:k]
            rankings = {
                "bm25": bm25.search(item.query),
                "dense": [
                    {"doc_id": ids[i], "score": float(scores[i]), "rank": r + 1}
                    for r, i in enumerate(order)
                ],
            }
            for engine, ranked in rankings.items():
                for hit in ranked:
                    hit["excerpt"] = bundle.corpus[hit["doc_id"]].body[:600]
                first = next((r["rank"] for r in ranked if item.relevant.get(r["doc_id"], 0)), None)
                row[f"{engine}_{form}"] = {
                    "query_id": item.id,
                    "query": item.query,
                    "hit": int(first is not None),
                    "rank": first,
                    "ranked": ranked,
                }
        rows.append(row)
        save_partial(rows, index_meta)
        job.progress(len(docs) + len(rows) * 2, message=f"Scored {len(rows)} intent pairs")
    if embedder.identity(identity["name"]) != identity:
        raise Conflict("Model changed while scoring; this run is invalid")
    return {
        "rows": rows,
        "index": index_meta,
        "report": report(
            rows,
            study["primary"],
            study["direction"],
            study["min_effect"],
            study["confidence"],
            study["seed"],
        ),
        "runtime": {"platform": platform.platform(), "numpy": np.__version__, **embedder.runtime()},
        "finished_at": now_iso(),
    }
