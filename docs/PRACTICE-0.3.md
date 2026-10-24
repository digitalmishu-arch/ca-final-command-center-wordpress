# Version 0.3.0 — iPad staging and permitted-content guide

This is a WordPress/PHP/MySQL plugin upgrade, with vanilla JavaScript/CSS. No Node.js, Supabase, extra WordPress plugin, payment connection or new hosting service is required. The connected hierarchy, academic review manager, CSV templates/importer and existing question IDs remain the foundation. The research corrections are reviewed separately.

## What is ready

Reviewed original/licensed question text appears directly on matching question cards. Text is selectable and searchable. Tables, calculations, superscripts/subscripts, native MathML and optional MCQ choices are supported. The question is open first; the answer is closed and absent from initial responses. Tapping **Show Answer** fetches the reviewed solution/official reference; closing clears it, and reopening makes a fresh authorised request. No automatic grading or invented examination marks are included.

Students retain their existing practice statuses and can save their own bookmarks/private notes. The bookmark filter is personal. The mobile layout includes quick access to filters; wider screens keep filters accessible. Navy, teal and purple are complemented by distinct subject accents. Keyboard controls, real touch targets and reduced-motion settings are supported. Progress summaries come from stored student records, including honest empty states.

Authored demo previews: [iPad question](previews/v03-ipad-practice.png), [iPad answer](previews/v03-ipad-answer.png), [phone](previews/v03-phone-practice.png). All pictured questions/solutions are independently authored synthetic fixtures in a disposable local site, clearly labelled. Counts reflect that actual test database. These fixtures are **not installed or seeded by the plugin ZIP** and do not claim to be ICAI examination material.

## Download and install on private staging — only when you choose to test

1. Open the practice PR's successful **Test and build WordPress plugin** Actions run. Tap the artifact **ca-final-command-center-0.3.0**. GitHub may require sign-in.
2. Save the artifact ZIP to iPad **Files**. Tap it once to extract the outer artifact archive. Inside is **ca-final-command-center.zip**, the installable plugin. Keep that inner ZIP intact.
3. Confirm you are in your private staging WordPress Admin, not production. Take a staging database/files backup using your existing hosting/backup tools. This task has not accessed Hostinger or tested its backup restore.
4. Go to **Plugins → Add New Plugin → Upload Plugin → Choose File** and select the inner plugin ZIP. Tap **Install Now → Replace current with uploaded**, then activate if needed. Do not install a second copy with a different folder name.
5. Check the plugin reports **0.3.0**. Existing data is retained; three new tables are added by schema 3. Clear any staging page cache. The dashboard shortcode remains **[ca_final_command_center]**; no page is automatically created or published.
6. Sign in with two staging student test accounts. Confirm the existing syllabus path/progress is available, question/answer permissions work, and each account sees only its own notes/bookmarks. Do not publish actual research data as part of this technology check.

For rollback, restore the matching database **and** plugin-file backup. Uploading the older V0.2 ZIP alone is not a schema downgrade. See [the migration report](MIGRATION-0.3.md).

## Add your independently authored or licensed practice text

1. In **CA Final Command Center → Connected academic manager**, create/review the normal question reference, source occurrence and appropriate edition-specific tags. Copy its existing question ID. Existing CSV imports still enter as drafts.
2. Open **Practice content & rights → New content**. Enter that question ID and choose **Question**. Leave **Reference only** when reproduction permission is absent; do not paste ICAI source prose.
3. For your own question, choose **Independently authored by us**, provide author credit and an authorship note. For licensed material, record the licence, permitted website reproduction scope and expiry. A downloaded PDF is not permission. Rights evidence is private admin metadata, not a public contract link.
4. Use the built-in WordPress editor to write/format text. **Insert table template** and **Insert calculation** provide editable structures. Native MathML can be entered in the editor's Text tab. Unsupported markup is stripped on save; inspect the saved preview. For choices, enter one per line, for example `A | First choice`. Do not put correct-answer flags in question choices.
5. Tap **Save as Draft / Needs Review**. Inspect the saved revision and source rights. Only then tick the rights confirmation and tap **Approve this revision**. The academic question itself must also be verified/published before students see its content.
6. Create a separate **Answer / solution** record for the same question ID, with its own author, rights evidence and answer location. Save/review/approve it separately. Students receive that payload only after tapping Show Answer.

Any later edit immediately withdraws that content's approval until the new revision is reviewed. To withdraw text without deleting student work, save it as a draft. Source/question unpublication also hides content while retaining all notes/bookmarks/progress. Review history is retained and available through the administrator-only history API.

Without reproduction rights, the card keeps your original reference/topic metadata and official ICAI link; it does not display extracted source text. Private PDFs and the offline corrections ledger remain outside WordPress. No workflow automatically copies research text into practice content.

## Practical limits

Actual iPad Safari, the Hostinger staging theme/cache configuration and backup restoration still need manual staging checks. Browser tests used real Chromium at phone/iPad/desktop widths, not Safari. Large-corpus load testing, automated semantic grading, OCR, mass import, subscriptions and payments are outside this release. The default UI does not contain fake students, performance percentages or demonstration data.
