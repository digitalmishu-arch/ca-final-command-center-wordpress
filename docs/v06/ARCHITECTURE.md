# Version 0.6 owner publication architecture

The normal workflow is one Academic ZIP preview followed by one owner-authorised batch publication. The older expert review services remain intact. The new policy explicitly distinguishes **permission to publish**, **technical identity/integrity**, **owner publication authorisation**, and **independent academic verification**.

## Additive schema 8

- `cafcc_owner_membership` links package ID, immutable candidate ID and retained review ID, with source hash and imported revision. Completed 0.5.2/0.5.3 package items are backfilled from their stored identities; never from titles/search terms. Matching old source identities are retained. No question, account, progress, notebook, highlight or timer ID is regenerated.
- `cafcc_owner_jobs` freezes the selected review IDs/revisions. Planning, canonical activation and application use bounded checkpoints. One explicit confirmation accepts provisional publication. Changed revisions are rejected; each publication is transactional. A retry cannot duplicate question identities or publications.
- `cafcc_academic_search_tags` stores separate academic search terms, evidence/method and naming-catalogue version. Its review/question/term indexes support server filtering. Student-created tags remain in private study storage.
- Existing review rows gain owner publication/revision, answer state, archive and manual-tag-override columns. Legacy publications default to their old policy. Existing taxonomy and editions gain a separate owner-enabled flag and provenance record. Their original review status remains unchanged. Importing or activating the plugin does not independently verify them.

All transaction tables must remain InnoDB. Migration is repeatable and non-destructive. There is no deletion on deactivation. Membership backfill is automatic; publication is not.

## Taxonomy and historical context

An owner batch can reuse a source-backed canonical path or an explicitly Editorial fallback. Usability is separate from `review_status`; an imported `needs_review` heading can become owner-enabled without being labelled independently verified. Official/editorial origin and original source location stay intact. Rejected nodes do not become available automatically.

A package publication enables its imported edition/node versions in bounded checkpoints. Record-level publication enables the applicable path. Historical applicability is checked using edition-specific attempt rules/source provenance. January 2026 FR stays in the May 2025 applicability / November 2024 material context, never blindly in the later May 2026 listing.

A prepared record with a demonstrably wrong edition can be reconciled only when source PDF hash, exact public URL, category, attempt, series and primary subject still match. A distinct correct-edition document context is used; the existing question and occurrence IDs remain. Prior source/metadata are audited. An actual source-identity conflict is not silently remapped. Old topic relationships remain in history.

## Provisional tags and naming catalogue

`standards-reference.json` retains 40 Ind AS and 38 SA naming references with official listing URLs, reference editions and a checked date. Sources:

- [ICAI compendium](https://www.icai.org/post/compendium-of-indian-accounting-standards), specifically the [2024–25 Volume I](https://www.icai.org/post/compendium-of-indian-accounting-standards-year-2024-25-volume-i) and [Volume II](https://www.icai.org/post/compendium-of-indian-accounting-standards-year-2024-25-volume-ii) naming lists.
- [ICAI auditing standards resources](https://www.icai.org/resources.shtml).

These are naming references, not a claim that the latest amendment applies to a historical question. Source-specific statutory and edition context remains attached to the occurrence. The catalogue deliberately retains historical names such as Ind AS 104; this does not imply that both 104 and 117 apply to every attempt.

The local engine combines retained proposed/owner-corrected paths, explicit standard references and constrained concept patterns. It stores `explicit_reference`, `imported_mapping`, `rule_assisted_inference`, `editorial_fallback` or `owner_correction` provenance. **It is not a configured external AI service and does not fabricate a model confidence score.** No private source content is sent to a provider. Inferred labels are not inserted as supposedly exact official headings. Unknown standard numbers are rejected. Unclear topics receive an explicitly Editorial “Topic to be refined” path. Manual tag correction can override inferred tags.

Student search and autocomplete can use standard numbers, official names, topics and aliases without selecting parents. Tag suggestions carry subject/edition context. Buttons on question cards expose the standard/concept tags visibly. Public results remain paginated and answer-free on initial load.

## Publication policy

The new publication audit records `owner_batch_provisional`, actor, time, current fingerprints and accepted exceptions. It does not forge individual classification approval or a manual PDF-comparison signature. Existing low-level publication flags remain compatibility gates; the separately exposed academic status is authoritative for whether independent verification occurred.

Hard blocks include a missing question, failed numerical/structural question checks, invalid table geometry, source/edition identity conflict, missing common facts and absent/out-of-scope/expired rights. Classification confidence and unperformed individual academic review are warnings, not hard blocks.

Answers have separate states. Exact source/series/question/subpart/alternative identity and eligible rights are required before solution text can be exposed. Unresolved mapping, shared-workings conflict, known uncertain answer table, missing content or withdrawn solution produces **Answer Pending**. A usable question can publish without that answer. A source-wide permission is resolved once for matching sources; pending-answer publication never widens its scope. Changing a grant/source still withdraws affected visibility.

Question text is sanitised selectable HTML. Current HTML table grids are validated, and extraction checks are retained. Owner text edits invalidate inherited extraction-check claims and preserve the previous revision. Automatic checks cannot establish academic or transcription accuracy; the reader labels provisional publication honestly.

## Correction, privacy and performance

The simplified editor saves a new revision, invalidates the affected publication and can republish atomically with owner confirmation. An answer can be withdrawn without discarding the question. Rollback restores historical content/tags into a new draft; it does not rewrite an audit record or reset student activity. Unresolved highlights remain unresolved rather than attaching to unrelated text.

Every new administrative route requires server-side `manage_options`, authenticated REST requests and nonce checks. Student entitlement, ownership, rights, subjective-only and current-content guards remain shared across old and new routes. No private Drive provenance, permission evidence or research-package payload appears in student APIs. Responses are private/no-store. Dynamic SQL values use prepared placeholders.

The library queries 30 rows per page. Public results use 20 occurrences per page. Batch jobs freeze up to 10,000 identity/revision pairs, validate/apply ten records per request, and activate at most 100 canonical entries per checkpoint. Full question/answer bodies are not loaded into the library list. Large-scale PDF processing remains offline.

## Test boundaries

Public fixtures and browser screenshots are independently authored. The unchanged private r016 archive is used only in disposable private integration/browser tests and never committed or uploaded to Actions. Publication in those installations is explicitly a software test authorisation, not owner academic verification or deployment. A genuine Hostinger/iPad acceptance step remains outstanding until the owner performs it.
