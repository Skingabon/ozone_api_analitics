"""Полный отчёт в PDF: все разделы сайта подряд + оглавление со ссылками. data/report/Otchet_HomeHelp_<дата>.pdf

  python collector/make_full_report.py
Сначала пересобирает сайт из data/metrics.json (build_site.py), кладёт рядом свежие задачи (data/tasks_live.json, если есть),
поднимает локальный сервер и печатает site/report.html в PDF через Chrome. Ключей и паролей в отчёте нет.
"""
import shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"; OUT = ROOT / "data/report"; OUT.mkdir(parents=True, exist_ok=True)
CHROME = next(p for p in ("C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe") if Path(p).exists())
PY = sys.executable
PORT = 8766

subprocess.run([PY, str(ROOT / "collector/build_site.py")], check=True, capture_output=True)
tl = ROOT / "data/tasks_live.json"
if tl.exists(): shutil.copy(tl, SITE / "tasks_live.json")
srv = subprocess.Popen([PY, "-m", "http.server", str(PORT)], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(2)
    pdf = OUT / f"Otchet_HomeHelp_polnyi_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=25000",
                    f"--print-to-pdf={pdf}", f"http://localhost:{PORT}/report.html"], check=True, capture_output=True)
    print("готово:", pdf, round(pdf.stat().st_size / 1024), "КБ")
finally:
    srv.terminate()
    (SITE / "tasks_live.json").unlink(missing_ok=True)
