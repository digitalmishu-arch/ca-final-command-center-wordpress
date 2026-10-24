#!/usr/bin/env bash
# Disposable local browser environment, never an existing WordPress site.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p work
cleanup_browser() {
    if [[ -f work/preview-containers.txt ]]; then
        mapfile -t practice_preview < work/preview-containers.txt
        if [[ "${practice_preview[0]:-}" == cafcc-test-*-wp && "${practice_preview[1]:-}" == cafcc-test-*-db && "${practice_preview[2]:-}" == cafcc-test-* ]]; then
            docker rm -fv "${practice_preview[0]}" "${practice_preview[1]}" >/dev/null 2>&1 || true
            docker network rm "${practice_preview[2]}" >/dev/null 2>&1 || true
        fi
        rm -f work/preview-containers.txt
    fi
}
trap cleanup_browser EXIT
CAFCC_PREVIEW=1 bash tests/run-integration.sh
python3 tests/browser-smoke.py
read -r practice_preview_wp < work/preview-containers.txt
docker exec "$practice_preview_wp" php /repo/tests/preview.php
docker exec -e CAFCC_PRACTICE_DEMO=1 "$practice_preview_wp" php /repo/tests/practice-demo.php
python3 tests/browser-practice.py
python3 tests/browser-review-access.py

python3 tests/browser-v041.py
if [[ "${CAFCC_TEST_WEBKIT:-0}" == 1 ]]; then CAFCC_BROWSER_ENGINE=webkit python3 tests/browser-v041.py; fi
