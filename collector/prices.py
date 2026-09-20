"""Раздел «Цены на товары»: цены продавца, что платит покупатель, баллы Ozon, автодобавление в акции, безубыточная цена -> metrics["prices"].
Данные: raw/prices.json (v5/product/info/prices), raw/accruals.json (фактические заказы), metrics["cards"]["rows"] (комиссия, логистика, себестоимость)."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L = lambda n: json.load(open(ROOT / "data/raw" / f"{n}.json", encoding="utf-8"))
M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
info = {i["offer_id"]: i for i in L("product_info")["items"]}
sku2o = {int(s["sku"]): i["offer_id"] for i in info.values() for s in (i.get("sources") or [])}
rows = {r["offer_id"]: r for r in M["cards"]["rows"]}
stocks = {r["offer_id"]: r.get("stock", 0) for r in M["products"]}

# фактические заказы: сколько платит покупатель деньгами и сколько закрывает Ozon баллами
buy = defaultdict(lambda: {"n": 0, "seller": 0.0, "paid": 0.0, "points": 0.0})
for a in L("accruals")["items"]:
    if a["accrued_category"] != "POSTING": continue
    for p in a["posting"]["products"]:
        c = p.get("commission")
        if not c: continue
        g = lambda k: float(c[k]["amount"]) if c.get(k) else 0.0
        if g("seller_price") <= 0: continue
        o = sku2o.get(int(p["sku"]))
        b = buy[o]; b["n"] += 1; b["seller"] += g("seller_price"); b["paid"] += g("sale_price"); b["points"] += g("bonus")

try: KEEP_AUTO = set(json.load(open(ROOT / "audit/autoadd_keep.json", encoding="utf-8")))   # автодобавление оставлено намеренно (выгодный буст)
except Exception: KEEP_AUTO = set()

# участие в акциях (для «цена с учётом акций»)
acts = {}
for aid, d in L("actions_detail").items():
    for p in d["products"]:
        o = next((k for k, v in info.items() if v["id"] == p["id"]), None)
        if o: acts.setdefault(o, []).append(float(p["action_price"]))

out = []
for x in L("prices")["items"]:
    o = x["offer_id"]; pr = x["price"]; r = rows.get(o, {}); cm = x.get("commissions", {})
    price = float(pr["price"]); c = (cm.get("sales_percent_fbs") or r.get("commission_pct") or 47) / 100
    dl = r.get("delivery_unit") or 109; cost = r.get("unit_cost")
    net = lambda p: p * (1 - c) - dl
    b = buy.get(o)
    be = (dl + (cost or 0)) / (1 - c)                    # безубыточная цена продавца
    p30 = (dl + (cost or 0)) / (1 - c - 0.30)            # цена для маржи 30%
    eff = min([price] + acts.get(o, []))                 # цена продавца с учётом акций
    notes = []
    if pr.get("auto_add_to_ozon_actions_list_enabled"):
        notes.append("автодобавление в акции оставлено намеренно (выгодный буст)" if o in KEEP_AUTO else "включено автодобавление в акции Ozon: Ozon сам вернёт товар в акции")
    if eff < price * 0.98: notes.append(f"в акциях цена {eff:.0f} ₽ вместо {price:.0f} ₽")
    if cost is not None and price < be: notes.append("цена ниже безубыточной")
    if pr.get("min_price") and float(pr["min_price"]) < price * 0.97: notes.append("минимальная цена ниже вашей: возможны автоскидки")
    out.append({"offer_id": o, "name": (info.get(o) or {}).get("name", ""), "stock": stocks.get(o, 0),
                "price": price, "old_price": float(pr.get("old_price") or 0), "min_price": float(pr.get("min_price") or 0),
                "effective": eff, "auto_add": bool(pr.get("auto_add_to_ozon_actions_list_enabled")), "auto_add_keep": o in KEEP_AUTO, "index": (x.get("price_indexes") or {}).get("color_index"),
                "commission_pct": round(c * 100, 1), "delivery": round(dl), "orders": b["n"] if b else 0,
                "buyer_paid": round(b["paid"] / b["n"]) if b else None, "ozon_points": round(b["points"] / b["n"]) if b else None,
                "seller_price_avg": round(b["seller"] / b["n"]) if b else None,
                "points_share": round(b["points"] / b["seller"] * 100) if b and b["seller"] else None,
                "profit_unit": round(net(eff) - cost) if cost is not None else None, "breakeven": round(be) if cost is not None else None,
                "price_m30": round(p30) if cost is not None else None, "notes": notes})
out.sort(key=lambda r: (-r["orders"], r["offer_id"]))
paid = [r for r in out if r["orders"]]
M["prices"] = {"rows": out, "kpi": {"products": len(out), "auto_add": sum(r["auto_add"] for r in out), "auto_add_unwanted": sum(1 for r in out if r["auto_add"] and not r["auto_add_keep"]),
               "below_breakeven": sum(1 for r in out if "цена ниже безубыточной" in r["notes"]),
               "avg_points_share": round(sum(r["points_share"] for r in paid if r["points_share"] is not None) / max(len([r for r in paid if r["points_share"] is not None]), 1))},
               "note": "«Покупатель платит» и «Баллы Ozon» — средние значения по фактическим заказам за период. Ваша выручка с заказа равна «Вашей цене» (за вычетом комиссии и логистики), баллы за скидки финансирует Ozon."}
(ROOT / "data/metrics.json").write_text(json.dumps(M, ensure_ascii=False), encoding="utf-8")
print("prices ok:", M["prices"]["kpi"])
