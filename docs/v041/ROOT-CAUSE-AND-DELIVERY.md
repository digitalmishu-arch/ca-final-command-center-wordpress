# Version 0.4.1 root causes and delivery

Base: unmerged PR #9, commit `93abdced4481d2dd04f294e2b85c8a609c6cd2dc`. No Hostinger or staging access was used. Zero Studio rows on staging is the owner's observation, not a database inspection by this task.

## Why the installation was empty

1. The plugin ZIP contains code and draft taxonomy, not private research output. `CAFCC_Bank_DB::migrate()` creates tables and append-only taxonomy seeds; it does not read the offline `work/` directory. `research/bridge.py::export()` writes private transport files. Only `CAFCC_Studio::import_preview()` followed by `import_apply()` creates research review rows. Installing v0.4 therefore cannot make the 139 offline candidates appear in Studio. They were never imported automatically.
2. At PR #9, `class-cafcc-facets.php::node_search()` applied an `EXISTS` eligible-question condition to every heading. A reviewed syllabus with no published questions looked empty. v0.4.1 separates `scope=browse` (reviewed paths, explicit availability flag) and `scope=practice` (eligible questions). Unreviewed/editorial drafts and paths with unpublished ancestors remain hidden. No publication gate was relaxed. Availability uses a materialized derived query rather than a repeated correlated node lookup, and is tested with 10,000 synthetic occurrences.
3. `class-cafcc-portal.php::render()` sent explorer/dashboard/practice to `CAFCC_Academic_UI::student()` identically. Dashboard now renders its own saved-activity summary with no question-list request. My Practice uses current-user saved/bookmark/revision queries, a separate heading/view and no academic browse sidebar. Explorer retains independent concepts, source and attempt filters.
4. v0.4 set select foreground through `--cc-navy`, but did not explicitly set WebKit text fill, option/optgroup colours or colour-scheme. A theme or native Safari rendering could override the visible result. The exact staging CSS cascade was not inspected. New portal-scoped rules set foreground/background/text-fill for normal/selected/disabled inputs, native options and autocomplete, with explicit light/dark variables and accessible contrast tests under a hostile theme rule. WordPress Admin is not globally recoloured.
5. Source links were placed below the question as generic Open Official Question Source links. Each eligible occurrence now receives a prominent citation generated from its actual approved source type, subject, attempt, series/question/subpart and reviewed standard/chapter. The official HTTPS ICAI URL remains occurrence-specific. Authored demonstrations are labelled independently authored and their ICAI link is background only.

## Five separate stages of data

- **PDF research output:** private extraction candidates, source hashes, coordinates, shared scenario context, proposed tags and exceptions. No WordPress write.
- **Private review package:** workbook/JSON/evidence delivered for owner inspection. Downloading it changes no database or approval.
- **WordPress research-draft import:** administrator uploads a JSON batch, validates duplicates/conflicts, then explicitly applies it. Review rows now exist, as Draft/Needs Review. Stable research IDs survive; portable packets do not assume WordPress numeric IDs.
- **Academic approval:** the CA reviewer checks source identity, boundaries/number, historical classification, exact answer, rights and question/answer revisions separately. Tests and AI confidence do not grant academic approval.
- **Student-visible occurrence:** final Publish When Eligible, eligible source/edition/taxonomy/content revisions and the student's current entitlement must all pass. Answers remain a separate deliberate request. Installing a ZIP, downloading Excel or importing drafts is insufficient.

## New administrator help

CA Final Command Center → Getting started reports local counts, current next action and the latest 20 review blockers, without source prose, private notes or credentials. It is administrator-only and read-only. Each Studio detail panel shows the next required approval/action. Checkmarks are shown only for approvals whose fingerprints still match the current revision; controls are locked while a review save/decision is in progress so a second tap cannot race a stale revision. Use proposed draft path resolves supplied historical edition/node keys against this database, saves a draft only and never approves a mapping. Missing nodes lead to an explicit import/review instruction. Original AI evidence and previous owner corrections remain immutable.

The guide covers Connected Academic Manager, draft Topic Proposals, research JSON, corrected tags, separate approvals, server-issued Excel decisions, Practice Content & Rights and student visibility. Existing grants, accounts, IDs, notes/bookmarks/progress and approved records are retained. No schema-version bump or destructive migration is needed: database schema stays 4, plugin becomes 0.4.1. There are no new automatic academic approvals or membership grants.

## Real-data pilot and limits

The private pilot selects FR January 2026 MCQ Q6–Q9 and descriptive Q14 from the same previously authorised 27-page PDF, SHA-256 `8bdb55ac0ffd3f01a96c5caac07326d4529d30acf8963094828a348e9b22c737`. The recorded official PDF is `https://resource.cdn.icai.org/88979bos-aps2822-p1.pdf`; the applicable historical FR chapter is Chapter 9, Ind AS 115, in `fr-may2025-jan2026`. No ICAI-numbered unit is invented for that chapter. Source identification, header attempt and bytes were checked; detailed topics, scheme applicability, exact answers and final approval remain for the owner.

Question pages are 3, 3, 4, 4 and 7; answer-marker candidates are 13, 13, 13, 13 and 20. MCQ shared-scenario coordinates are retained. The four editorial topic proposals are Period-specific revenue recognition; Contract modifications; Remaining consideration after contract modification; Consideration payable to a customer. These are proposals from the corrected sidecar, not official ICAI headings or newly approved classifications. The existing owner Ind AS 115 concept instructions are retained, without turning them into full academic approval. FR Answer 19 and all AFM conflicts are excluded.

The downloadable JSON is compatible with v0.4's existing importer and carries no question/answer prose, approvals, public flags or numeric taxonomy IDs. The accompanying hierarchy CSV is draft-only. The pilot is private and is never committed or processed on public CI.

A disposable WordPress test imported all five as drafts. A clearly labelled **workflow simulation** applied test-only review decisions to Q6 and verified its student citation and official answer reference in a browser. These are not owner academic decisions, are not included in the import packet and did not reach staging. A separate unmodified v0.4.0 installation also imported all five as drafts. The authored formatted practice/solution demonstration remains separate from the real ICAI reference.

## Validation and outstanding acceptance

Fresh/prototype WordPress integration suites, all retained privacy/entitlement/migration tests, 10,000-record pagination, research regressions, Chromium browser workflows, original formatted Show Answer, two-student notes/bookmarks/status and the new syllabus/portal tests are run. CI also runs the new browser checks in WebKit on Linux. WebKit engine testing is not physical Apple Safari/iPad acceptance. Local WebKit download was blocked by environment network policy; no bypass was attempted. Actual staging CSS/native dropdown popup behaviour, hosting mail and the owner's academic review remain manual acceptance steps.

No Hostinger access, deployment, PR merge, DNS change, real membership grant or third-party full-text publication occurred. The actual staging installation remains unchanged until the owner installs/imports/reviews deliberately.
