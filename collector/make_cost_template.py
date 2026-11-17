"""Шаблон себестоимости: cost_prices.xlsx (заполняется вручную, в git не попадает)."""
import json, sys
from collections import defaultdict
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

ROOT = Path(__file__).resolve().parent.parent
L = lambda n: json.load(open(ROOT / "data/raw" / f"{n}.json", encoding="utf-8"))
info = L("product_info")["items"]
stocks = {s["offer_id"]: sum(x["present"] for x in s["stocks"]) for s in L("stocks")["items"]}
sold = defaultdict(int)
for p in L("fbs_postings")["items"] + L("fbo_postings")["items"]:
    if p["status"] != "cancelled":
        for pr in p["products"]:
            sold[pr["offer_id"]] += pr["quantity"]

out = ROOT / "cost_prices.xlsx"
wb = Workbook(); ws = wb.active; ws.title = "Себестоимость"
head = ["Артикул (offer_id)", "SKU", "Название", "Цена на Ozon, ₽", "Остаток, шт",
        "Продано за 30 дн, шт", "Себестоимость ед., ₽ (ЗАПОЛНИТЬ)", "Доп. расходы на ед., ₽ (упаковка, доставка до склада)", "Комментарий"]
ws.append(head)
rows = sorted(info, key=lambda i: -sold.get(i["offer_id"], 0))
for i in rows:
    sku = (i.get("sources") or [{}])[0].get("sku", "")
    ws.append([i["offer_id"], sku, i.get("name", ""), float(i.get("price") or 0),
               stocks.get(i["offer_id"], 0), sold.get(i["offer_id"], 0), None, None, None])
fill = PatternFill("solid", fgColor="FFF2CC")
for c in ws[1]:
    c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True, vertical="center")
ws.row_dimensions[1].height = 48
for r in range(2, ws.max_row + 1):
    for col in "GH":
        ws[f"{col}{r}"].fill = fill
        ws[f"{col}{r}"].number_format = "#,##0.00"
for col, w in zip("ABCDEFGHI", [26, 14, 60, 14, 12, 14, 24, 30, 30]):
    ws.column_dimensions[col].width = w
ws.freeze_panes = "D2"
dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True,
                    errorTitle="Ошибка", error="Введите число ≥ 0")
ws.add_data_validation(dv); dv.add(f"G2:H{ws.max_row}")
wb.save(out); print("saved", out, len(rows), "товаров")
