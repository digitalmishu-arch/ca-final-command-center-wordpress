# Validation — Version 0.2.0, 22 October 2026

Local environment: WordPress 6.8.3, PHP 8.2.29, MariaDB 11.4. All test questions, marks, answers and history records are explicitly synthetic TEST ONLY fixtures outside the installable plugin folder.

| Check | Result |
| --- | --- |
| PHP syntax: all plugin and PHP test files | Passed |
| Original Version 0.1 regression tests | Passed in both scenarios |
| Schema-1 to schema-2 with populated existing tables; exact field/ID/progress preservation; repeated migration | Passed |
| Sourced catalogue: six editions, 180 nodes, official/editorial distinction, exact FR example | Passed |
| Administrator vs anonymous/Subscriber/Editor access across all connected collections and import/review endpoints | Passed |
| Real HTTP cookie/nonces, denied master writes and unpublished-answer privacy | Passed |
| Dependent hierarchy path validation, search, source/attempt matching, multiple topic mappings and IBS cross-subject paths | Passed |
| Occurrence uniqueness and verified marks | Passed |
| All five CSV types, preview non-persistence, owner-bound tokens, retry idempotence, duplicate revalidation and atomic late-failure rollback | Passed |
| Batch withdrawal retains exact student progress, cannot be republished or bypassed through v1 | Passed |
| Historical mappings and family/comparison entities do not remap question identities or invent repeat metrics | Passed |
| Browser: real WordPress student/admin login, dependent filters, CSV preview/commit, question cards, authored answer and official link, hidden draft answer, progress reload | Passed |
| Browser: iPad-width and phone-width layout, no horizontal overflow, parent changes clear descendants, no JavaScript page errors | Passed |
| JavaScript syntax and ZIP structure/integrity | Passed |

Final local totals: **336 fresh-install assertions and 340 prototype-compatibility assertions passed (676 total)**, including the guard that prevents original endpoints from reassigning connected source/question relationships. PHP syntax, all four JavaScript syntax checks and the 24-file plugin ZIP structure/integrity checks also passed.

Screenshots: [iPad-width](previews/ipad-explorer.png), [phone-width](previews/phone-explorer.png). Captured from the real local WordPress shortcode/API with reviewed hierarchy data and an empty verified-question state. Browser tests also exercised explicitly synthetic question/solution fixtures; those fixtures are not imported or shipped as exam data.

No Hostinger, staging/production deployment, real iPad Safari session, hosting backup restoration, external-cache configuration or live content migration was performed. Local Chromium viewport tests do not establish actual-device or third-party theme/plugin compatibility. GitHub Actions execution is reported separately in the PR/run page; the workflow tests and packages but does not deploy.
