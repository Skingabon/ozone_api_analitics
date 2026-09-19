"""Убрать товары из акций с глубокой автоскидкой (режим AUTO, скидка >= порога) и откат по бэкапу.

  python collector/apply_promos.py              # план (dry-run)
  python collector/apply_promos.py --apply      # применить
  python collector/apply_promos.py --auto       # ежедневная автоочистка (AUTO, скидка >= 20%), журнал data/promo_cleanup_log.json
  python collector/apply_promos.py --rollback   # вернуть участие из data/backup/actions_before_*.json
Ручные добавления (MANUAL) не трогаются. Бэкап участия пишется перед применением.
"""
import json, os, sys, time
from datetime import date
from pathlib import Path
import apply_cards as A

ROOT = Path(__file__).resolve().parent.parent
THRESHOLD = 0.20
KEEP = set()   # артикулы, которые не трогаем (дополняется из audit/promo_keep.json)
MAX_PER_RUN = 60   # защита: не удалять массово за один запуск
LOG = ROOT / "data/promo_cleanup_log.json"


def snapshot():
    acts = A.call("/v1/actions", None)[1] if False else None
    import requests
    acts = requests.get(A.BASE + "/v1/actions", headers=A.H, timeout=60).json()["result"]
    snap = {}
    for a in acts:
        p = A.call("/v1/actions/products", {"action_id": a["id"], "limit": 100, "offset": 0})[1].get("result", {}).get("products", [])
        snap[a["id"]] = {"title": a["title"].strip(), "products": p}
    return snap


def main(mode):
    info = {i["id"]: i for i in json.load(open(ROOT / "data/raw/product_info.json", encoding="utf-8"))["items"]}
    snap = snapshot()
    plan = []
    for aid, d in snap.items():
        for p in d["products"]:
            disc = 1 - p["action_price"] / p["price"] if p["price"] else 0
            o = info.get(p["id"], {}).get("offer_id", p["id"])
            if p.get("add_mode") == "AUTO" and disc >= THRESHOLD and o not in KEEP:
                plan.append((aid, d["title"], p["id"], o, p["price"], p["action_price"], disc))
    for aid, t, pid, o, pr, ap, disc in sorted(plan, key=lambda x: x[3]):
        print(f"{o[:26]:26} {t[:40]:40} {pr:6.0f} → {ap:6.0f} (−{disc*100:.0f}%)")
    print(f"К удалению: {len(plan)} участий, {len({x[3] for x in plan})} товаров")
    if mode == "plan": return
    if mode == "apply":
        bk = ROOT / f"data/backup/actions_before_{date.today().isoformat()}.json"
        bk.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8"); print("бэкап:", bk.name)
        by = {}
        for aid, t, pid, *_ in plan: by.setdefault(aid, []).append(pid)
        for aid, pids in by.items():
            s, r = A.call("/v1/actions/products/deactivate", {"action_id": aid, "product_ids": pids})
            print(aid, s, "удалено", len(r.get("result", {}).get("product_ids", [])), "отклонено", r.get("result", {}).get("rejected"))
    if mode == "rollback":
        bk = sorted((ROOT / "data/backup").glob("actions_before_*.json"))[-1]; old = json.load(open(bk, encoding="utf-8"))
        cur = snapshot()
        for aid, d in old.items():
            have = {p["id"] for p in cur.get(int(aid), cur.get(aid, {"products": []}))["products"]}
            back = [{"product_id": p["id"], "action_price": p["action_price"], "stock": p.get("stock", 0) or 0} for p in d["products"] if p["id"] not in have]
            if back:
                s, r = A.call("/v1/actions/products/activate", {"action_id": int(aid), "products": back}); print(aid, s, str(r)[:150])



def auto():
    """Ежедневная автоочистка: убрать участия режима AUTO со скидкой >= THRESHOLD. Ручные добавления не трогаем. Пишет журнал."""
    try: KEEP.update(json.load(open(ROOT / "audit/promo_keep.json", encoding="utf-8")))
    except Exception: pass
    info = {i["id"]: i for i in json.load(open(ROOT / "data/raw/product_info.json", encoding="utf-8"))["items"]}
    snap = snapshot(); plan = []
    for aid, d in snap.items():
        for p in d["products"]:
            disc = 1 - p["action_price"] / p["price"] if p["price"] else 0
            o = info.get(p["id"], {}).get("offer_id", str(p["id"]))
            if p.get("add_mode") == "AUTO" and disc >= THRESHOLD and o not in KEEP:
                plan.append({"aid": aid, "action": d["title"], "pid": p["id"], "offer_id": o, "price": p["price"], "action_price": p["action_price"], "discount": round(disc * 100)})
    entry = {"date": time.strftime("%Y-%m-%d"), "removed": [], "error": None, "planned": len(plan)}
    if len(plan) > MAX_PER_RUN:
        entry["error"] = f"план {len(plan)} > {MAX_PER_RUN}, автоочистка пропущена"
    elif plan:
        bk = ROOT / "data/backup"; bk.mkdir(parents=True, exist_ok=True)
        (bk / f"actions_before_{time.strftime('%Y-%m-%d')}_auto.json").write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
        by = {}
        for x in plan: by.setdefault(x["aid"], []).append(x["pid"])
        done = set()
        for aid, pids in by.items():
            s, r = A.call("/v1/actions/products/deactivate", {"action_id": int(aid), "product_ids": pids})
            if s == 200: done.update((aid, pid) for pid in r.get("result", {}).get("product_ids", []))
            else: entry["error"] = f"deactivate {aid}: {s}"
        entry["removed"] = [{k: x[k] for k in ("offer_id", "action", "price", "action_price", "discount")} | {"aid": x["aid"]} for x in plan if (x["aid"], x["pid"]) in done]
    hist = []
    try: hist = json.load(open(LOG, encoding="utf-8")).get("history", [])
    except Exception: pass
    LOG.write_text(json.dumps({**entry, "history": (hist + [{"date": entry["date"], "count": len(entry["removed"]), "error": entry["error"]}])[-60:]}, ensure_ascii=False), encoding="utf-8")
    print(f"автоочистка акций: убрано {len(entry['removed'])} из {len(plan)}" + (f" | ОШИБКА: {entry['error']}" if entry["error"] else ""))
    for x in entry["removed"]: print(f"   {x['offer_id']} ← {x['action'][:40]} (−{x['discount']}%)")


if __name__ == "__main__":
    if "--auto" in sys.argv: auto()
    else: main("apply" if "--apply" in sys.argv else "rollback" if "--rollback" in sys.argv else "plan")
