"""Сборка статического сайта: web/* + data/metrics.json -> site/."""
import csv, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir()
for f in ("style.css", "app.js"):
    shutil.copy(ROOT / "web" / f, OUT / f)
PAGES = {"index": "hub", "dashboard": "dashboard", "products": "products", "accounting": "accounting", "savings": "savings", "cards": "cards", "ideas": "ideas", "quality": "quality", "media": "media"}
tpl = ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
       '<meta name="robots" content="noindex"><title>Ozon · {t}</title><link rel="stylesheet" href="style.css"></head>'
       '<body data-page="{p}"><div id="app"></div><script src="app.js"></script></body></html>')
for name, p in PAGES.items():
    (OUT / f"{name}.html").write_text(tpl.format(t={"hub": "Хаб", "dashboard": "Дашборд", "products": "Товары", "accounting": "Бухгалтерия", "savings": "Экономия", "cards": "Карточки", "ideas": "Идеи", "quality": "Качество", "media": "Медиа"}[p], p=p), encoding="utf-8")

M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
M["ideas"] = json.load(open(ROOT / "audit/ideas.json", encoding="utf-8"))
try:
    M["media"] = {"groups": json.load(open(ROOT / "data/media_map.json", encoding="utf-8"))}
except Exception:
    M["media"] = {"groups": {}}
M["tasks_seed"] = json.load(open(ROOT / "data/tasks_seed.json", encoding="utf-8"))
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
