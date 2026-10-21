# CA Final Command Center — WordPress plugin 0.1.0

A standalone PHP/MySQL WordPress plugin for CA Final academic references and individual student practice progress. Runs on ordinary WordPress hosting, including Hostinger Business. **No Node.js, Supabase, external application server, subscriptions or payments are needed on your hosting.**

## Included in 0.1.0

- Versioned, repeatable database installation and upgrades using the WordPress table prefix.
- Six initial subjects: FR, AFM, Advanced Audit, DT, IDT and IBS.
- Administrator editor for subjects, chapters, topics, source documents and question references.
- Source type, exam attempt, syllabus version, question number, chapter/topic association, official URL, verification and publication states.
- `[ca_final_command_center]` student dashboard and chapter-wise question explorer.
- Per-account Not Started / Attempted / Needs Revision / Completed progress.
- Empty states until verified references exist. No exam attempts, chapters, question content or analytics are invented or seeded.
- A test-and-build GitHub Actions workflow with a downloadable installable ZIP.

The code does **not** create a page, publish a site, register students, change DNS, contact Hostinger, or install other plugins. Only the six subject records are added automatically.

## Requirements

- WordPress 6.6 or newer; PHP 8.1 or newer; MySQL 8.0+ or MariaDB 10.6+ recommended.
- A normal administrator account with permission to upload plugins.
- HTTPS for a hosted installation. Network-wide multisite activation is intentionally unsupported; activate per site.
- Tested on WordPress 6.8.3, PHP 8.2.29 and MariaDB 11.4 in disposable containers. Hostinger and an actual iPad have not been accessed or tested.

## Install from an iPad

Use a private staging/development WordPress site with a current database/files backup first. This repository and its pull request do not deploy anything to Hostinger.

1. Download **`ca-final-command-center.zip`** into the iPad Files app. Do not upload GitHub's **Code → Download ZIP** source archive.
2. In Safari, open the staging site's WordPress Admin. Sign in as an administrator.
3. Go to **Plugins → Add New Plugin → Upload Plugin → Choose File → Browse** and select `ca-final-command-center.zip` from Files.
4. Tap **Install Now**, then **Activate Plugin**. If upload is unavailable, verify your account's administrator permissions and whether hosting configuration disables file modifications. Do not change production configuration to work around this.
5. Open **CA Final Command Center** in the WordPress Admin menu. You should see six subjects and no chapters, source documents or questions.
6. Add a page on the private staging site and place `[ca_final_command_center]` in a Shortcode block. For an owner-only preview, keep it private. To test student accounts, use a staging site protected by hosting-level access control and make the test page accessible *within that protected site*. A WordPress Private page is not readable by ordinary Subscriber accounts.
7. Use **Users → Add New** to create two test accounts with the **Subscriber** role. Test each account's dashboard and progress separately.

A shortcode page requires a signed-in account to access academic questions. **This is not whole-site privacy protection.** Search-engine discouragement alone does not make staging private. Use Hostinger's available password/access protection on staging before real student or unpublished academic data is added.

### Download a ZIP from GitHub without a laptop

Open this repository in Safari → **Actions → Test and build WordPress plugin** → open a successful run for the feature branch/PR → **Artifacts → ca-final-command-center-0.1.0**. GitHub sign-in may be required.

GitHub wraps artifacts in an outer ZIP. Tap that downloaded archive in Files to extract it. Inside is **`ca-final-command-center.zip`**, the file to upload to WordPress. Do not extract the inner plugin ZIP. Artifacts expire after 30 days; a new successful run creates another. The workflow runs on branch pushes and pull requests. After it reaches the default branch, **Run workflow** is also available manually.

The plugin ZIP contains:

```text
ca-final-command-center/
  ca-final-command-center.php
  includes/
  assets/
  readme.txt
```

### If updating an existing test installation

Back up the staging database/files, upload the newer plugin ZIP, and use WordPress's replace-version prompt. Existing academic records and progress remain. Migrations run after activation and when a newer schema version loads. Never downgrade the database or replace a live site without a separate approved release process.

## Add the first reviewed reference

Only an Administrator can do this. Use **CA Final Command Center → Record type**:

1. **Chapters:** choose one seeded subject, enter the real chapter title and exact syllabus version. Position controls explorer order.
2. **Topics:** choose the chapter and enter a real topic title (optional for a question).
3. **Documents:** enter the source title, source type (`exam`, `rtp`, `mtp`, `study_material`, `other`), actual exam attempt/context and matching syllabus version. For a source without a specific attempt, use a truthful description such as `Not attempt-specific`; do not guess an exam date.
4. Add a direct official HTTPS ICAI resource URL. Review the actual source yourself before setting **Verification Status → Verified**. Accepted hosts are `icai.org`, `icai.nic.in` and their subdomains. Query strings, embedded credentials, fragments, custom ports, Google Drive and other hosts are rejected. This conservative policy may need a future allowlist change for other official resource hosts.
5. **Questions:** choose the source document, chapter and optional topic, enter the actual question number and a short reference title. Initially save it as **Unverified / Draft**. After checking the official source, set **Verified / Published**.

A published question appears only while **both question and document are verified**, the source has an official URL, and the document/chapter syllabus versions match. Revoke verification or change the question to Draft to hide it. The plugin does not fetch URLs, check whether a URL returns a PDF, or verify academic accuracy automatically.

Existing dependent records block deletion or structural reassignment. Questions with student progress cannot be deleted; unpublish them instead. Revoking verification hides the reference and excludes it from the student summary while keeping saved progress in the database.

## Privacy, permissions and caching

- Master edits and approvals require both the `administrator` role and `manage_options` capability (or an authorized multisite super administrator). Editors, students and public visitors cannot write master records through REST or direct admin access.
- Every plugin REST request requires a signed-in account, `read` capability and a valid WordPress REST nonce. Master writes additionally check administrator privileges inside the repository layer.
- Progress writes accept only a status. The owner is always the authenticated WordPress user, never a supplied `user_id`.
- Resource links are limited to approved official ICAI hosts. Do not put private or confidential links in record titles either.
- The shortcode page sets WordPress no-cache signals and REST responses use `private, no-store`. **Exclude the dashboard page and `/wp-json/cafcc/*` (including `?rest_route=/cafcc/…`) from any Hostinger/CDN/LiteSpeed page cache. Never enable caching for logged-in users.** External caches can override application headers, so verify using two test accounts.
- A WordPress nonce is CSRF protection, not a substitute for server permissions. Expired sessions/nonces require reloading the page.
- Deactivation and deletion of plugin files do not erase academic records or progress. Database backups contain student progress; keep them private.

## Development and validation

No build step is required to run the plugin. For contributors with Docker and Python:

```sh
bash tests/run-integration.sh
node --check ca-final-command-center/assets/admin.js
node --check ca-final-command-center/assets/student.js
python3 scripts/build.py
```

Node is used **only for contributor/CI JavaScript syntax checks**, not for building or running anything on Hostinger. PHP syntax checks run inside the disposable WordPress container. Tests create their own isolated MariaDB/WordPress network, publish no host ports, and remove test containers and database volumes afterward. Test fixtures are explicitly marked TEST ONLY and are never included in the plugin ZIP.

See [architecture](docs/ARCHITECTURE.md), [test coverage and staging checklist](docs/TESTING.md), and [release notes](docs/CHANGELOG.md).

## Current limitations and next task

Version 0.1.0 stores question **references**, not full exam papers, answer evaluation or licensed question text. There is no importer/exporter, PDF parsing, subscriptions, payments, student registration, study planner, historical analytics, audit log, automatic source verification or offline dashboard. No import endpoint exists for public users or students. The admin picker is intended for a small reviewed corpus (up to 10,000 records per entity); student results are paginated 20 per page.

**Next development task:** on private staging, curate and verify a small real question-reference set for one chapter, then complete the documented two-student acceptance test before expanding academic content.

License: GPL-2.0-or-later, https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
