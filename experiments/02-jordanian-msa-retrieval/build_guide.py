"""Build the learning guide with python-docx; no evaluation is performed."""

from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Inches(11.7), Inches(8.3)
sec.top_margin = sec.bottom_margin = Inches(0.7)
sec.left_margin = sec.right_margin = Inches(0.8)
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)
normal.paragraph_format.space_after = Pt(7)
normal.paragraph_format.line_spacing = 1.08
for name in ["Title", "Heading 1", "Heading 2"]:
    doc.styles[name].font.color.rgb = RGBColor.from_string("000000")
doc.styles["Title"].font.size = Pt(27)
doc.styles["Heading 1"].font.size = Pt(20)
doc.styles["Heading 2"].font.size = Pt(13)
for border in doc.styles.element.xpath(".//w:pBdr"):
    border.getparent().remove(border)
footer = sec.footer.paragraphs[0]
footer.alignment = 2
r = footer.add_run("Brainwave Eval  |  ")
r.font.size = Pt(9)
field = OxmlElement("w:fldSimple")
field.set(qn("w:instr"), "PAGE")
footer._p.append(field)


def p(text, style=None):
    return doc.add_paragraph(text, style)


def h(text):
    doc.add_heading(text, level=2)


def page(title):
    doc.add_page_break()
    doc.add_heading(title, level=1)


def code(text):
    para = p(text)
    para.paragraph_format.space_after = Pt(9)
    for run in para.runs:
        run.font.name = "Consolas"
        run.font.size = Pt(9)


def arabic(text):
    para = p(text)
    para.alignment = 2
    para._p.get_or_add_pPr().append(OxmlElement("w:bidi"))
    run = para.runs[0]
    run.font.name = "Arial"
    run.font.size = Pt(13)
    run._element.get_or_add_rPr().append(OxmlElement("w:rtl"))
    run._element.rPr.rFonts.set(qn("w:cs"), "Arial")
    size = OxmlElement("w:szCs")
    size.set(qn("w:val"), "26")
    run._element.rPr.append(size)


doc.add_heading("Comparing Jordanian Arabic and MSA retrieval", 0)
p("A practical learning guide for a four-condition BM25 and dense retrieval study")
p("Updated 25 November 2026")
h("What you will learn and produce")
p(
    "You will ask the same questions in Jordanian Arabic and Modern Standard Arabic (MSA), "
    "using both BM25 and dense retrieval over one shared passage collection. The four "
    "conditions are BM25 with MSA, BM25 with Jordanian, dense with MSA, and dense with "
    "Jordanian. You will learn to build fair pairs, record a hypothesis, run both engines, "
    "interpret paired differences and publish the evidence."
)
p(
    "The question is: Does query form affect retrieval, and does the size of that effect "
    "differ between BM25 and dense retrieval? There is no automatic rewriting stage at "
    "search time. Dense retrieval encodes text into numerical vectors and ranks by "
    "similarity; it does not generate answers."
)
h("One intent and two expressions")
arabic("متى يُعاد مبلغ الطلب بعد الإرجاع؟")
arabic("إمتى بترجعلي مصاريي بعد ما أرجّع الطلب؟")
p(
    "These illustrative questions seek the same fact. Both must use the same relevant "
    "passages. Creating an MSA equivalent of a source Jordanian question is preparation of "
    "the paired dataset; it is not a rewriting system being evaluated."
)
h("Your route through the guide")
p(
    "2  Study design and hypothesis\n3  Benchmark choice\n4  Preparing the dataset\n5  BM25 "
    "practice\n6 and 7  Design fields and criteria\n8  The four-condition comparison\n9  "
    "Dense setup and model identity\n10  Dense UI run and export\n11  Study execution and "
    "checks\n12 and 13  Interpretation and diagnosis\n14  Publishing"
)
h("What the current lab supports")
p(
    "Golden Sets and Retrieval support Local BM25 and an existing local Indexed search path. "
    "With Hybrid (RRF) off, the latter uses vector search. The paired exporter now supports "
    "both engines and their comparison. The UI still cannot represent a query-form "
    "interaction as its registered primary outcome; use a saved Design draft and the paired "
    "export for this exploratory study."
)

page("2  Define the experiment before running it")
h("Hypothesis means a testable expectation")
p(
    "Write: “On a fixed collection of MSA passages, Local BM25 will achieve a lower Hit@5 "
    "for Jordanian questions than for human-reviewed, meaning-equivalent MSA questions.”"
)
p(
    "This is a prediction, not a result. It specifies the system, the comparison, the metric "
    "and the expected direction. We chose it because BM25 relies on lexical overlap, while "
    "dialect and MSA can use different words for the same concept. The prediction could be "
    "wrong: shared words, names and numbers may make both forms work equally well, or some "
    "dialect questions may do better."
)
h("Rationale means why the prediction is reasonable")
p(
    "Write: “The documents use formal Arabic. Jordanian wording may share fewer terms with "
    "them, which may reduce BM25 matching. Pairing each information need controls for "
    "question difficulty and target evidence. Our earlier normalization experiment motivates "
    "further Arabic retrieval investigation but does not establish a dialect effect.”"
)
p(
    "How we arrived here: client language can differ from document language; BM25 uses term "
    "matching; therefore a vocabulary gap is a plausible mechanism. We test the mechanism "
    "rather than assuming that dialect is harder or worse."
)
h("Name the variables")
p(
    "Two factors vary: query form (Jordanian or MSA) and engine (BM25 or dense). Hold "
    "corpus, passages, qrels, normalization, cutoff and fetch depth fixed. Change only query "
    "form when comparing within an engine; change only engine when comparing a fixed form. "
    "One intent supplies four observations. Fifty intents yield 100 queries scored by each "
    "engine, or 200 scored observations, but only 50 intent units."
)
h("Choose a useful effect before results")
p(
    "Use a proposed practical threshold of 0.05, or five percentage points, for the "
    "Jordanian minus MSA gap. It represents five fewer successful searches per 100 "
    "questions. This is a study design choice, not an established client requirement or "
    "expected result. Record why this would matter to your intended application."
)
p(
    "The null comparison is a zero average gap. Report the measured gap and its interval "
    "even if your prediction fails. A 50-pair pilot tests the workflow and exposes problems; "
    "it is not guaranteed to detect a five-point difference. Decide any larger sample before "
    "inspecting its outcomes."
)

page("3  Choose the data for the question")
h("Recommended primary source")
p(
    "TyDi QA-WANA includes Jordanian Arabic information-seeking questions and Wikipedia "
    "article answer annotations. Questions were collected directly in the language "
    "varieties. This makes its Jordanian subset a useful starting point for authentic "
    "wording. It was designed for question answering, so you must derive and review "
    "retrieval passages and qrels. Some questions have no answer in the associated article. "
    "[1]"
)
p(
    "Use a labeled release and keep its exact version, source IDs and download date. Start "
    "with 50 eligible answerable Jordanian questions as a proposed pilot. Avoid selecting "
    "questions because a particular system succeeds on them. The resulting study is your "
    "retrieval adaptation, not an official TyDi QA-WANA retrieval leaderboard result."
)
h("Alternative for an easier retrieval baseline")
p(
    "Mr. TyDi Arabic provides retrieval data, collections and qrels. Choose it when your "
    "immediate goal is learning benchmark import and retrieval scoring with ready labels. To "
    "study Jordanian versus MSA, you would still need to add and review a Jordanian "
    "counterpart to each selected formal question. That measures performance on newly "
    "authored dialect variants, which is different provenance from natural Jordanian "
    "questions. [2]"
)
h("Optional replication")
p(
    "MIRACL Arabic is another established retrieval resource with relevance judgments. It "
    "can support a later replication across a different collection. For the present study, "
    "choose one source and document it carefully; combining sources immediately adds "
    "differences in topic, annotation and difficulty. [3]"
)
h("Business demonstration versus benchmark evidence")
p(
    "A later collection of publishable client policies can test relevance to customer "
    "support. The included practice.json has invented retail policies and three question "
    "pairs for learning only. Wikipedia retrieval results establish behavior on your sampled "
    "Wikipedia task; they do not establish performance on a client’s policies."
)
h("Your laptop and the role of RAGAS")
p(
    "Your 32 GB RAM machine is suitable for a small CPU BM25 pilot. Dense retrieval adds "
    "local embedding inference; record the actual device and memory use rather than assuming "
    "the service uses your 8 GB class GPU. Keep imports below the 12 MB request limit. RAGAS "
    "is not required for the qrels-based Hit@5 comparisons; generated-answer evaluation "
    "would be a separate stage."
)

page("4  Prepare the paired dataset")
h("Step 1  Record and sample the source")
p(
    "Open the official TyDi QA-WANA repository [1], follow Download the Dataset and choose a "
    "labeled Jordanian release. Save the original file unchanged outside Git. Record its "
    "URL, release or revision, file hash and annotation format. Read the release fields "
    "before converting them; the lab does not directly import raw TyDi QA-WANA."
)
p(
    "Select answerable questions using a written rule and a fixed seed, such as 42. Record "
    "excluded NULL or ambiguous examples and why. Do not silently count excluded questions "
    "as retrieval failures. This defines exactly which population your results describe."
)
h("Step 2  Make the two forms equivalent")
p(
    "Retain the original Jordanian question. Ask a competent Arabic reviewer to create an "
    "MSA equivalent from its meaning, without borrowing answer wording from the article. A "
    "second review should check entities, dates, negation, constraints and requested detail. "
    "Log reviewer IDs, corrections and decisions. MSA authoring can introduce bias; report "
    "it as a limitation."
)
h("Step 3  Build one shared passage collection")
p(
    "Use article text distributed with the selected data where available. Split articles "
    "into paragraph passages with stable IDs. Keep answer-bearing text intact and retain "
    "source article IDs. Include competing paragraphs and unrelated articles sampled under a "
    "fixed rule. Record the segmentation method, sampling seed and corpus size. A corpus "
    "containing only correct passages makes the task artificially easy."
)
p(
    "Answer annotations may use byte offsets. Arabic UTF-8 byte positions are not character "
    "positions. Verify each extracted answer against the original bytes and article text "
    "before assigning a passage. Never use a loose answer-string match as the only relevance "
    "check."
)
h("Step 4  Create shared qrels and metadata")
p(
    "For every intent, review which passages provide the requested information. Give "
    "accepted relevant passages grade 1 and duplicate that qrels map across its two forms. "
    "Check alternative correct passages. One missing label can create a false failure. Use "
    "unique query IDs, shared metadata.pair_id, and metadata.form equal to jo or msa."
)
p(
    "Copy the structure in practice.json into study.json: documents contain id and text; "
    "queries contain id, question, qrels and metadata. Replace every practice record. Keep "
    "provenance and human review notes in a companion file. This conversion and review are "
    "preparation tasks, not an automatic lab feature."
)

page("5  Learn the lab with the practice dataset")
h("Step 1  Start your local lab")
p(
    "In PowerShell, run the following commands. If the lab is already running, reuse it. On "
    "a fresh checkout run scripts/setup.ps1 once first. Leave the server terminal open."
)
code("cd 'C:\\Users\\ALIEN WARE\\repo\\multilingual-eval-lab'\n.\\scripts\\start.ps1")
p(
    "Open http://127.0.0.1:8000/evaluation/dataset. The practice workflow uses Local BM25 "
    "and needs no language model or Know Hub index."
)
h("Step 2  Import and inspect")
p(
    "In Golden Sets, click Import labeled dataset and choose practice.json beside this "
    "guide. Confirm eight documents and six questions. Under Ask → Items, inspect the "
    "questions. Each intent should have an MSA and a Jordanian version. This inspection "
    "catches missing rows and mistaken IDs before a misleading score is produced."
)
p(
    "For separate qrels, import documents and questions first, then use Ask → Items → Import "
    "qrels while the version is a draft. Accepted lines have query ID, document ID and "
    "integer grade; four-column TREC format adds a second placeholder column. Referenced IDs "
    "must already exist. Imports merge labels, so inspect the result before freezing."
)
code("p01_msa Q0 d01 1\np01_jo  Q0 d01 1")
h("Step 3  Use one retrieval configuration")
p(
    "Open Retrieval, confirm the dataset picker, then open Probe and its configuration row. "
    "Set Name to jo-msa-practice-v1; Search engine to Local BM25; Corpus normalisation to "
    "off; Query normalisation to off; Fetch depth to 50; and k (cutoff) to 5. Both forms "
    "will use these exact settings."
)
p(
    "Open Score, select dev and click Run jo-msa-practice-v1. The labeled importer assigns "
    "queries to dev. Confirm all six queries were scored and no query failed. Read the run "
    "ID. This rehearses the import, retrieval and export path before using reviewed "
    "benchmark data."
)
h("What the settings mean")
p(
    "BM25 rewards query-term matches while accounting for frequency and document length. The "
    "local engine fixes k1 at 1.5 and b at 0.75. Fetch depth limits the candidate ranking "
    "returned; k defines the top results used by Hit@k. These are different controls. Keep "
    "normalization off here to isolate query form from your earlier normalization experiment."
)

page("6  Write the design in your UI")
h("Step 1  Open the study notebook")
p(
    "Import your prepared study.json through Golden Sets. Review its documents, questions, "
    "labels and metadata. Then open Retrieval Experiments → New experiment. Select the "
    "intended Dataset version. Use the following text in Design and click Save draft. A "
    "draft preserves your plan but is editable; save a dated copy of the protocol before "
    "scoring for an auditable record."
)
h("Name")
p("Enter: Jordanian versus MSA across BM25 and dense retrieval v1")
p(
    "A name should tell you what is compared and which study version it is. Avoid a result "
    "in the title before evidence exists."
)
h("Hypothesis")
p(
    "Enter: H1 (primary): Under BM25, Jordanian Hit@5 will be lower than MSA Hit@5; a "
    "decrease of 0.05 is practically important. H2 (secondary): With the fixed dense model, "
    "the Jordanian-minus-MSA gap will move upward relative to BM25, while Jordanian Hit@5 "
    "improves. Both engines will score the same reviewed intent pairs and corpus. This is an "
    "exploratory four-condition study."
)
p(
    "Why this wording: it makes the outcome and its sign explicit. The five-point threshold "
    "is your proposed practical decision rule, not a claim that the effect exists. A "
    "hypothesis gives you something that observations can support, contradict or leave "
    "uncertain."
)
h("Rationale and prior evidence")
p(
    "Enter: BM25 relies on lexical overlap, so Jordanian wording may match MSA passages less "
    "often. Dense embeddings may connect different words with similar meanings, but the "
    "selected model may still have dialect weaknesses. Paired intents hold meaning and "
    "evidence fixed. The earlier normalization study motivates investigation, not an "
    "expected result. No rewriting or generation occurs during retrieval."
)
p(
    "Why this field matters: the hypothesis states what you expect; the rationale explains "
    "the mechanism and where the idea came from. Keeping them separate prevents an "
    "attractive explanation from being mistaken for evidence."
)
h("Dataset version")
p(
    "Select the version containing both forms and their shared corpus. In Golden Sets → "
    "Freeze → Lifecycle, freeze the reviewed study version and record its content hash. A "
    "hash identifies the exact content used. If you discover a label error later, fork a new "
    "version, document the correction and rerun; preserve the original result."
)
p(
    "Do not treat this saved experiment draft as registered. The next page explains the "
    "current limitation and the correct execution route."
)

page("7  Set criteria and understand the arms")
h("Criteria to enter in the Design screen")
p(
    "Primary metric: Hit rate. k: 5. Direction: decrease. Minimum effect: 0.05. Confidence "
    "level: 95%. Leave Guardrails empty for this descriptive pilot. Choose MRR as an "
    "exploratory secondary metric only if you will calculate and report it separately by "
    "form."
)
p(
    "Hit@5 answers a simple question: did search supply any labeled relevant passage in its "
    "first five results? It suits this evidence-availability study but misses rank changes "
    "within the top five. The direction is decrease because the reported difference is "
    "Jordanian minus MSA. A minimum effect is the smallest gap you intend to call "
    "practically important."
)
p(
    "Confidence level controls the interval procedure. It is not a 95% probability that the "
    "hypothesis is true. Guardrails are extra constraints, such as preventing a latency "
    "increase, useful for deployment changes; this pilot does not need invented deployment "
    "criteria."
)
h("Arms are the conditions being compared")
p(
    "Within each engine, MSA is the reference form and Jordanian is the comparison form. "
    "Across engines, BM25 is the baseline and dense is the comparison. Keep normalization "
    "off, fetch 50 and k = 5. There are two separate contrasts; do not compare BM25 with MSA "
    "against dense with Jordanian and call that an engine effect."
)
p(
    "The current UI arms select configurations and run each over the same items. They have "
    "no query-form filter. You can set baseline to Local BM25 and treatment to Indexed "
    "search with Hybrid off to describe the engine contrast. Use document level, both "
    "normalizations off, min similarity 0 and fetch 50 in both. Record the intended "
    "four-condition analysis in Rationale."
)
h("Why you must stop at Save draft here")
p(
    "Registration can lock a supported configuration comparison, but the UI report averages "
    "query forms together. Its criterion does not encode the primary dialect gap or the "
    "engine-by-form interaction in this guide. Keep this study as a saved draft notebook and "
    "use paired exports for the four cells. A mixed average improvement is not evidence that "
    "dense reduced the dialect deficit."
)
h("Pilot and holdout boundary")
p(
    "Use this route as an exploratory pilot. The importer assigns all questions to dev. "
    "Ad-hoc scoring cannot evaluate holdout items. A confirmatory dialect-interaction "
    "workflow needs pair-aware grouping and a corresponding protected endpoint. Do not "
    "bypass the holdout restriction or present a draft as registered. Keep future evaluation "
    "intents and source articles out of pilot tuning."
)


page("8  Design the four conditions")
h("A two by two design")
p(
    "Run the same query pairs twice, once per engine. BM25 plus MSA is cell A; BM25 plus "
    "Jordanian is B; dense plus MSA is C; dense plus Jordanian is D. Each cell uses the same "
    "N intents and the same corpus and labels. This design separates query-form differences "
    "from engine differences."
)
h("Keep the original question as the primary analysis")
p(
    "H1 remains the BM25 Jordanian-versus-MSA comparison: B minus A. Keep Hit@5, the "
    "predicted decrease and the five-point practical threshold chosen before results. Adding "
    "dense does not justify changing this primary endpoint after inspecting BM25 outcomes."
)
h("Add a secondary hypothesis and explain why")
p(
    "H2: The selected dense model will improve Jordanian Hit@5 and make the "
    "Jordanian-minus-MSA gap less negative than BM25. Rationale: vector representations may "
    "connect dialect words with formal equivalents even when their spellings differ. This is "
    "a model-specific hypothesis; dense retrieval is not guaranteed to help Arabic or "
    "dialect queries."
)
h("Calculate the contrasts")
p(
    "BM25 dialect gap = B − A. Dense dialect gap = D − C. Jordanian engine gain = D − B. MSA "
    "engine gain = C − A. Gap change = (D − C) − (B − A). Multiply rate differences by 100 "
    "to express percentage points. The exporter computes these from the same paired intents."
)
p(
    "A positive gap change means the Jordanian-minus-MSA gap moved upward. It can arise "
    "because MSA got worse, or it can overshoot into a larger opposite gap. Inspect all four "
    "rates and Jordanian engine gain before calling it a useful reduction in dialect "
    "disadvantage. An equal improvement for both forms can help users without changing the "
    "gap."
)
h("Uncertainty and honest interpretation")
p(
    "Resample whole intents, keeping all four observations together. The helper uses 5,000 "
    "bootstrap resamples and seed 42. Its secondary intervals are exploratory and unadjusted "
    "for multiple comparisons. Do not infer an interaction from one significant "
    "within-engine interval and one nonsignificant interval; use the paired interval for "
    "gap_change_pp itself."
)

page("9  Prepare the local dense pipeline")
h("What is available and what must be recorded")
p(
    "Indexed search uses the sibling Brainwave Know Hub and local Ollama services. The "
    "source default embedding model is nomic-embed-text, but runtime configuration can "
    "override it. The UI does not select an embedding model. Check the actual service model "
    "before calling the result a dense baseline; report its name and digest rather than "
    "simply saying dense."
)
h("Step 1  Start or reuse the services")
p(
    "Reuse a healthy local stack. Otherwise, with Docker Desktop running, run the following "
    "from the lab root. The helper depends on the sibling Brainwave checkout and previously "
    "initialized model and node-module caches. If it reports a missing cache, resolve the "
    "reference setup first; a failed service is not a poor retrieval result."
)
code("uv run python scripts/start_eval_services.py")
h("Step 2  Record model identity")
p(
    "Find the Know Hub container with the first command, then substitute its ID in the "
    "second. Only the model setting is printed. Compare it with the Ollama model list, and "
    "record the matching digest, service revision, embedding dimension, prefix handling and "
    "device in a study manifest. These details are not guaranteed to be captured in the lab "
    "run JSON."
)
code('docker ps --filter label=com.docker.compose.service=know-hub --format "{{.ID}} {{.Names}}"')
code("docker exec KNOW_HUB_ID printenv OLLAMA_MODEL")
code("(Invoke-RestMethod http://127.0.0.1:11434/api/tags).models | Select-Object name,digest")
h("Model choice for an Arabic study")
p(
    "Use the existing configured model for a pipeline pilot and name it explicitly; do not "
    "generalize its result to all dense models. A suitable candidate for a later "
    "multilingual baseline is intfloat/multilingual-e5-small: 384-dimensional vectors, "
    "query: and passage: prefixes, and a 512-token input limit. Its card lists Mr. TyDi and "
    "MIRACL training data, so disclose overlap and avoid training splits for reported "
    "evaluation. [5]"
)
p(
    "E5-small is not a drop-in UI option: the current Know Hub schema expects "
    "768-dimensional vectors and its adapter must apply the correct prefixes. This guide "
    "does not install or integrate another model. Do not change only the model name and "
    "reuse the old index. A validated adapter and fresh index are prerequisites for that "
    "model-specific extension."
)

page("10  Run dense retrieval in the UI")
h("Step 1  Build and verify the corpus index")
p(
    "On the same Golden Set version, open Index. Under Index · off, click Index corpus and "
    "wait until the state is current and every document is INDEXED. Failed, skipped or "
    "incomplete ingestion must be fixed before scoring. Use this same off index for both "
    "language forms."
)
p(
    "The current service chunks ingested text with a configured maximum of 512 and overlap "
    "of 64 in its chunker, then document search ranks by the best chunk per document. BM25 "
    "ranks the full imported passage. Keep passages short and verify one indexed chunk per "
    "passage for a cleaner comparison. Otherwise describe the result as a comparison of two "
    "retrieval pipelines, since chunking also differs. Record the actual chunking and "
    "truncation; do not assume the chunker’s token count equals the model tokenizer’s count."
)
h("Step 2  Set dense controls explicitly")
p(
    "Open Retrieval → Probe and expand the configuration. Set Name to jo-msa-dense-v1; "
    "Search engine to Indexed search; Level to document; Hybrid (RRF) OFF; Corpus index off; "
    "Query normalisation off; Min similarity 0; Fetch depth 50; and k (cutoff) 5. Leaving "
    "Hybrid on tests lexical-plus-vector fusion, not dense-only retrieval."
)
p(
    "Open Score, choose dev and run. Confirm 2N queries without errors and retain the dense "
    "run ID. Do not tune the model or threshold against these study outcomes. Test service "
    "connectivity and settings with practice.json first. No GPU inference or dense benchmark "
    "score has been validated by the creation of this guide."
)
h("Step 3  Export each engine and their comparison")
p(
    "From the repository root, use the commands below with actual run IDs. Each output "
    "folder must be new. The first produces dense pairs.csv, summary.json and run.json. The "
    "second produces the BM25 paired export plus dense-run.json and engine-comparison.json "
    "containing all four Hit@5 rates, the two engine gains and gap change with paired "
    "intervals."
)
code(
    "uv run python experiments/02-jordanian-msa-retrieval/export_pairs.py DENSE_ID results-dense-v1"
)
code(
    "uv run python experiments/02-jordanian-msa-retrieval/export_pairs.py BM25_ID "
    "results-both-v1 --dense-run DENSE_ID"
)
p(
    "These folders are local analysis outputs, not automatically published artifacts. Check "
    "model identity separately: passing the export checks verifies paired inputs and "
    "controls, not embedding model suitability or an unchanged external service."
)


page("11  Score and export your study")
h("Step 1  Freeze the protocol and input")
p(
    "Before scoring, save a dated protocol containing the hypothesis, rationale, source "
    "revision, sampling rule, review procedure, exclusions, primary metric and threshold. "
    "Record the corpus size, pair count, dataset version and hash, and lab revision. This "
    "prevents hindsight from quietly changing the question."
)
code("git rev-parse HEAD")
h("Step 2  Run the reviewed version")
p(
    "In Golden Sets, freeze the reviewed version via Freeze → Lifecycle. Select it in "
    "Retrieval. Run BM25 as described on page 5, then dense as described on page 10. Use "
    "dev, k = 5 and fetch 50 for both. Each run must score 2N queries without errors. "
    "Preserve two separate run IDs and the same dataset hash. Complete and verify dense "
    "indexing before scoring."
)
p(
    "Each overall UI score mixes MSA and Jordanian. Preserve both run IDs and use the paired "
    "exporter to separate forms. Runs are listed at http://127.0.0.1:8000/api/eval/runs. Do "
    "not infer a dialect benefit from the mixed average or compare raw BM25 scores with "
    "cosine similarities; compare qrels-based metrics."
)
h("Step 3  Export the paired comparison")
p(
    "Keep the server running. In a second PowerShell terminal, use the following command "
    "from the repository root. Replace RUN_ID with the actual saved ID; choose a new output "
    "directory for each run."
)
code(
    "uv run python experiments/02-jordanian-msa-retrieval/export_pairs.py RUN_ID "
    "experiments/02-jordanian-msa-retrieval/results-study-v1"
)
p(
    "The script produces run.json with raw rankings and settings; pairs.csv with both "
    "question forms, first relevant ranks within five, binary hits and outcomes; and "
    "summary.json with group Hit@5, the paired gap and its bootstrap interval."
)
h("Step 4  Check that the export is trustworthy")
p(
    "The exporter rejects failed or incomplete pairs, inconsistent qrels, a changed dataset "
    "hash, non-document scoring and dense runs with Hybrid enabled. Engine comparison also "
    "requires the same dataset version, split, cutoff, fetch depth, normalization settings "
    "and query text. For N intents expect N paired rows per engine and 2N queries in each "
    "run. Correct inputs in a new version and rerun both engines."
)
p(
    "The exporter calculates paired Hit@5 and, with --dense-run, engine gains and the change "
    "in the dialect gap. It does not calculate group MRR or nDCG or verify the live "
    "embedding model identity. Save model and indexing metadata separately. No measured "
    "benchmark results or GPU validation are supplied by this guide."
)

page("12  Understand what your numbers say")
h("Hit rate and the paired gap")
p(
    "A query earns 1 if any labeled relevant passage is in its top five, otherwise 0. Hit@5 "
    "is the average. A value of 0.72 means relevant evidence was found for 72% of questions. "
    "The paired gap is 100 × (Jordanian Hit@5 − MSA Hit@5), in percentage points."
)
p(
    "Illustration only: if 40 of 50 MSA queries and 35 of 50 Jordanian queries succeed, the "
    "rates are 80% and 70%. The gap is −10 percentage points. These are teaching numbers, "
    "not measured results."
)
h("The four outcomes reveal the comparison")
p(
    "both: both forms succeed. msa_only: only formal wording succeeds. jo_only: only "
    "Jordanian wording succeeds. neither: both miss. MSA successes equal both + msa_only; "
    "Jordanian successes equal both + jo_only. The gap also equals 100 × (jo_only − "
    "msa_only) / N."
)
p(
    "The two forms of one intent belong together. The exporter resamples whole pairs 5,000 "
    "times using seed 42 and reports a 95% percentile bootstrap interval. Sampling "
    "individual queries separately would lose the paired structure. Repeated intents or many "
    "questions from the same article can still make a pair-only interval too optimistic; "
    "document clustering and consider an article-cluster analysis for stronger claims."
)
h("Read direction and practical size separately")
p(
    "An interval spanning zero leaves the direction uncertain. An interval wholly below zero "
    "supports a decrease under the sampling assumptions. To support a decrease of at least "
    "five points, the entire interval should be below −5 percentage points. A negative "
    "estimate alone does not establish that threshold. A small pilot can be inconclusive "
    "even when its point estimate looks large."
)
p(
    "The interval does not prove generalization to all Jordanian speakers or client domains. "
    "A tiny or highly repetitive sample can give misleading confidence. Do not increase the "
    "sample repeatedly until a desired result appears."
)
h("Other metric names you may see")
p(
    "Recall@5 asks what fraction of all labeled relevant passages was retrieved; it differs "
    "from Hit@5 when multiple relevant passages exist. MRR rewards an early first relevant "
    "passage. In the current UI, rank-aware metrics use depth max(k, 10), so at k = 5 do not "
    "relabel displayed MRR as MRR@5. RAGAS faithfulness evaluates generated answers and is "
    "outside this retrieval-only endpoint."
)

page("13  Diagnose failures and write the finding")
h("Step 1  Inspect contrasting pairs")
p(
    "Open pairs.csv as UTF-8 and filter msa_only, then jo_only. For each available group, "
    "inspect both queries, their relevant passages and their ranked results in run.json. "
    "Also inspect both for rank changes and neither for missing evidence. This connects "
    "aggregate numbers to concrete behavior."
)
p(
    "Possible explanations include dialect vocabulary mismatch, changed question meaning, "
    "ambiguous entities, missing qrels, incomplete passage boundaries or common words "
    "outranking specific evidence. Record explanations as hypotheses until the text or a "
    "separate controlled test supports them. Include counterexamples to your expectation."
)
h("Step 2  Keep data corrections separate")
p(
    "If a reviewer finds that the two forms ask different things or that a correct passage "
    "is unlabeled, log the issue and decision. Preserve the original dataset and run; "
    "correct a new version and rerun the full set. Selectively removing difficult questions "
    "after seeing scores biases the conclusion."
)
h("Step 3  Write the result using exported values")
p(
    "Use this template: “Across [N] reviewed intents and [D] passages, Local BM25 found "
    "labeled relevant evidence in the top five for [X/N] MSA queries and [Y/N] Jordanian "
    "queries. Jordanian minus MSA Hit@5 was [delta] percentage points, with a paired 95% "
    "bootstrap interval of [lower, upper]. This was an exploratory retrieval adaptation of "
    "[source and revision].”"
)
p(
    "Then state whether the interval supports the expected direction and whether it supports "
    "your five-point practical threshold. Say “inconclusive” when appropriate. Report the "
    "full result even if Jordanian performs better."
)
h("Step 4  Explain limits and client relevance")
p(
    "Report the passage sampling method, corpus size, natural-versus-authored query "
    "provenance, reviewer procedure, exclusion counts, qrels coverage and shared-article "
    "clustering. Reduced corpora change difficulty, so your scores are not comparable to "
    "full-corpus benchmark leaderboards."
)
p(
    "A supported gap would justify investigating dialect-aware retrieval. Dense is already "
    "part of this study; judge its effect using all four rates. Automatic rewriting, "
    "normalization, reranking or another embedding model would be separate follow-up "
    "conditions. A client-policy collection would test whether the benchmark finding "
    "transfers to that client."
)
h("A useful self-check")
p(
    "Can another reader identify the only intended changing factor, reproduce each metric "
    "from the saved rankings, and find an example that challenges your explanation? If yes, "
    "your report provides evidence they can examine rather than a score they must trust."
)

page("14  Publish a reproducible experiment")
h("Keep the learning folder and public repository separate")
p(
    "This folder stores your guide, practice input and export helper. Create a separate "
    "publication repository such as jordanian-msa-retrieval. Include README.md, the dated "
    "four-condition protocol, preparation and review notes, permitted data, lab revision, "
    "model identity and digest, index settings and both raw runs. Include both per-engine "
    "paired exports and engine-comparison.json."
)
p(
    "Document source IDs, hashes, sampling, passage construction, exclusions, fixed BM25 "
    "settings and dense model configuration. Save prefix handling, embedding dimension, "
    "truncation and chunking, service revision, device and the exact export commands. A "
    "model change requires a fresh index and a new study run. Preserve negative or "
    "inconclusive results."
)
h("GitHub publication steps")
p(
    "1. Review the source dataset terms and Wikipedia text attribution requirements before "
    "redistributing. The repository code license is not automatically the license for all "
    "source text. If needed, publish preparation scripts and source identifiers instead of "
    "restricted text.\n2. Create the separate repository and commit the reviewed protocol, "
    "code and permitted data.\n3. Add the result statement, examples and limitations to "
    "README.md. Link the source benchmarks and this lab revision.\n4. Push the files, create "
    "a versioned release, and record its commit hash."
)
h("Hugging Face publication steps")
p(
    "Create a dataset repository under your account, for example "
    "ahmad-awad/jordanian-msa-retrieval if available. Upload permitted data and a dataset "
    "card describing language forms, provenance, schema, qrels, review, intended use and "
    "limitations. Keep corpus, queries, qrels and paired results in separate configurations "
    "because they have different columns. Follow the current Hub dataset-card and data-file "
    "instructions. [4]"
)
p(
    "Link the GitHub release in the dataset card and the exact Hugging Face revision in "
    "GitHub. Download your published files and verify their hashes and Arabic text. Rerun "
    "the workflow and compare counts, rankings and the paired gap; run IDs and timings can "
    "differ."
)
h("Sources and further learning")
p(
    "[5] Multilingual E5 small model card and usage\n"
    "https://huggingface.co/intfloat/multilingual-e5-small"
)
p(
    "[1] TyDi QA-WANA dataset and download instructions\n"
    "https://github.com/google-research-datasets/tydiqa-wana\n[2] Mr. TyDi collections and "
    "qrels\nhttps://github.com/castorini/mr.tydi\n[3] MIRACL benchmark\n"
    "https://github.com/project-miracl/miracl\n[4] Hugging Face dataset cards and "
    "configuration\nhttps://huggingface.co/docs/hub/datasets-cards\n"
    "https://huggingface.co/docs/hub/datasets-data-files"
)
p(
    "Previous experiment packaging reference: "
    "github.com/Ahmadawad1/arabic-normalization-retrieval and "
    "huggingface.co/datasets/ahmad-awad/arabic-normalization-retrieval. Reuse the publishing "
    "structure while documenting this study’s distinct question and data."
)

doc.core_properties.title = "Comparing Jordanian Arabic and MSA retrieval"
doc.core_properties.subject = "A practical experiment and learning guide for Brainwave Eval"
doc.core_properties.author = "Brainwave Eval"
for filename in ["Golden Sets Experiment Guide.docx", "Experiment Guide.docx"]:
    doc.save(ROOT / filename)
print("Updated both guide filenames with the same current guide.")
