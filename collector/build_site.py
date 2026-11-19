"""Сборка статического сайта: web/* + data/metrics.json -> site/."""
import csv, hashlib, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir()
ASSETS = ("style.css", "app.js", "report.js")
for f in ASSETS:
    shutil.copy(ROOT / "web" / f, OUT / f)
# Хеш содержимого в URL ассета: nginx для этого сайта не шлёт Cache-Control, поэтому без версии
# браузер держит старый app.js из кэша и пользователь не видит обновлений интерфейса.
V = {f: hashlib.md5((ROOT / "web" / f).read_bytes()).hexdigest()[:8] for f in ASSETS}
CSS, JS, RJS = f"style.css?v={V['style.css']}", f"app.js?v={V['app.js']}", f"report.js?v={V['report.js']}"
PAGES = {"index": "hub", "dashboard": "dashboard", "products": "products", "accounting": "accounting", "savings": "savings", "cards": "cards", "ideas": "ideas", "quality": "quality", "media": "media", "promos": "promos", "prices": "prices", "admin": "admin"}
TITLE = {"hub": "Хаб", "dashboard": "Дашборд", "products": "Товары", "accounting": "Бухгалтерия", "savings": "Экономия", "cards": "Карточки", "ideas": "Идеи", "quality": "Качество", "media": "Медиа", "promos": "Акции", "prices": "Цены", "admin": "Админ"}
tpl = ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
       f'<meta name="robots" content="noindex"><title>Ozon · {{t}}</title><link rel="stylesheet" href="{CSS}"></head>'
       f'<body data-page="{{p}}"><div id="app"></div><script src="{JS}"></script></body></html>')
for name, p in PAGES.items():
    (OUT / f"{name}.html").write_text(tpl.format(t=TITLE[p], p=p), encoding="utf-8")

(OUT / "report.html").write_text(tpl.format(t="Полный отчёт", p="report").replace(f'<script src="{JS}"></script>', f'<script src="{JS}"></script><script src="{RJS}"></script>'), encoding="utf-8")
M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
M["ideas"] = json.load(open(ROOT / "audit/ideas.json", encoding="utf-8"))
try:
    M["media"] = {"groups": json.load(open(ROOT / "data/media_map.json", encoding="utf-8"))}
except Exception:
    M["media"] = {"groups": {}}
M["tasks_seed"] = json.load(open(ROOT / "data/tasks_seed.json", encoding="utf-8"))
try:
    M["health"] = json.load(open(ROOT / "data/health.json", encoding="utf-8"))   # раздел «Админ»: пишет collector/health.py
except Exception:
    M["health"] = None
(OUT / "data.json").write_text(json.dumps(M, ensure_ascii=False), encoding="utf-8")

def w_csv(name, header, rows):
    with open(OUT / name, "w", encoding="utf-8-sig", newline="") as f:
        cw = csv.writer(f, delimiter=";"); cw.writerow(header); cw.writerows(rows)
w_csv("products.csv", ["Артикул", "Название", "Цена", "Остаток", "Продано", "Выручка", "Комиссия", "Логистика", "Прочие сборы", "Себестоимость", "Прибыль", "Маржа %"],
      [[r["offer_id"], r["name"], r["price"], r["stock"], r["units"], r["sales"], r["commission"], r["delivery"], r["item_fees"], r["cogs"], r["profit"], r["margin_pct"]] for r in M["products"]])
raw = json.load(open(ROOT / "data/raw/accruals.json", encoding="utf-8"))["items"]
types = {t["id"]: t["name"] for t in json.load(open(ROOT / "data/raw/accrual_types.json", encoding="utf-8"))["accrual_types"]}
w_csv("accruals.csv", ["Дата", "ID начисления", "Категория", "Номер отправления/юнита", "Сумма", "Валюта"],
      [[a["date"], a["accrual_id"], a["accrued_category"], a.get("unit_number", ""), a["total_amount"]["amount"].replace(".", ","), a["total_amount"]["currency"]] for a in raw])
print("site built:", sorted(p.name for p in OUT.iterdir()))
