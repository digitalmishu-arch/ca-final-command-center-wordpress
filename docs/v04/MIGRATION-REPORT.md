# Version 0.3 → 0.4 migration report

WordPress foundation: PR #5, commit 8b9ed731b37a750b44bbfaa7cdee94ebb8ad2536. Corrected offline engine: PR #4, commit 2a0a3b3d372895f21850dbfaf825a3bf8b837ae6, extended independently in PR #8. No Hostinger installation or user database was accessed. These results are from disposable WordPress/MariaDB databases.

## Additive schema 4

Eight new prefix-aware InnoDB tables: `cafcc_bank_closure`, `aliases`, `reviews`, `audit`, `batches`, `access`, `access_events`, `resources`. Their purposes are ancestor indexing; reviewed search aliases; occurrence-specific private review/approvals; immutable audit snapshots; import/export manifests; WordPress-user entitlements; access audit; official source directory. Review identity is unique by stable candidate ID, source SHA-256 + section + question/subpart, and linked occurrence ID. Public text is bound to the approved saved content ID/revision.

Existing `cafcc_document_meta` gains `source_sha256`, `source_revision`, `scheme`, `law_context`, with empty defaults. Existing `cafcc_occurrences` gains `document_section` with an empty default. Source hashes become immutable once explicitly bound. New occurrence identities include verified source bytes/section; legacy location hashes are retained. Additional indexes cover taxonomy type/title/parent/publication, document source/attempt, occurrence document/question/publication, and topic-node/question lookups. No existing column is dropped, no table is truncated and no foreign user/question/progress IDs are reassigned.

Append-only seed: 76 sourced historical FR/AFM hierarchy nodes in two separate editions, plus 24 proposed FR Financial Instruments editorial nodes, separating Ind AS 109, 32 and 107. Existing keys/states are preserved. Original six-subject 180-node catalogue remains. Another 437 editorial navigation proposals are packaged as review data and loaded only on administrator preview/commit (100 missing entries maximum per batch). They are never automatically published or used to classify an old attempt.

Closure is derived from retained taxonomy IDs. Existing question references, occurrences, rights/content revisions, notes, bookmarks, progress, WordPress users/passwords and previous corrections are retained. Deactivation and ordinary upgrades delete no academic/student rows. InnoDB is required for academic review transactions; the plugin does not silently convert table engines.

## Deliberate visibility/access changes

Preservation does not imply automatic new approvals. Existing v0.3 published flags cannot bypass the eight-stage Studio gate. Adopt an existing connected occurrence using its actual source SHA-256 and section; approve it explicitly. Legacy v0.1 references first need an explicit connected edition/occurrence in the retained manager. No migration guesses their historical taxonomy.

Existing Subscribers without an access decision are `legacy_pending`. Their IDs, logins, passwords, notes and practice records survive, but practice access requires explicit identity/email review or a fresh verification link and manual entitlement. Administrators retain preview access. Previously valid test Subscribers therefore need the documented manual migration before testing as students.

## Verification and rollback

Fresh and populated prototype paths are tested. The test suite hashes every row in chunks before retrying schema 3 → 4 with 10,000 synthetic occurrences, comparing all fields/IDs in core questions, connected metadata/occurrences/tags/reviews, notebook, permitted content, progress and WordPress users. Real Hostinger data has not been tested or changed.

Before owner installation, take a staging database **and files** backup and retain the v0.3 ZIP. Test privately. A rollback restores that matched database/files snapshot together; merely uploading the old ZIP would remove new security gates while leaving schema-4 data/decisions. Do not use an old plugin to access a newer database as a rollback shortcut. Soft batch Hold withdraws publication atomically without removing records/progress; Resume returns drafts and never republishes. Never restore production from this disposable test database.
