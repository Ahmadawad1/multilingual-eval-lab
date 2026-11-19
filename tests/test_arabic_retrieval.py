import pytest

from backend.normalization import normalize, tokenize
from backend.retrieval import BM25
from backend.schemas import Document, RetrievalConfig


@pytest.mark.parametrize(
    "source,conservative,aggressive",
    [
        ("إِدَارَة", "إدارة", "اداره"),
        ("الخــدمات", "الخدمات", "الخدمات"),
        ("أإآٱ", "أإآٱ", "اااا"),
        ("على", "على", "علي"),
        ("هبة", "هبة", "هبه"),
        ("ءؤئ", "ءؤئ", "ءؤئ"),
        ("QWEN ٣", "qwen ٣", "qwen ٣"),
    ],
)
def test_normalization_policy(source, conservative, aggressive):
    assert normalize(source, "conservative") == conservative
    assert normalize(source, "aggressive") == aggressive
    assert normalize(normalize(source, "aggressive"), "aggressive") == aggressive


def test_unicode_canonical_equivalence_and_tokens():
    assert normalize("ا\u0654", "none") == "أ"
    assert tokenize("سؤال، جَوَاب! English.") == ["سؤال", "جَوَاب", "english"]
    with pytest.raises(ValueError):
        normalize("test", "unknown")


def test_asymmetric_normalization_is_real():
    docs = [Document(id="a", text="إدارة")]
    asymmetric = BM25(docs, RetrievalConfig(query_normalization="aggressive"))
    symmetric = BM25(
        docs, RetrievalConfig(query_normalization="aggressive", corpus_normalization="aggressive")
    )
    assert asymmetric.search("إدارة") == []
    assert symmetric.search("إدارة")[0]["doc_id"] == "a"


def test_entity_collision_stable_tie_break_and_repeated_query_terms():
    docs = [Document(id="b", text="هبة تعمل"), Document(id="a", text="هبه تعمل")]
    base = BM25(docs, RetrievalConfig())
    aggressive = BM25(
        docs, RetrievalConfig(query_normalization="aggressive", corpus_normalization="aggressive")
    )
    assert base.search("هبة")[0]["doc_id"] == "b"
    assert [r["doc_id"] for r in aggressive.search("هبة")] == ["a", "b"]
    assert aggressive.search("هبة هبة") == aggressive.search("هبة")
    assert aggressive.search("no-match") == []


def test_bm25_hand_calculated_equal_length_corpus():
    import math

    index = BM25(
        [Document(id="a", text="one two"), Document(id="b", text="three four")], RetrievalConfig()
    )
    assert index.search("one")[0]["score"] == pytest.approx(math.log(2))
