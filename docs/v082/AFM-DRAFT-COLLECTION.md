# AFM private draft collection, application v0.8.2

This patch continues PR #16 / v0.8.1. It adds a bounded, draft-only subject collection adapter. Existing Academic Package v1 ZIPs and the existing Upload → Preview → Publish All workflow are unchanged. No student interface, planner, source permission or database schema is replaced.

A whole-subject delivery can contain multiple source/attempt-specific Academic Package v1 children plus a private Excel workbook, source register, HTML details and evidence. The owner uploads that outer collection once through **Upload Questions → Preview → Save as Drafts**. Subjective and MCQ children stay separate. Collection uploads do not publish, grant rights, approve taxonomy, archive existing records or move student activity.

## Install and use on iPad

1. Back up the staging database and current plugin files using your existing hosting tools. This release does not access hosting.
2. Download the `ca-final-command-center-0.8.2` Actions artifact from the reviewed branch. In Files, uncompress the artifact wrapper to find **ca-final-command-center.zip**.
3. WordPress staging → Plugins → Add New → Upload Plugin → select that inner plugin ZIP → replace the installed version. Do not uninstall it. Confirm version 0.8.2.
4. Download the private AFM academic collection ZIP. **Keep this ZIP compressed for uploading.** It is academic data, not a plugin.
5. CA Final Command Center → Upload Questions → choose the entire AFM ZIP → Preview → inspect the actual counts → Save as Drafts. Keep the tab open. Resume saved import if disconnected.
6. Question Library → All records → AFM for subjective drafts. Use the MCQ Library separately. Source/attempt child memberships remain available; the collection does not replace the current January FR pilot filter.
7. To read the workbook, uncompress a separate downloaded copy in Files and open `AFM/academic-review/AFM-Owner-Review.xlsx` in Excel or Numbers. Full HTML is retained beside source/year/attempt details when Excel's cell limit is reached.

Research workbook choices are not automatically applied as publication approvals. Use a fresh WordPress review export and its revision-safe decision workflow for applying later decisions. All real records are Needs Review.

## Compatibility and safeguards

The new `CAFCC-ACADEMIC-COLLECTION-1` envelope is accepted only by v0.8.2 or later. It contains at most 100 existing v1 child ZIPs, 100 records per child and 2,500 records overall. Outer ZIP limit: 16,000,000 bytes; expanded review members: 64 MB; expanded child JSON: 48 MB. Ordinary v1 limits remain unchanged.

Each member is declared by path, byte length and SHA-256. Duplicate names, path traversal, symlinks, encryption, executable files, undeclared members, recursive collections and imported rights declarations are rejected. Review attachments are checked and discarded from the application import; they are never extracted to Media or served from public uploads. Existing administrator authentication, REST nonce, ownership and private-cache controls apply.

Dependency preview rolls back academic writes. Applying commits a bounded child and its parent cursor together. Repeated requests resume rather than replay committed children. Identical package keys with different bytes are rejected. Existing source IDs, stable question IDs, owner corrections, student accounts and private activity are retained. Unknown MTP examination targets and historical SFM applicability stay explicit; the worker cannot promote automatic matches to academic approval.

## Research tooling

AFM source profiles preserve issue periods, target-attempt evidence, original SFM identity, parent/part boundaries, shared facts and source coordinates. Answer association requires full subject/type/attempt/issue/series context and printed part identity, with internal numerical/terminology corroboration recorded separately. Bare RTP answer numbers, shifted MTP parent numbers and inline parent/part labels are handled without using numbered workings as new questions.

MCQs use printed options and explicit key rows. Conflicting/duplicate option labels, absent keys and an official “No correct option” remain exceptions. The worker does not solve an official MCQ or invent its answer. Booklet explanations stay attached to their individual source key.

Financial table repair is scoped to AFM. Vertically merged label cells can be reconstructed using repeated source monetary baselines only when all cell tokens and numeric tokens are conserved. Source crops and selectable HTML remain private comparison evidence. Passing those checks does not establish independent academic accuracy. Unresolved geometry remains a review/publication hold.

## Migration and rollback

Database schema remains **11**. No new tables, destructive changes or data reset are required. The version increment refreshes application assets.

To roll back the application, replace plugin files with the prior ZIP while retaining the database. Prior versions cannot interpret collection job items; resume those jobs only after restoring v0.8.2. Successfully imported ordinary child records remain normal Needs Review records. Do not restore an old database over newer student activity merely to roll back plugin files. The collection introduces no automatic withdrawal or deletion.

## Validation boundaries

Disposable WordPress/MariaDB tests cover existing publication and student privacy plus collection checksums, forbidden nesting/rights, mixed subjective/MCQ children, rollback preview, resumed checkpoints, unchanged reimport and correction retention. Authored browser fixtures contain no ICAI prose. Source-derived acceptance outputs stay private and explicitly distinguish disposable software approvals from owner academic decisions.

No Hostinger staging database or physical iPad has been inspected by this patch. Local browser emulation and CI WebKit checks are distinct from owner physical-device acceptance. Private content is never part of the public plugin/research-code artifact.
