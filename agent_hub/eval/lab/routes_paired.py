"""Complete local four-condition studies with immutable registered protocols."""

import csv
import hashlib
import io
import json
import random
import subprocess
import uuid
import zipfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from .models import SLUG, DatasetMeta, GoldenItem, now_iso
from .paired_data import adapt_wana, assign_pairs, pair_groups, validate_split
from .paired_engine import ENGINE_VERSION, LocalEmbeddings, digest, evaluate
from .store import _LOCK, Conflict


class PairEdit(BaseModel):
    pair_id: str = Field(pattern=SLUG)
    msa_id: str = Field(pattern=SLUG)
    jo_id: str = Field(pattern=SLUG)
    msa: str = Field(min_length=1, max_length=10000)
    jo: str = Field(min_length=1, max_length=10000)
    qrels: dict[str, int]
    source_article: str = Field(default="", max_length=2000)
    reviewed: bool = False
    reviewer: str = Field(default="", max_length=200)


class PairSplit(BaseModel):
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    holdout_fraction: float = Field(default=0.3, ge=0.1, le=0.5)


class StudyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    dataset_id: str = Field(pattern=SLUG)
    dataset_version: int = Field(ge=1)
    hypothesis: str = Field(min_length=20, max_length=10000)
    rationale: str = Field(min_length=10, max_length=10000)
    model_name: str = Field(min_length=1, max_length=100)
    primary: Literal["bm25_gap", "dense_gap", "jo_gain", "gap_change"] = "bm25_gap"
    direction: Literal["increase", "decrease"] = "decrease"
    min_effect: float = Field(default=0.05, gt=0, le=1)
    confidence: Literal[0.9, 0.95, 0.99] = 0.95
    k: int = Field(default=5, ge=1, le=50)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)


class RunInput(BaseModel):
    split: Literal["dev", "holdout"] = "dev"
    reason: str = Field(default="", max_length=3000)


class WanaInput(BaseModel):
    name: str = Field(default="Jordanian MSA TyDi adaptation", min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=11_000_000)
    limit: int = Field(default=50, ge=1, le=500)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    confirm: bool = False


def build_router(store, jobs, bundle_json, embedder=None):
    router = APIRouter(prefix="/api/eval/paired", tags=["paired retrieval"])
    embeddings = embedder or LocalEmbeddings()
    # A process restart cannot resume an in-memory worker. Preserve partial evidence.
    for run in store.list_doc_json("paired_runs"):
        if run["status"] == "running":
            run.update(
                status="failed", error="Interrupted by server restart", finished_at=now_iso()
            )
            store.put_doc_json("paired_runs", run["id"], run)

    def save(study):
        store.put_doc_json("paired_studies", study["id"], study)

    def load(sid):
        return store.get_doc_json("paired_studies", sid)

    def checked(study, registration=False):
        bundle = store.bundle(study["dataset_id"], study["dataset_version"])
        pairs, errors = pair_groups(bundle)
        if errors:
            raise Conflict("; ".join(errors[:12]))
        if not bundle.corpus or len(bundle.corpus) > 10000 or len(pairs) > 500:
            raise Conflict("Use 1–10,000 passages and at most 500 intent pairs per local study")
        if registration or study["status"] == "registered":
            if (
                bundle.manifest.status != "frozen"
                or bundle.current_hash != bundle.manifest.content_hash
            ):
                raise Conflict("Freeze an unchanged reviewed dataset version before registration")
            validate_split(bundle, pairs)
        if study.get("dataset_hash") and study["dataset_hash"] != bundle.current_hash:
            raise Conflict("Dataset changed since the study was saved; create a new study")
        return bundle

    @router.get("/models")
    def models():
        try:
            return {"models": embeddings.models()}
        except Exception as exc:
            raise HTTPException(503, f"Local Ollama unavailable: {exc}") from exc

    @router.get("/datasets/{dataset_id}/{version}")
    def dataset(dataset_id: str, version: int):
        bundle = store.bundle(dataset_id, version)
        _, errors = pair_groups(bundle)
        return {"bundle": bundle_json(bundle), "issues": errors}

    @router.put("/datasets/{dataset_id}/{version}/pair")
    def edit_pair(dataset_id: str, version: int, body: PairEdit):
        with _LOCK:
            bundle = store.bundle(dataset_id, version)
            if body.msa_id == body.jo_id:
                raise Conflict("Each form needs a different question ID")
            if not body.msa.strip() or not body.jo.strip():
                raise Conflict("Both question texts must contain words")
            if set(body.qrels) - bundle.corpus.keys() or any(
                g not in (0, 1, 2, 3) for g in body.qrels.values()
            ):
                raise Conflict("Qrels must reference existing passages with grades 0–3")
            if not any(body.qrels.values()):
                raise Conflict("Add at least one positive relevance judgment")
            if body.reviewed and (
                not body.reviewer.strip()
                or "[MSA review required]" in body.msa
                or body.msa.strip() == body.jo.strip()
            ):
                raise Conflict(
                    "Replace the MSA placeholder, review both forms and enter reviewer ID"
                )
            existing = {i.id: i for i in bundle.items}
            chosen = {body.msa_id, body.jo_id}
            old_pair = {i.id for i in bundle.items if i.metadata.get("pair_id") == body.pair_id}
            if old_pair - chosen:
                raise Conflict("This pair already has other question IDs; edit those IDs")
            for iid in chosen:
                other = existing.get(iid)
                if other and other.metadata.get("pair_id") not in (None, "", body.pair_id):
                    raise Conflict(f"{iid} belongs to another pair")
            updated = [i for i in bundle.items if i.id not in chosen]
            for form, iid, text in [("msa", body.msa_id, body.msa), ("jo", body.jo_id, body.jo)]:
                previous = existing.get(iid, GoldenItem(id=iid, query=text, lang="ar"))
                updated.append(
                    previous.model_copy(
                        update={
                            "query": text.strip(),
                            "relevant": {d: g for d, g in body.qrels.items() if g},
                            "judged_nonrelevant": [d for d, g in body.qrels.items() if not g],
                            "split": None,
                            "evidence": [],
                            "metadata": {
                                **previous.metadata,
                                "pair_id": body.pair_id,
                                "form": form,
                                "source_article": body.source_article,
                                "pair_reviewed": body.reviewed,
                                "reviewer": body.reviewer.strip(),
                                "reviewed_at": now_iso(),
                            },
                        }
                    )
                )
            store.replace_items(dataset_id, version, updated)
            return dataset(dataset_id, version)

    @router.post("/datasets/{dataset_id}/{version}/split")
    def split(dataset_id: str, version: int, body: PairSplit):
        with _LOCK:
            bundle = store.bundle(dataset_id, version)
            items = assign_pairs(bundle, body.seed, body.holdout_fraction)
            store.set_split(dataset_id, version, items, bundle.manifest)
            return dataset(dataset_id, version)

    @router.post("/wana")
    def wana(body: WanaInput):
        try:
            raw = body.text.lstrip("\ufeff").strip()
            records = (
                json.loads(raw)
                if raw.startswith("[")
                else [json.loads(line) for line in raw.splitlines() if line.strip()]
            )
            if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
                raise ValueError("Expected JSON array or JSONL of TyDi objects")
            random.Random(body.seed).shuffle(records)
            docs, items, excluded = adapt_wana(records, body.limit)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        result = {
            "passages": len(docs),
            "pairs": len(items) // 2,
            "excluded": excluded,
            "input_sha256": hashlib.sha256(body.text.encode("utf-8")).hexdigest(),
            "seed": body.seed,
            "segmentation": "WANA v1: 256 words, 32 overlap; legacy TyDi: supplied candidates",
            "warning": "Derived candidate qrels. Review passages and author MSA equivalents.",
            "sample": [i.model_dump() for i in items[:4]],
        }
        if body.confirm:
            if not items:
                raise Conflict("No eligible answerable Jordanian records")
            sid = "wana_" + uuid.uuid4().hex[:12]
            store.create_dataset(
                DatasetMeta(
                    id=sid,
                    name=body.name,
                    lang="ar",
                    description=json.dumps(result, ensure_ascii=False),
                ),
                docs,
                items,
            )
            result["dataset_id"] = sid
        return result

    @router.get("/studies")
    def studies():
        return sorted(
            store.list_doc_json("paired_studies"), key=lambda s: s["created_at"], reverse=True
        )

    @router.post("/studies")
    def create(body: StudyInput):
        with _LOCK:
            study = {
                **body.model_dump(exclude={"model_name"}),
                "id": "paired_" + uuid.uuid4().hex[:12],
                "status": "draft",
                "created_at": now_iso(),
                "runs": [],
                "holdout_access": [],
                "engine_version": ENGINE_VERSION,
                "bm25": {"k1": 1.5, "b": 0.75, "normalization": "none"},
            }
            checked(study)
            study["model"] = embeddings.identity(body.model_name)
            try:
                study["lab_revision"] = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=Path(__file__).resolve().parents[3],
                    text=True,
                    timeout=5,
                ).strip()
                study["lab_dirty"] = bool(
                    subprocess.check_output(
                        ["git", "status", "--porcelain", "--untracked-files=no"],
                        cwd=Path(__file__).resolve().parents[3],
                        text=True,
                        timeout=5,
                    ).strip()
                )
            except (OSError, subprocess.SubprocessError):
                study["lab_revision"] = "unavailable"
            study["dataset_hash"] = store.bundle(body.dataset_id, body.dataset_version).current_hash
            save(study)
            return study

    @router.get("/studies/{sid}")
    def get(sid: str):
        study = load(sid)
        return {
            **study,
            "run_records": [store.get_doc_json("paired_runs", rid) for rid in study["runs"]],
        }

    @router.post("/studies/{sid}/register")
    def register(sid: str):
        with _LOCK:
            study = load(sid)
            if study["status"] != "draft":
                raise Conflict("Study already registered")
            checked(study, registration=True)
            if embeddings.identity(study["model"]["name"]) != study["model"]:
                raise Conflict("Model changed; create a new study")
            study.update(status="registered", registered_at=now_iso())
            study["protocol_hash"] = digest(study)
            save(study)
            return study

    @router.post("/studies/{sid}/runs")
    def run(sid: str, body: RunInput):
        with _LOCK:
            study = load(sid)
            bundle = checked(study)
            if any(r["status"] == "running" for r in store.list_doc_json("paired_runs")):
                raise Conflict("Another paired run is active; wait for it to finish")
            selected = [i for i in bundle.items if i.split == body.split]
            exposure = set()
            for item in selected:
                exposure.add("query:" + digest(item.query.strip()))
                if item.metadata.get("source_article"):
                    exposure.add("article:" + str(item.metadata["source_article"]))
                for did in item.relevant:
                    exposure.add("passage:" + digest(bundle.corpus[did].body))
            if body.split == "holdout":
                if study["status"] != "registered":
                    raise Conflict("Register the frozen protocol before holdout evaluation")
                prior = [
                    r
                    for r in store.list_doc_json("paired_runs")
                    if exposure.intersection(r.get("exposure_keys", []))
                    or (r["dataset_hash"] == bundle.current_hash and r["split"] == "holdout")
                ]
                # Existing configuration experiments also count as prior exposure.
                for summary in store.list_runs():
                    old = store.get_run(summary["id"])
                    if any("query:" + digest(row.query.strip()) in exposure for row in old.results):
                        prior.append({"id": old.id})
                if prior and len(body.reason.strip()) < 10:
                    raise Conflict(
                        "Holdout questions or related sources were already evaluated. "
                        "Give a written reason; this access will be exploratory."
                    )
            else:
                prior = []
            rid = "paired_run_" + uuid.uuid4().hex[:12]
            record = {
                "id": rid,
                "study_id": sid,
                "status": "running",
                "split": body.split,
                "dataset_hash": bundle.current_hash,
                "started_at": now_iso(),
                "rows": [],
                "confirmatory": body.split == "holdout" and not prior,
                "reason": body.reason,
                "engine_version": ENGINE_VERSION,
                "exposure_keys": sorted(exposure),
            }
            study["runs"].append(rid)
            if body.split == "holdout":
                study["holdout_access"].append(
                    {
                        "at": now_iso(),
                        "run_id": rid,
                        "reason": body.reason,
                        "prior_accesses": len(prior),
                    }
                )
            save(study)
            store.put_doc_json("paired_runs", rid, record)

            def work(job):
                def partial(rows, index):
                    record.update(rows=list(rows), index=index)
                    store.put_doc_json("paired_runs", rid, record)

                try:
                    result = evaluate(
                        study, bundle, body.split, embeddings, store.root, job, partial
                    )
                    if (
                        store.bundle(study["dataset_id"], study["dataset_version"]).current_hash
                        != bundle.current_hash
                    ):
                        raise Conflict("Dataset changed during evaluation; run invalidated")
                    record.update(result, status="done")
                except Exception as exc:
                    record.update(
                        status="failed", error=f"{type(exc).__name__}: {exc}", finished_at=now_iso()
                    )
                    raise
                finally:
                    store.put_doc_json("paired_runs", rid, record)
                return {"run_id": rid}

            return jobs.submit("paired", study["name"], work).as_dict()

    @router.get("/studies/{sid}/export")
    def export(sid: str):
        with _LOCK:
            study = get(sid)
            bundle = store.bundle(study["dataset_id"], study["dataset_version"])
            if bundle.current_hash != study["dataset_hash"]:
                raise Conflict("Dataset changed; export cannot represent the original run inputs")
            files = {
                "protocol.json": study,
                "dataset.json": bundle_json(bundle),
                "import.json": {
                    "name": bundle.meta.name,
                    "language": bundle.meta.lang,
                    "source": bundle.meta.description,
                    "documents": [{"id": d.doc_id, "text": d.body} for d in bundle.corpus.values()],
                    "queries": [
                        {
                            "id": i.id,
                            "question": i.query,
                            "qrels": {**dict.fromkeys(i.judged_nonrelevant, 0), **i.relevant},
                            "metadata": {**i.metadata, "original_split": i.split},
                        }
                        for i in bundle.items
                    ],
                },
                "replay_paired.py": (
                    Path(__file__).resolve().parents[3] / "scripts/replay_paired.py"
                ).read_text(encoding="utf-8"),
                "README.md": "# Brainwave Eval paired retrieval experiment\n\n"
                "Four cells: BM25/dense × MSA/Jordanian. Inputs, protocol, model digest, "
                "index identity, rankings and all attempts are included. No weights included.\n\n"
                "Verify: python replay_paired.py path/to/export.zip\n\n"
                "Import import.json via Golden Sets Import labeled dataset. That creates a new "
                "dev draft; original splits are retained as metadata. dataset.json preserves "
                "the exact snapshot for audit. Use the same installed Ollama model digest, "
                "prefixes, k, split, seed and BM25 configuration. Dense retrieval is exact cosine "
                "over full passages with truncation disabled. Record your lab commit.\n\n"
                "Interpret only the registered primary contrast as confirmatory on first holdout "
                "access. Secondary intervals are exploratory. Check redistribution permissions "
                "for source text. This bundle does not certify Arabic model quality.\n",
            }
            for record in study["run_records"]:
                files[f"runs/{record['id']}.json"] = record
                if record["rows"]:
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(
                        ["pair_id", "cluster", "bm25_msa", "bm25_jo", "dense_msa", "dense_jo"]
                    )
                    for row in record["rows"]:
                        writer.writerow(
                            [
                                row["pair_id"],
                                row["cluster"],
                                *[
                                    row[n]["hit"]
                                    for n in ("bm25_msa", "bm25_jo", "dense_msa", "dense_jo")
                                ],
                            ]
                        )
                    files[f"results/{record['id']}.csv"] = output.getvalue()
            encoded = {
                name: (
                    value
                    if isinstance(value, str)
                    else json.dumps(value, ensure_ascii=False, indent=2)
                ).encode("utf-8")
                for name, value in files.items()
            }
            encoded["checksums.json"] = json.dumps(
                {n: hashlib.sha256(v).hexdigest() for n, v in encoded.items()}, indent=2
            ).encode()
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, value in encoded.items():
                    archive.writestr(name, value)
            return Response(
                stream.getvalue(),
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{sid}.zip"'},
            )

    return router
