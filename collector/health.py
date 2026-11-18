"""Состояние автообновления для раздела «Админ»: data/runs.json + ошибки сбора + data/metrics.json -> data/health.json.

  python collector/health.py

Запускается из server/run_daily.sh перед build_site.py. Ошибки Ozon API не валят прогон (collect.py пишет _error
в data/raw/*.json и выходит с кодом 0), поэтому единственный способ их увидеть — прочитать сырьё и журнал.
"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
LOG = Path("/var/log/ozon-update.log")
KEEP_ON_ERROR = {"queries", "queries_details", "analytics_data", "analytics_stocks", "fbo_postings", "fbs_postings"}
MAX_AGE_H = 26        # cron ежедневный в 06:00: больший возраст означает, что прогон не состоялся
LONG_RUN_S = 90 * 60  # сбор на сервере идёт ~60 минут, дольше — уже повод посмотреть журнал
RUNS_SHOWN = 60
NEXT_RUN = "06:00 (время сервера)"

now = datetime.now().astimezone()
errors = []


def add(level, title, detail=""):
    errors.append({"level": level, "title": title, "detail": str(detail)[:300]})


def age_h(dt):
    return (now - dt).total_seconds() / 3600


def ago(dt):
    m = round((now - dt).total_seconds() / 60)
    if m < 60: return f"{m} мин назад"
    if m < 48 * 60: return f"{m // 60} ч назад"
    return f"{m // 1440} дн назад"


def dur(s):
    return f"{s // 60} мин {s % 60} с" if s >= 60 else f"{s} с"


def plural(n, one, few, many):
    n10, n100 = n % 10, n % 100
    return f"{n} " + (one if n10 == 1 and n100 != 11 else few if 2 <= n10 <= 4 and not 12 <= n100 <= 14 else many)


# --- журнал прогонов ---
try:
    runs = json.loads((ROOT / "data" / "runs.json").read_text(encoding="utf-8"))
    runs = runs if isinstance(runs, list) else []
except Exception:
    runs = []
last = runs[-1] if runs else None

if not runs:
    add("critical", "История обновлений пуста", "data/runs.json не найден: cron не запускался или run_daily.sh на сервере не обновлён.")
elif last and not last.get("finished_at"):
    pass                                             # прогон ещё идёт — статус выставим ниже
elif last:
    started = datetime.fromisoformat(last["started_at"])
    for s in last.get("steps", []):
        if s.get("rc"):
            add("critical", f"Шаг «{s['name']}» завершился с кодом {s['rc']}", f"Прогон от {started:%d.%m.%Y %H:%M}, длительность {dur(last.get('duration_s') or 0)}.")
    if last.get("status") == "failed" and not any(s.get("rc") for s in last.get("steps", [])):
        add("critical", "Прогон завершился ошибкой", "run_daily.sh вернул ненулевой код, подробности в /var/log/ozon-update.log.")
    if age_h(started) > MAX_AGE_H:
        add("critical", "Ежедневное обновление не выполняется", f"Последний прогон — {started:%d.%m.%Y %H:%M} ({ago(started)}). Проверьте cron: /etc/cron.d/ozon.")
    if (last.get("duration_s") or 0) > LONG_RUN_S:
        add("info", f"Прогон шёл {dur(last['duration_s'])}", "Дольше обычного: вероятны потери пакетов до api-seller.ozon.ru или лимиты API.")

# --- сырьё: ошибки API и не обновившиеся разделы ---
run_start = datetime.fromisoformat(last["started_at"]).timestamp() if last else None
raw_info, not_refreshed = [], []
for f in sorted(RAW.glob("*.json")):
    mt = datetime.fromtimestamp(f.stat().st_mtime).astimezone()
    err = None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(d, dict) and d.get("_error"):
            err = f"HTTP {d['_error']}: {str(d.get('_body', ''))[:200]}"
    except Exception as e:
        err = f"файл не читается: {e}"
    raw_info.append({"name": f.stem, "mtime": mt.isoformat(timespec="seconds"), "error": err})
    if err:
        kept = " В отчёте остались прошлые данные (раздел в KEEP_ON_ERROR)." if f.stem in KEEP_ON_ERROR else ""
        add("critical", f"Раздел «{f.stem}»: {err.split(':')[0]}", err + kept)
    elif run_start and mt.timestamp() < run_start - 60:
        not_refreshed.append((f.stem, mt))

for s, mt in not_refreshed[:3]:
    add("warn", f"Раздел «{s}» не обновлялся", f"Последняя запись {mt:%d.%m.%Y %H:%M}: сбор не дошёл до раздела или сработал KEEP_ON_ERROR.")
if len(not_refreshed) > 3:
    names = [s for s, _ in not_refreshed[3:]]
    add("warn", f"Ещё {plural(len(names), 'раздел', 'раздела', 'разделов')} без обновления",
        ", ".join(names[:15]) + (f" и ещё {len(names) - 15}" if len(names) > 15 else ""))
if raw_info and len(not_refreshed) == len(raw_info):
    add("critical", "Сырьё не обновилось ни по одному разделу",
        f"Все {plural(len(not_refreshed), 'файл', 'файла', 'файлов')} в data/raw старше начала прогона: collect.py не записал данные.")

# --- отчёт ---
metrics = None
try:
    metrics = json.loads((ROOT / "data" / "metrics.json").read_text(encoding="utf-8"))
except Exception as e:
    add("critical", "data/metrics.json не читается", e)

generated = None
if metrics:
    try:
        generated = datetime.fromisoformat(metrics["generated_at"]).astimezone()
        if age_h(generated) > MAX_AGE_H:
            add("critical", f"Отчёт устарел: собран {ago(generated)}", f"generated_at = {metrics['generated_at']}.")
        kpi = metrics.get("kpi") or {}
        if not kpi.get("orders") and not kpi.get("sales"):
            add("critical", "Отчёт собрался пустым", "Ни одного заказа и нулевая выручка за период: проверьте отправления FBO/FBS в data/raw.")
        if not metrics.get("products"):
            add("critical", "В отчёте нет товаров", "data/metrics.json: пустой список products.")
    except Exception as e:
        add("critical", "В data/metrics.json нет generated_at", e)
    if generated and raw_info:
        newest = max(datetime.fromisoformat(r["mtime"]) for r in raw_info)
        if (newest - generated).total_seconds() > 300:   # запас 5 минут: в штатном прогоне analyze.py идёт сразу за collect.py
            add("warn", "Отчёт не пересобран после сбора", f"Сырьё обновлено {newest:%d.%m.%Y %H:%M}, отчёт — {generated:%d.%m.%Y %H:%M}: analyze.py/build_site.py не отработали.")

# --- журнал cron: строки ошибок последнего прогона ---
log_tail = []
try:
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    start_i = max((i for i, l in enumerate(lines) if " start" in l), default=0)
    seg = lines[start_i:]
    log_tail = [l for l in seg if any(k in l for k in ("ERROR", "Traceback", "error:", "Не удалось", "не выполнена"))][-25:]
    for l in log_tail[-5:]:
        add("warn", "Строка ошибки в журнале", l.strip()[:200])
except FileNotFoundError:
    pass                                             # локальный запуск: журнала cron нет
except Exception as e:
    add("info", "Журнал /var/log/ozon-update.log не прочитан", e)

# --- итоговый статус: каждый реальный случай со своей меткой, «остановлено» не переиспользуем ---
step_failed = bool(last) and (last.get("status") == "failed" or any(s.get("rc") for s in last.get("steps", [])))
report_old = generated is None or age_h(generated) > MAX_AGE_H
run_old = bool(last) and age_h(datetime.fromisoformat(last["started_at"])) > MAX_AGE_H
if not runs:
    status = "never"
elif last and not last.get("finished_at"):
    status = "running"
elif step_failed:
    status = "failed"
elif report_old or run_old:
    status = "stale"
elif any(e["level"] == "critical" for e in errors):
    status = "errors"
elif any(e["level"] == "warn" for e in errors):   # инфо-поводы (например, долгий прогон) статус не понижают
    status = "warn"
else:
    status = "ok"

LABELS = {"ok": "обновлено успешно", "warn": "обновлено с предупреждениями", "errors": "обновлено, но данные с ошибками",
          "failed": "прогон завершился ошибкой", "stale": "данные устарели", "running": "идёт обновление", "never": "не запускалось"}

health = {
    "generated_at": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
    "status": status, "label": LABELS[status], "next_run": NEXT_RUN,
    "report_generated_at": metrics.get("generated_at") if metrics else None,
    "report_age": ago(generated) if generated else None,
    "period": [min(metrics["days"]), max(metrics["days"])] if metrics and metrics.get("days") else None,
    "last_run": {**last, "duration": dur(last["duration_s"]) if last.get("duration_s") is not None else None} if last else None,
    "runs": [{**r, "duration": dur(r["duration_s"]) if r.get("duration_s") is not None else None} for r in runs[-RUNS_SHOWN:]][::-1],
    "counts": {"critical": sum(e["level"] == "critical" for e in errors), "warn": sum(e["level"] == "warn" for e in errors),
               "info": sum(e["level"] == "info" for e in errors), "runs": len(runs)},
    "errors": errors,
    "log_tail": log_tail,
    "legend": LABELS,
}
out = ROOT / "data" / "health.json"
out.write_text(json.dumps(health, ensure_ascii=False), encoding="utf-8")
print("health:", status, "|", health["counts"])
