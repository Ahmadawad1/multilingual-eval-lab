"""Small authored synthetic fixtures, not a benchmark or customer evidence."""

from .schemas import Dataset


def demo_dataset() -> Dataset:
    pairs = [
        ("hamza", "إجراءات", "اجراءات", "إجراءات السفر موضحة في دليل الرحلات.", "Hamza"),
        ("insurance", "تأمين", "تامين", "تأمين المركبات يتطلب وثيقة سارية.", "Hamza"),
        ("alef", "آثار", "اثار", "آثار المدينة محفوظة في المتحف.", "Hamza"),
        ("diacritics", "التَّعْلِيم", "التعليم", "التَّعْلِيم متاح عبر منصة الدروس.", "Diacritics"),
        ("vowels", "السَّفَر", "السفر", "السَّفَر يحتاج وثيقة هوية صالحة.", "Diacritics"),
        ("tatweel", "الخــدمات", "الخدمات", "الخــدمات الرقمية متاحة طوال اليوم.", "Tatweel"),
        ("elongation", "المكـتبة", "المكتبة", "المكـتبة تفتح صباحا كل يوم.", "Tatweel"),
        ("maqsura", "مستشفى", "مستشفي", "مستشفى المدينة يقدم الرعاية للمرضى.", "Alef Maqsura"),
        ("marbuta", "مدرسة", "مدرسه", "مدرسة الحي تستقبل الطلاب صباحا.", "Taa Marbuta"),
        ("mixed", "الإدارة", "الاداره", "الإدارة مسؤولة عن تنظيم المواعيد.", "Combined folds"),
    ]
    documents, queries = [], []
    for slug, original, query_form, passage, category in pairs:
        doc_id = f"doc-{slug}"
        documents.append({"id": doc_id, "title": original, "text": passage})
        queries.append(
            {
                "id": f"q-{slug}",
                "question": query_form,
                "expected_answer": passage,
                "qrels": {doc_id: 3},
                "metadata": {"category": category, "synthetic": True},
            }
        )
    # Equal-length competing entity passages intentionally expose lossy-fold collisions.
    for slug, target, decoy, category in [
        ("hiba", "هبة", "هبه", "Taa Marbuta · entity"),
        ("ali", "علي", "على", "Alef Maqsura · entity"),
        ("amal", "أمل", "امل", "Hamza · entity"),
        ("aya", "آية", "ايه", "Combined folds · entity"),
    ]:
        documents += [
            {
                "id": f"entity-{slug}-a",
                "title": f"ملف {decoy}",
                "text": f"{decoy} تعمل في قسم التصميم.",
                "metadata": {"synthetic_entity": True},
            },
            {
                "id": f"entity-{slug}-b",
                "title": f"ملف {target}",
                "text": f"{target} تعمل في قسم التحليل.",
                "metadata": {"synthetic_entity": True},
            },
        ]
        queries.append(
            {
                "id": f"q-entity-{slug}",
                "question": target,
                "expected_answer": f"{target} تعمل في قسم التحليل.",
                "qrels": {f"entity-{slug}-b": 3, f"entity-{slug}-a": 0},
                "metadata": {"category": category, "synthetic": True},
            }
        )
    for slug, question, passage in [
        ("support", "الدعم", "الدعم متاح عبر الهاتف خلال ساعات العمل."),
        ("returns", "الاسترجاع", "الاسترجاع ممكن خلال أسبوع من الشراء."),
        ("account", "الحساب", "الحساب يتطلب عنوان بريد إلكتروني."),
        ("password", "password", "Reset your password using the account settings page."),
    ]:
        documents.append({"id": f"doc-{slug}", "title": question, "text": passage})
        queries.append(
            {
                "id": f"q-{slug}",
                "question": question,
                "expected_answer": passage,
                "qrels": {f"doc-{slug}": 3},
                "metadata": {"category": "Control", "synthetic": True},
            }
        )
    return Dataset(
        name="Arabic normalization · synthetic lab",
        language="ar",
        description="18 authored queries and 22 passages. Includes spelling variants, "
        "exact-name collisions and controls. Not representative customer data.",
        source="Synthetic, authored for this repository; Apache-2.0. No personal data.",
        documents=documents,
        queries=queries,
    )
