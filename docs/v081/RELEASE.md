# Version 0.8.1 status

Based on exact PR #15 v0.8.0 commit `759052a8bbe058f08a5aac28cc47b8590de2915b`, on a separate feature branch. No hosting access, deployment, production changes or merge.

| Component | Delivery / limitation |
|---|---|
| Personal-list actions | Owner-scoped remove Important/bookmark/revision, note clear/Undo, recoverable session archive and saved-list hiding. Other activity and academic questions remain intact. |
| Attempt History | Server-paginated completed-session summaries and individual comparison; archived completed sessions count. Faster work does not establish correctness. |
| Modern Light | Optional, same-content Explorer/My Practice/Dashboard preview. Current appearance remains the default. Both light/dark supported. |
| Existing workflows | One-package import/publication, subjective/MCQ separation, lazy answers, entitlements, private activity and January IDs retained. |
| Study Planner / Resources | Their implementation and assets are unchanged. No planner redesign. |
| Source register | Actual bytes obtained for 535 PDFs: 526 main-directory files, eight supporting files and one source-link manifest. 12,790 PDF pages; 253,481,315 bytes. Nine normalized-content duplicate groups contain ten additional copies. These are source-copy relationships, not question-repeat claims. |
| Layout processing | Checkpointed per hash/engine/context. Source-specific IBS case numbering and short-adjacent-question heading regression added. Seven existing January source IDs/content-equivalent copies reserved. |
| Academic completion | **Not a fully verified six-subject bank.** Unknown MTP targets/series, historical SFM/current-AFM mapping, image PDFs, exact answer parts, tables and historical taxonomy have explicit holds/warnings. Private coverage reports give actual draft/import counts. No academic approval or publication is supplied. |
| OCR | Seven image-heavy PDFs, 186 pages, have separately hashed OCR review evidence. OCR figures/tables are not automatically publication eligible. |
| Naming / law | Existing Ind AS/SA naming catalogue reused; source-heading/statutory references are provisional editorial search proposals. Current law is not substituted for historical answers. Full source-backed historical chapter/topic reconciliation remains incomplete. General unsupported-formula-glyph, misplaced-placeholder and unresolved multi-row table checks add explicit holds; numeric token equality alone is insufficient. |
| Excel | Six private research overview books plus bounded revision-safe subjective decision books. Missing keys/options and long content remain in private details. MCQ sheet annotations are not a new automatic decision-import feature. |
| Delivery | Private subject bundles/reports are separate from the software. Exact filenames, hashes, Drive readback results and coverage are supplied privately. An internal workspace path is not delivery. |
| Physical iPad | Awaiting the owner's staging installation and Safari acceptance; no physical-device claim. |

## Test evidence

Local WordPress 6.8.3 / PHP 8.2.29: **961 legacy integration assertions**. Python: **112 authored regression tests**. Local Chromium tablet/phone tests cover reversible actions, comparison, lazy answers, two-student privacy, opt-in same-content appearance and unchanged Planner appearance. The exact v0.8→v0.8.1 upgrade fingerprint check retained rows across **62 prior tables**, including private activity. GitHub Actions reruns the public suites and installs WebKit; report its actual result separately rather than assuming it passed.

Real source-derived ZIP validation runs only in a private disposable WordPress installation. It performs preview, dependency-ordered draft import and checksum-identical reimport checks. Any deliberately tested publication in that installation is a **disposable software fixture**, not owner academic approval. No real data enters public test artifacts.

## Migration and recovery

Schema **10→11** adds only `cafcc_saved_visibility`, `cafcc_saved_events` and `cafcc_saved_locks` (actual WordPress prefix applies). Visibility is a sidecar; original stopwatch rows are not rewritten. The migration does not recreate planner records, retag academic data, change memberships or publish content. A failed migration leaves the old data retained and can be retried after resolving database availability/DDL permissions.

Private mutation requests require authenticated entitlements and a REST nonce, infer the owner server-side, compare the current action-specific fingerprint and retain a unique request key. Concurrent/stale Undo cannot replace a newer note or tag revision. Responses use private/no-store caching. Archive changes presentation, not lifetime practice totals.

New public Drive citations require an explicit authenticated source-copy confirmation for the exact file ID/hash and registered PDF role/context. This does not grant publication rights, expose private research URLs or change sharing. The source's current rights declaration must still cover the intended use.

See [iPad installation/import/rollback](IPAD.md). Private exceptions are actionable by exact source ID, hash, question reference and page; parsing counts must not be described as academic or publication accuracy.
