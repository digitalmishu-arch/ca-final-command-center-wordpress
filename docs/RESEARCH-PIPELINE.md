# Private RTP research proof of concept

This adds offline research tools around the tested Version 0.2.0 importer. The plugin, connected hierarchy, review manager, database schema and student experience are unchanged. Python and Poppler run in the research workspace, never on Hostinger. No deployment or plugin replacement is needed for this change.

## Access and privacy

Access must succeed before extraction. The example manifest deliberately sets `access_authorised: false`. Record the authenticated acquisition or user attachment in a private manifest; a workbook link, filename, or Drive metadata listing alone does not establish readable PDF access. Use connected Drive raw-file download after MIME/metadata inspection, or direct user attachments. Never change a source's sharing to Anyone with the link.

The 23 October 2026 demonstration successfully read the research workbook and six individually selected PDF files through authenticated Drive downloads. It did not alter the workbook. Workbook rows informed sample selection and review cautions; provisional question classifications and duplicate seed rows were not imported as facts.

PDFs and extracted working text stay under ignored `work/`. PDFs are also excluded by `.gitignore`. The pipeline has no network client, WordPress credentials, publication API or analytics/repetition scoring. Public GitHub Actions uses synthetic fixtures only. Do not upload private manifests, PDF screenshots, text layers, research CSVs or review reports to public Actions artifacts or this public repository. Deliver actual research metadata through a separately verified private destination or user attachments.

## Reproduce in an authorised private workspace

Requirements: Python 3.10+ and Poppler `pdftotext`. No Python packages or Node.js are needed. Validate new/untrusted PDFs in a controlled environment with updated Poppler. The command has a 32 MiB file limit and a 60-second extraction timeout per file. Scanned PDFs without usable text are blocked for private OCR/manual handling; OCR is not implemented.

1. Copy `research/manifest.example.json` to `work/research/manifest.json`. Supply private local PDF paths, acquisition evidence, actual title tokens/evidence page, source attempt and direct official ICAI URLs. The script never downloads URLs. Source title is transcribed metadata checked against PDF tokens, not the archive filename. Document issue month remains blank when not established by the source; it is not inferred from the exam month or PDF creation timestamp.
2. Declare separate historical research editions in `edition_setup`. They are source-scoped classification contexts, not fabricated full study-material editions. Unknown edition/reprint months remain blank. Do not assign January 2026 papers to the May 2026 baseline. DT/IDT law cut-offs and assessment years require independent review.
3. Run `python3 research/rtp_pipeline.py work/research/manifest.json --output work/research/run-001`. Each run requires a new output directory. Exit 1 indicates extraction/annotation errors requiring review; inspect `errors.csv`. A successful CSV preflight does not approve academic content.
4. Open `review.html` privately. Choose a question and select its original PDF from the device. SHA-256 matching blocks a changed/wrong file when Web Crypto is available; otherwise the viewer explicitly requires manual file verification. The left panel shows metadata, suggested classifications and notes; the right panel shows the selected question/answer page. It does not embed or distribute PDFs. Review decisions download as a separate CSV and never approve or publish content.
5. Inspect `report.json`, the metadata sidecar and source documents before any administrator import. Preserve the entire run for provenance, including CSV hashes and the private acquisition manifest separately.

The optional private validation command is `CAFCC_RESEARCH_PACKAGE=/repo/work/research/run-001 bash tests/run-integration.sh`. It creates disposable local WordPress/MariaDB containers, provisions draft historical contexts, runs the unchanged real importer, checks retention, withdraws batches and removes the database. It never connects to an existing WordPress site. Do not set this variable in public GitHub Actions.

## Outputs and V0.2 compatibility

| Output | Purpose |
| --- | --- |
| `documents-001.csv` | Exact V0.2 document template: official title/type/URL, attempt, separately known issue period |
| `occurrences-001.csv` | Exact occurrence template: stable question/occurrence keys, PDF start page, Q/subquestion reference, verified marks or blank |
| `answers-001.csv` | Exact answer template, `official_link` only, URL/location, empty answer text and rights field |
| `hierarchy-001.csv`, `question_topics-001.csv` | Header-only when no historical mapping has been validated; **do not import empty files** |
| `review-sidecar.csv`, `review.json` | Suggested current-catalogue tags, editorial topics/subtopics, candidate subpart markers, confidence, review notes and Draft/Needs Review status; **not importer files** |
| `edition-setup.json` | Six administrator setup records; **not a CSV import type** |
| `report.json`, `errors.csv`, `review-issues.csv` | Source hashes, counts, preflight result, technical errors and unresolved academic review issues |
| `review.html` | Offline side-by-side source validation and session-only review decisions |

Headers/order come directly from the existing five plugin templates. Files split before exceeding 200 rows or 512 KiB. Extra confidence/status columns belong in the sidecar because the existing importer rejects additional headers. The importer itself forces Draft/Needs Review. Question master rows internally use `verification_status=unverified`; occurrences/answers use `review_status=needs_review`.

The stable identifier is a source-scoped research question key, not a verified cross-source question identity. Repeat-family consolidation is deferred. One occurrence is exported per source/reference/explicit subreference. The initial AFM Q1/Q2 subparts replace their aggregate parent export, so the run does not export both parent and children for those questions. Other candidate subparts remain review notes until separately checked. MCQ options are not automatically treated as question parts.

Current ICAI chapter/unit suggestions use existing sourced catalogue labels and carry the target edition key. Finer tags are explicitly editorial. These suggestions are never inserted into the historical hierarchy automatically. Ordinary subjects retain the existing same-edition restriction. IBS supports several cross-subject suggestions, but this POC exports no unapproved topic relationships. After historical taxonomy review, administrators can use the existing hierarchy and question-topic templates; multi-tag compatibility is covered by real importer tests. There is no automatic reclassification of old records.

## Demonstration: available six-file sample

| Subject | Attempt | PDF pages | Numbered questions | Draft occurrences | Answer-link candidates |
| --- | --- | ---: | ---: | ---: | ---: |
| FR | January 2026 | 27 | 20 | 20 | 19 |
| AFM | January 2026 | 29 | 16 | 24 | 24 |
| Advanced Audit | January 2026 | 26 | 20 | 20 | 20 |
| DT | January 2026 | 31 | 20 | 20 | 20 |
| IDT | January 2026 | 29 | 20 | 20 | 20 |
| IBS | September 2025 | 41 | 17 | 17 | 17 |
| Total | | 183 | 113 | 121 | 120 |

The official [January 2026 RTP listing](https://www.icai.org/post/rtp-final-course-jan2026) and [September 2025 RTP listing](https://www.icai.org/post/rtp-final-course-sep2025) supplied public source links. Public PDF identity was checked by title/attempt/page count and sample content, not by a complete byte comparison to the downloaded private archives. The private copies have individual SHA-256 provenance hashes. “Latest IBS” means latest RTP in the supplied workbook inventory, not the latest ICAI publication.

Six sample question pages were visually inspected in addition to text extraction. This is an extraction spot check, **not human CA approval or exhaustive validation**. A DT Q1 context-based suggestion was corrected after checking the actual question; this demonstrates why scenario-wide signals cannot approve individual-question tags.

Unresolved items:

- All 121 references need historical syllabus/classification review. The output intentionally leaves imported chapter/topic mappings empty. Detailed topic/subtopic suggestions cover selected representative items; the catalogue signal matcher does not classify every question.
- All marks remain blank. No numeric marks allocation was verifiable in these RTPs; amounts, percentages and words such as “distinctive marks” are not marks evidence. Blank does not mean zero.
- Numbering runs, candidate question extents, answer tables and nested subparts require source validation. Answer start references are not a complete solution page range. Scenario context can begin before the question page. PDF page numbers and printed page numbers can differ, especially AFM.
- AFM Q3/Q4 have multiple answer-page candidates because numbered content later in the solution can resemble answer headings. Both are flagged in the sidecar and require disambiguation.
- The private FR copy retains superseded wording in Answer 19 on PDF p.25. ICAI's [corrigendum](https://resource.cdn.icai.org/89601bos-aps2822-p1-corrigendum.pdf) says the hosted copy is corrected. Its answer reference is withheld until that version difference is reviewed; the original archive is preserved.
- The text extractor excludes Audit academic-update pages from question numbering. DT specifies A.Y.2025–26 and a 30 June 2025 update cut-off; IDT also specifies a 30 June 2025 cut-off. These are historical, not advice about current tax applicability.
- There are zero human CA approvals. No exact-repeat, globally-new, frequency or percentage conclusion was produced. Duplicate checks cover source bytes/identity and occurrence locations within this run; existing-site duplicates are checked again by WordPress preview/commit.

## iPad workflow

Source access succeeded for this sample, so no re-upload is needed. For future inaccessible PDFs: in the Google Drive iPad app, open a PDF's three-dot menu, choose **Open in / Send a copy → Save to Files**, then use ChatGPT's attachment button to select the six PDFs from Files. Keep Drive sharing private. Label each subject; filenames do not establish the attempt. If ChatGPT Work is unavailable, retain those six Files copies for the next session.

For review, download the private metadata bundle, tap its ZIP in Files to extract it, and read `READ-ME-FIRST.md`. Open CSVs in Numbers for inspection; import the original UTF-8 CSV bytes rather than a reformatted Numbers export. Use iPad Split View with the source PDF in Files/Books alongside the sidecar in Numbers. Local HTML JavaScript/PDF embedding varies in Safari/Quick Look; this Split View workflow is the fallback, not a reason to publish the review screen on Hostinger.

For a later, explicitly authorised administrator import: first prepare the six **Draft/Needs Review** historical edition contexts in the existing Academic Manager using `edition-setup.json` (select the subject; subject IDs are site-specific). Preview/commit documents, then occurrences, then answer references, one nonempty file at a time. Do not import sidecars, setup JSON or header-only files. Keep every record draft. WordPress preview is authoritative for the actual site's existing keys and duplicates. Batch withdrawal preserves all records and student progress. **This task performs no hosting import.**

## Validation

`python3 -m unittest discover -s tests -p 'test_research.py' -v` covers numbering/section boundaries, IBS references, formula/private-link rejection, marks, same-edition relationships, multi-tags, official answer rights, duplicate locations/files, required access evidence, private output paths, atomic source failure and no-prose exports. Existing WordPress integration includes synthetic research-shaped CSVs, permission/draft checks and progress retention. The optional private run additionally validates actual six-file metadata through the same importer in a disposable database.

No schema migration is introduced. The WordPress plugin remains Version 0.2.0; its installable ZIP is unchanged. Next development task: CA review of historical edition mappings and representative question/subpart/answer locations, beginning with the FR corrigendum, before any classification import or publication.
