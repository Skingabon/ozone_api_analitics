#!/usr/bin/env bash
# Ежедневное обновление данных Ozon и сайта. Запускается cron'ом на сервере.
# Каждый шаг пишется в data/runs.json (collector/run_log.py), итог публикуется в разделе «Админ» на сайте.
set -uo pipefail
APP=/opt/ozon/app
cd "$APP"
exec 9>/var/lock/ozon-update.lock; flock -n 9 || { echo "already running"; exit 0; }
echo "=== $(date -Is) start"
export PYTHONIOENCODING=utf-8   # cron даёт LANG=C: иначе кириллица в логе ломается, а apply_promos.py падает на «−»
PY="$APP/.venv/bin/python"
rl() { "$PY" collector/run_log.py "$@"; }
fatal=0

step() {   # step <имя> <команда...>: код возврата и длительность шага уходят в журнал, ошибка — ещё и в лог cron
  local name=$1 t0=$SECONDS rc=0
  shift
  "$@" || rc=$?
  rl step "$name" "$rc" $((SECONDS - t0))
  [ "$rc" -eq 0 ] || echo "ШАГ $name ЗАВЕРШИЛСЯ С КОДОМ $rc"
  return "$rc"
}

rl begin

# collect и analyze фатальные: без свежего сырья и расчёта остальные разделы теряют смысл.
# Прочие шаги падают в одиночку — analyze.py мержит metrics.json по ключам, сайт соберётся с прежним значением раздела.
step collect "$PY" collector/collect.py 30 || fatal=1
step apply_promos "$PY" collector/apply_promos.py --auto || echo "автоочистка акций не выполнена"
[ "$fatal" -eq 0 ] && { step analyze "$PY" collector/analyze.py || fatal=1; }
for s in savings quality card_audit prices promos make_tasks; do
  step "$s" "$PY" "collector/$s.py" || echo "раздел $s не обновлён"
done

rl end "$fatal"

step health "$PY" collector/health.py || fatal=1
step build_site "$PY" collector/build_site.py || fatal=1
step publish cp -r site/. /var/www/ozon/ || fatal=1
chmod -R a+rX /var/www/ozon

# Снимок состояния собирается до публикации, поэтому второй проход дописывает в сайт итог build_site и publish.
# data.json подменяем через mv: nginx не должен отдать наполовину записанный файл.
"$PY" collector/health.py && "$PY" collector/build_site.py && cp site/data.json /var/www/ozon/data.json.tmp \
  && mv /var/www/ozon/data.json.tmp /var/www/ozon/data.json || echo "итог прогона не опубликован"

echo "=== $(date -Is) done fatal=$fatal"
exit "$fatal"
