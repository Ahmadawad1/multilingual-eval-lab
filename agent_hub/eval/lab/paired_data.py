"""Pair validation, leakage-resistant grouping and reviewed TyDi adaptation."""

import hashlib
import random
import re
from collections import defaultdict

from .models import CorpusDoc, GoldenItem
from .store import Conflict


def pair_groups(bundle, require_review=True):
    pairs = defaultdict(dict)
    errors = []
    for item in bundle.items:
        pair = item.metadata.get("pair_id")
        form = item.metadata.get("form")
        if (
            not isinstance(pair, str)
            or not pair
            or not isinstance(form, str)
            or form not in {"msa", "jo"}
        ):
            errors.append(f"{item.id}: set pair_id and form (msa or jo)")
            continue
        if form in pairs[pair]:
            errors.append(f"{pair}: duplicate {form} question")
        pairs[pair][form] = item
    for pair, forms in pairs.items():
        if set(forms) != {"msa", "jo"}:
            errors.append(f"{pair}: needs one MSA and one Jordanian question")
            continue
        a, b = forms["msa"], forms["jo"]
        if not a.relevant or a.relevant != b.relevant:
            errors.append(f"{pair}: both forms need identical positive qrels")
        if set(a.judged_nonrelevant) != set(b.judged_nonrelevant):
            errors.append(f"{pair}: nonrelevant judgments differ")
        if set(a.relevant) - bundle.corpus.keys():
            errors.append(f"{pair}: qrels reference missing passages")
        if a.split != b.split:
            errors.append(f"{pair}: query forms cross splits")
        if require_review and not all(
            i.metadata.get("pair_reviewed") is True
            and isinstance(i.metadata.get("reviewer"), str)
            and i.metadata["reviewer"].strip()
            for i in (a, b)
        ):
            errors.append(f"{pair}: confirm meaning and qrels with a reviewer name or ID")
        if require_review and (
            a.query.strip() == b.query.strip() or "[MSA review required]" in a.query
        ):
            errors.append(f"{pair}: author an MSA equivalent before confirming review")
    if not pairs:
        errors.append("Add paired questions first")
    return dict(pairs), errors


def clusters(bundle, pairs):
    """Connected components across pair IDs, all qrels and source articles."""
    parent = {p: p for p in pairs}

    def root(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    owners = {}
    for pair, forms in sorted(pairs.items()):
        keys = set()
        for item in forms.values():
            source = item.metadata.get("source_article")
            if source:
                keys.add("source:" + str(source))
            for did in item.relevant:
                keys.add("doc:" + did)
                doc = bundle.corpus.get(did)
                # CorpusDoc.source may be a dataset-wide description. Grouping it
                # would collapse every imported benchmark into one component.
                if doc and doc.source.startswith("article:"):
                    keys.add(doc.source)
        for key in keys:
            if key in owners:
                parent[root(pair)] = root(owners[key])
            owners[key] = pair
    return {p: root(p) for p in pairs}


def assign_pairs(bundle, seed, fraction):
    pairs, errors = pair_groups(bundle)
    if errors:
        raise Conflict("; ".join(errors[:12]))
    groups = clusters(bundle, pairs)
    ids = sorted(set(groups.values()))
    if len(ids) < 2:
        raise Conflict("At least two independent source groups are required for dev/holdout")
    random.Random(seed).shuffle(ids)
    holdout = set(ids[: max(1, min(len(ids) - 1, round(len(ids) * fraction)))])
    return [
        item.model_copy(
            update={
                "split": "holdout" if groups[item.metadata["pair_id"]] in holdout else "dev",
                "metadata": {
                    **item.metadata,
                    "split_seed": seed,
                    "source_cluster": groups[item.metadata["pair_id"]],
                },
            }
        )
        for item in bundle.items
    ]


def validate_split(bundle, pairs):
    seen = defaultdict(set)
    for pair, group in clusters(bundle, pairs).items():
        seen[group].update(i.split for i in pairs[pair].values())
    if any(None in splits or len(splits) != 1 for splits in seen.values()):
        raise Conflict("Assign paired splits: related intents or source articles cross splits")
    if {i.split for i in bundle.items} != {"dev", "holdout"}:
        raise Conflict("Both dev and holdout must contain complete pairs")


def adapt_wana(records, limit=50):
    """Adapt raw TyDi JSON records using byte spans; never invent an MSA rewrite.

    Preserve legacy candidate boundaries; segment WANA articles independently of answers.
    Missing/NULL/HTML-only or
    conflicting annotations are excluded with a reason. Review is still required.
    """
    docs, items, excluded = {}, [], []
    used = set()
    for row in records:
        if len(items) // 2 >= limit:
            break
        row = dict(row)
        # WANA v1 uses parallel answer arrays, unlike the original TyDi schema.
        # Segment independently of answer locations, preserving exact byte offsets.
        if "article_plaintext" in row:
            row["document_plaintext"] = row.get("article_plaintext")
            row["question_text"] = row.get("question")
            if isinstance(row.get("article_plaintext"), str):
                text = row["article_plaintext"]
                words = list(re.finditer(r"\S+", text))
                byte_offsets = [0]
                for char in text:
                    byte_offsets.append(byte_offsets[-1] + len(char.encode("utf-8")))
                row["passage_answer_candidates"] = [
                    {
                        "plaintext_start_byte": byte_offsets[words[start].start()],
                        "plaintext_end_byte": byte_offsets[
                            words[min(start + 255, len(words) - 1)].end()
                        ],
                    }
                    for start in range(0, len(words), 224)
                ]
                row.setdefault(
                    "example_id",
                    hashlib.sha256(
                        (str(row.get("language")) + text + str(row.get("question"))).encode()
                    ).hexdigest(),
                )
            types = row.get("answer_types", [])
            starts = row.get("answer_start_byte_indices", [])
            ends = row.get("answer_end_byte_indices", [])
            answers = row.get("answer_texts", [])
            if not all(isinstance(v, list) for v in (types, starts, ends, answers)) or not (
                len(types) == len(starts) == len(ends) == len(answers)
            ):
                excluded.append(
                    {
                        "example_id": str(row.get("example_id", "")),
                        "reason": "inconsistent WANA answer arrays",
                    }
                )
                continue
            row["annotations"] = [
                {
                    "minimal_answer": {"plaintext_start_byte": start, "plaintext_end_byte": end},
                    "answer_text": answer,
                }
                for kind, start, end, answer in zip(types, starts, ends, answers, strict=True)
                if kind == "minimal_span"
            ]
        sid = str(row.get("example_id", ""))
        try:
            if not sid or sid in used:
                raise ValueError("missing or duplicate example_id")
            text = row.get("document_plaintext")
            question = row.get("question_text")
            if not isinstance(text, str) or not text or not isinstance(question, str):
                raise ValueError("requires question_text and document_plaintext")
            language = str(row.get("language", "")).lower()
            if not any(x in language for x in ("jordan", "ar-jo", "ar_jo")):
                raise ValueError("language is not explicitly Jordanian; supply a Jordanian subset")
            raw = text.encode("utf-8")
            annotations = row.get("annotations", [])
            spans = [a.get("minimal_answer", {}) for a in annotations]
            valid = [
                s
                for s in spans
                if isinstance(s.get("plaintext_start_byte"), int)
                and 0 <= s["plaintext_start_byte"] < s.get("plaintext_end_byte", -1) <= len(raw)
            ]
            if not valid:
                raise ValueError("NULL, yes/no, or missing minimal answer span")
            for annotation in annotations:
                span = annotation.get("minimal_answer", {})
                if "answer_text" in annotation:
                    extracted = raw[
                        span["plaintext_start_byte"] : span["plaintext_end_byte"]
                    ].decode("utf-8")
                    if extracted != annotation["answer_text"]:
                        raise ValueError("answer_text does not match UTF-8 byte offsets")
            article = str(row.get("document_url") or hashlib.sha256(raw).hexdigest())
            candidates = row.get("passage_answer_candidates", [])
            if not candidates:
                raise ValueError("missing passage_answer_candidates")
            passage_docs, relevant = {}, {}
            for c in candidates:
                start, end = c["plaintext_start_byte"], c["plaintext_end_byte"]
                if not 0 <= start < end <= len(raw):
                    raise ValueError("invalid passage byte offsets")
                body = raw[start:end].decode("utf-8")
                did = "w_" + hashlib.sha256((article + str(start) + body).encode()).hexdigest()[:24]
                passage_docs[did] = CorpusDoc(
                    doc_id=did, body=body, lang="ar", source="article:" + article
                )
                if any(
                    start <= s["plaintext_start_byte"] < s["plaintext_end_byte"] <= end
                    for s in valid
                ):
                    relevant[did] = 1
            if not relevant:
                raise ValueError("answer spans are not contained in a candidate passage")
            for s in valid:
                raw[s["plaintext_start_byte"] : s["plaintext_end_byte"]].decode("utf-8")
            pair = "p_" + hashlib.sha256(sid.encode()).hexdigest()[:20]
            docs.update(passage_docs)
            for form in ("jo", "msa"):
                items.append(
                    GoldenItem(
                        id=f"{pair}_{form}",
                        query=question if form == "jo" else "[MSA review required]",
                        relevant=relevant,
                        lang="ar",
                        origin="imported",
                        metadata={
                            "pair_id": pair,
                            "form": form,
                            "source_article": article,
                            "source_example_id": sid,
                            "pair_reviewed": False,
                        },
                    )
                )
            used.add(sid)
        except (KeyError, TypeError, ValueError, UnicodeError, AttributeError, IndexError) as exc:
            excluded.append({"example_id": sid, "reason": str(exc)})
    return list(docs.values()), items, excluded
