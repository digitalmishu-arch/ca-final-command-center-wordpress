# Version 0.4 private inventory and resumable research

Based on PR #4's corrected engine (2a0a3b3). The layout engine and all 42 previous regression tests are retained. The worker wraps it; it does not revert to Poppler/question-number slicing. No PDF processing runs inside WordPress or normal hosting requests.

## Actual coverage, 24 October 2026

The master workbook contains 423 inventory rows. A metadata scan of 118 accessible subject/model/case folders found 1,029 PDF IDs, including all 423 workbook IDs as listed/downloadable. The other 606 PDFs are outside this catalogue scope. No folder reached the 100-child listing bound. Missing-in-scanned-folders and listing-denied counts are zero; this is listing evidence, not a claim that every PDF was downloaded or is licensed.

Catalogue kinds: 91 RTP, 122 MTP question, 122 MTP answer, 79 suggested answer, six case-study and three MTP corrigendum rows. Six May 2026 examination papers and six matching-subject suggested-answer resources were additionally identified through official ICAI listings; factual metadata is in research/official-exam-inventory.json. The question-paper web reader recovered no text, so visual/OCR needs remain unresolved. Their copying rights and question-level pairings are unverified.

Only the existing six previously authorised local PDF copies were extracted. The new resumable worker processed them as two batches of three; the next run skipped all six idempotently. Output: FR 20, AFM 32, Audit 21, DT 22, IDT 24, IBS 20 = 139 parent/subpart records (113 parents). All remain Draft/Needs Review. No new real academic approval, publication, exact-repeat label or global accuracy percentage was created. The 417 other catalogue files are held pending the owner's private extraction/storage rights scope. Public reproduction rights remain separate. Listing/download access does not provide that evidence.

FR reviewed concept corrections and the AFM raw-number conflict remain source-scoped in the original ledger. Historical Audit/DT/IDT/IBS mapping, exact answer locations, FR Answer 19 corrigendum, general semantic classification and real MTP/examination profiles still require source/owner review. The delivered full exception report includes each unprocessed inventory row, pairing issue and pilot warning.

## Private commands

Install research/requirements.txt in a private worker environment. Python/PyMuPDF/openpyxl are not WordPress/Hostinger runtime dependencies.

```
python3 research/inventory.py reconcile --workbook work/workbook-inventory.json --drive-snapshot work/drive-snapshot.json --state work/inventory.sqlite --report work/inventory-report.json
python3 research/inventory.py batch --state work/inventory.sqlite --manifest work/authorised-sources.json --limit 3 --ledger work/corrections-ledger.json
```

The metadata snapshot is obtained through authorised Drive connector reads; no sharing changes are necessary. Existing workbook snapshot shape is `{values: [headers, ...rows]}`. Drive snapshot shape is `{folders: [{folder: {id,path}, result: {structuredContent: {files: [...]}}}]}`. File MIME/can_download and folder-limit indicators are retained. Provider failures must remain explicit, not converted to empty successful scans.

Each worker source uses the existing layout manifest fields plus `file_id`, `private_extraction_authorised: true` and nonempty `private_copy_basis`. MTP/exam sources also require a reviewed layout profile (`layout_profile_reviewed`), exact series/attempt evidence and authorised paired answers when supplied. Rights are checked before reading local file bytes. A fresh output directory, source/engine/manifest/ledger hashes, timestamps and previous review comparisons are retained. SQLite checkpoints, bounded batches, two-hour per-file leases and retained run attempts allow interruption/retry. Changed bytes/ledger/profile create a new attempt. Identical completed work is skipped. Failed identities are held unless `--retry-failed` is explicitly supplied; source/profile changes naturally produce a new identity. Duplicate bytes across file IDs are reported for review, not counted as repeated questions.

Use `research/bridge.py` to create metadata-only Studio draft JSON batches (maximum 100 rows) and an eight-sheet private XLSX research workbook. No source prose, WordPress taxonomy IDs, approvals or private Drive links are copied into Studio packets. Original source hashes/section/ref identities and prior corrections remain. Assign actual historical edition/node IDs in the Studio; do not substitute May 2026 for a January 2026 source.

The offline research workbook is not an authorised WordPress approval token. Import the reference-only draft JSON through administrator preview, then download a fresh server-issued Studio Review Excel for the secure decision round trip. Long text is never silently truncated.

## Scheduling and future files

No live Drive background synchronisation, cron schedule, stored Drive credential or Hostinger connection is installed. A private worker operator can refresh the connector metadata snapshot and run the same commands. Scheduling requires an actual private worker, authorised credentials, least-privilege folder access, monitored job runner and secure snapshot/materialisation path; these are not provisioned here. Raw PDFs, extracted private text, inventory state, workbooks and logs stay under ignored work/, outside the plugin ZIP and public Actions artifacts. Public CI runs authored synthetic fixtures only.

## Navigation proposals

`research/taxonomy_proposals.py` accepts observed contents-page metadata and the existing versioned catalogue. Printed chapter/page references determine the parent, rather than the last captured chapter heading. Ambiguous unit parents are held. Labels are balanced across chapters within a bounded per-source metadata budget. The output remains Editorial/Draft; it is not a question classifier or a complete approved syllabus. The v0.4 delivery includes 437 proposals (FR 69, AFM 42, Audit 109, DT 106, IDT 105, IBS six integration domains) and 181 unresolved mapping/paraphrase/context exceptions. These counts exclude the separately seeded Financial Instruments proposals and historical FR/AFM chapter headings. Source snapshots are metadata hashes, explicitly not PDF-byte hashes. Never infer permission to copy question/answer prose from these navigation facts.
