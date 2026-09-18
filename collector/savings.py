"""Потенциал снижения расходов -> добавляет "savings" в data/metrics.json."""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L = lambda n: json.load(open(ROOT / "data/raw" / f"{n}.json", encoding="utf-8"))
M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
K, OH, P = M["kpi"], M["overhead"], M["products"]
types = {t["id"]: t["name"] for t in L("accrual_types")["accrual_types"]}

# категории и комиссии
names = {}
def rec(nodes, path, cat):
    for c in nodes:
        if "category_name" in c: rec(c.get("children", []), path + [c["category_name"]], c["description_category_id"])
        else: names[(cat, c["type_id"])] = " > ".join(path[-2:]) + " > " + c["type_name"]
try: rec(L("category_tree")["result"], [], None)
except Exception: pass
sales_by_offer = {r["offer_id"]: r for r in P}
cats = defaultdict(lambda: {"products": 0, "sales": 0.0, "commission": 0.0, "percent": None})
for i in L("product_info")["items"]:
    k = names.get((i["description_category_id"], i["type_id"]), f"{i['description_category_id']}/{i['type_id']}")
    c = cats[k]; c["products"] += 1
    r = sales_by_offer.get(i["offer_id"], {})
    c["sales"] += r.get("sales", 0); c["commission"] += r.get("commission", 0)
    fbs = next((x["percent"] for x in i.get("commissions", []) if x["sale_schema"] == "FBS"), None)
    if fbs is not None: c["percent"] = fbs
categories = sorted(({"name": k, **{a: round(b, 2) if isinstance(b, float) else b for a, b in v.items()}} for k, v in cats.items()), key=lambda x: -x["sales"])

# логистика по услугам
dl, dn = defaultdict(float), Counter()
for a in L("accruals")["items"]:
    if a["accrued_category"] == "POSTING":
        for p in a["posting"]["products"]:
            for s in (p.get("delivery") or {}).get("services", []):
                n = types.get(s["type_id"], str(s["type_id"])); dl[n] += float(s["accrued"]["amount"]); dn[n] += 1
logistics = [{"name": k, "sum": round(v, 2), "count": dn[k]} for k, v in sorted(dl.items(), key=lambda x: x[1])]

sales = K["sales"]; comm = sum(r["commission"] for r in P)
delivered = max(K["orders"] - K["cancelled"], 1)
profit_per_order = K["profit_products"] / delivered
late = M["cancel"]["reasons"].get("Вы не отгрузили заказ вовремя", 0)
fines = -(OH.get("DefectFineShipmentDelayRate", 0) + OH.get("DefectFineErrors", 0))
loss = -sum(r["profit"] for r in P if r["units"] > 0 and r["profit"] is not None and r["profit"] < 0)
stars = -M["by_type"].get("StarsMembership", 0); reviews = -OH.get("AcceleratedReviewCollection", 0)
ret_logistics = -next((x["sum"] for x in logistics if x["name"] == "ReturnFlowLogistic"), 0)
ret_cnt = sum(r["returns"] for r in P)
pct = -comm / sales * 100 if sales else 0

S = [
 {"id": "fines", "lever": "Штрафы за просрочки и ошибки", "current": round(fines), "potential": round(fines), "confidence": "высокая",
  "how": "Отгружать в день заказа (график сборки, уведомления, запас времени до дедлайна), проверять комплектность и маркировку перед отправкой.",
  "basis": "Прямой расход: штрафы DefectFineShipmentDelayRate и DefectFineErrors за период."},
 {"id": "late-cancel", "lever": f"Потерянные заказы из-за несвоевременной отгрузки ({late} шт.)", "current": 0, "potential": round(late * profit_per_order),
  "confidence": "средняя", "how": "То же, что со штрафами: успевать с отгрузкой. Товары с медленной сборкой перевести на FBO.",
  "basis": f"{late} заказов × средняя прибыль на заказ {profit_per_order:.0f} ₽ (упущенная прибыль, не расход)."},
 {"id": "loss", "lever": "Убыточные товары", "current": round(loss), "potential": round(loss), "confidence": "высокая",
  "how": "Поднять цену или вывести из продажи товары, где прибыль отрицательная (см. Товары → «убыточные»).", "basis": "Сумма убытков по товарам с продажами."},
 {"id": "paid", "lever": "Платные подписки и услуги (Звёздные товары, ускоренный сбор отзывов)", "current": round(stars + reviews),
  "potential": round((stars + reviews) * 0.5), "confidence": "низкая",
  "how": "Оценить, дают ли они рост заказов. Отключить то, что не окупается; оставить по хитам.", "basis": "Условно берём 50% от расхода: часть услуг может приносить продажи."},
 {"id": "returns", "lever": f"Возвраты ({ret_cnt} шт.): обратная логистика", "current": round(ret_logistics), "potential": round(ret_logistics * 0.5),
  "confidence": "низкая", "how": "Точнее описывать товар (совместимость с моделью авто, размеры, фото), чтобы снизить возвраты «не подошёл».",
  "basis": "Условно −50% возвратов; при возврате комиссия и логистика не возвращаются полностью."},
]
sens = [{"points": p, "gain": round(sales * p / 100)} for p in (2, 5, 10)]
quick = sum(s["potential"] for s in S if s["id"] != "late-cancel")
total = sum(s["potential"] for s in S)
M["savings"] = {"items": S, "commission_pct": round(pct, 1), "commission_sum": round(-comm), "sensitivity": sens,
                "categories": categories, "logistics": logistics,
                "total_potential": total, "expense_only_potential": quick, "current_profit": K["profit_total"],
                "note": "Оценки по данным за 30 дней; факт зависит от действий и объёма продаж. Себестоимость взята из вашей таблицы."}
(ROOT / "data/metrics.json").write_text(json.dumps(M, ensure_ascii=False), encoding="utf-8")
print("total potential", total, "expense-only", quick, "| commission", round(pct, 1), "% =", round(-comm))
for s in S: print(f"  {s['lever'][:60]:60} cur {s['current']:6} pot {s['potential']:6} [{s['confidence']}]")
print("sens", sens)
for c in categories[:5]: print(" ", c["name"][:70], c["percent"], "% sales", c["sales"])
