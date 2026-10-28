# v0.8 upgrade and rollback

Base: PR14/v0.7 commit `0b4e42fdc9dbe10ec11473016397598971e2d2be`. Plugin version 0.8.0; database schema **10** (previous **9**).

The migration adds seven indexed InnoDB tables only:

| Table suffix | Purpose |
| --- | --- |
| planner_owners | Active plan and per-student write lock |
| planner_plans | Private plans, applicability, target dates, revisions, archives |
| planner_subjects | Course/group paper-name snapshot |
| planner_entries | Chapters/topics, tasks, revisions, mock tests, actual study logs |
| planner_events | Idempotent request/replay records |
| planner_audit | Private before/after revision history |
| resource_index | Administrator-verified course/attempt PDF metadata |

The existing notebook, progress, sessions, highlights, tags, MCQ records, academic sources, rights and publication tables are preserved. No question/answer text is rewritten. Existing routes remain available. Student data remains owner-scoped and private/no-store. No automatic academic import, publication, membership grant or deployment occurs.

The disposable v0.7 upgrade test fingerprints every row in all **55 existing academic/student/user tables** before and after the migration. It compares hashes, not exported private row values. New planner/resource data is stored separately. Fresh/legacy integration tests also exercise repeat migrations and existing publication/security checks.

## Before installing

Take a complete staging **database and plugin-files backup** using your existing backup process. Keep the v0.7 plugin ZIP and the backup timestamp. Install only on protected staging. No uninstall/reset is needed.

## Safe rollback

1. Prefer a forward correction if students have created new activity since the backup.
2. For a staging rollback, preserve a fresh copy of the v0.8 database/files first. Restore the matching pre-upgrade staging database and v0.7 files together.
3. Do not just lower the schema-version option or replace files against a newer schema: the existing downgrade guard deliberately refuses incompatible APIs.
4. Restoring the earlier database discards activity created after its backup. Stop staging usage before a restore and retain the later backup for reconciliation. No automated destructive downgrade is supplied.

Per-plan revisions and archived plans remain accessible. Changing attempt/course creates a new plan snapshot; prior revisions, mocks and logs remain in the old plan. Planner completion is self-reported, not academic mastery. Daily logged hours, stopwatch time, revision durations and mock durations are deliberately separate to avoid double counting.
