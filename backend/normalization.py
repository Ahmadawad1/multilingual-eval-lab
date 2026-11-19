import re
import unicodedata

DIACRITICS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
AGGRESSIVE = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"})
TOKEN = re.compile(r"[\w\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]+", re.UNICODE)


def normalize(text: str, mode: str = "none") -> str:
    """NFC and case-fold in all modes; aggressive folding is deliberately lossy.

    Standalone Hamza and Hamza on waw/ya remain unchanged even in aggressive mode.
    This is a documented policy, not a claim of linguistically universal equivalence.
    """
    if mode not in {"none", "conservative", "aggressive"}:
        raise ValueError(f"Unknown normalization mode: {mode}")
    text = unicodedata.normalize("NFC", text).casefold()
    if mode != "none":
        text = DIACRITICS.sub("", text).replace("ـ", "")
    if mode == "aggressive":
        text = text.translate(AGGRESSIVE)
    return text


def tokenize(text: str, mode: str = "none") -> list[str]:
    return TOKEN.findall(normalize(text, mode))


def diagnostic_hypotheses(question: str, relevant_text: str, config: dict) -> list[str]:
    text = question + " " + relevant_text
    hints = []
    if DIACRITICS.search(text):
        hints.append("Diacritic sensitivity: inspect vocalized and unvocalized token matches.")
    if "ـ" in text:
        hints.append("Tatweel sensitivity: decorative elongation may break exact token matches.")
    if any(char in text for char in "أإآٱ"):
        hints.append("Hamza/Alef sensitivity: folding may improve recall or merge distinct forms.")
    if "ى" in text:
        hints.append("Alef Maqsura sensitivity: folding ى → ي may conflate names such as علي/على.")
    if "ة" in text:
        hints.append("Taa Marbuta sensitivity: folding ة → ه can merge named entities.")
    if config["query_normalization"] != config["corpus_normalization"]:
        hints.append("Asymmetric normalization: query and corpus tokens may no longer align.")
    if not hints:
        hints.append(
            "Lexical mismatch or ranking competition; inspect passage evidence and labels."
        )
    return hints
