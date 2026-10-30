# Publication preview diagnostics and protected draft corrections

This application patch adds a read-only diagnostic download and a narrowly scoped
source-correction path. It does not publish records, create rights, change schema
version 11 or change student pages. Academic reports and datasets are private
separate deliverables, not public software fixtures.

## Reconcile a saved preview

1. Back up staging and replace the application plugin. Do not uninstall it.
2. In Question Library, choose **Download last preview diagnostics**, using the
   browser that created the preview. This reads the saved job; it does not resume
   or confirm publication.
3. If the saved key is unavailable, repeat the original dataset and filters,
   create a preview and choose **Download private diagnostic report**. Close the
   panel without confirming publication.
4. Keep that JSON in the authorised restricted review area. It contains selected
   IDs/revisions, active filters, excluded memberships, internal import checkpoints,
   retained conflicts, source hashes and validation labels. It omits academic
   prose, student activity and permission documents.

Changing Package explicitly selects that dataset instead of retaining Current
scope. New previews save the resolved Current package identity. For older jobs,
where the historical package was not saved, the export labels that limitation;
selected record IDs remain authoritative. It also shows incomplete internal
child jobs and individual record-batch checkpoints. Do not infer the cause of a
selection mismatch from aggregate figures alone.

The export is paginated, nonce-protected, administrator-only and restricted to
the saved preview owner. Saved messages and current validation are separate.
Missing question text stays blocking without fictitious private-reference or
invalid-table diagnoses. Actual unsafe/private references remain blocked.

## Import a protected correction

Keep the academic ZIP compressed. Use Upload Questions → Preview → **Save as
Drafts**. Review the completion report, select the exact collection and inspect
protected conflicts. Do not confirm publication while material exceptions remain.

A correction requires the exact completed server-retained baseline archive,
original child input, entire current payload and captured imported revision.
The row must remain an unprepared, unapproved Needs Review draft. Earlier
reconstructed drafts may already be at a later imported revision; a hardcoded
revision-one assumption is not used for this path. Edited, prepared, published,
stale or internally inconsistent records remain explicit conflicts.

The older baseline reconstruction guard is retained. Where its prerequisite
collection has not been imported, do not force a correction over a conflict.
Stable identities and student history are never automatically moved. A valid
HTML grid or technical eligibility does not establish academic correctness.
Source-specific findings, evidence and review requirements belong in the private
workbook. No attribution, permission reference or missing amount is invented.

## Validation and rollback

Tests cover exact package selection, diagnostic paging and access controls,
interrupted imports, imported-revision matching, conflicting edits, safe HTML,
private-reference blocking and preservation of student records. Browser automation
is distinct from physical iPad acceptance. Check the linked Actions run for the
version of the application artifact being installed.

Restore previous plugin files for software rollback while retaining the current
database. Do not overwrite newer student activity with an older database backup.
Use audited draft revisions for targeted content recovery. There is no destructive
migration, forced database reset or deployment in this patch.
