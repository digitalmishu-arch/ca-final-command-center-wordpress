# Version 0.5.1 January 2026 FR review candidate

Continues PR #11. Adds a source-specific layout/table renderer, protected manual-comparison gate, common facts and alternatives, a full student reader with server-timed sessions, private tags/highlights, actual personal dashboard activity and resumable owner bulk review. Real academic records remain Needs Review.

**Academic acceptance is incomplete:** the RTP is available; January 2026 MTP I/II and examination/suggested-answer raw originals and owner decisions are still required. No other attempt is substituted. Public code/CI contains no copied PDF prose or private research files.

[iPad install/review](docs/v051/IPAD-INSTALL-AND-REVIEW.md) · [feature/source coverage matrix](docs/v051/RELEASE-AND-FEATURE-MATRIX.md) · [migration/rollback](docs/v051/MIGRATION-AND-ROLLBACK.md).

# Version 0.5 — Financial Reporting subjective review release candidate

Continues PR #10 / V0.4.1. [iPad installation and review](docs/v05/IPAD-INSTALL-AND-REVIEW.md), [migration and architecture](docs/v05/MIGRATION-AND-ARCHITECTURE.md), and [actual coverage / unfinished work](docs/v05/COVERAGE-AND-UNFINISHED.md).

Adds subjective-only server gates, source-wide private ICAI permissions, complete authorised rich draft imports, one owner Publish transaction, Needs Review / Publish / Reject, a simple revision-safe Excel workflow and official numbered contents hierarchy imports. Existing login, entitlements, progress, private notes/bookmarks, Dashboard/My Practice and light/dark mode remain.

All **79 catalogued FR PDFs (1,776 pages)** were processed privately into provisional extraction candidates. The separate private delivery contains the actual data, workbooks, small import batches and exceptions. **No real academic approvals or automatic publications were made. The complete verified FR archive is not finished**: additional official files, exact URLs/revisions, historical taxonomy, transcription fidelity, answer matches and owner decisions remain open. The reported lifetime permission has no invented expiry; its actual written scope must be confirmed privately. No source prose is in this repository, plugin ZIP or public CI.

The retained sections below document earlier versions; the V0.5 guidance takes precedence.

# Version 0.4.1 — First Question Pilot fix

Continues unmerged v0.4 PR #9. Start with [root causes and delivery](docs/v041/ROOT-CAUSE-AND-DELIVERY.md) and the [iPad first-pilot instructions](docs/v041/IPAD-FIRST-PILOT.md). New administrator Getting started diagnostics explain the research/import/review/publication separation and next blockers. Browse Syllabus includes reviewed empty paths; Practice Questions remains publication-gated. Dashboard and My Practice now have distinct purposes. A portal-only persistent light/dark control and explicit Safari form colours are included. No schema bump, automatic publication, membership grant or Hostinger deployment.

The private five-reference FR JSON is delivered separately, never bundled in public code/CI. Import it as drafts; your academic approval remains mandatory. CI uses original synthetic question/solution fixtures only. Chromium/WebKit engine testing is distinct from actual iPad Safari and staging acceptance.

# CA Final Command Center — Version 0.4.0

WordPress/PHP/MySQL question-bank foundation, continuing v0.3 PR #5 and integrating the corrected offline research engine from PR #4/#8. No deployment, live payment or automatic academic publication.

Read [the original v0.3 gap analysis](docs/v04/GAP-ANALYSIS.md), [iPad installation and owner review](docs/v04/IPAD-INSTALL-AND-REVIEW.md), [migration report](docs/v04/MIGRATION-REPORT.md), [Review Studio / Excel guide](docs/v04/REVIEW-STUDIO.md), [architecture and unfinished work](docs/v04/ARCHITECTURE.md), and [actual research coverage](docs/RESEARCH-V04.md).

Independent academic/source/attempt search, occurrence-specific audited approvals, private Excel round trip, rights-controlled full text and deliberate Show Answer, WordPress email verification/manual access, real source directory and navigation are implemented. Real corpus approval is unfinished: only six previously authorised PDFs were processed into 139 draft parent/subpart candidates; the other 417 catalogue files await private extraction/storage rights confirmation. The ZIP contains no real exam prose or approved questions.

The test suite uses authored synthetic content only. `bash tests/run-integration.sh`, `CAFCC_TEST_LEGACY=1 bash tests/run-integration.sh`, `bash tests/run-browser.sh`, and `python3 -m unittest discover -s tests -p 'test_*.py'` exercise the release in disposable environments. `python3 scripts/build.py` creates the installable code-only ZIP. Hostinger needs no Node/Python runtime.

The following retained documentation describes earlier foundations; v0.4 access/review gates supersede any earlier publication assumptions.

# CA Final Command Center — WordPress plugin 0.3.0

Version 0.3 adds rights-reviewed full-text practice, deliberately fetched answers, private student notes/bookmarks and a colourful responsive interface on the tested V0.2 foundation. [Exact iPad staging instructions and content-rights workflow](docs/PRACTICE-0.3.md), [migration report](docs/MIGRATION-0.3.md), and [validation](docs/VALIDATION-0.3.md). The offline research accuracy fixes are a separate pull request. No research text is copied into WordPress and no questions are seeded by this ZIP.

A connected CA Final syllabus and verified-question explorer for WordPress/PHP/MySQL, with vanilla JavaScript and CSS. No Node.js, separate application server, Supabase, payment service or external API is required on Hostinger.

The Version 0.2 foundation is based on the complete **Version 0.1.0 implementation in PR #1**, not the older `main` prototype. Version 0.3 development branch: `feat/v0.3.0-permitted-practice`, based on `feat/v0.2.0-connected-explorer`. The practice pull request targets the tested V0.2 branch so it can be reviewed independently from the research fixes. Neither PR is automatically merged or deployed.

## What connects to what

**Subject → Syllabus edition → Chapter → ICAI unit → Topic → Subtopic → Matching questions.** Each selector obtains its options from the database and the selected parent path. The server rejects inconsistent combinations. Chapters without separately listed units do not receive invented unit headings. Modules are represented in the hierarchy and admin manager; the student chapter selector spans their chapters.

Questions retain stable IDs and can have several topic/subtopic tags, several official source occurrences, and a question-family association. IBS cases can carry several subject and topic tags. Progress remains keyed to the existing WordPress user and question IDs, not to individual appearances.

Included:

- Versioned additive schema-3 installation and migrations; schema-1/schema-2 and prototype data retained.
- Six subjects and a sourced starter catalogue with **6 editions, 180 hierarchy records: 17 module/resource groups, 112 chapter/navigation entries, 45 units, 2 editorial topics and 4 editorial subtopics**.
- Dependent student filters, exam-attempt/source filters, search, source cards, pagination, four practice states and reviewed answer panels.
- Administrator taxonomy/resource editor, ordering, historical edition mappings, approval/publication, families/comparisons and non-destructive unpublishing.
- Five CSV templates, validation/preview, duplicate checks, owner-bound commit tokens, append-only transactional imports and safe batch withdrawal.
- PHP/database/REST tests, real browser smoke tests, iPad/phone viewport previews and GitHub Actions ZIP packaging.

**No real exam questions, marks, repeat percentages or solutions are seeded.** Research imports and the bundled hierarchy begin as Draft/Needs Review. Only reviewed published references appear to students.

## Source catalogue: scope and provenance

The baseline is ICAI's **May 2026 study-material listings**, as requested. This is not a claim that these editions remain applicable to every later examination. Edition dates, reprint dates, exam applicability and retrieval date are separate fields. Historical editions have separate IDs; mappings do not merge their questions or progress.

The catalogue contains 173 exact official module/chapter/unit/resource labels and 7 explicitly editorial navigation/topic/subtopic entries. It does not claim complete fine-grained topic coverage across all six subjects. Most detailed topics/subtopics must be curated and reviewed through the manager or CSV import. IBS's official page lists case resources rather than a numbered chapter/unit syllabus; the cross-subject chapter grouping is editorial.

See [source register and limitations](docs/SOURCES.md). For example, [ICAI's FR listing](https://www.icai.org/post/sm-final-p1-may2026) places Accounting and Reporting of Financial Instruments at Chapter 11 and Derivatives and Embedded Derivatives at Unit 4. Finer navigation tags under that unit are labelled Editorial, not ICAI headings.

## Precise iPad staging installation/update

This repository does not access or modify `demo.cadeepanshuagarwal.in`. Perform these steps yourself only on that protected staging installation.

1. In Hostinger, confirm the target is **staging**, make a current **database and files backup**, and record the restore option. Confirm staging access protection. Search-engine discouragement alone is not privacy.
2. In Safari, open the successful Version 0.3 GitHub Actions run. Under **Artifacts**, download **`ca-final-command-center-0.3.0`**. GitHub sign-in may be required.
3. In Files → Downloads, tap the downloaded **outer artifact ZIP** to extract it. Inside is **`ca-final-command-center.zip`**. Keep that **inner ZIP compressed**. Do not upload GitHub's Code → Download ZIP source archive.
4. Sign in to the staging site's WordPress Admin as Administrator. Open **Plugins → Add New Plugin → Upload Plugin → Choose File → Browse**, select the inner `ca-final-command-center.zip`, then tap **Install Now**.
5. Because Version 0.1 or 0.2 is already installed, WordPress should show the existing plugin and offer **Replace current with uploaded**. Check the new version is **0.3.0**. Replace the plugin and activate it if WordPress leaves it inactive. Do not delete database tables or change the schema-version option.
6. Open **CA Final Command Center → Connected academic manager**. Existing Version 0.1 records remain available through the original main menu. The new manager should contain the six researched editions and 180 draft hierarchy records on a clean upgrade.
7. Review the source URLs, dates and applicability. Under **Review bundled ICAI hierarchy**, choose an edition, confirm you checked the source and publish its official headings. **Editorial nodes remain drafts** and need individual review in the taxonomy editor. The IBS editorial case chapter is approved separately.
8. Existing shortcode pages continue working: `[ca_final_command_center]` and `[cafcc_dashboard]` are both supported. If creating a test page, do so only within protected staging. WordPress Private pages are not readable by ordinary Subscribers; use hosting-level staging protection when testing Subscriber access.
9. Exclude the dashboard and both `/wp-json/cafcc/v1/*` and `/wp-json/cafcc/v2/*` (including the `?rest_route=` equivalents) from Hostinger/CDN/LiteSpeed caches. Keep logged-in page caching disabled. Test using two separate Subscriber sessions.
10. Verify the dependent filters, first reviewed source/occurrence, answer access and separate progress before expanding content. See [staging acceptance checklist](docs/TESTING.md).

The plugin ZIP has one top-level `ca-final-command-center/` folder containing the main PHP entry file, includes, assets, sourced catalogue and blank CSV templates. No test fixtures, screenshots or development tools are installed on Hostinger. GitHub artifacts expire after 30 days; another successful build produces a new artifact.

## Add academic records in the manager

Recommended order:

1. Review/create an edition with truthful applicability, source URL and edition/reprint month (`YYYY-MM`; leave unknown dates blank with a note).
2. Create module/chapter/unit/topic/subtopic nodes in parent-first order. Parent, edition and subject must agree. Use **Official** only for an exact cited heading; use **Editorial** for your finer taxonomy. Position controls ordering. Publish the reviewed edition and parent before publishing a child.
3. Add a source document with a stable key, edition, official title/URL, source type, attempt/context, issue period and MTP series when applicable. Verify and publish only after inspecting it.
4. Add a stable question record, its primary source/subject/edition and optional primary chapter. Record short reference titles, not unlicensed question text. Add a separate **occurrence** for every appearance, with its document, page, question/subquestion number and verified marks where available.
5. Add as many **question-topic mappings** as needed, including subtopics. IBS cases may additionally have several subject mappings and tags from relevant subject editions. Normal questions cannot silently cross editions/subjects.
6. Add answers using either **Official Link** (URL and location, no copied text) or **Authored / Licensed** (solution text and clear authorship/reproduction-rights basis). Only verified published answers reach students. Rights evidence remains private to administrators; a link being publicly readable does not establish reproduction permission.
7. Use Draft/Rejected to withdraw incorrect material. Records with connected data cannot be deleted through the old editor. Source URLs with recorded appearances are not silently reassigned: add a corrected source/occurrence and unpublish the incorrect one.

Families/comparisons are preparation for future human-reviewed repetition analysis. No percentage, automated equivalence or exam-frequency claim is calculated in this version.

### Existing Version 0.1 records

Migration does not guess their editions or tags. They remain accessible with their existing progress as unclassified Version 0.1 references when no connected filters are selected.

To connect one deliberately: add source metadata using its **existing Document ID**, then question metadata using its **existing Question ID** and the same primary document. The initial connection adds metadata without rewriting the old rows. Review the source, add verified occurrences and classification mappings, then publish. Connecting draft source metadata temporarily withdraws its questions until the source is reviewed, so do this deliberately on staging.

The older `main` prototype's `cafcc_questions` / `cafcc_progress` tables, including notes, remain untouched and separate. No automatic conversion from that prototype is attempted.

## CSV import

Download templates inside the manager or use [the five bundled templates](ca-final-command-center/templates). Keep their exact column order. UTF-8 CSV, comma-delimited, maximum **200 rows / 512 KB** per batch.

- **Hierarchy:** editions/subject codes must already exist; use stable `node_key` / `parent_key` values, parent rows before children.
- **Documents:** reference the edition key and supply the actual official source metadata.
- **Occurrences:** reference document/edition keys. An unknown question key creates a new draft stable question using the supplied reference title. Existing question keys reuse that identity. Every appearance must have a unique location. Question/edition/source mismatches fail validation.
- **Question-topic mappings:** use question and node keys; several rows can classify one question.
- **Answer references:** use question and optional occurrence keys. Official-link rows must leave answer text empty; authored/licensed rows require a rights basis.

Choose the file → **Validate & preview** → inspect the preview → **Import validated draft batch**. Preview validates relations and duplicates inside a transaction that is rolled back; no academic rows remain, though auto-increment ID gaps are normal. Commit revalidates and uses a lock; retrying the same token cannot duplicate a batch. Imports never approve themselves or overwrite existing stable keys.

**Withdraw batch safely** removes it from student access while retaining every row and all progress. It also hides dependent resources where their source/edition/path is withdrawn. It is not a delete or a reversal of unrelated later administrator edits. Withdrawn records cannot be accidentally republished; use a corrected new batch. Preview tokens expire in one hour and belong to the administrator who created them. Safe imports require InnoDB; the plugin will not convert table engines automatically.

## Security and deployment boundary

Server-side administrator role **and** capability checks protect all master mutations and imports. Every plugin REST request requires a signed-in user, `read` capability and a valid WordPress REST nonce. Students cannot choose the owner of progress writes. All three REST namespaces honor withdrawn source/question batches and send private/no-store headers. SQL values use prepared operations; text/enum/relationship validation and DOM text metadata and allowlisted rich content prevent injection.

Only direct HTTPS ICAI-host resource URLs are accepted, without credentials, query strings, fragments or custom ports. Google Drive URLs are rejected as sources/answers. No private files, credentials or unpublished answer text are exported to student endpoints. The plugin makes no external content-fetching requests.

Deactivation retains all data. Restoring old plugin files alone is not a validated database downgrade: restore the matching **database and files backup** if you need to return to an earlier release. See [schema-3 migration report](docs/MIGRATION-0.3.md).

## Requirements, tests and previews

WordPress 6.6+, PHP 8.1+, InnoDB MySQL/MariaDB. Tested on WordPress 6.8.3, PHP 8.2.29, MariaDB 11.4. Network-wide activation remains unsupported; activate per site.

```sh
bash tests/run-integration.sh
CAFCC_TEST_LEGACY=1 bash tests/run-integration.sh
node --check ca-final-command-center/assets/explorer.js
node --check ca-final-command-center/assets/manager.js
python3 scripts/build.py
```

Node/Python/Docker are contributor/CI tools only; none is required on Hostinger. Optional local browser tests use Python Playwright and Chromium: run `CAFCC_PREVIEW=1 bash tests/run-integration.sh`, then `python3 tests/browser-smoke.py`. The optional preview binds only to loopback port 8092; remove its disposable containers/network afterward using the names in `work/preview-containers.txt`.

See [validation results](docs/VALIDATION.md), [architecture](docs/ARCHITECTURE.md), [iPad-width preview](docs/previews/ipad-explorer.png), [phone-width preview](docs/previews/phone-explorer.png). Screenshots show real local WordPress/database behavior, including honest empty question states. They are Chromium viewport previews, not a claim of testing on actual iPad Safari or Hostinger.

## Remaining work

The sourced starter catalogue does not provide exhaustive detailed topics/subtopics, newer 2027 tax editions or attempt-specific statutory updates. Those need source review and separate editions/imports. There is no mass PDF ingestion, licensed-content acquisition, AI question generation, automatic answer/rights verification, complex analytics, subscriptions or payments. User privacy export/erasure, a full administrator audit log and broad theme/cache compatibility remain future work. The admin picker is intended for up to 10,000 records per collection; larger corpora need server-side picker search.

License: GPL-2.0-or-later.
