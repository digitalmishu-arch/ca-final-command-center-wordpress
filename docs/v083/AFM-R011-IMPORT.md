# AFM r011 draft correction: iPad guide

Install the **0.8.3 application ZIP** from PR #17 before importing the private
academic ZIP. The academic collection format remains compatible with 0.8.2;
0.8.3 adds protected reconstruction and readable import conflict results.
This release does not add database tables or change the schema version.

1. Back up staging's database and plugin files. In WordPress → Plugins → Add
   Plugin → Upload Plugin, choose the application ZIP and replace the existing
   plugin. Do not uninstall it.
2. Open CA Final Command Center → Upload Questions. Choose the complete private
   `AFM_PAPER_2_ALL_ATTEMPTS_REVIEW_AND_IMPORT_r011.zip`, keeping it compressed.
3. Preview, then **Save as Drafts**. The importer processes its internal child
   packages in order. Resume the saved job after an interruption.
4. Select the exact r011 collection in Question Library. The intended membership
   is 1,130 subjective entries and 503 separate MCQ drafts. Nothing is published.
5. Read the completion summary and expand **Retained conflicts**. Open each
   protected record by its ID before applying an individual correction.

Only an untouched, unprepared, unapproved revision-1 r010 draft can be
reconstructed automatically. The server verifies the completed original
collection, stored original child input, entire current payload and content
fingerprints, then saves a new draft revision under a row lock. A raw payload
whose stored hash no longer matches is retained for explicit correction.
Local edits, prepared identities, approvals and published records are retained
as conflicts. Earlier 0.8.2 builds retain changed records without reconstruction.

Superseded child IDs and their student history are retained. The old-to-new
ledger identifies proposed complete-problem replacements; notes, progress and
timer history are **never automatically transferred**. Existing published
records are not automatically withdrawn by this import. Review any conflict
affecting published content and explicitly unpublish it when necessary.

To read the private workbook, uncompress a second copy in iPad Files and open
`AFM/academic-review/AFM-Owner-Review.xlsx` in Excel or Numbers. Its review cells
do not silently publish records. Obtain a fresh WordPress review export after
import for revision-safe decisions. Full HTML, source comparisons, remaining
issues and the ID ledger are included in the same archive.

All source-corroboration labels describe automated/AI-assisted evidence, not
independent human academic verification. Known official “No correct option”
outcomes remain unscored. Unresolved source, boundary and table/formula issues
retain publication holds. No permission scope is widened.

For software rollback, restore the previous plugin files and retain the current
database. Do not restore an older database over newer student activity. Imported
draft revisions and original collection history remain available for explicit
review. Any database restoration requires a separately planned backup recovery.
Hostinger staging and physical iPad Safari acceptance remain the owner's checks.
