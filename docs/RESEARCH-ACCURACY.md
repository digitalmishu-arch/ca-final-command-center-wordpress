# Layout-aware academic research — engine 2

Based on the complete PR #3 research implementation, on a separate accuracy branch. The WordPress plugin is unchanged in this PR. Raw text is now comparison-only; the normal `research/rtp_pipeline.py` command delegates to the layout engine. No mass-processing mode is provided.

## What failed and what replaces it

The original numbering algorithm sliced from Q N to Q N+1. A chapter heading immediately before Q N+1 therefore contaminated Q N's classification. It also treated numbered working notes as answer starts and did not preserve font/colour/coordinates, sections or historical classification evidence.

The new stages are explicit:

1. **Identification:** confirm visible paper number, declared subject, RTP/MTP/exam type and exam attempt. MTP series must match printed evidence. An answer-only document is identified and held for explicit pairing; it is not processed as a question paper. Document issue period is distinct from the attempt. Unknown identities stop extraction.
2. **Layout:** offline PyMuPDF spans retain page, bounding box, font, size, weight and RGB colour. Versioned profiles are in `research/layout-profiles.json`. The six supplied RTPs use a one-column BoS profile; generic MTP/exam profiles have synthetic coverage only. Sparse scans and possible multiple columns become explicit exceptions. No OCR or automatic reading-order recovery is claimed.
3. **Boundaries:** a standalone styled heading closes the previous question *before* that heading and introduces the following question/group, including across page breaks. Shared case context has separate locations. MCQ sections, subjective sections, numbering restarts, uppercase Roman subparts and candidate operative subparts have source-scoped identities. Options, nested lists and tables are not assumed to be new questions. Uncertain subparts require review.
4. **Classification:** reliable preceding headings are matched to a separately supplied historical taxonomy. Transparent operative-requirement concept rules support selected MCQs; scenario/background keyword frequency does not approve classifications. This is a conservative rule engine with owner semantic review, not an autonomous academic understanding model. Unknown concepts remain unclassified. Fine topics are explicitly Editorial and require separate approval. A current-edition node is never substituted for a missing historical one.
5. **Answers:** left-margin styled markers are distinguished from indented working notes and paragraphs. More than one candidate stays ambiguous. A candidate location is not a verified answer location. Answer-only PDFs need explicit source pairing/manual matching in this pilot; that generalised pairing workflow remains unfinished.
6. **Review:** exact evidence, previous AI classifications, corrected suggestions, reasoning, uncertainty and source/section/question identities are shown privately. No test or confidence value verifies/publishes an academic record.

## Actual six-file reprocessing

The original six private PDFs were reused; no new PDFs were processed. All 113 parent references were recovered, with 24 additional candidate independently classifiable subparts: 137 review records. Parent records remain in the review package; original WordPress IDs and rows are not deleted, reassigned or updated. The before/after files include the old reference key and the new source-hash/section/ref identity for a future reviewed crosswalk, not an automatic migration.

All eight supplied FR concept corrections now agree with the uncorrected engine proposal: Q6–Q9 and Q14 are Ind AS 115; Q11 is Ind AS 102; Q12 is Ind AS 21; Q13 is Ind AS 8. Fine suggestions include contract modifications, remaining consideration, period-specific revenue recognition, consideration payable to a customer, group share-based arrangements, foreign-operation exchange differences and prior-period errors. These are editorial suggestions, not invented official headings.

The independently retrieved [historical FR listing](https://www.icai.org/post/sm-final-p1-may2025) explicitly covers May/September 2025 and January 2026. Its relevant labels place Ind AS 115 in Chapter 9; Ind AS 102 in Chapter 10 Unit 3; Ind AS 21 in Chapter 7 Unit 2; and Ind AS 8 in Chapter 4 Unit 1. Exact classification still needs owner approval. The old workbook's numbering and May 2026 keys were not silently reused. The [historical AFM listing](https://www.icai.org/post/sm-final-p2-may2025) is kept as a separate edition too. Both listings were retrieved 24 October 2026; this does not establish original publication dates.

AFM parent Q2 is under International Financial Management; parent Q5 is in the Security Valuation group with a Yield to Maturity suggestion. The owner labels “Q1–Q4 → Securitisation—Theory” may denote Q1(I)–Q1(IV). They are retained as unresolved numbering corrections, and are never applied arbitrarily to parent Q3/Q4. In this PDF, parent Q3 is introduced by Advanced Capital Budgeting Decisions and parent Q4 by Security Valuation. The private report keeps the owner's original correction events and the exact evidence for resolving that distinction.

All 137 records still require some owner review. Historical Audit/DT/IDT/IBS mappings remain unresolved; none borrows May 2026 taxonomy. FR Answer 19 remains held for its previously identified corrigendum. Some answer tables/markers remain absent or ambiguous. The complete exception report lists these per record; a successful extraction is not a claim that the record is academically correct.

## Persistent owner ledger

The private ledger is keyed by PDF SHA-256 + document section + original question + subreference. It records actor, timestamp, decision, classification, approved labels, prior-event hash and supersession. Same numbering in another PDF or section cannot inherit a correction. Every run uses a new directory, hashes the previous review and ledger, and retains the earlier outputs. Changed boundaries under a previous approval become a conflict. No approved classification is silently replaced.

The hash chain detects accidental/history changes; it is not an identity signature or authentication service. Keep the ledger private. Only the founder should create owner approval events. Tests never create approvals in the actual ledger.

On iPad: download the metadata-only corrected ZIP to Files, tap to extract, and open `review.html` if Safari supports it. Select and hash-verify the original PDF. Inspect heading/start/end coordinates, old/corrected classifications and answer candidates. Approve, reject, correct or mark Conflict. **Download a NEW ledger before closing**, and load that file next session. Local Safari/Quick Look support varies; use Split View with the PDF in Files/Books and the CSV/JSON evidence in Numbers or a text editor. Never publish the review page to Hostinger to work around local-browser restrictions.

CLI ledger editing is also append-only: `python research/ledger_cli.py work/ledger.json work/event.json --output work/new-ledger.json`. Superseding an existing approval must name its event hash explicitly.

## Commands and the owner-approved pilot gate

Install offline research dependencies with `python3 -m pip install -r research/requirements.txt`. PyMuPDF is an offline research dependency, not bundled into WordPress; review its upstream licensing when redistributing research tooling. Copy the manifest and historical-taxonomy examples into ignored `work/`, record authorised acquisition evidence and use source-specific profiles. Keep PDFs private.

Run `python3 research/rtp_pipeline.py work/research/manifest-layout.json --output work/research/NEW-RUN --ledger work/research/corrections-ledger.json --previous work/research/run-final/review.json`.

Outputs include `boundary-evidence.json`, `review.json`, `before-after.csv`, `comparison.json`, the persistent ledger, `historical-review-queue.csv`, complete exception JSON/CSV, `report.json` and the private reviewer. The `PRIVATE-segments-do-not-distribute.json` working file contains extracted source text, stays in ignored work, and is deliberately excluded from deliverable ZIPs and public GitHub/CI.

Default pilot CSVs are header-only and must not be imported. `--export-reviewed` requires fully owner-labelled exact boundaries, historical chapter/unit/topic keys and a single approved answer location; at most ten references can be selected. CSV preflight then uses the existing V0.2 templates and relationships. Even these exports remain Draft/Needs Review. Set up historical editions explicitly from the setup JSON, then preview hierarchy → documents → occurrences → question topics → answer references in a later authorised administrator session. Existing keys or edition conflicts must be reviewed; the exporter never remaps imported records. No hosting import occurs here.

## Accuracy gates

Metrics are separate: boundary agreement, exact chapter agreement, exact unit/topic agreement, owner-verified answer-location coverage and manual-review percentage. Exact agreement requires the corresponding owner-labelled benchmark field. The supplied concept corrections are not a complete coordinate/unit/topic/answer benchmark, so those agreement percentages are **unavailable**, not invented. Verified answer-location coverage is 0/137; all 137 currently require review. The ten context-resolved owner concept corrections match the automated concept proposals; that is a small labelled-concept result, not a global accuracy percentage. No bulk run opens before owner review.

Synthetic regression tests cover all ten requested defect classes, plus source type/series/answer-role identification, PDF attributes, decimal table values, background-keyword exclusion, ledger history and separate metrics. Real MTP/examination layout accuracy has not been demonstrated without authorised samples. Browser checks use private original PDFs for navigation/ledger loading only; they do not create owner approvals. Public Actions builds a **code-only** research artifact, never a private research-data artifact.
