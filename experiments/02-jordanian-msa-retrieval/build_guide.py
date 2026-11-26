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
p("Updated 26 November 2026")
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
    "practice\n6  Review paired questions\n7  Split and freeze\n8  Study design\n9  "
    "Dense setup and model identity\n10  Register and run\n11  Inspect and export\n"
    "12 and 13  Interpretation and diagnosis\n14  Publishing"
)
h("What the current lab supports")
p(
    "The full paired workflow is available under Retrieval Experiments → Paired language "
    "study. It includes paired editing, source-aware splits, model selection, registration, "
    "protected holdout runs, four-condition reports and complete exports. It uses local "
    "Ollama for dense retrieval and does not require the older Know Hub indexed-search path."
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
    "Download a labeled Jordanian subset from the official TyDi QA-WANA repository [1]. Keep "
    "the original file unchanged and record its source release, download date and hash. The "
    "new UI can preview and adapt WANA v1 JSONL or JSON-array subsets below 11 MB. Larger "
    "releases need local sampling before upload."
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
    "Use the article text included in the selected release. The WANA v1 importer creates "
    "passages of up to 256 whitespace words with 32-word overlap, independently of answer "
    "locations. It preserves source identity and derives candidate qrels from answer-byte "
    "containment. Include competing passages and review alternative valid answers. Record "
    "corpus size and any later passage corrections."
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
    "provenance and human review notes. Alternatively, use the WANA adaptation on the "
    "paired study Data page, then review its candidate labels and edit both question forms."
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


page("6  Review paired questions in your UI")
h("Open the complete workflow")
p(
    "Open Retrieval Experiments and click Paired language study, or visit "
    "http://127.0.0.1:8000/evaluation/experiments/paired. The four steps are Data, Design, "
    "Run and Report. Select your Golden Set and version using the pickers at the top. This "
    "page implements the full four-condition study; the older configuration-experiment "
    "screen remains available for other tasks."
)
h("Import the benchmark adaptation")
p(
    "On Data, upload a labeled Jordanian TyDi QA-WANA JSONL subset or JSON array below 11 "
    "MB. Choose a maximum pair count and sampling seed. Click Preview adaptation, inspect "
    "the included question examples and exclusion reasons, then Import preview as draft. The "
    "importer accepts official WANA v1 fields and legacy TyDi-style byte annotations. It "
    "creates candidate qrels and an MSA placeholder; it does not pretend to author or review "
    "equivalent Arabic wording."
)
p(
    "For WANA v1, passages contain up to 256 whitespace-delimited words with 32-word "
    "overlap. Splitting is independent of answer locations. A minimal answer must fit inside "
    "a passage and match its UTF-8 byte offsets. NULL, yes/no and malformed or unsupported "
    "records are excluded with reasons. Record the source release and review coverage before "
    "reporting results."
)
h("Edit one complete intent at a time")
p(
    "Select a pair under Paired questions. Keep its existing query IDs. Enter the MSA and "
    "Jordanian questions, shared qrels as JSON, source article or source group, and your "
    "reviewer ID. For an existing unpaired import, enter the two existing question IDs to "
    "link them. To create a pair, enter a new pair ID and two different query IDs."
)
p(
    "Confirm the review checkbox only after checking equal meaning and the relevant "
    "passages. Click Save pair. Both forms receive identical qrels. Changing question text "
    "or labels resets the editor’s review confirmation. Saving also clears the pair’s split "
    "so you must reassign splits. The passage and question list below the editor helps you "
    "check IDs and read the corpus."
)
h("Why review comes first")
p(
    "Without equivalent meaning, you may measure two different tasks. Without shared labels, "
    "different scoring rules could create an apparent dialect effect. The validation panel "
    "flags missing forms, duplicate forms, mismatched labels, missing passages and missing "
    "human review. A frozen dataset must be forked in Golden Sets before editing."
)

page("7  Create a fair split and freeze the data")
h("Assign groups rather than individual questions")
p(
    "On Data, choose a sampling and split seed such as 42 and a Holdout fraction such as "
    "0.3. Click Assign paired splits. The lab keeps both forms together and connects pairs "
    "sharing any relevant passage or source article. All intents in a connected source group "
    "go to the same split."
)
p(
    "This avoids a subtle leak: if you tune on an MSA question, its Jordanian equivalent is "
    "no longer an unseen evaluation question. Shared articles can also reveal answer "
    "vocabulary. Enter source article IDs consistently; generic dataset descriptions are not "
    "treated as article IDs."
)
h("Check counts and freeze")
p(
    "Check the displayed Dev, Holdout and Unassigned question counts. Every intent "
    "contributes two questions. The number of source groups, rather than just query count, "
    "limits how much independent evidence you have. The split requires at least two source "
    "groups. Large connected groups can make the achieved fraction differ from your "
    "requested fraction."
)
p(
    "Resolve all pair validation issues and click Freeze version. Freezing records the "
    "content hash and prevents edits. The full protocol can be registered only when this "
    "frozen snapshot has complete reviewed pairs, both splits and no source group crossing "
    "the split boundary."
)
h("What dev and holdout mean")
p(
    "Dev is where you check the workflow and investigate settings. Holdout is reserved for "
    "the registered final question. The lab records prior evaluated queries and related "
    "sources across paired studies and checks older retrieval runs for matching questions. A "
    "later fork or new study cannot silently turn already evaluated material into a clean "
    "holdout."
)
p(
    "If a holdout has prior exposure, another run requires a written reason and is labeled "
    "exploratory. A tool cannot detect every external viewing or unpublished experiment; "
    "disclose any exposure outside the lab. Registration protects the recorded design, not "
    "the scientific quality of poorly constructed data."
)
h("Plan sample size honestly")
p(
    "A 50-intent pilot is a proposed starting point. It is not a guarantee that a five-point "
    "gap can be detected. Review the number of independent source groups and the resulting "
    "interval. Avoid enlarging the sample repeatedly until the result you wanted appears. If "
    "fewer than two groups remain in a scored split, the lab reports no uncertainty interval."
)

page("8  Fill in the study design")
h("Name and hypothesis")
p(
    "Open Design. Name: Jordanian versus MSA across BM25 and dense v1. Hypothesis: Under "
    "BM25, Jordanian Hit@5 will be lower than MSA Hit@5; a decrease of five percentage "
    "points is practically important. As a secondary question, the fixed dense model may "
    "improve Jordanian retrieval and reduce the deficit. These are predictions to test, not "
    "results."
)
h("Rationale")
p(
    "Enter: BM25 relies on word overlap, while dense embeddings may connect different words "
    "expressing similar meanings. Jordanian and MSA can differ in vocabulary and wording. "
    "Paired intents hold meaning and target passages fixed. The earlier normalization study "
    "motivates this investigation but does not establish a dialect effect."
)
p(
    "The rationale explains how we came up with the hypothesis. It is plausible that dialect "
    "vocabulary lowers lexical overlap; dense similarity might help, but a model can still "
    "perform poorly on Arabic or Jordanian wording. That uncertainty is why the experiment "
    "is useful."
)
h("Primary criterion")
p(
    "Choose Primary contrast: BM25 dialect gap; Expected direction: Decrease; Minimum "
    "meaningful effect: 0.05; Hit rate cutoff k: 5; Confidence level: 95%; Bootstrap seed: "
    "42. The primary contrast is the one prespecified decision. The dense gap, engine gains "
    "and gap change are secondary exploratory analyses unless you deliberately select one as "
    "primary before seeing results."
)
h("Understand all four conditions")
p(
    "A = BM25 with MSA; B = BM25 with Jordanian; C = dense with MSA; D = dense with "
    "Jordanian. Dialect gaps are B − A and D − C. Jordanian engine gain is D − B; MSA gain "
    "is C − A. Gap change is (D − C) − (B − A). Every difference uses the same intent pairs "
    "and is shown in percentage points."
)
p(
    "A positive gap change can occur because MSA got worse. It can also overshoot into an "
    "opposite gap. Inspect all four rates and the Jordanian gain before claiming a useful "
    "reduction in disadvantage. Never compare A directly with D and call that a pure engine "
    "effect; both engine and query form changed."
)

page("9  Select and identify a local dense model")
h("Start the local model service")
p(
    "The paired workflow talks directly to Ollama at http://127.0.0.1:11434. It does not "
    "require Know Hub or its database. Reuse an already running Ollama service. If needed, "
    "start Ollama and install a supported embedding model. The UI does not download model "
    "weights automatically."
)
code("ollama serve\nollama pull bge-m3")
p(
    "Run the pull command in a second terminal if ollama serve occupies the first. "
    "Downloading weights needs internet once; evaluation runs locally without paid APIs. "
    "Your dedicated GPU memory is about 8 GB, not the total shared graphics-memory figure. "
    "The lab records runtime information rather than assuming GPU execution."
)
h("Choose the model in Design")
p(
    "Click Refresh models, then select Local embedding model. Supported installed families "
    "are bge-m3 and nomic-embed-text. BGE-M3 is a multilingual candidate for this study [5]. "
    "Nomic can exercise the pipeline, but its result is not evidence about all multilingual "
    "dense models. Record the chosen model before comparing outcomes."
)
p(
    "The lab captures the model name, digest, model information and required prefixes. Nomic "
    "receives search_query and search_document prefixes; BGE-M3 uses its supported "
    "unprefixed mode. The service is restricted to loopback and locally installed supported "
    "embedding models. A cloud model or arbitrary remote endpoint is not part of this "
    "workflow."
)
h("What remains identical across engines")
p(
    "Both engines rank the same imported passages. The dense index uses exact cosine "
    "similarity, normalized vectors, no extra chunking and no silent truncation. An overlong "
    "passage causes a visible error; revise the shared dataset and create a new version "
    "rather than truncating only one engine’s input. BM25 uses its existing tokenizer with "
    "NFC and case folding, k1 = 1.5 and b = 0.75."
)
p(
    "Index identity includes corpus content, model metadata, prefixes and engine settings. "
    "Cached vectors have a checksum. The model is checked before and after scoring; a "
    "changed identity invalidates the run. The export retains index dimension, vector "
    "checksum, model identity and available runtime details. It does not contain weights or "
    "claim Arabic calibration."
)

page("10  Register and run all four conditions")
h("Save the protocol")
p(
    "With the intended dataset selected, click Save new study draft in Design. The lab "
    "validates the reviewed pairs and captures the dataset hash and installed model "
    "identity. The saved protocol appears under Run. Changing your plan requires saving a "
    "new study; the recorded version is not silently overwritten."
)
h("Register before final evaluation")
p(
    "Read the saved hypothesis, rationale, primary contrast, model digest and dataset hash. "
    "Click Register protocol. Registration requires a frozen, correctly split dataset and an "
    "unchanged model. The protocol hash records this design. This replaces the old guide’s "
    "manual draft-only workaround."
)
h("Run the development split first")
p(
    "Click Run all four on dev. The lab prepares or reuses the dense passage index and "
    "scores both forms through both engines. Progress and failures appear on the page. One "
    "intent produces four scored observations. A failed run is retained with its error and "
    "available traces; it never produces a completed verdict."
)
p(
    "Use the practice dataset to check mechanics, then use your reviewed benchmark sample. "
    "The index uses the entire fixed corpus, while only the selected split’s questions are "
    "scored. Selecting k determines the returned ranking depth and Hit@k cutoff for both "
    "engines. Scores from BM25 and cosine similarity are not directly comparable; "
    "relevance-based outcomes are."
)
h("Run holdout when ready")
p(
    "Click Run all four on holdout after registration. The first eligible access is labeled "
    "a registered holdout evaluation. If those questions or related sources were already "
    "evaluated, enter a reason of at least ten characters. The repeat is logged and labeled "
    "exploratory. All run attempts remain available in the study and export."
)
p(
    "The hypothesis may fail. A lower dense score, an unchanged gap or an inconclusive "
    "interval is a valid outcome. Do not choose a model, primary contrast or threshold after "
    "inspecting holdout results and then present the selection as the original registered "
    "question."
)

page("11  Inspect and export the complete result")
h("Read the four scores")
p(
    "Open Report and choose a completed run. The four cards show BM25/MSA, BM25/Jordanian, "
    "Dense/MSA and Dense/Jordanian Hit@k. The table shows both dialect gaps, each form’s "
    "engine gain and the gap change, with source-cluster bootstrap intervals. The registered "
    "primary contrast is marked."
)
p(
    "The practical-threshold statement checks whether the entire primary interval reaches "
    "the chosen effect in the expected direction. It is not a general claim about Arabic "
    "users. Dev runs and repeated holdout access remain exploratory. Secondary intervals are "
    "not corrected for multiple comparisons."
)
h("Inspect one intent across all four conditions")
p(
    "Use Previous and Next in Inspect an intent across all four conditions. Compare the "
    "question forms, correct passage IDs, hit or miss, first relevant rank and returned "
    "passages. Excerpts are limited to 600 characters; the exported dataset retains full "
    "text. This helps distinguish vocabulary mismatch from bad labels, changed meaning or "
    "missing evidence."
)
h("Export a reproducible package")
p(
    "Click Export complete experiment ZIP. It includes the protocol, exact dataset snapshot, "
    "an importable dataset, model and index identity, all raw runs including failures, "
    "paired CSV results, checksums, a README and replay_paired.py. Every run stays in the "
    "record, which helps prevent selective reporting."
)
p(
    "After extracting replay_paired.py, run it against the ZIP using the command below. This "
    "verifies checksums and recomputes Hit@k point estimates from saved rankings and qrels. "
    "It does not rerun model inference or certify the statistical assumptions."
)
code("python replay_paired.py path/to/experiment.zip")
p(
    "To repeat inference, use the exact model digest and exported settings and restore the "
    "recorded dataset and split. Importing import.json through Golden Sets creates a new dev "
    "draft; original splits are retained as metadata, while dataset.json is the exact audit "
    "snapshot. Preserve the original archive and lab revision."
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
    "All four observations for an intent belong together. The UI resamples connected source "
    "groups 2,000 times with the recorded seed, keeping all pairs within each source group "
    "intact. It reports pair-weighted mean intervals at the chosen confidence level. This "
    "respects known article dependence; unrecorded relationships can still make uncertainty "
    "too optimistic. A split with fewer than two source groups has no interval."
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
    "Open the exported results CSV and find pairs where an engine has msa = 1 and jo = 0, "
    "then the reverse. Inspect both queries, relevant passages and rankings on Report or "
    "in the corresponding runs JSON file. Also inspect shared successes for rank changes "
    "and shared misses for missing evidence. This connects "
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
    "Use this template separately for each engine: “Across [N] reviewed intents and [D] "
    "passages, [engine and model] found labeled relevant evidence in the top five for [X/N] "
    "MSA queries and [Y/N] Jordanian queries. Jordanian minus MSA was [delta] percentage "
    "points with a [confidence]% source-cluster interval of [lower, upper].” Then report "
    "both engine gains and the gap change. Identify the registered primary contrast and "
    "whether this was dev, first holdout, or repeat holdout."
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
    "This folder stores your guide and older export helper. The new UI exports the complete "
    "four-condition experiment as a ZIP. Create a separate publication repository such as "
    "jordanian-msa-retrieval, using the reviewed protocol, permitted data, both engine "
    "results and model identity from that archive. Retain all failed and completed attempts, "
    "and add your interpretation and limitations."
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
p("[5] BGE-M3 model card and multilingual retrieval usage\nhttps://huggingface.co/BAAI/bge-m3")
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
