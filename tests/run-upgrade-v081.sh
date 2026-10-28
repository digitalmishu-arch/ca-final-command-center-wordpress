#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
release_root="$PWD"
mkdir -p work/v081-baseline
# Exact PR15 v0.8 foundation; no hosting database or old main branch.
git archive 759052a8bbe058f08a5aac28cc47b8590de2915b | tar -x -C work/v081-baseline
cd work/v081-baseline
mkdir -p work docs/previews
cleanup(){
 if [[ -f work/preview-containers.txt ]]; then
  mapfile -t owned <work/preview-containers.txt
  if [[ "${owned[0]:-}" == cafcc-test-*-wp && "${owned[1]:-}" == cafcc-test-*-db && "${owned[2]:-}" == cafcc-test-* ]]; then
   docker rm -fv "${owned[0]}" "${owned[1]}" >/dev/null 2>&1 || true
   docker network rm "${owned[2]}" >/dev/null 2>&1 || true
  fi
 fi
}
trap cleanup EXIT
# No published port: use the baseline preview setup on loopback only after integration.
CAFCC_KEEP_FAILURE=1 bash tests/run-integration.sh
mapfile -t baseline <work/preview-containers.txt
upgrade_wp="${baseline[0]}"
docker cp "$release_root/tests/upgrade-v08.php" "$upgrade_wp:/tmp/upgrade-v081.php"
docker exec -e CAFCC_UPGRADE_MODE=snapshot "$upgrade_wp" php /tmp/upgrade-v081.php
docker cp "$release_root/ca-final-command-center/." "$upgrade_wp:/var/www/html/wp-content/plugins/ca-final-command-center/"
docker exec "$upgrade_wp" chmod -R a+rX /var/www/html/wp-content/plugins/ca-final-command-center
docker exec "$upgrade_wp" php /tmp/upgrade-v081.php
