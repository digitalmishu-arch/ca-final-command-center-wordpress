# Schema 2 → schema 3: permitted practice content

Version 0.3.0 is based on tested Version 0.2.0 commit `3aab466a100c5b496a395f730434b81db92ecf1d`. This frontend/practice branch is independent of the offline research correction branch. No research PDF, extracted prose, corrections ledger or private research output is installed into WordPress.

## Additive storage only

| New table suffix | Purpose |
| --- | --- |
| `cafcc_practice_content` | Existing question ID + question/answer kind, sanitised rich text, question-only MCQ options, explicit rights basis/author/expiry, draft/review state and revision approval |
| `cafcc_practice_revisions` | Append-only snapshots, actor, event and revision evidence for edits/approvals |
| `cafcc_practice_notebook` | Current student ID + existing question ID, private note, bookmark and timestamp |

Actual table names use the site's WordPress prefix. New tables use InnoDB. No old table, column, question ID, edition, chapter, note, progress status or account is deleted or remapped. Existing Version 0.1/0.2 tables and incompatible original prototype tables remain in place. Original private prototype notes remain stored; this release does not guess their ID mapping or automatically convert them into the new notebook.

The schema version advances to 3 only after all new columns exist. Repeated migrations are idempotent. New content defaults to Draft/Needs Review with no approval. No practice questions, answers, marks or student activity are seeded. The six-subject draft hierarchy from V0.2 is retained.

## Content and rights lifecycle

Saving a new or edited content record always resets approval, increments its revision and keeps it draft. Existing question/kind identity is immutable. An administrator must separately confirm rights against the saved revision to publish it. Concurrent/stale edits or approvals are rejected. The previous approved payload is retained in the revision log. Read access requires the academic question/source/edition/occurrence to be available too.

Reference-only content cannot store copied question or answer prose in WordPress. Original/licensed material requires attribution and rights evidence. Expired licences are hidden at read/search time. HTML is explicitly allowlisted; scripts, images, links, arbitrary styles, event handlers and embeds are removed. Tables, calculations and a native MathML subset are supported. Question responses contain no solution payload; answers are fetched on an explicit action and cleared on collapse. The old reviewed plain-answer/reference modes remain supported.

Notebooks always derive their user ID from the signed-in server session. There is no user-selector write API. Unpublishing content/questions retains every notebook and progress row. Old question-delete routes also protect references with new content/notebook relationships. Deactivation, plugin-file removal and reactivation retain all records.

## Verification and rollback

Disposable WordPress/MariaDB tests snapshot every field/ID in the original six tables, twelve connected academic tables, new content/history/notebook rows and user accounts. They simulate schema-2 upgrade and repeated migration, then compare snapshots. Both fresh and prototype-compatibility scenarios pass. Existing private notes/progress and two-student separation are tested. Actual Hostinger/MySQL configuration has not been inspected.

Schema 3 deliberately refuses older plugin code expecting schema 2. To undo an installation, restore the matching **staging database backup and plugin files together**. Do not simply upload V0.2 after migration and do not delete new tables manually. No automatic downgrade or destructive cleanup is provided. Back up the staging database and files before a manual staging test. This task performs no installation, hosting connection or live migration.
