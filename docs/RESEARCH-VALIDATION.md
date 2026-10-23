# Research validation — 23 October 2026

The research branch starts at tested V0.2.0 commit `3aab466a100c5b496a395f730434b81db92ecf1d`. No file in the installable plugin directory changed. There is no schema migration, data remapping, live-site import or student-record modification.

## Checks completed locally

| Check | Result |
| --- | --- |
| Python research unit tests | 19 tests passed |
| Private six-file extraction | 6 PDFs, 183 pages, 113 numbered questions; 121 occurrence rows, including separately checked AFM Roman subparts |
| CSV preflight | 6 documents + 121 occurrences + 120 official answer-link references; exact existing headers/order, limits and relationships passed |
| Real WordPress with actual private CSV bytes | 383 integration assertions passed; all 247 importer rows passed preview/commit in a disposable database |
| Original-prototype compatibility scenario | 357 integration assertions passed; synthetic research import also covered |
| PHP/Python syntax | Passed |
| Private Chromium review screen | 121 references, source hash match/mismatch, question/answer page navigation, decision download, phone width and no JavaScript errors passed |
| Installable WordPress ZIP | Same 24 files and SHA-256 as tested V0.2.0: `1fbf167f545ef26556de04f369296acb83bc18340e582388376ca228f269006a` |
| Source duplicate checks | Six distinct private PDF SHA-256 hashes; no duplicate byte/source identity accepted |
| Occurrence duplicate checks | No duplicate source/edition/page/Q/subquestion location accepted; real importer also rejects retries |

Fresh/private WordPress and prototype tests use WordPress 6.8.3, PHP 8.2.29 and MariaDB 11.4 in disposable containers. The private test snapshots existing question rows and every field of student progress, imports drafts, withdraws batches and verifies retention. Containers and test database volumes are then removed. No persistent site credentials are configured.

Research tests cover permission-independent offline safety and the existing importer covers server-side administrator access, nonce enforcement, student isolation, unpublished data visibility and rollback. No research code is installed into WordPress or exposed as a new REST endpoint.

Actual PDF text and metadata packages are not submitted to public CI. GitHub Actions runs the 19 synthetic research tests and both existing WordPress scenarios. The normal V0.2 build workflow still packages only the plugin directory.

## Evidence limits

All records remain Draft/Needs Review and zero questions have human CA approval. Six representative question pages received visual extraction spot checks. This is not an exhaustive line-by-line audit. Marks were not inferred. Historical taxonomy mappings remain blank. AFM Q3/Q4 answer-page candidates remain ambiguous. FR Answer 19 is withheld because the archive predates an official correction. See [the pipeline guide](RESEARCH-PIPELINE.md) and private sidecar for review limitations and iPad instructions.

The package's CSV hashes match the files used in the successful private WordPress run. Research-only sidecar suggestions do not change those importer bytes. No exact-repeat or globally-new assessment was attempted.
