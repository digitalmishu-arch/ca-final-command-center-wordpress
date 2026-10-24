# Version 0.3 validation

Base: tested Version 0.2.0, commit `3aab466a100c5b496a395f730434b81db92ecf1d`. The offline research branch is separate and no PDF extraction is shipped inside this plugin.

- **413 fresh-install/upgrade assertions passed**, including all original tests plus rights, sanitisation, revision, notebook, search, answer privacy and schema-3 retention checks.
- **417 prototype-compatibility assertions passed**; incompatible prototype questions/private notes/progress are retained. Total across the two local scenarios: 830 assertions.
- PHP syntax checks pass for every plugin/test PHP file. All five JavaScript files pass syntax checks.
- Existing Chromium smoke checks pass: actual login, connected dependent navigation, original CSV preview/commit UI, official answer links, hidden draft text, progress reload and responsive widths.
- New real Chromium practice checks pass: published authored text/table/MathML, zero initial answer requests, keyboard-triggered Show Answer, clearing on collapse, bookmark/note/status persistence, two independently signed-in students, bookmark filtering, reduced motion, no horizontal overflow at 375/390/768/1024/1440 pixels, and the native WordPress content editor's draft-save/separate-rights-approval cycle.
- The installable ZIP has one top-level `ca-final-command-center/` folder, the main plugin entry and 27 plugin files. No tests, synthetic sample records, PDFs, private research output or credentials are packaged.

Tests use disposable WordPress 6.8.3, PHP 8.2.29 and MariaDB 11.4. No Hostinger connection or production/staging write occurs. Authored preview fixtures are created only under an explicit local test flag in database `cafcc_test`; plugin activation never seeds them.

Rights tests cover unpublished/expired content, reference-only source-text rejection, missing confirmation/stale revisions, student/editor/anonymous writes, encoded Drive links, script/event removal, question-option answer-key rejection and preservation of old approvals as history. Initial question/search responses never contain answer-only text. A revoked/expired permission is checked again on subsequent server reads; text already delivered to a browser cannot be remotely erased.

Migration tests compare all original/connected academic rows and IDs, new notebook/content/history rows and student/admin account fields before/after schema-2 upgrade, retry and reactivation. Student A/B note, bookmark and progress changes remain separate. Deleting a reference with new practice relationships is blocked by the old API too.

The [iPad guide](PRACTICE-0.3.md) describes the exact staging installation and review steps. The [migration report](MIGRATION-0.3.md) documents schema and rollback limitations. Hostinger, actual iPad Safari, third-party themes/caches, large-corpus performance and backup restoration remain untested. No automatic merge/deployment/publication is configured.
