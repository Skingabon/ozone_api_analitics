"""Качество магазина: рейтинг продавца, контент-рейтинг, оборачиваемость, заявки на скидку, компенсации -> metrics["quality"]."""
import json, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

ROOT = Path(__file__).resolve().parent.parent
L = lambda n: json.load(open(ROOT / "data/raw" / f"{n}.json", encoding="utf-8"))
M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
info = L("product_info")["items"]
sku2o = {int(s["sku"]): i["offer_id"] for i in info for s in (i.get("sources") or [])}
sales = {p["offer_id"]: p["sales"] for p in M["products"]}

# рейтинг продавца
groups = L("rating_summary").get("groups", [])
ratings = [{"group": g["group_name"], "name": it["name"], "value": it["current_value"], "past": it["past_value"],
            "status": it["status"], "kind": it.get("value_type"), "key": it["rating"]} for g in groups for it in g["items"]]
premium = warn = None
try:
    r0 = L("rating_history")["ratings"][0]; premium, warn = r0["premium_threshold"], r0["warning_threshold"]
except Exception: pass
fbs = L("rating_fbs")

# контент-рейтинг
cr = []
for p in L("content_rating")["products"]:
    o = sku2o.get(int(p["sku"]), str(p["sku"]))
    miss = []
    FAM = ("media_images", "text_annotation", "other_")   # «лестницы»: если выполнен уровень выше, нижние не считаем
    for g in p.get("groups", []):
        last = {}   # индекс самого высокого выполненного уровня в «лестнице»
        for i, c in enumerate(g["conditions"]):
            fam = next((f for f in FAM if c["key"].startswith(f)), None)
            if fam and c["fulfilled"]: last[fam] = i
        for i, c in enumerate(g["conditions"]):
            fam = next((f for f in FAM if c["key"].startswith(f)), None)
            if c["fulfilled"] or (fam and i < last.get(fam, -1)): continue
            miss.append({"group": g["name"], "what": c["description"], "gain": c["cost"], "weight": g["weight"]})
    # реальный выигрыш ~ стоимость условия × вес группы
    for m in miss: m["score"] = m["gain"] * m["weight"] / 100
    miss.sort(key=lambda m: -m["score"])
    cr.append({"offer_id": o, "sku": p["sku"], "rating": p["rating"], "sales": sales.get(o, 0),
               "groups": [{"name": g["name"], "rating": g["rating"], "weight": g["weight"]} for g in p.get("groups", [])],
               "improve": miss[:3], "improve_attrs": sorted({a["name"] for g in p.get("groups", []) for a in g.get("improve_attributes", [])})[:6]})
cr.sort(key=lambda x: (-x["sales"], x["rating"]))

# оборачиваемость (по данным Ozon: товары на складах Ozon)
tv = [{"offer_id": i["offer_id"], "stock": i["current_stock"], "ads": i["ads"], "idc": i["idc"], "grade": i["turnover_grade"]} for i in L("turnover").get("items", [])]

# заявки на скидку
dt = L("discount_tasks"); new = []
for t in dt.get("NEW", []):
    new.append({"offer_id": sku2o.get(int(t["sku"]), str(t["sku"])), "original": t["original_price"], "requested": t["requested_price"],
                "discount": t["requested_discount"], "min_auto": t["min_auto_price"], "qty": t["requested_quantity_max"], "end_at": t["end_at"]})
counts = {k: len(v) for k, v in dt.items()}

# компенсации
comp = L("compensation_rows").get("items", []) if (ROOT / "data/raw/compensation_rows.json").exists() else []

M["quality"] = {"ratings": ratings, "premium_threshold": premium, "warning_threshold": warn,
                "fbs_index": {"index": fbs.get("index"), "from": fbs.get("period_from"), "to": fbs.get("period_to"), "cost": fbs.get("processing_costs_sum")},
                "content": cr, "content_avg": round(sum(x["rating"] for x in cr) / max(len(cr), 1), 1),
                "turnover": tv, "turnover_grades": dict(Counter(t["grade"] for t in tv)),
                "discount_new": new, "discount_counts": counts, "compensation": comp,
                "compensation_note": "Отчёты Ozon за последние 3 месяца; здесь только выплаты, которые Ozon уже начислил."}
(ROOT / "data/metrics.json").write_text(json.dumps(M, ensure_ascii=False), encoding="utf-8")
print("quality ok: контент", M["quality"]["content_avg"], "| заявок на скидку", len(new), "| компенсаций", len(comp))
