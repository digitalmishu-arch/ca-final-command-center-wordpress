# Version 0.8.1 — iPad installation and review

1. In WordPress staging, make a full database/files backup. Do not uninstall the existing plugin. No hosting changes are made by this release.
2. Open the linked GitHub Actions run, sign in to GitHub, and download **ca-final-command-center-0.8.1** under Artifacts. In Files, extract that artifact once. The inner **ca-final-command-center.zip** is the installable plugin.
3. Staging Admin → Plugins → Add New → Upload Plugin → choose the inner plugin ZIP → **Replace current with uploaded**. Confirm version **0.8.1**. Refresh the student portal. Existing IDs/accounts/academic approvals and activity are retained.
4. My Practice → Important: remove one marker with **×**. Confirm its note, bookmark and completed timings remain. **Undo** is offered for ten minutes. A marker is not the academic question.
5. Timed Practice → archive a finished session. Use **Archived** to restore it. Lifetime timed totals and Attempt History deliberately include archived sessions. All Saved hiding affects that table only; notes and timings remain in their own tabs.
6. Attempt History → **Compare**: inspect first/latest/best/average and the individual completed sessions. **Reattempt** opens the question without preloading its answer; start the next session using the existing timer.
7. On Explorer, My Practice or Dashboard, set **Appearance → Modern Light preview** to try the calmer styling. Set **Current** to revert. This is a device/browser preference, does not change the site's default and does not alter Study Planner or ICAI Resources. The separate light/dark toggle remains available.
8. Check portrait, landscape and dark mode on physical iPad Safari: five Explorer filters, smart search, List/One-by-One, answer tables, source links, notes, timer and dashboard drill-downs. Browser automation is not physical-device acceptance.

## Private academic data

The six outer subject bundles are **delivery archives**, not plugins or direct Academic ZIP uploads. Download a subject bundle from the separately supplied private Drive link and **Uncompress** in Files. Read `READ-FIRST.txt`, `processing-summary.json`, `exceptions.json` and `import-order.json`.

Open **Upload Questions** and choose each inner `imports/*.zip` in the listed order. Each child contains its own taxonomy → sources → shared facts → subjective records **or** MCQs. No separate taxonomy approval chain is required. Preview actual counts and preserve reported existing corrections. **Save as Drafts** first. The existing **Publish All** action remains an explicit owner decision; technical integrity, missing MCQ keys and actual permission scope still apply. Answer Pending is not a substituted solution.

The January FR pilot source hashes are excluded from new records; do not remove its existing 55 subjective / 54 eligible MCQs. The larger main Excel workbooks are research overviews. For revision-safe subjective decisions, use the included `decisions/*.xlsx` batches (maximum 150 records), or export current revisions from WordPress after import. Edited/existing records require a fresh WordPress export. MCQ annotations in the research workbook are not automatically applied by the subjective decision importer.

If Preview reports a conflict, retain the existing correction. Do not reset the database or delete earlier records. Use the exact Question ID and source/page in the private exception report to correct a record. Do not publish a materially broken question/table or an MCQ with an unresolved key.

## Rollback

Replace the plugin with the saved v0.8.0 plugin ZIP **without uninstalling**. Leave the three additive saved-list tables intact; original notes and stopwatch rows remain usable by v0.8.0. Full database rollback requires the matching backup and would discard activity created after that backup, so use it only as a deliberate maintenance operation. Never drop tables or reset schema flags on a live site.
