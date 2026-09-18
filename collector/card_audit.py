"""Аудит карточек, экономика акций и рекомендации -> metrics["cards"] (после analyze.py)."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L = lambda n: json.load(open(ROOT / "data/raw" / f"{n}.json", encoding="utf-8"))
M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
C = json.load(open(ROOT / "audit/cards_content.json", encoding="utf-8"))
P = {r["offer_id"]: r for r in M["products"]}
info = {i["offer_id"]: i for i in L("product_info")["items"]}
attrs = {a["offer_id"]: a for a in L("attributes")["result"]}
meta = L("attr_meta")
pid2o = {i["id"]: o for o, i in info.items()}

# участие в акциях
acts = defaultdict(list)
for aid, d in L("actions_detail").items():
    for p in d["products"]:
        o = pid2o.get(p["id"])
        if o: acts[o].append({"action": d["action"]["title"].strip(), "price": p["action_price"], "mode": p.get("add_mode")})

# логистика на единицу (медиана по товарам с продажами), комиссия по умолчанию 47
dl = sorted(-r["delivery"] / r["units"] for r in P.values() if r["units"] > 0 and r["delivery"])
med_delivery = dl[len(dl) // 2] if dl else 100
KEY = {"Марка", "Модель", "Модификация", "OEM-номер", "Вид запчасти", "Альтернативные артикулы товара"}

rows = []
for o, i in info.items():
    r = P.get(o, {}); a = attrs.get(o, {})
    price = float(i.get("price") or 0)
    ap = acts.get(o, [])
    low = min((x["price"] for x in ap), default=None)
    pct = r.get("commission_pct") or next((x["percent"] for x in i.get("commissions", []) if x["sale_schema"] == "FBS"), 47)
    dpu = (-r["delivery"] / r["units"]) if r.get("units", 0) > 0 and r.get("delivery") else med_delivery
    net = lambda pr: pr * (1 - pct / 100) - dpu
    cu = r.get("unit_cost")
    at = a.get("attributes", [])
    m = meta.get(f"{a.get('description_category_id')}/{a.get('type_id')}", {})
    filled = {str(x["id"]) for x in at}
    names_missing = [v["name"] for k, v in m.items() if k not in filled and v["name"] in KEY]
    tags = next((x["values"][0]["value"] for x in at if x["id"] == 23171), "")
    desc = next((x["values"][0]["value"] for x in at if x["id"] == 4191), "")
    photos = len(a.get("images") or []) + (1 if a.get("primary_image") else 0)
    ntags = len([t for t in tags.split() if t.startswith("#")])
    score = 100
    score -= min(30, len(names_missing) * 6)
    score -= 15 if ntags < 8 else 0
    score -= 10 if photos < 5 else 0
    score -= 10 if len(desc) < 700 else 0
    score -= 10 if len(i.get("name", "")) < 40 else 0
    score -= 5   # нет видео
    rows.append({"offer_id": o, "name": i.get("name", ""), "units": r.get("units", 0), "sales": r.get("sales", 0),
                 "stock": r.get("stock", 0), "list_price": price, "action_low": low, "discount_pct": round((1 - low / price) * 100) if low and price else None,
                 "actions": ap, "commission_pct": pct, "delivery_unit": round(dpu), "unit_cost": cu,
                 "net_list": round(net(price)), "net_action": round(net(low)) if low else None,
                 "profit_list": round(net(price) - cu) if cu is not None else None, "profit_action": round(net(low) - cu) if low and cu is not None else None,
                 "photos": photos, "hashtags": ntags, "desc_len": len(desc), "missing_key": names_missing, "score": max(score, 0),
                 "name_len": len(i.get("name", "")), "rating": None})
rows.sort(key=lambda x: (-x["sales"], -x["stock"]))

q = L("queries").get("items", [])
qd = defaultdict(list)
for e in L("queries_details").get("queries", []):
    qd[str(e["sku"])].append({"q": e["query"], "users": e["unique_search_users"]})
o2s = {o: str(i["sources"][0]["sku"]) for o, i in info.items() if i.get("sources")}
for r in rows:
    r["queries"] = qd.get(o2s.get(r["offer_id"], ""), [])[:8]
    r["search_users"] = next((x["unique_search_users"] for x in q if x["offer_id"] == r["offer_id"]), None)

M["cards"] = {"rows": rows, "systemic": C["systemic"], "competitors": C["competitors"], "content": C["cards"],
              "actions_advice": C["actions_advice"], "checked_at": C["checked_at"], "median_delivery": round(med_delivery)}
(ROOT / "data/metrics.json").write_text(json.dumps(M, ensure_ascii=False), encoding="utf-8")
print("cards audit ok:", len(rows), "товаров; в акциях:", sum(1 for r in rows if r["actions"]))
for r in rows[:6]:
    print(f"{r['offer_id'][:24]:24} скор {r['score']:3} | прайс {r['list_price']:.0f} → акц {r['action_low']} ({r['discount_pct']}%) | чист/ед: прайс {r['net_list']} акц {r['net_action']} | приб/ед: {r['profit_list']} / {r['profit_action']} | ком {r['commission_pct']}% | нет: {r['missing_key']}")
