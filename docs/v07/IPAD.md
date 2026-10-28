# Version 0.7.0: iPad installation and first practice

Use the protected **staging** site only. This release has not been installed or accepted on your physical iPad. It does not deploy itself.

1. Make a staging **database and files backup**. Keep the installed 0.6.0 ZIP. Avoid student writes during the upgrade/acceptance window.
2. Open this release's successful **Test and build WordPress plugin** Actions run while signed into GitHub. Download **ca-final-command-center-0.7.0**. In Files, unzip the outer artifact; choose the inner **ca-final-command-center.zip**.
3. Staging WordPress → Plugins → Add New → Upload Plugin → choose that inner ZIP → Install → **Replace current with uploaded**. Do not uninstall. Confirm the plugin version is 0.7.0. Its additive migration advances schema 8 → 9 and asset URLs refresh.
4. Existing r016 subjective questions, publication decisions and personal activity remain. No subjective reimport is required. If they were not previously imported, the unchanged r016 Academic ZIP remains compatible.
5. Download the separate private **FR-Jan2026-v0.7.0-MCQ-Academic-Import-r002.zip** from your authorised private review folder. Do **not** unzip it, upload it as a plugin, or put it in Media.
6. CA Final Command Center → **Upload Questions** → choose the MCQ Academic ZIP → **Upload & Preview**. Inspect the four source groups and exceptions. The existing January source-wide physical-permission declaration is reused within its actual scope; no scan is mandatory. Confirm a declaration only if the displayed scope is yours.
7. Choose **Save as Drafts**, or **Publish All** → one batch confirmation. All 55 candidates import as Needs Review. At preparation time, 54 have a single matching printed key; examination Q7 is held because its key lists A and C. No real MCQ was automatically published by this work. Topic suggestions remain provisional.
8. If interrupted, choose **Resume saved work**. Reuploading the identical ZIP resumes its checkpoint. A changed ZIP must use a new package revision. Existing corrections are retained.
9. Question Library → **Question type: MCQ** → current dataset. Search its stable ID to correct a draft. Publish selected eligible revisions after inspection. Subjective and MCQ current datasets stay separate.

Student acceptance, using an entitled test account:

- Explorer → Financial Reporting → type **Ind AS 105** in Topic / Standard; select the counted suggestion. No prior chapter/unit selection is needed. Clear All removes active filters.
- Open a January MTP occurrence. Test Question, Answer and Both in light/dark, portrait/landscape. Confirm table labels and amounts against its source.
- Tap the source badge: it opens the exact owner-public Drive PDF. The verified **PDF page is shown**. Direct Drive page jumping is **not promised**; navigate to that page in the viewer. Printed page numbering may differ.
- Mark Important, save a note, finish three separate timed attempts. Reattempt starts a new session only after the prior one is finished; it hides the answer and keeps history.
- My Practice → Important/Bookmarks/My Notes/Needs Revision/Timed Practice/All Saved. Lists are compact. Open one exact question; close it to return to the same table. Timed history shows first/latest/best/average and difference, without inferring correctness.
- Dashboard → Private Notes and Total Active Practice Time. Counts and links should reconcile with the underlying saved-record/session tables.
- MCQ Practice → January 2026 → RTP/MTP I/MTP II/Examination. Select an option, then **Check Answer**. Feedback includes text/icons as well as green/red. Reattempt preserves scored history. Timed practice uses explicitly labelled practice scoring, not an asserted ICAI marking scheme.
- Sign out and back in; verify persistence. A second account must not see the first account's private data.

Physical iPad Safari, Drive page navigation and Hostinger theme/cache compatibility require your staging acceptance. Test results from Chromium and Linux WebKit are not physical-device results.

Rollback: prefer a forward fix. 0.6.0 refuses schema 9. To revert, restore the matching **pre-upgrade database and plugin files together**; first preserve any activity created since the backup. Never uninstall/delete tables to downgrade. See [architecture and migration](ARCHITECTURE.md).
