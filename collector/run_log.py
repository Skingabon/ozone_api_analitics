"""Журнал ежедневных прогонов обновления: data/runs.json. Вызывается из server/run_daily.sh.

  python collector/run_log.py begin                  # открыть запись прогона
  python collector/run_log.py step <имя> <код> <сек>  # результат шага
  python collector/run_log.py end <код>               # закрыть прогон и посчитать итог

Шаги health/build_site/publish выполняются уже после end — они дописываются в тот же прогон
и продлевают его, иначе в истории повис бы вечно «незакрытый» прогон.
"""
import json, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "data" / "runs.json"
KEEP = 90


def load():
    try:
        runs = json.loads(F.read_text(encoding="utf-8"))
        return runs if isinstance(runs, list) else []
    except Exception:
        return []


def save(runs):
    F.parent.mkdir(parents=True, exist_ok=True)
    tmp = F.with_suffix(".tmp"); tmp.write_text(json.dumps(runs[-KEEP:], ensure_ascii=False, indent=1), encoding="utf-8"); tmp.replace(F)


def blank(at):
    return {"started_at": at, "finished_at": None, "duration_s": None, "status": None, "steps": []}


def close(run, at, rc=None):
    """finished_at/duration/status: status учитывает и код, переданный end, и коды всех шагов."""
    run["finished_at"] = at
    run["duration_s"] = max(0, round((datetime.fromisoformat(at) - datetime.fromisoformat(run["started_at"])).total_seconds()))
    run["status"] = "failed" if (rc or any(s.get("rc") for s in run["steps"])) else "ok"


cmd = sys.argv[1] if len(sys.argv) > 1 else ""
runs = load()
now = datetime.now().astimezone().isoformat(timespec="seconds")

if cmd == "begin":
    runs.append(blank(now))
elif cmd in ("step", "end"):
    if not runs:
        runs.append(blank(now))             # begin не отработал (сбой диска, ручной запуск) — журнал всё равно ведём
    cur = runs[-1]
    if cmd == "step":
        name, rc, sec = sys.argv[2], int(sys.argv[3]), int(float(sys.argv[4]))
        cur["steps"] = [s for s in cur["steps"] if s.get("name") != name]   # повтор шага заменяет прежний результат
        cur["steps"].append({"name": name, "rc": rc, "s": sec, "at": now})
        if cur.get("finished_at"):
            close(cur, now)
    else:
        close(cur, now, int(sys.argv[2]))
else:
    print(__doc__); sys.exit(2)

save(runs)
print("run_log", cmd, "->", len(runs), "записей")
