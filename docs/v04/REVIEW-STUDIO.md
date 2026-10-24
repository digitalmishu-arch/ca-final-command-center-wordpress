# Question Review Studio and Excel decisions

Open **CA Final Command Center → Question Review Studio** as an administrator. The wide table uses server-side search/sort and 50-row pages. Select rows for export; hide/show columns without storing academic content in browser storage. Tap a Stable ID to open its secure detailed preview. Private text is shown only if its storage rights were explicitly recorded. Otherwise inspect the official source alongside the coordinates. Complete text stays in the detail record; table previews never pretend to contain the whole question.

Research integration: upload a `studio-drafts-NNN.json` file (at most 100 candidates/under 1.8 MB), inspect validation/duplicates/conflicts, then **Apply validated draft batch**. Imported candidates have immutable source hashes/sections/question numbers and permanent research IDs. No taxonomy is guessed to fit WordPress IDs. Select the applicable edition and reviewed chapter/unit/topic/subtopic nodes in the panel. All five original CSV imports/managers remain available.

Review source identification, boundary/number, classification, exact answer mapping, rights, question revision and answer revision separately. Each button records reviewer, time and revision. **Publish When Eligible** is a distinct eighth decision. Failed gates never publish. Classification changes invalidate the relevant approval; edits always withdraw final publication. Answer mappings carry source SHA-256, exact question/subpart identity and location. Historical statutory context is mandatory for DT/IDT source approval. Headings/editorial tags must already be reviewed in the taxonomy manager before classification approval.

Reference-only publication stores original educational metadata and an official ICAI link. It does not move private PDF prose into student content. To publish your own/licensed text, use the existing **Practice content & rights** editor; review and approve that saved content revision, then approve its corresponding Studio content revision and final publication. Student list APIs never include answers. Exact-occurrence answer requests are separate; the private research payload never appears in a student response.

Existing v0.3 connected occurrences are retained, but require explicit Studio adoption/review. The authenticated endpoint `POST /cafcc/v4/admin/reviews/adopt/{occurrence_id}` takes the verified PDF `source_hash` and identified `section`; it retains the original question/occurrence IDs and creates only a draft review record. Legacy v0.1 references must first be explicitly connected using the retained manager. Nothing is silently reclassified or granted new approval during upgrade.

## Excel round trip

1. Select 1–100 records (or export the current 50-row page) and tap **Download Review Excel**. Keep the workbook private. The server retains the issued IDs/revisions/source hashes, owner and seven-day expiry; those fields are protected for convenience, not relied on as security.
2. In Excel on iPad, edit **Approval Decisions** only. Every approval stage has its own dropdown; final publication is a separate column. Enter corrected existing numeric node IDs and explanatory notes there when needed. Use the Studio for source/answer/boundary corrections. Other sheets provide questions, answers, syllabus, sources, exceptions, batch instructions and actual progress counts.
3. Upload the `.xlsx`, inspect the changes and conflicts, then deliberately apply. Uploading/marking cells alone changes nothing. Stale/altered IDs, hashes, revisions, reused/expired workbooks and another administrator's export are rejected.
4. All changes apply through the same audited services and one database transaction with nested savepoints. A failed approval rolls the whole decision batch back. Do not combine Hold/Reject and Publish for the same row. Re-export after any intervening edit.

Only server-issued workbooks can apply decisions. The separately delivered offline research workbook is a private research aid; import its reference-only draft transport first, then export a fresh Studio workbook. This preserves identity and stale-revision protections before WordPress IDs exist.

OOXML is implemented without macros or an external PHP package. ZIP entries, expanded sizes, worksheet paths, formula cells, external relationships and DTD/entities are checked. No upload is extracted into the public media directory. Download bytes are returned only over the authenticated, nonce-protected, private/no-store administrator API. Temporary files are deleted. PHP ZIP, SimpleXML and mbstring extensions are required for XLSX; direct Studio review remains available if Excel export is unavailable.

A cell over Excel's 32,767-character limit gets an explicit secure-detail notice with its Stable ID; the original stored text is not truncated. The website's private administrator detail is the complete source of review content. No public bearer links are generated.

Batch withdrawal uses `POST /cafcc/v4/admin/research/withdraw` with `batch_key`. It holds the batch and retains all rows/history/progress. It is not a destructive rollback. Large-scale extraction stays outside Hostinger requests.
