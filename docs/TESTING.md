# Validation and acceptance checklist

## Automated checks

Run `bash tests/run-integration.sh` with Docker. It creates a private internal Docker network, MariaDB and WordPress with no published ports. It installs a disposable WordPress database, activates the plugin through WordPress's API and exercises real repository/REST code against that database. The script cleans up containers, anonymous database volumes and network on exit. Never point tests at production.

Coverage includes:

- PHP syntax for all plugin files and the test runner.
- Activation, migration version, repeated migrations, exact six subject seeds and empty academic tables.
- Administrator create/update/delete, HTML sanitization, field types, relational integrity and safe deletion.
- Source allowlist rejection, missing official URLs, unverified publication and mismatched syllabus/topic rejection.
- Anonymous, Subscriber and Editor denial for GET/POST/PATCH/DELETE on all five master collections.
- A nonadministrator with `manage_options` still denied; direct repository writes also checked.
- Missing/invalid nonces; invalid IDs and query-filter injection attempts.
- Draft/hidden questions unavailable for student progress, enum validation and forged owner ID rejection.
- All four progress states, repeated writes, two students with separate explorer and summary results.
- Real loopback HTTP requests through Apache and WordPress cookie authentication: anonymous, missing/invalid nonce, valid session, administrator access, denied student master writes and separate student progress.
- Source-verification revocation hides references and excludes their saved progress from the summary.
- Deactivation/reactivation preserve academic records and progress; incompatible schema blocks API access.
- Private/no-store REST response headers.

Fixtures use TEST ONLY labels and a non-existent example path on an allowlisted host. They establish behavior, not academic correctness. They are outside the distributable plugin folder.

JavaScript syntax: `node --check ca-final-command-center/assets/admin.js` and `node --check ca-final-command-center/assets/student.js`. ZIP structure/integrity is asserted by `python3 scripts/build.py`. CI repeats these checks before producing its artifact.

## Manual checks on private staging (not yet performed)

These require your WordPress/Hostinger environment and an iPad; they must not be reported as passed based on container tests.

1. **Backup and privacy:** record the latest database/files backup; confirm recovery options. Check staging needs hosting-level authentication in an incognito session. Do not rely on `noindex` or a Private page for whole-site protection.
2. **Installation:** upload the inner plugin ZIP through Safari/Files; activate with no fatal error. Confirm the six subjects. Confirm the plugin created no page, published no content and changed no DNS.
3. **Editor:** add one real chapter, optional topic, source document and draft reference. Verify the source yourself, approve it and publish the reference inside protected staging. Try a Google Drive URL and confirm rejection. Try a mismatched topic/syllabus and confirm rejection.
4. **Dashboard:** put the shortcode on a page within protected staging. At iPad portrait and landscape widths confirm readable filters, cards, empty/error messages, touch-sized controls and keyboard focus. Check narrow phone width too if available.
5. **Student isolation:** sign in as Subscriber A; mark a question Completed; reload. In another browser/session sign in as Subscriber B and confirm Not Started, then mark Needs Revision. Return to A and confirm Completed. Verify counts match real visible references.
6. **Master access:** as each Subscriber and an Editor, open `/wp-admin/admin.php?page=cafcc`; WordPress must deny access. With the user's own REST nonce, POST/PATCH/DELETE the master routes and confirm 403. Without authentication expect 401; missing/invalid nonces must not permit writes.
7. **Progress access:** try PUT with an extra `user_id` and confirm 400. Try another status or draft question ID and confirm rejection. No route should allow a student to request another student's progress.
8. **Revocation:** as Administrator revoke document verification. Both students must stop seeing the reference and associated counts. Reverify the source; their prior individual progress should return.
9. **Caching:** exclude the dashboard and REST URLs from LiteSpeed/Hostinger/CDN caches. Inspect REST responses for `private, no-store`. Repeat the two-account check after any cache changes. Reload an expired session to refresh the nonce.
10. **Retention:** deactivate/reactivate and confirm records and progress remain. Do not delete tables as part of this check.

## Practical limits

Automated tests use one WordPress/PHP/database combination and no real Hostinger services. Browser layout, assistive-technology behavior, third-party theme/plugin conflicts, Hostinger upload limits, real iPad Files interaction, HTTPS/cache behavior and backup recovery still require the checklist above. There are no end-to-end browser automation tests in 0.1.0.
