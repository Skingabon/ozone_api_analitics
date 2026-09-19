#!/usr/bin/env bash
# Ежедневное обновление данных Ozon и сайта. Запускается cron'ом на сервере.
set -euo pipefail
APP=/opt/ozon/app
cd "$APP"
exec 9>/var/lock/ozon-update.lock; flock -n 9 || { echo "already running"; exit 0; }
echo "=== $(date -Is) start"
PY="$APP/.venv/bin/python"
"$PY" collector/collect.py 30
"$PY" collector/analyze.py >/dev/null
"$PY" collector/savings.py >/dev/null
"$PY" collector/quality.py >/dev/null
"$PY" collector/card_audit.py >/dev/null
"$PY" collector/make_tasks.py >/dev/null
"$PY" collector/build_site.py >/dev/null
cp -r site/. /var/www/ozon/
chmod -R a+rX /var/www/ozon
echo "=== $(date -Is) done"
