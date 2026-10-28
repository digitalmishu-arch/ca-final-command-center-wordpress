# Private Notes incident: evidence and limits

## Reproduced application defect

The v0.7 student client called `response.json()` without checking the response type. An injected HTML 503 response at the existing `/cafcc/v6/study/{question_id}?occurrence_id=…` request reproduced `Unexpected token '<', "<h1>Error "… is not valid JSON` in the study feedback beside Private Notes. This was a disposable WordPress test, not inspection of Hostinger. The old renderer also expanded many questions and started study-state/highlight requests for each, amplifying simultaneous traffic.

The owner's actual failed HTTP request, HTTP status and PHP/MySQL logs have **not** been inspected. We cannot establish whether Hostinger hit a connection/resource limit, an upstream outage or another hosting failure. An HTML error inside a card does not establish a permanent site-wide database disconnection. No hosting access was used.

## Application repairs

* `assets/net.js`: at most two active student requests, coalesced identical reads, explicit JSON validation, bounded timeout, safe text errors. No raw response body, HTML, SQL or credentials is displayed. Writes are not automatically retried.
* `assets/experience.js`: metadata-only list, one selected reader; no per-row note/timer/highlight fan-out.
* `assets/explorer.js`: notes load only when opened. The textarea remains disabled until a successful read. An unavailable read cannot turn into an empty-note save. Explicit retry preserves unsaved edits unless the student confirms discarding them.
* `includes/class-cafcc-notes.php`: owned existing notebook rows, hash-based compare-and-swap in a transaction, harmless replay after a lost save response, 409 for stale different edits. No new note identities or note deletion.
* Existing study REST callbacks are wrapped by a safe database-error guard. Plugin-handled query failures produce JSON 503 responses. Failures before WordPress/plugin bootstrap cannot be converted by the plugin; the client still handles their HTML safely.

## Administrator diagnosis

Settings → Advanced Academic Tools → Student experience contains bounded diagnostic events: code, route category, status, UTC timestamp and request ID. There is also an administrator-only `/cafcc/v10/admin/service-diagnostics` endpoint. Failed database queries log the event to the PHP error log because an unavailable database cannot reliably save its own diagnostic. No note text, SQL or credentials is collected. Copy only the event code/time/request ID when requesting hosting investigation.

## Verification

Tests cover existing notes, save/update/replay, stale edits, query failure, injected HTML failure, explicit retry, reload/login persistence and two-student isolation. The injected HTML test is fault simulation, not a claim to have reproduced the owner's precise hosting outage. Physical iPad/Hostinger acceptance remains required. If an error persists after upgrade, capture the failed request's status/time and correlate it with hosting PHP/database logs; do not send passwords or private notes.
