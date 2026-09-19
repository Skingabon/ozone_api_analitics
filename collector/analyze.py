"""Расчёт метрик магазина: data/raw + cost_prices.xlsx -> data/metrics.json."""
import json
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
L = lambda n: json.load(open(ROOT / "data/raw" / f"{n}.json", encoding="utf-8"))
amt = lambda d: float(d["amount"]) if d else 0.0

info = L("product_info")["items"]
sku2offer, offers = {}, {}
for i in info:
    for s in i.get("sources") or []:
        sku2offer[int(s["sku"])] = i["offer_id"]
    offers[i["offer_id"]] = {"offer_id": i["offer_id"], "name": i.get("name", ""), "price": float(i.get("price") or 0)}
stocks = {s["offer_id"]: sum(x["present"] for x in s["stocks"]) for s in L("stocks")["items"]}
types = {t["id"]: t["name"] for t in L("accrual_types")["accrual_types"]}

# себестоимость
cost = {}
for r in load_workbook(ROOT / "cost_prices.xlsx", data_only=True).active.iter_rows(min_row=2, values_only=True):
    if r[0] and r[6] is not None:
        cost[r[0]] = float(r[6]) + float(r[7] or 0)

P = defaultdict(lambda: defaultdict(float))  # offer -> метрики
day = defaultdict(lambda: defaultdict(float))
overhead = Counter()
by_type = Counter()
for a in L("accruals")["items"]:
    cat, d = a["accrued_category"], a["date"]
    if cat == "POSTING":
        for p in a["posting"]["products"]:
            o = sku2offer.get(int(p["sku"]), f"sku{p['sku']}")
            c = p["commission"] or {}
            sale = amt(c.get("sale_amount")); comm = amt(c.get("commission")); dl = amt((p.get("delivery") or {}).get("total_accrued"))
            sign = 1 if sale >= 0 else -1
            q = (p.get("quantity") or 1) * sign
            m = P[o]
            m["units"] += q; m["sales"] += sale; m["commission"] += comm; m["delivery"] += dl
            if sign < 0: m["returns"] += 1
            day[d]["sales"] += sale; day[d]["net"] += sale + comm + dl
            by_type["Комиссия"] += comm; by_type["Логистика и доставка"] += dl
            by_type["Продажи (реализация)"] += sale
    elif cat == "ITEM":
        for it in a["item_fees"]["fees"]:
            o = sku2offer.get(int(it["sku"]), f"sku{it['sku']}")
            for f in it["fees"]:
                v = amt(f["accrued"]); P[o]["item_fees"] += v; by_type[types.get(f["type_id"], str(f["type_id"]))] += v
                day[d]["net"] += v
    else:
        v = amt(a["total_amount"]); n = types.get(a["non_item_fee"]["type_id"], str(a["non_item_fee"]["type_id"]))
        overhead[n] += v; by_type[n] += v; day[d]["net"] += v

rows = []
for o, base in offers.items():
    m = P.get(o, {}); u = m.get("units", 0)
    net = m.get("sales", 0) + m.get("commission", 0) + m.get("delivery", 0) + m.get("item_fees", 0)
    cu = cost.get(o)
    cogs = cu * u if cu is not None else None
    profit = net - cogs if cogs is not None else None
    rows.append({**base, "stock": stocks.get(o, 0), "units": u, "sales": round(m.get("sales", 0), 2),
                 "commission": round(m.get("commission", 0), 2), "delivery": round(m.get("delivery", 0), 2),
                 "item_fees": round(m.get("item_fees", 0), 2), "net_before_cost": round(net, 2),
                 "unit_cost": cu, "cogs": None if cogs is None else round(cogs, 2),
                 "profit": None if profit is None else round(profit, 2),
                 "margin_pct": round(profit / m["sales"] * 100, 1) if profit is not None and m.get("sales", 0) > 0 else None,
                 "commission_pct": round(-m["commission"] / m["sales"] * 100, 1) if m.get("sales", 0) > 0 else None,
                 "returns": int(m.get("returns", 0))})
rows.sort(key=lambda r: -r["sales"])

# отправления: отмены
fbs, fbo = L("fbs_postings")["items"], L("fbo_postings")["items"]
allp = [("FBS", p) for p in fbs] + [("FBO", p) for p in fbo]
cancel = Counter(); cancel_reasons = Counter()
for sch, p in allp:
    if p["status"] == "cancelled":
        cancel[sch] += 1
        cr = p.get("cancellation") or {}
        cancel_reasons[cr.get("cancel_reason") or "не указана"] += 1
orders_day = Counter(p["in_process_at" if "in_process_at" in p else "created_at"][:10] for _, p in allp)

tot_sales = sum(r["sales"] for r in rows)
tot_profit = sum(r["profit"] or 0 for r in rows)
oh = sum(overhead.values())
ratios = [cost[o] / offers[o]["price"] for o in cost if o in offers and offers[o]["price"]]   # архивные товары из таблицы пропускаем
bal = L("balance"); cf = L("cash_flow")["result"]["cash_flows"]
metrics = {
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "kpi": {"orders": len(allp), "cancelled": sum(cancel.values()), "sales": round(tot_sales, 2),
            "profit_products": round(tot_profit, 2), "overhead": round(oh, 2), "profit_total": round(tot_profit + oh, 2),
            "sku_total": len(rows), "sku_sold": sum(1 for r in rows if r["units"] > 0),
            "stock_units": sum(stocks.values()), "closing_balance": bal["total"]["closing_balance"]["value"]},
    "products": rows, "overhead": {k: round(v, 2) for k, v in overhead.items()},
    "by_type": {k: round(v, 2) for k, v in by_type.items()},
    "days": {d: {k: round(v, 2) for k, v in x.items()} for d, x in sorted(day.items())},
    "orders_day": dict(sorted(orders_day.items())),
    "cancel": {"by_schema": dict(cancel), "reasons": dict(cancel_reasons)},
    "cost_ratio": {"min": round(min(ratios), 4), "max": round(max(ratios), 4)} if ratios else None,
    "balance": bal, "cash_flow": cf,
}
(ROOT / "data/metrics.json").write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
print("KPI", json.dumps(metrics["kpi"], ensure_ascii=False))
print("cost/price ratio", metrics["cost_ratio"])
print("overhead", metrics["overhead"]); print("cancel", metrics["cancel"])
for r in rows[:8]:
    print(f"{r['offer_id'][:24]:24} ед{r['units']:4.0f} прод{r['sales']:8.0f} ком{r['commission']:8.0f} дост{r['delivery']:7.0f} проч{r['item_fees']:6.0f} с/с{r['cogs']} приб{r['profit']} марж{r['margin_pct']}%")
