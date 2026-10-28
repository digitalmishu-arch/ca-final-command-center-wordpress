#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
release_root="$PWD"
mkdir -p work/v08-baseline
# Exactly the reviewed v0.7 foundation; never main and never a hosting database.
git archive 0b4e42fdc9dbe10ec11473016397598971e2d2be | tar -x -C work/v08-baseline
cd work/v08-baseline
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
CAFCC_PREVIEW=1 bash tests/run-integration.sh
read -r upgrade_wp <work/preview-containers.txt
docker cp "$release_root/tests/upgrade-v08.php" "$upgrade_wp:/tmp/upgrade-v08.php"
docker exec -e CAFCC_UPGRADE_MODE=snapshot "$upgrade_wp" php /tmp/upgrade-v08.php
docker cp "$release_root/ca-final-command-center/." "$upgrade_wp:/var/www/html/wp-content/plugins/ca-final-command-center/"
docker exec "$upgrade_wp" chmod -R a+rX /var/www/html/wp-content/plugins/ca-final-command-center
docker exec "$upgrade_wp" php /tmp/upgrade-v08.php
