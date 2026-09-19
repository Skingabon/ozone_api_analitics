"""Сбор сырых данных Ozon Seller API за N дней в data/raw/*.json."""
import json, os, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
H = {"Client-Id": os.environ["OZON_SELLER_CLIENT_ID"], "Api-Key": os.environ["OZON_SELLER_API_KEY"]}
BASE = "https://api-seller.ozon.ru"
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
now = datetime.now(timezone.utc)
since = now - timedelta(days=DAYS)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def call(path, body):
    for attempt in range(4):
        r = requests.post(BASE + path, headers=H, json=body, timeout=60)
        if r.status_code == 429:
            time.sleep(2 ** attempt); continue
        if r.status_code != 200:
            return {"_error": r.status_code, "_body": r.text[:300]}
        return r.json()
    return {"_error": 429}


KEEP_ON_ERROR = {"queries", "queries_details", "analytics_data", "analytics_stocks"}   # платная аналитика: при отказе не затираем прошлые данные


def save(name, obj):
    err0 = obj.get("_error") if isinstance(obj, dict) else None
    if err0 and name in KEEP_ON_ERROR and (RAW / f"{name}.json").exists():
        try:
            old = json.loads((RAW / f"{name}.json").read_text(encoding="utf-8"))
            if not (isinstance(old, dict) and old.get("_error")):
                print(f"{name}: ERROR {err0}, оставлены прошлые данные"); return
        except Exception:
            pass
    (RAW / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    err = obj.get("_error") if isinstance(obj, dict) else None
    print(f"{name}: {'ERROR ' + str(err) + ' ' + str(obj.get('_body','')) if err else 'ok'}")


# товары
items, last = [], ""
while True:
    r = call("/v3/product/list", {"filter": {"visibility": "ALL"}, "last_id": last, "limit": 1000})
    if "_error" in r: save("product_list", r); break
    items += r["result"]["items"]; last = r["result"].get("last_id", "")
    if not last or not r["result"]["items"]: break
save("product_list", {"items": items})
pids = [i["product_id"] for i in items]
info = []
for i in range(0, len(pids), 1000):
    r = call("/v3/product/info/list", {"product_id": pids[i:i+1000]})
    info += r.get("items", []) if "_error" not in r else []
save("product_info", {"items": info})
save("category_tree", call("/v1/description-category/tree", {"language": "DEFAULT"}))
save("stocks", call("/v4/product/info/stocks", {"filter": {"visibility": "ALL"}, "last_id": "", "limit": 1000}))
save("prices", call("/v5/product/info/prices", {"filter": {"visibility": "ALL"}, "last_id": "", "limit": 1000}))

# отправления FBO / FBS
def paged_postings(path, key):
    out, offset = [], 0
    while True:
        body = {"dir": "ASC", "filter": {"since": iso(since), "to": iso(now)}, "limit": 1000, "offset": offset,
                "with": {"analytics_data": True, "financial_data": True}}
        r = call(path, body)
        if "_error" in r: return r
        res = r.get("result", r)
        rows = res if isinstance(res, list) else res.get(key, [])
        out += rows
        if len(rows) < 1000: break
        offset += 1000
    return {"items": out}
save("fbo_postings", paged_postings("/v2/posting/fbo/list", "postings"))
save("fbs_postings", paged_postings("/v3/posting/fbs/list", "postings"))

# финансы (v3 transaction устарели -> accrual/balance/cash-flow)
save("accrual_types", call("/v1/finance/accrual/types", {}))
acc = []
for n in range(DAYS + 1):
    day = (since + timedelta(days=n)).strftime("%Y-%m-%d")
    last = None
    while True:
        r = call("/v1/finance/accrual/by-day", {"date": day, **({"last_id": last} if last else {})})
        if "_error" in r: print("accrual", day, r); break
        acc += r.get("accruals", [])
        last = r.get("last_id")
        if not last or not r.get("accruals"): break
save("accruals", {"items": acc})
save("balance", call("/v1/finance/balance", {"date_from": since.strftime("%Y-%m-%d"), "date_to": now.strftime("%Y-%m-%d")}))
save("cash_flow", call("/v1/finance/cash-flow-statement/list", {"date": {"from": iso(since), "to": iso(now)}, "page": 1, "page_size": 100}))

# аналитика (может требовать Premium)
save("analytics_stocks", call("/v1/analytics/stocks", {"skus": [int(i["sources"][0]["sku"]) for i in info if i.get("sources")][:100]}))
save("analytics_data", call("/v1/analytics/data", {"date_from": since.strftime("%Y-%m-%d"), "date_to": now.strftime("%Y-%m-%d"), "metrics": ["revenue", "ordered_units", "hits_view", "hits_tocart"], "dimension": ["sku"], "limit": 1000, "offset": 0}))

# карточки: атрибуты, метаданные категорий, акции, поисковые запросы
pid_list = [str(i["id"]) for i in info]
attrs = call("/v4/product/info/attributes", {"filter": {"product_id": pid_list, "visibility": "ALL"}, "limit": 1000})
save("attributes", attrs)
meta, seen = {}, set()
for a in attrs.get("result", []):
    k = (a["description_category_id"], a["type_id"])
    if k in seen: continue
    seen.add(k)
    r = call("/v1/description-category/attribute", {"description_category_id": k[0], "type_id": k[1], "language": "DEFAULT"})
    meta[f"{k[0]}/{k[1]}"] = {str(x["id"]): {"name": x["name"], "required": x["is_required"]} for x in r.get("result", [])}
save("attr_meta", meta)
acts = requests.get(BASE + "/v1/actions", headers=H, timeout=60).json()
save("actions", acts)
detail = {}
for a in acts.get("result", []):
    p = call("/v1/actions/products", {"action_id": a["id"], "limit": 100, "offset": 0})
    c = call("/v1/actions/candidates", {"action_id": a["id"], "limit": 100, "offset": 0})
    detail[str(a["id"])] = {"action": {k: v for k, v in a.items() if k != "description"},
                            "products": p.get("result", {}).get("products", []), "candidates": c.get("result", {}).get("products", [])}
save("actions_detail", detail)
skus = [str(i["sources"][0]["sku"]) for i in info if i.get("sources")]
QD = {"date_from": since.strftime("%Y-%m-%dT00:00:00Z"), "date_to": now.strftime("%Y-%m-%dT00:00:00Z")}
save("queries", call("/v1/analytics/product-queries", {"skus": skus, **QD, "page": 0, "page_size": 100}))
try:
    mp = json.load(open(ROOT / "data" / "metrics.json", encoding="utf-8"))["products"]
    o2s = {i["offer_id"]: str(i["sources"][0]["sku"]) for i in info if i.get("sources")}
    top = [o2s[p["offer_id"]] for p in mp if p["units"] > 0 and p["offer_id"] in o2s][:8]
except Exception:
    top = skus[:8]
save("queries_details", call("/v1/analytics/product-queries/details", {"skus": top, **QD, "limit_by_sku": 15, "page": 0, "page_size": 100}))

# качество: рейтинг продавца, контент-рейтинг карточек, оборачиваемость, заявки на скидку, компенсации
save("rating_summary", call("/v1/rating/summary", {}))
save("rating_fbs", call("/v1/rating/index/fbs/info", {}))
rh = call("/v1/rating/history", {"date_from": iso(since), "date_to": iso(now), "ratings": ["rating_review_avg_score_total", "rating_shipment_delay_cb"]})
save("rating_history", rh)
cr = []
for i in range(0, len(skus), 100):
    r = call("/v1/product/rating-by-sku", {"skus": skus[i:i + 100]})
    cr += r.get("products", []) if "_error" not in r else []
save("content_rating", {"products": cr})
tv, off = [], 0
while True:
    r = call("/v1/analytics/turnover/stocks", {"limit": 1000, "offset": off})
    if "_error" in r or not r.get("items"): break
    tv += r["items"]; off += 1000
    if len(r["items"]) < 1000: break
save("turnover", {"items": tv})
tasks = {}
for st in ("NEW", "APPROVED", "DECLINED", "AUTO_APPROVED", "AUTO_DECLINED"):
    r = call("/v2/actions/discounts-task/list", {"status": st, "limit": 50})
    tasks[st] = r.get("tasks", []) if "_error" not in r else []
save("discount_tasks", tasks)
comp = {}
for m in range(3):
    d = (now.replace(day=1) - timedelta(days=30 * m)).strftime("%Y-%m")
    comp[d] = {"compensation": call("/v1/finance/compensation", {"date": d, "language": "DEFAULT"}),
               "decompensation": call("/v1/finance/decompensation", {"date": d, "language": "DEFAULT"})}
save("compensation", comp)

# разбор отчётов о компенсациях (без персональных данных): тип, товар, кол-во, сумма
import io
from openpyxl import load_workbook
crows = []
for month, kinds in comp.items():
    for kind, r in kinds.items():
        code = (r.get("result") or {}).get("code") if isinstance(r, dict) else None
        if not code: continue
        for _ in range(8):
            info_r = call("/v1/report/info", {"code": code}); res = info_r.get("result") or {}
            if res.get("status") != "processing": break
            time.sleep(4)
        if res.get("status") != "success" or not res.get("file"): continue
        try:
            ws = load_workbook(io.BytesIO(requests.get(res["file"], timeout=60).content), data_only=True).active
            for row in ws.iter_rows(values_only=True):
                if row[1] and str(row[1]).isdigit() and row[2]:
                    crows.append({"month": month, "kind": kind, "type": row[2], "offer_id": row[4], "qty": row[7], "amount": row[13] if len(row) > 13 else None})
        except Exception as e:
            print("compensation parse", month, kind, e)
save("compensation_rows", {"items": crows})
