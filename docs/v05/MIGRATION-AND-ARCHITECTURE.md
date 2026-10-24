# Schema 5 migration and publication architecture

Base: PR #10, `feat/v0.4.1-first-pilot`, commit `bff3dcaff07959b1a35f5e82b802181ab8ce8168`. Corrected PR #4/#8 research code and corrections remain in the branch. No old-main restart, merge, live deployment or account grant occurs.

Additions:

| Storage | Change | Preservation |
|---|---|---|
| `cafcc_bank_reviews` | Indexed `question_format`; grant ID/revision; indexed permission-required flag | Existing stable IDs, payload, approvals, academic IDs, notes and progress are retained. The new format derives only from explicit section/type evidence. Unknown remains mixed. |
| `cafcc_private_rights` | Administrator-only source-wide scope, revision, expiry, audit metadata and optional private permission PDF BLOB | Outside public uploads. No permission document is bundled or seeded. Existing rights audits remain. |
| Existing rich content/revisions | Bounded safe rich draft ingestion and current-revision owner publication | Content stays private until the owner publishes the exact revisions. Original snapshots retained. |
| Existing academic hierarchy | Optional nested official numbered subtopics; new-node closure indexing | No fabricated units or historical reparenting. Existing keys/wording are retained on taxonomy import; differences are warnings. |
| Existing Excel batches/audit | Simple three-decision workbook, exact source/content/revision checks, validated private archive books | Legacy advanced workbooks remain accepted through their original route. No macros or anonymous decisions. |

The migration creates no user/account, question, membership or publication. It does not delete or regenerate canonical academic/student records. It does not bulk-map old questions into current editions. New derived format/permission fields are separate from academic history. Older plugin/schema combinations are refused.

`CAFCC_Release_V5` implements the normal Needs Review / Publish / Reject workflow. Publish locks the review and applicable permission scope; validates edition, source, boundaries, exact answer hash/context/reference/subpart, reviewed taxonomy paths, full question/answer revisions and unresolved blockers; materialises the existing/permanent IDs; stores reviewed rich content and approval fingerprints; then publishes atomically. A failed validation withdraws publication and remains Needs Review. A stale decision cannot withdraw or overwrite a newer correction. Rejection and batch hold retain student activity.

The SQL gate applies to the original and connected APIs, exact-occurrence answers, rich content, notebooks and practice writes. MCQ/mixed records remain private. The canonical question type and occurrence type also guard older paths. An indexed permission flag avoids repeatedly parsing large private payloads during public searches. Correlated aggregate guards preserve indexed question/occurrence lookups rather than allowing an expensive semijoin plan. Facet and Studio pagination remain bounded at 20/50 rows. Source-wide scope revision/revocation/expiry is rechecked on reads.

Full private rich content is an explicit authorised import field, never an automatic copy from a raw extraction buffer. HTML is allowlisted server-side; tables, merged-cell attributes, lists, MathML, superscripts and subscripts are supported. Source PDFs and detailed extraction structures stay in the private offline worker. No answer prose is included in the initial student question response. Deliberate Show Answer uses the exact published occurrence; Hide Answer clears it.

The offline worker checkpoints each source/hash/engine revision in SQLite and retains earlier runs. Role/section identification precedes numbering. Corrected colour/font/coordinate heading logic is retained for its RTP profile, with conservative separate handling of older MTPs and alternating question/answer books. Shared parent facts remain attached to subparts. Answer candidates require document context plus exact reference/subpart; multiple matches remain unresolved. Numerical/sign/date/symbol and table checks flag uncertainty, not academic verification. A structural candidate is not an approved answer pair.

Private exports contain inventory, full candidate text/structured evidence, small JSON imports, official contents hierarchy, protected XLSX workbooks, exception reports, source hashes and checksums. No raw PDF, private extracted prose or permission document is committed to GitHub or included in CI artifacts. No background Drive schedule or Hostinger processing worker is installed.

## Validation scope

Use the recorded GitHub Actions runs for final results. Local tests run disposable WordPress/MariaDB, not Hostinger. The opt-in `tests/private-fr-import.php` validates actual authorised draft packages locally; it is never enabled by public CI. Synthetic browser approvals are explicitly test fixtures, never real ICAI academic approvals. Linux WebKit is engine emulation, not physical iPad Safari acceptance.
