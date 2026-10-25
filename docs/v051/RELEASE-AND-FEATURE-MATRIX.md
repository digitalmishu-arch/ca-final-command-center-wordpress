# V0.5.1: software candidate, January 2026 academic acceptance still open

Base: PR #11, commit `1d270dd99cbe939c52596b1567e1a199a6fec265`. This branch retains prior WordPress/research work. No historical archive mass run, live-site access, merge, payment or actual owner academic approval occurs.

## Source coverage

The authorised January 2026 FR RTP was reprocessed from its original 27-page PDF. It has ten initial MCQs and ten descriptive parent questions (Q11–Q20). The actual answer-section start is on PDF page 12; descriptive answers follow the MCQ key. Each question has one source-scoped structural answer candidate. These are **not ten academically verified pairs**. The earlier Q19 answer/corrigendum exception remains blocking. Q12 and Q15 scenario-level separation requires the owner's decision.

All five existing module initial-pages sources explicitly print **Edition: November, 2024**. The BoS applicability notice specifies those Modules 1–5 for January 2026. The retained `fr-may2025-jan2026` key describes that edition's applicability range; it is not the May 2026 edition. Existing keys/IDs/approved wording are not renamed or reparented.

Source evidence: [applicability notice](https://boslive.icai.org/announcement_details.php?id=522), [examination archive](https://www.icai.org/post/19926), [suggested answers listing](https://www.icai.org/post/sugg-ans-final-jan2026), [RTP PDF](https://resource.cdn.icai.org/88979bos-aps2822-p1.pdf).

The official [16-page examination PDF](https://resource.cdn.icai.org/90237bos-aps3809-final-p1.pdf) and [41-page suggested-answer PDF](https://resource.cdn.icai.org/91141bos-aps4314-sa-jan2026-p1.pdf) were identified, but their raw layout bytes were unavailable in this worker. The examination PDF is not replaced with an MCQ answer key. Connected Drive searches did not find the January 2026 MTP I/II question/answer originals. Their scheduled issue dates (17 November / 4 December 2025) remain separate from target attempt and require confirmation against the actual PDFs. Exact official MTP PDF URLs and corrigendum discovery remain unresolved. Six required raw documents are listed individually as missing, with no substitute attempt or fabricated question count.

The private manifest/coverage/exception reports are authoritative. Missing documents have unknown counts, not an invented zero-question result. The earlier July 2021 suggested-answer source is used only as a private regression: six parent questions/answer regions are distinguished; Q1(a)/(b) are separated; other ambiguous subparts remain in the exception queue. It is not January 2026 pilot data.

## Feature matrix

| Feature | Delivery state |
|---|---|
| Six-subject navigation; direct topics/aliases; chapter/subtopic filters | Retained; reviewed taxonomy only |
| Attempt, source, independent MTP-series filters | Implemented; actual MTP pilot data blocked on originals |
| Selectable rich questions, answers, tables and calculations | Implemented; real RTP transcription remains owner-reviewed provisional data |
| Question / Answer / Both; deliberate Show/Hide Answer | Implemented; no solution in initial question/study response; late hidden responses discarded |
| Previous/Next with active filters; filter persistence on refresh | Implemented |
| Read, attempted, completed, solved independently, revision markers | Implemented; correctness is explicit self-assessment |
| Notes, bookmarks/Important, private custom tags and filtering | Implemented; separate from master taxonomy |
| Anchored question/answer highlights | Implemented; unique quote/context remapping or unresolved state; answer quotes not in initial state |
| Server stopwatch, pause/resume/finish, repeated attempts | Implemented; server time, version checks, idempotent requests and InnoDB locks |
| Dashboard, revision queue, recent sessions, tagged topic activity | Implemented from current student's data; no fabricated percentage |
| My Practice | Separate saved-activity view with notes/tags/bookmarks/highlight/revision filters |
| Source-wise completion / exam slot matrix | Approved January 2026 coverage only; empty when no eligible records |
| Multi-year PYP trends / exact repetition | Not available; no inference from one attempt |
| Separate MCQ Practice | Coming Soon; preserved MCQs excluded from subjective APIs |
| Quick Concepts | Configurable owner-reviewed editorial text; no supplied approved content is invented |
| How It Works video | Administrator-configurable public HTTPS link; none hardcoded or auto-embedded |
| AI explanations | Not implemented/enabled; no simulated responses or provider costs |
| Three owner decisions, actionable checklist, table cell edits | Implemented; private reconstruction comparison retains prior IDs/classifications/history |
| Bulk owner decisions | Frozen revisions, bounded preview/apply checkpoints, stale checks and explicit confirmation |
| Excel decisions | Retained, revision-safe; source-comparison gate still applies. Export a fresh book after WordPress corrections/comparison |
| Premium responsive appearance, light/dark, reduced motion | Retained and extended; physical iPad Safari acceptance remains required |
| All four January source categories academically ready | **Not complete: MTP and exam originals plus owner decisions are missing** |

## Extraction changes and limits

`gold_layout.py` discovers a source-specific role/section/numbering profile before classifying records. It records heading text, fonts, colours and coordinates; scopes introducing headings forward; separates question/answer sections; excludes aligned working-note numbering in alternating answer books; and keeps lettered requirements separate from MCQ choices. Ambiguous layouts/requirements are not automatically verified.

Separate question and solution PDFs are paired only through an explicitly pinned answer-document hash plus subject, attempt, category, series and exact subpart/alternative. Answer HTML and table crops are read from the answer PDF. Changed or invalid originals produce a per-file exception while other files continue. These adapters still require validation against the missing real MTP/examination originals.

The renderer rejects ordinary two-column prose as a financial table. True ruled cells use word geometry. Printed accounting rows inside a large ruled cell are split by repeated monetary baselines, preserving blank subtotal cells and source section labels. Borderless financial rows require repeated aligned values. Cell values, row/column spans, page boxes, numerical checks and private PDF comparison crops are retained. The Rupee font's backtick glyph is explicitly normalised to ₹ with a recorded normalisation, not silently guessed.

Visual checks are additional evidence, not owner approval. The first numerical-only pass missed collapsed printed rows; that failure is retained as a regression. Complex journal tables, narrow/ambiguous regions, scenario boundaries and Q19 remain exceptions until resolved. No global accuracy percentage or zero-error claim is made.

Public CI uses original synthetic fixtures. Private PDF-derived data, source crops, workbooks and academic acceptance captures remain outside Git/CI artifacts. Actual test results and downloadable code artifacts are recorded in the pull request. Hostinger/staging data and real iPad Safari have not been inspected.
