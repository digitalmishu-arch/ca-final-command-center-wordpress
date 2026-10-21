#!/usr/bin/env bash
# Disposable local WordPress + MariaDB. Never points to a hosting account.
set -euo pipefail
cd "$(dirname "$0")/.."
repo_path="$PWD"
run_id="cafcc-test-${RANDOM}-$$"
wp_container="${run_id}-wp"
db_container="${run_id}-db"
cleanup() {
    docker rm -fv "$wp_container" "$db_container" >/dev/null 2>&1 || true
    docker network rm "$run_id" >/dev/null 2>&1 || true
}
trap cleanup EXIT
# No published ports, no external access, no persistent database volumes.
docker network create --internal "$run_id" >/dev/null
docker run -d --name "$db_container" --network "$run_id" --network-alias db \
    -e MARIADB_ROOT_PASSWORD=cafcc-disposable-only -e MARIADB_DATABASE=cafcc_test \
    -e MARIADB_USER=cafcc -e MARIADB_PASSWORD=cafcc-disposable-only mariadb:11.4 >/dev/null
ready=0
for ((i=0;i<60;i++)); do
    if docker exec "$db_container" healthcheck.sh --connect --innodb_initialized >/dev/null 2>&1; then ready=1; break; fi
    sleep 1
done
if [[ "$ready" != 1 ]]; then echo 'Test database failed to start.' >&2; exit 1; fi
docker run -d --name "$wp_container" --network "$run_id" \
    --mount "type=bind,src=$repo_path,dst=/repo,readonly" \
    -e WORDPRESS_DB_HOST=db -e WORDPRESS_DB_USER=cafcc -e WORDPRESS_DB_PASSWORD=cafcc-disposable-only \
    -e WORDPRESS_DB_NAME=cafcc_test wordpress:6.8-php8.2-apache >/dev/null
ready=0
for ((i=0;i<60;i++)); do
    if docker exec "$wp_container" test -f /var/www/html/wp-config.php; then ready=1; break; fi
    sleep 1
done
if [[ "$ready" != 1 ]]; then echo 'Test WordPress failed to start.' >&2; exit 1; fi
# Copy into the disposable install and emulate WordPress ZIP extraction modes.
# The source workspace may use a private umask that Apache cannot read.
docker cp "$repo_path/ca-final-command-center" "$wp_container:/var/www/html/wp-content/plugins/ca-final-command-center"
docker exec "$wp_container" chmod -R a+rX /var/www/html/wp-content/plugins/ca-final-command-center
docker exec "$wp_container" sh -c 'find /repo/ca-final-command-center /repo/tests -name "*.php" -print0 | xargs -0 -n 1 php -l'
if ! docker exec "$wp_container" php /repo/tests/integration.php; then
    docker exec "$wp_container" php -r 'require "/var/www/html/wp-load.php"; echo json_encode(array("active"=>get_option("active_plugins"),"loaded"=>class_exists("CAFCC_REST"),"namespaces"=>rest_get_server()->get_namespaces())),PHP_EOL;'
    exit 1
fi
