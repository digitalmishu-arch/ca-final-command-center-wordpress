# AFM publication preview: 0.8.4 / r012

This patch adds a read-only diagnostic download and a narrowly scoped r011
correction path. It does not publish records, create rights, change schema
version 11, or change student pages. The original r011 ZIP remains unchanged.

## Reconcile staging before publication

The delivered r011 collection contains 1,130 distinct subjective candidates.
All contain question HTML, ICAI attribution and a matching source-register hash.
Its completed disposable import has 1,130 subjective memberships. The owner's
940-record selection is 190 fewer. Its exact cause cannot be established from
four aggregate counts or from a different disposable database.

1. Back up staging and replace the application plugin with 0.8.4. Do not uninstall.
2. In Question Library, select **Download last preview diagnostics**, using the
   same browser that created the preview. This reads the saved job key; it does
   not resume or confirm publication.
3. If that saved key is unavailable, repeat the original dataset and filters,
   select the records, and create a preview. In the confirmation panel choose
   **Download private diagnostic report**. Close the panel without confirming.
4. Keep the JSON private and provide it through the authorised restricted review
   folder. It contains selected IDs/revisions, active filters, package checkpoint
   states, excluded memberships, conflicts, source hashes and exact blocker
   labels. It omits academic prose, student activity and permission documents.

The export is paginated, nonce-protected, administrator-only and restricted to
the owner of the saved preview. Each row distinguishes the saved preview message
from current validation. Missing question text remains blocking; it no longer
also produces a fictitious private-reference or invalid-table diagnosis.

## What the r012 package changes

The private correction ledger contains five reconstructed tables in four
questions. Exact source hashes, source regions, before/after HTML fingerprints
and numerical-token conservation are recorded. One heading belonging to the
following question is removed. Question identities, numbering, answers,
attribution and previous material holds are retained. These are AI-assisted
source corrections, not owner academic approvals.

The full r012 collection retains the established single-upload format and
separate MCQ library. It does not relabel genuine MCQs as subjective or import
new MCQs. WordPress → Upload Questions → Preview → **Save as Drafts**. Inspect the
completion report and select the exact r012 collection. Do not Publish All while
material academic exceptions remain unresolved.

An existing question is corrected automatically only if its entire current
payload matches the exact completed, server-retained r011 input and the stored
imported revision. The row must remain an unprepared, unapproved Needs Review
draft. Edited, prepared, published, stale or internally inconsistent rows remain
explicit conflicts. Even an unchanged-looking edit is protected by its revision.
Previously materialised question identities and student history are never moved.

The r010 reconstruction guard remains supported. A direct r010 → r012 upgrade
may retain the four new corrections until r011 has been imported and reconciled;
do not force them over a conflict. Existing corrections take precedence.

## Validation and limitations

The actual 0.8.3 planning phase on the full disposable r011 collection reports
403 eligible, 727 blocked and 278 warning-bearing eligible records **conditional
on an explicitly labelled disposable rights fixture**. With no matching rights
grant, all records correctly block. This is not evidence of the owner's actual
staging permission scope. Technical eligibility is not academic verification.

The four invalid question-table records have source-backed HTML corrections.
Other question, answer, source-period, formula, font, boundary and corrigendum
holds remain individually documented in the private workbook. No hold is cleared
merely because HTML renders or text is present. The staging selection remains
unreconciled until its saved diagnostic is supplied. Physical iPad and hosting
acceptance are separate from local/CI browser automation.

For rollback restore previous plugin files while retaining the current database.
Do not replace a newer database containing student work with an older backup.
Corrections create audited draft revisions; use the existing revision history
for targeted recovery. This release has no destructive migration or uninstall.
