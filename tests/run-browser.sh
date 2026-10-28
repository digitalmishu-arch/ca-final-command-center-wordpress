#!/usr/bin/env bash
# Owned local WordPress/MariaDB only. New student UI replaces obsolete legacy selectors.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p work docs/previews
cleanup_browser(){
 if [[ -f work/preview-containers.txt ]]; then
  mapfile -t owned <work/preview-containers.txt
  if [[ "${owned[0]:-}" == cafcc-test-*-wp && "${owned[1]:-}" == cafcc-test-*-db && "${owned[2]:-}" == cafcc-test-* ]]; then
   docker rm -fv "${owned[0]}" "${owned[1]}" >/dev/null 2>&1 || true
   docker network rm "${owned[2]}" >/dev/null 2>&1 || true
  fi
 fi
}
trap cleanup_browser EXIT
CAFCC_PREVIEW=1 bash tests/run-integration.sh
read -r preview_wp <work/preview-containers.txt
docker exec "$preview_wp" php /repo/tests/preview.php
docker exec -e CAFCC_PRACTICE_DEMO=1 "$preview_wp" php /repo/tests/practice-demo.php
python3 tests/browser-review-access.py
CAFCC_ADMIN_ONLY=1 python3 tests/browser-v05.py
CAFCC_ADMIN_ONLY=1 python3 tests/browser-v051.py
CAFCC_ADMIN_ONLY=1 python3 tests/browser-v052.py
CAFCC_ADMIN_ONLY=1 python3 tests/browser-v06.py
python3 tests/browser-v08.py
if [[ "${CAFCC_TEST_WEBKIT:-0}" == 1 ]]; then CAFCC_BROWSER_ENGINE=webkit python3 tests/browser-v08.py; fi
