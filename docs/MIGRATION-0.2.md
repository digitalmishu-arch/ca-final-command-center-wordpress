# Data migration report — Version 0.2.0

## What was actually run

Schema-1-to-schema-2 migrations were tested in disposable WordPress/MariaDB installations containing existing questions, chapters, source documents and two students' progress. A second scenario also contained the older prototype tables and private notes. The test compares every field of all six schema-1 tables before and after migration and repeats the upgrade to check idempotence.

**No migration was run on Hostinger, staging or production.** Actual staging row counts, backups, installed plugin conflicts and cache configuration have not been inspected. This report describes the implementation and test evidence, not a claim that your hosting database has been changed.

## Changes to the database

The schema option advances from `cafcc_db_version = 1` to `2` only after setup succeeds. Existing schema-1 table definitions are retained. Twelve additive tables use the site's normal WordPress prefix:

- `cafcc_editions`: subject editions, month-precision dates, applicability and sources.
- `cafcc_taxonomy`: typed module/chapter/unit/topic/subtopic entities with validated parents, provenance, ordering and review/publication.
- `cafcc_document_meta`: edition, stable key, issue period, MTP series and publication metadata linked to existing source IDs.
- `cafcc_question_meta`: stable question key, edition, primary subject, type and optional family, linked to existing question IDs.
- `cafcc_occurrences`: unique source appearances with page/question/subquestion, verified marks and publication status.
- `cafcc_question_tags`: many-to-many hierarchy classifications.
- `cafcc_question_subjects`: additional IBS subject classifications.
- `cafcc_answers`: independently authored/licensed solutions or link-only official answer references.
- `cafcc_families`, `cafcc_comparisons`: future repetition-analysis relationships; no inferred percentages.
- `cafcc_edition_mappings`: historical correspondences without reassignment.
- `cafcc_import_batches`: owner, manifest and withdrawal status for append-only imports.

The six existing schema-1 tables (`subjects`, `chapters`, `topics`, `documents`, `question_references`, `student_progress`) retain all old rows, IDs, columns and progress. The older prototype `cafcc_questions` / `cafcc_progress`, including notes, are not altered, deleted or automatically converted.

The migration prepares six researched editions and 180 sourced/editorial hierarchy rows as **Draft/Needs Review**. It inserts no real question, source occurrence, answer text, mark or repetition metric. Re-running setup does not overwrite edited catalogue rows with the same stable keys.

## Existing content and deliberate classification

Unknown old syllabus strings are not guessed into an official edition. Version 0.1 references remain available outside connected filters, with their existing progress. An administrator can deliberately connect existing document/question IDs and add reviewed metadata. The initial connection is tested to leave the old row unchanged. Connected filtering requires actual mappings; a historical mapping never remaps questions or progress.

Adding draft metadata to an existing source withdraws it from student responses until reviewed. This is a deliberate admin operation, not an automatic migration side effect. Establish the edition and source review workflow on staging first.

One stable question can have several occurrences; progress stays attached to its question ID. Occurrence uniqueness includes official source URL, edition, page and question/subquestion location. Source identities with recorded appearances are not silently reassigned to a different URL. Add a corrected source/occurrence and unpublish the old one instead.

## CSV rollback and data retention

Preview validates inside a transaction that is always rolled back. No academic rows remain; auto-increment gaps are expected and do not remap IDs. Commit validates again under an import lock and is atomic. It only appends, never upserts an existing stable key.

Batch withdrawal marks the batch rolled back. It does not delete academic rows, private notes or progress. Both API versions exclude withdrawn source/question batches; the connected explorer also checks occurrences, editions and taxonomy paths. Dependent records remain stored and can become unavailable when their source/path is withdrawn. Existing administrator edits outside the batch are not reversed. Withdrawn batch records cannot be accidentally republished.

Safe import/write operations require InnoDB. No table engine is automatically converted. The migration uses normal WordPress `dbDelta` and preserves existing records; schema changes themselves are not represented as a reversible SQL transaction.

## Installation/recovery checks on your iPad

Before replacement: confirm staging URL, protect access, record database/files backup and restore option, record existing question/progress counts and test-account statuses. After replacement: check version 0.2.0, manager catalogue, original records, two-account progress and cache exclusions. These hosting-specific steps remain unperformed.

Deactivation retains data. Returning to older plugin files alone is not a supported schema downgrade: the old version should refuse the newer schema. Restore the matching **database and plugin-files backup** together. Never edit the schema-version option to force a downgrade.
