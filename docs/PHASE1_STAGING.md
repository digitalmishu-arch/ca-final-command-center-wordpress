# Phase 1 — WordPress staging deployment and acceptance test

Status: **Prepared, not deployed or verified in WordPress**.

## Safety prerequisites
- Use a **staging** subdomain/site, not production. Protect it from public indexing and unwanted visitors.
- Back up staging files and database before installing. Do not copy real student accounts or personal data.
- Use HTTPS, an administrator account, and a supported WordPress / PHP / database stack.
- Give testers distinct WordPress user accounts. **Never send administrator passwords or API secrets in chat.**
- Confirm that the staging site is authorized for modification.

## Build a plugin ZIP
From this repository, package **only** the `ca-final-command-center` directory so the ZIP has this layout:
```
ca-final-command-center/
  ca-final-command-center.php
  assets/
    app.js
    style.css
```
Example from a checkout:
```bash
git checkout phase-1-staging
zip -r ca-final-command-center.zip ca-final-command-center
```
Or compress the plugin directory using your computer's file manager. Do **not** upload the GitHub repository's ZIP directly; WordPress expects the plugin PHP file at the plugin folder's root.

## Install on staging
1. Sign in to staging `/wp-admin/` as administrator.
2. Open **Plugins → Add New Plugin → Upload Plugin**.
3. Upload `ca-final-command-center.zip`, select **Install Now**, then **Activate**.
4. Confirm the admin left menu **CA Final CC** appears.
5. Open **Pages → Add New**, title it “CA Final Dashboard (Staging)”, add a Shortcode block with `[cafcc_dashboard]`, then publish with restricted access.
6. Create two separate *Subscriber* test accounts A and B. Do not give them academic edit rights.
7. Use an administrator to create two clearly identified *dummy* questions through **CA Final CC**.

## Smoke tests (record pass/fail)
- [ ] Plugin activates without PHP fatal errors or warnings.
- [ ] Both database tables are created with your WordPress table prefix (`cafcc_questions`, `cafcc_progress`).
- [ ] Administrator can create a question with subject, chapter, topic, source and exam term.
- [ ] Logged-out visitors cannot see the student dashboard data.
- [ ] Logged-in student A sees questions and can filter by subject.
- [ ] Student A saves `attempted` plus private notes; page reload retains values.
- [ ] Student A can change status to `revision`, then `mastered`.
- [ ] Student B does not see student A's statuses or private notes.
- [ ] Subscriber cannot see/use the **CA Final CC** admin menu or academic write endpoint.
- [ ] Student without a valid REST nonce cannot write progress using cookie authentication.
- [ ] Invalid question ID and invalid practice status return safe errors.
- [ ] Staging works on mobile-width and desktop browsers.
- [ ] Staging logs do not show new PHP/JS errors during the above tests.

## Known Phase 1 limits
- There is no academic bulk import, deduplication, search, pagination or learning analytics.
- The API returns at most 200 newest questions; scale-up requires pagination.
- `wpdb->replace` is sufficient for simple per-user state but should be reviewed before expansion.
- No automated test suite or staging server is configured in this repository yet.
- No deployment to staging is implied by committing code.

## Exit criteria
Do not move to Phase 2 until all smoke tests pass on staging with at least two separate student accounts. Record WordPress/PHP versions and any failures in a GitHub issue before fixing.
