# v0.7 architecture, data boundaries and migration

The working 0.6 owner publication policy remains. No individual taxonomy approval chain is restored. The JSON-only checksummed Academic ZIP gains an optional `mcqs` item kind; existing r016 bytes and subjective item behavior remain compatible. Mixed subjective/MCQ ZIPs are rejected to keep exact dataset selection unambiguous.

| Component | Responsibility |
| --- | --- |
| `class-cafcc-library.php`, `library.js/css` | Owned metadata-only practice tables, exact question reader, private note revision checks, timer history and clickable dashboard |
| `class-cafcc-standards.php` | Query-backed published-occurrence counts and concepts, independent standard selection |
| `class-cafcc-public-sources.php` | Additive, exact-hash owner-public PDF citation overlay; original source register and rights identity unchanged |
| `class-cafcc-mcq.php` | Separate MCQ/scenario/tag identities, draft imports, source/series/key/rights integrity gates |
| `class-cafcc-mcq-admin.php` | Exact MCQ package membership; resumable owner preview/publication; revision-safe corrections and audit snapshots |
| `class-cafcc-mcq-student.php`, `mcq.js/css` | Options without initial keys, owned scored sessions, tests, bookmarks/tags and performance |
| `research/mcq_pipeline.py` | Offline layout/case/option/key extraction. Private outputs never enter the plugin ZIP or public CI |

## Schema 9

Adds `cafcc_public_source_links` and nine InnoDB `cafcc_mcq_*` tables: questions, scenarios, tags, members, personal, sessions, attempts, tests, jobs. Existing question/account/progress/notebook/timer primary keys and records are retained. No existing subjective content is rewritten. Deactivation retains all records. Migration is additive and checked before advancing the schema version. Older plugin/schema combinations are refused.

MCQ identities derive from source hash + document section + original reference; occurrences remain distinct across attempts/series. Shared facts have a separate source-scoped scenario row. Reimport retains existing corrections and reports differences; it never remaps an old stable ID to a different source. `cafcc_current_mcq_package` is separate from `cafcc_current_package`. Package item writes and checkpoints commit together. Public-citation mappings require an exact registered PDF hash, owner selection and technical integrity state.

## Access, keys and revisions

Every REST route requires authenticated current entitlement and a WordPress REST nonce; administrator routes additionally require the administrator role and capability. Personal queries/writes derive user ID from the authenticated account. No client-selected owner is accepted. All parameter values use prepared SQL, bounded enums and content sanitisation. Private endpoints send `private, no-store`. No password database, payment processor, Drive permission update or deployment is introduced.

MCQ lists return metadata. Opening a question returns common facts, question/options and that student's history, without the key or explanation. Only a deliberate Check Answer with a nonempty valid choice and an owned session returns feedback. The private key is matched to subject, source category, attempt, series, question-source hash/reference, answer-source hash/page and evidence. Unresolved key policies or incomplete facts stay held, even when academic tagging warnings are accepted provisionally.

An InnoDB personal-row lock serialises attempt numbering and Check Answer. An open session survives refresh; an already scored session replays its saved result for the same choice and refuses a changed choice. Reattempt creates a new session, retaining earlier attempts. Timed-test creation has an owner-scoped request key; choices/checkpoints and final scoring commit under an owned test lock. Keys remain absent until Submit. Expired tests accept only saved responses. Changed/withdrawn revisions are excluded from new scoring and old key details are withheld. Test scoring is expressly practice-only: one point per correct response, zero otherwise. Question-view elapsed times do not prove attention or mastery.

Editing MCQ content creates a new draft revision, invalidates its publication fingerprint and retains prior scored attempts. Publication freezes current content/key/grant revisions. Suspended, expired or revised rights grants suppress student availability. Original physical-permission attestation remains source-wide and scan-free within the owner-recorded scope.

## Search and display

The Ind AS/SA catalogue is a naming reference, not automatic academic verification. Assigned inferred tags remain separate from official historical taxonomy. Exact normalised standard matching prevents Ind AS 2 matching 20/21. Query-backed suggestions count published eligible occurrences; optional concepts derive from their actual assigned tags/edition-specific paths. No chain of prior dropdown selections is required.

Practice lists paginate at 20 rows; question and answer HTML load separately. Dashboard links use the same predicates as their corresponding tables. Unique-question counts and saved-occurrence/session counts are identified separately. Subjective outcomes remain student self-assessments; MCQ correctness uses scored attempts.

The shared rich-reader palette explicitly sets background, ink, headers, cells, borders, notes, links and highlights for both themes. Safe rendering strips PDF inline styles; CSS never fills absent source values. Accounting tables scroll within the reader on narrow screens. Reduced-motion preferences are respected.

## Operational limits

- No live-site acceptance, physical Safari test or reliable Drive page-fragment claim.
- The private MCQ workbook supports review annotations; MCQ workbook decisions are not automatically imported. Correct stable IDs through Question Library. The existing subjective Excel workflow is retained.
- No new mass ingestion, multi-year analytics, official exam-marking assertion, live payments or simulated AI explanation.
- A database/files backup is required for rollback. Restore both together only after preserving post-backup student activity; merely downgrading code is intentionally refused.
