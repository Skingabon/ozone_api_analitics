#!/usr/bin/env bash
# Установка сборщика на сервер: код, ключ Ozon (только OZON_SELLER_*), venv, cron 06:00.
set -euo pipefail
source <(grep -E '^SERVER_SSH_(HOST|USER)=' .env)
T="$SERVER_SSH_USER@$SERVER_SSH_HOST"
ssh "$T" 'mkdir -p /opt/ozon/app/data && (python3 -c 'import ensurepip' 2>/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -q python3-venv >/dev/null)'
scp -q -r collector web "$T:/opt/ozon/app/"
scp -q cost_prices.xlsx server/run_daily.sh "$T:/opt/ozon/app/"
grep -E '^OZON_SELLER_(CLIENT_ID|API_KEY)=' .env | ssh "$T" 'umask 077; cat > /opt/ozon/app/.env'
ssh "$T" 'set -e; cd /opt/ozon/app; chmod 600 .env cost_prices.xlsx; chmod 700 run_daily.sh
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q requests python-dotenv openpyxl
cat > /etc/cron.d/ozon <<CRON
# Ежедневное обновление данных Ozon (время сервера)
0 6 * * * root nice -n 10 /opt/ozon/app/run_daily.sh >> /var/log/ozon-update.log 2>&1
CRON
chmod 644 /etc/cron.d/ozon
cat > /etc/logrotate.d/ozon <<LR
/var/log/ozon-update.log { weekly rotate 4 compress missingok notifempty }
LR
echo installed'
