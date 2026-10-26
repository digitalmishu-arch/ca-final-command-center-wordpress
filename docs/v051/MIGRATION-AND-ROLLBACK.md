# Schema 6: additive V0.5.1 migration

Adds `cafcc_study_personal`, `sessions`, `events`, `highlights`, `scenarios`, `links` and `bulk`. They separate student occurrence activity, multiple timed attempts, idempotency receipts, anchored highlights, one stored common scenario, parent/alternative links and private owner bulk checkpoints. Unique student/occurrence, attempt and request-key indexes plus InnoDB transactions protect concurrent actions.

Adds `pilot_gate` and `manual_quality_pass` to the existing review table. **Existing FR January 2026 publications are hidden until their exact reconstruction receives renewed manual comparison.** Their question IDs, saved content, prior status/approval history and student activity are preserved. This is a visibility safeguard, not approval deletion or historical remapping. Other historical records are not mass-reprocessed.

A source-comparison signature binds the authorised reviewer, timestamp, original source identity/URL/attempt/series/edition, boundaries, shared facts and current question/answer content. Imported checked flags cannot forge it. Editing the bound evidence invalidates it. Final owner Publish still validates the exact answer identity, classification, content revisions and current source-wide permission. Publication is never granted by an extraction score or a passing test.

Existing `cafcc_question_references`, academic records, WordPress users/passwords, student progress, notes and bookmarks retain their IDs and data. New imports do not regenerate old stable research identifiers when the original source/section/reference identity is unchanged. New children/alternatives get distinct identities; the old parent/history remains. No existing progress is copied or reassigned to a new child automatically. A private old-to-new reconciliation file accompanies the research output.

The reconstruction comparison action explicitly replaces only the current private transcription/boundary/answer evidence after an administrator compares both versions. It retains existing identity, academic tags, owner notes and student data, withdraws publication, clears comparison approval and retains the old snapshot/audit. Existing and incoming exceptions remain visible. A conflicting source identity cannot be reassigned through this action.

Shared facts are stored once, with source hash/revision and child links. Editing them withdraws linked child publications. Withdrawing a question pauses its running new stopwatch sessions at the server timestamp; accumulated time and all prior attempts are retained. It does not change a student's stated outcome or mark an answer correct.

Stopwatch times measure server elapsed time while the timer is Running, including a background tab or disconnection. They do not measure attention or prove correctness. Pause/Resume/Finish use current session versions; retries use idempotency keys. A student's request cannot select another user or submit elapsed seconds.

Deactivation never deletes data. Downgrading an older plugin against schema 6 is refused. Before staging installation, retain paired files/database backups and the V0.5 ZIP. To roll back the whole installation, pause editing, retain a current backup, and restore the paired pre-upgrade files/database backup through your normal hosting tools. A backup restore can discard subsequent activity; retain/export it before restoring. Do not delete tables or reinstall an old plugin against the upgraded database.

No hosting, production, staging, DNS or payment operation is part of this migration work. Disposable database tests are not staging acceptance.
