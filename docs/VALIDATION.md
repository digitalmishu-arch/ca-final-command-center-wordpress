# Validation result — 21 October 2026

For version 0.1.0, run in an isolated development environment:

| Check | Result |
| --- | --- |
| PHP syntax, six plugin PHP files and integration runner | Passed |
| WordPress/MariaDB integration suite | 132 assertions passed |
| Actual HTTP authentication/authorization cases within the suite | Passed |
| JavaScript syntax, admin and student scripts | Passed |
| Installable ZIP structure, CRC/integrity and single top-level folder | Passed |
| Git whitespace/error check | Passed |

Runtime: WordPress 6.8.3, PHP 8.2.29, MariaDB 11.4 container image. The integration runner creates a new internal network/database/site and removes them afterward; it never uses Hostinger or live-site credentials. Synthetic TEST ONLY fixtures stay outside the plugin archive.

No Hostinger, real iPad browser, staging access control, real academic-source verification, external cache configuration or backup restoration was tested. Complete the [manual acceptance checklist](TESTING.md) on a protected staging site before using real student data. GitHub Actions execution is reported separately in the pull request/run page; local results do not establish a successful hosted CI run.
