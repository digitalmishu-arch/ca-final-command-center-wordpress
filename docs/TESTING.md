# Testing — Version 0.2.0

## Reproducible automated checks

```sh
bash tests/run-integration.sh
CAFCC_TEST_LEGACY=1 bash tests/run-integration.sh
node --check ca-final-command-center/assets/admin.js
node --check ca-final-command-center/assets/student.js
node --check ca-final-command-center/assets/explorer.js
node --check ca-final-command-center/assets/manager.js
python3 scripts/build.py
```

Docker creates a disposable WordPress/MariaDB database and internal network; default tests publish no ports. Containers/volumes/network are removed afterward. No Hostinger credentials, endpoint or existing database is used. PHP syntax checks run inside the WordPress image. Node/Python are contributor/CI tools only.

`tests/integration.php` retains the Version 0.1 suite and includes `tests/v02.php`. The latter tests additive migrations against populated original tables with exact row comparisons; edition/hierarchy provenance and publication; every new collection's permissions; actual HTTP authentication; dependent paths; search; multiple tags; source/attempt combinations; verified marks; unique occurrences; IBS tags; answer rights/privacy; all five CSV imports; token ownership; retry idempotence; late duplicate races; atomic rollback; safe withdrawal and v1 compatibility guards. Synthetic fixtures are explicitly marked TEST ONLY and are outside the distributable folder.

## Optional real browser smoke test

Prerequisites: Python Playwright and Chromium installed in the development environment (the script currently uses `/usr/bin/chromium`).

```sh
CAFCC_PREVIEW=1 bash tests/run-integration.sh
python3 tests/browser-smoke.py
```

This mode keeps a disposable preview on **127.0.0.1:8092 only**, creates a local shortcode page and records its container/network names in `work/preview-containers.txt`. Its synthetic test accounts are not production credentials. The browser uses real WordPress login and APIs, tests the dependent FR path, mobile layout, administrator CSV preview/commit, reviewed answer modes and saved student status. It saves screenshots under `docs/previews/` before publishing any synthetic test question for the remaining UI assertions.

Afterward, remove the two named containers with `docker rm -fv` and their named network with `docker network rm`, using exactly the names in `work/preview-containers.txt`. Never run preview fixtures against a real WordPress database; `tests/preview.php` requires the disposable `cafcc_test` database.

## Manual acceptance on your protected Hostinger staging

These checks remain unperformed here.

1. Confirm staging URL and privacy protection; record a current database/files backup and restore option. Do not rely on `noindex` alone.
2. Record existing source/question counts and two students' saved statuses. Upload the inner 0.2.0 plugin ZIP from iPad Files using WordPress's replace-version flow. Confirm version/schema setup without a fatal error. Nothing should automatically publish.
3. Confirm old questions, prototype notes and progress remain. Inspect the six draft sourced editions and 180 starter hierarchy entries; check dates/applicability against source links. Do not assume the May 2026 baseline covers later tax attempts.
4. Publish reviewed official headings for one edition. Approve any editorial topic/subtopic nodes separately. Confirm the student selectors load the actual dependent chapter/unit/topic/subtopic path. Try incompatible IDs through REST and confirm rejection.
5. Add one real reviewed source, stable question, occurrence and multiple classifications. Check source title/URL, issue period/series, page and question/subquestion number. Leave marks empty unless verified.
6. Test the source/attempt filters and search. Another appearance of the same question should retain the same stable question/progress identity. Duplicate appearance locations must be rejected.
7. Use an authored/licensed solution only with a recorded rights basis. For unlicensed official answers, use only their URL and answer location. Verify draft/unpublished text stays hidden from students.
8. In two separate Subscriber sessions, save different statuses and reload. Confirm neither session sees or changes the other student's progress. Anonymous users must be asked to sign in; students/editors must not use master/import/review routes or the admin manager.
9. Download each CSV template, preview a small valid file, inspect Draft/Needs Review output, commit once and try a retry. Try invalid/duplicate records; they must not partly import. Withdraw a batch after test progress exists; references should disappear while progress/rows remain stored.
10. Unpublish an incorrect occurrence/source/question. Test that hidden content cannot be reached through either REST namespace. Existing progress should reappear when the same permitted record is reviewed again; withdrawn import batches require a corrected new batch.
11. Exclude dashboard and both REST namespaces from Hostinger/CDN/LiteSpeed caches, including plain `?rest_route=` URLs. Keep logged-in caching disabled and repeat the two-account check. Reload to renew expired nonces.
12. On actual iPad Safari and a phone, test native selectors, touch targets, landscape/portrait, answer-panel keyboard/focus behavior and file upload/download. Check theme/plugin conflicts and backup restoration separately. Deactivation/reactivation should retain all records and statuses.
