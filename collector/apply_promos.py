"""Убрать товары из акций с глубокой автоскидкой (режим AUTO, скидка >= порога) и откат по бэкапу.

  python collector/apply_promos.py              # план (dry-run)
  python collector/apply_promos.py --apply      # применить
  python collector/apply_promos.py --rollback   # вернуть участие из data/backup/actions_before_*.json
Ручные добавления (MANUAL) не трогаются. Бэкап участия пишется перед применением.
"""
import json, sys, time
from datetime import date
from pathlib import Path
import apply_cards as A

ROOT = Path(__file__).resolve().parent.parent
THRESHOLD = 0.20
KEEP = set()   # артикулы, которые не трогаем


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


if __name__ == "__main__":
    main("apply" if "--apply" in sys.argv else "rollback" if "--rollback" in sys.argv else "plan")
