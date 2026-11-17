"""Отчёт по акциям Ozon: участие, экономика, рекомендации «участвовать / убрать» -> metrics["promos"].
Данные: data/raw/actions.json, actions_detail.json (участники и кандидаты), metrics.json["cards"]["rows"] (комиссия, логистика, себестоимость).
Изменения к предыдущему запуску (например, Ozon вернул товар в акцию автоматически) берутся из data/promo_snapshot.json.
"""
import json, sys
from datetime import date, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

ROOT = Path(__file__).resolve().parent.parent
L = lambda n: json.load(open(ROOT / "data/raw" / f"{n}.json", encoding="utf-8"))
M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
info = {i["id"]: i for i in L("product_info")["items"]}
rows = {r["offer_id"]: r for r in M["cards"]["rows"]}
detail = L("actions_detail")

# пороги рекомендаций (доля от прайса)
DEEP = 0.15       # с такой скидкой и выше почти всегда невыгодно
SOFT = 0.05       # до этой скидки участие безвредно и даёт видимость
MIN_KEEP = 0.7    # прибыль по акции должна быть не ниже 70% прибыли по прайсу


def economics(o, price, aprice):
    r = rows.get(o, {})
    c = (r.get("commission_pct") or 47) / 100; dl = r.get("delivery_unit") or 109; cost = r.get("unit_cost")
    net = lambda p: p * (1 - c) - dl
    pa, pl = net(aprice) - (cost or 0), net(price) - (cost or 0)
    return {"net_list": round(net(price)), "net_action": round(net(aprice)), "profit_list": round(pl) if cost is not None else None,
            "profit_action": round(pa) if cost is not None else None, "has_cost": cost is not None}


def advise_participant(o, price, aprice, mode, boost=None):
    disc = 1 - aprice / price if price else 0
    e = economics(o, price, aprice); units = rows.get(o, {}).get("units", 0)
    if e["profit_action"] is not None and e["profit_action"] < 0:
        return "remove", "Убрать: при этой цене продажа в убыток"
    if disc >= DEEP:
        why = f"скидка {disc*100:.0f}% забирает {e['net_list']-e['net_action']} ₽ с каждой штуки"
        if units <= 3: return "remove", f"Убрать: {why}, продаж за 30 дней всего {units:.0f}"
        if e["profit_list"] and e["profit_action"] < MIN_KEEP * e["profit_list"]: return "remove", f"Убрать: {why}; прибыль на штуке падает более чем на 30%"
        return "check", f"Проверить: {why}. Оставляйте, только если акция реально даёт рост заказов"
    bt = f", буст показов +{boost:.0f}%" if boost else ""
    if disc >= SOFT and boost and boost >= 2.5 * disc * 100: return "keep", f"Оставить: скидка {disc*100:.0f}% (потеря {e['net_list']-e['net_action']} ₽ на штуке){bt}. Буст заметно больше скидки"
    if disc >= SOFT: return "check", f"Проверить: скидка {disc*100:.0f}%, потеря {e['net_list']-e['net_action']} ₽ на штуке{bt}"
    return "keep", "Оставить: скидка небольшая, даёт видимость" + (f" (буст +{boost:.0f}%)" if boost else "")


def advise_candidate(o, price, max_price, action_type, boost=None):
    if not price or not max_price: return "skip", "Нет данных о цене"
    disc = 1 - max_price / price
    e = economics(o, price, max_price)
    if disc <= 0: return "join", "Участвовать: цена акции не ниже вашей"
    if disc >= DEEP: return "skip", f"Не участвовать: скидка до {disc*100:.0f}% слишком глубокая"
    if e["profit_action"] is not None and e["profit_action"] < 0: return "skip", "Не участвовать: продажа в убыток"
    bt = f", буст +{boost:.0f}%" if boost else ""
    if disc <= SOFT: return "join", f"Участвовать: скидка {disc*100:.0f}% почти незаметна, даёт видимость{bt}"
    if boost and disc <= 0.10 and boost >= 2.5 * disc * 100: return "join", f"Участвовать: скидка {disc*100:.0f}% при бусте +{boost:.0f}% (потеря {e['net_list']-e['net_action']} ₽ на штуке)"
    return "maybe", f"На ваше усмотрение: скидка {disc*100:.0f}%, потеря {e['net_list']-e['net_action']} ₽ на штуке{bt}"


# журнал автоочистки за сегодня: эти участия уже удалены после сбора данных, из отчёта о текущем участии исключаем
from datetime import date as _d
cleanup_log = {}
try: cleanup_log = json.load(open(ROOT / "data/promo_cleanup_log.json", encoding="utf-8"))
except Exception: pass
cleaned = cleanup_log.get("removed", []) if cleanup_log.get("date") == _d.today().isoformat() else []
cleaned_keys = {f"{x['offer_id']}|{x['aid']}" for x in cleaned}
actions, part, cand = [], [], []
now = set()
for aid, d in detail.items():
    a = d["action"]; ps = d["products"]; cs = d["candidates"]
    deep = 0
    for p in ps:
        o = info.get(p["id"], {}).get("offer_id", str(p["id"])); price = float(p["price"]); ap = float(p["action_price"])
        if f"{o}|{aid}" in cleaned_keys: now.add(f"{o}|{aid}|c"); continue   # уже убрано автоочисткой
        adv, why = advise_participant(o, price, ap, p.get("add_mode"), p.get("current_boost"))
        e = economics(o, price, ap); deep += adv == "remove"
        part.append({"offer_id": o, "action": a["title"].strip(), "action_id": int(aid), "price": price, "action_price": ap,
                     "discount": round((1 - ap / price) * 100) if price else 0, "mode": p.get("add_mode"), "boost": p.get("current_boost"),
                     "boost_min": p.get("min_boost"), "boost_max": p.get("max_boost"), "advice": adv, "why": why, **e})
        now.add(f"{o}|{aid}")
    for p in cs:
        o = info.get(p["id"], {}).get("offer_id", str(p["id"])); price = float(p["price"]); mp = float(p.get("max_action_price") or 0)
        adv, why = advise_candidate(o, price, mp, a.get("action_type"), p.get("current_boost"))
        cand.append({"offer_id": o, "action": a["title"].strip(), "action_id": int(aid), "price": price, "max_price": mp,
                     "discount": round((1 - mp / price) * 100) if price and mp else 0, "boost": p.get("current_boost"), "advice": adv, "why": why})
    actions.append({"id": int(aid), "title": a["title"].strip(), "type": a.get("action_type"), "start": (a.get("date_start") or "")[:10], "end": (a.get("date_end") or "")[:10],
                    "participating": a.get("is_participating"), "in": len(ps), "potential": len(cs), "remove_advised": deep})

# изменения с прошлого запуска
snap_f = ROOT / "data/promo_snapshot.json"
try: prev = json.load(open(snap_f, encoding="utf-8"))
except Exception: prev = None
changes = {"added": [], "removed": [], "cleaned": [], "since": None}
if prev is not None:
    old = set(prev["items"]); changes["since"] = prev["date"]
    fmt = lambda k: {"offer_id": k.split("|")[0], "action": next((x["title"] for x in actions if str(x["id"]) == k.split("|")[1]), k.split("|")[1])}
    now_c = {k[:-2] for k in now if k.endswith("|c")}; now_real = {k for k in now if not k.endswith("|c")}
    changes["added"] = [fmt(k) for k in sorted((now_real | now_c) - old)]; changes["removed"] = [fmt(k) for k in sorted(old - now_real - now_c)]
    changes["cleaned"] = [{"offer_id": x["offer_id"], "action": x["action"], "discount": x["discount"]} for x in cleaned]
if True:
    snap_f.write_text(json.dumps({"date": date.today().isoformat(), "items": sorted(k for k in now if not k.endswith("|c"))}, ensure_ascii=False), encoding="utf-8")

rm = [p for p in part if p["advice"] == "remove"]; jn = [c for c in cand if c["advice"] == "join"]
avg = round(sum(p["discount"] for p in part) / len(part)) if part else 0
M["promos"] = {"actions": sorted(actions, key=lambda x: -x["in"]), "participation": sorted(part, key=lambda p: (p["advice"] != "remove", -p["discount"])),
               "candidates": sorted(cand, key=lambda c: (c["advice"] != "join", c["offer_id"])), "changes": changes,
               "kpi": {"participations": len(part), "products": len({p["offer_id"] for p in part}), "avg_discount": avg,
                       "remove": len(rm), "remove_products": len({p["offer_id"] for p in rm}), "join": len(jn)},
               "autoclean": {"enabled": True, "threshold": 20, "last": cleanup_log.get("date"), "error": cleanup_log.get("error"), "history": cleanup_log.get("history", [])[-14:]},
               "note": "Рекомендации считаются по вашим себестоимостям, комиссии Ozon и логистике на единицу; эффект акции на объём заказов Ozon не показывает. Буст: на сколько процентов Ozon усиливает показ товара в этой акции (данные Ozon)."}
(ROOT / "data/metrics.json").write_text(json.dumps(M, ensure_ascii=False), encoding="utf-8")
print("promos ok:", M["promos"]["kpi"], "| изменения:", len(changes["added"]), "добавлено,", len(changes["removed"]), "убрано")
