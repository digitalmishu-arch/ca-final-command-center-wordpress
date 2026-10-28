# v0.8 implementation and acceptance matrix

This release changes application software. It does not ingest new source PDFs, approve academic content or modify Hostinger.

| Area | Implementation | Acceptance / limits |
| --- | --- | --- |
| Private Notes | Lazy reads, safe JSON handling, bounded transport, owned compare-and-swap saves/replay and diagnostics | Disposable server/browser failure injection; actual hosting outage cause unconfirmed; physical Safari acceptance required |
| Shared design/navigation | Compact light/dark portal, grouped existing URLs, native 16px controls, accessible touch targets, reduced motion | Browser tablet portrait/landscape and phone; no physical-device claim |
| Explorer | Five filters + one debounced server search; zero-question sourced headings; metadata list and one reader; original numbering; on-demand answers | Existing rights/entitlements/source links retained; bounded pages |
| Reader | Compact Start/Pause/Resume + Finish, star/bookmark, collapsed notes/tags/history/modes; existing highlight and progress storage | No academic content changes |
| Dashboard/My Practice | Course/subject cards, actual timed/recorded activity, compact charts, preserved clickable drill-downs and saved-question tables | Planner self-report kept separate from stopwatch and scored MCQ activity |
| Planner: My Exam Plan | Three-step course/group/attempt/date/weekday/target wizard; edits, archives, active-plan selection, daily tasks/logs, due queue, local-date countdown | No official timetable is indexed; exact dates are personal milestones or explicitly month-end targets |
| Planner: Syllabus | Course/group paper snapshots, sourced existing Final templates or labelled custom chapters/units/topics, status/difficulty/priority/dates/hours; selectable first-study/revision/mock coverage | Intermediate/Foundation chapter templates are not populated or invented |
| Planner: Revisions | Revision 1/2/3/custom, dates, postponements, time/notes/difficulty, next target, audit history | No silent overwrite of question practice status |
| Planner: Mocks | Mock 1/2/custom, subject/group, own or indexed MTP; dates/duration/marks/mistakes/retest/action; owned completed in-app MCQ score import | Self-reported scores explicitly separated from recorded practice points; no score without data |
| Planner: Insights | Actual chapter coverage donut, revision bars, recorded-hour bars, score trend/table, daily/weekly targets, countdown | Coverage is not certified readiness/mastery; chart shows latest 100 scores, totals include all plan mocks |
| ICAI Resources | Course-specific six/six/four grid, actual attempt/series links, responsive subject view, verified PDF-only source cells, separate directories | Missing authoritative PDFs remain Not indexed; no third-party mirrors or invented links; new scheme names from existing official course references |
| MCQ | One-question reader, four filters, delayed key/check feedback, navigation/counter; timed response/save/resume/submit retained; active-test key guard | Existing eligible records remain; ambiguous Exam Q7 held; practice scoring is not an official marking claim |
| Community/Back to Top | One fixed accessible control; configurable slow/dismissible/date-bound WhatsApp strip | Banner intentionally hidden until owner supplies a real destination |
| Publication/security | Existing one-package import/batch publication preserved, schema 10 additive only, revision/ownership/nonce/entitlement checks | No deploy, merge, entitlement grants, new academic approvals or source-sharing changes |

## Intentionally unavailable

* New authoritative Intermediate/Foundation chapter templates and unindexed resource PDFs need source data/administrator indexing; custom planning works meanwhile.
* Official ICAI timetable prefilling is unavailable until an exact verified timetable is indexed. The personal-date/month-end choices work now.
* Mass ingestion, historical multi-year trend claims, AI explanations without a configured real provider, and payments are outside this release. Existing navigation keeps honest limited/coming-soon states.
* No physical iPad or Hostinger acceptance is claimed. All production/staging data remains untouched.

## Regression strategy

All previous backend/security/migration/publication assertions remain in the integration runner. Legacy owner Studio, rights, Excel, registration/access and ZIP publication browser paths remain tested. The v0.8 student browser suite replaces obsolete sidebar/multi-expanded-card selectors with equivalent preserved-function checks plus planner/resources coverage. Historical test files remain available for maintenance of their respective older versions.

See the release PR/Actions run for exact final test counts and browser artifacts. Screenshots generated in public CI use independently authored fixtures only. They are not owner academic approvals or newly extracted ICAI content.
