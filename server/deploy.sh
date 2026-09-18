#!/usr/bin/env bash
# Выкладка сайта на сервер (ssh по ключу). Запуск из корня проекта после build_site.py.
set -euo pipefail
source <(grep -E '^SERVER_SSH_(HOST|USER)=' .env)
T="$SERVER_SSH_USER@$SERVER_SSH_HOST"
ssh "$T" 'mkdir -p /opt/ozon /var/www/ozon'
scp -q server/tasks_api.py "$T:/opt/ozon/tasks_api.py"
scp -q server/ozon-api.service "$T:/etc/systemd/system/ozon-api.service"
scp -q server/ozon.nginx.conf "$T:/etc/nginx/sites-available/ozon"
scp -q -r site/. "$T:/var/www/ozon/"
ssh "$T" 'chown -R root:root /opt/ozon && chmod -R a+rX /var/www/ozon && systemctl daemon-reload && systemctl enable --now ozon-api && systemctl restart ozon-api && nginx -t && systemctl reload nginx && sleep 1 && systemctl is-active ozon-api nginx'
