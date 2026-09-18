"""Применение правок к карточкам Ozon через /v3/product/import.

  python collector/apply_cards.py                # проверка (dry-run): показывает изменения
  python collector/apply_cards.py --apply OFFER  # применить к одному или нескольким offer_id
  python collector/apply_cards.py --rollback OFFER  # вернуть атрибуты из бэкапа

Все прочие атрибуты карточки передаются как есть (из /v4/product/info/attributes), цена не меняется.
"""
import json, os, sys, time
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
H = {"Client-Id": os.environ["OZON_SELLER_CLIENT_ID"], "Api-Key": os.environ["OZON_SELLER_API_KEY"]}
BASE = "https://api-seller.ozon.ru"
BACKUP = ROOT / "data/backup/attributes_before_2026-09-18.json"

BRAND = {"Volkswagen": 58175, "Chery": 58105, "Changan": 58104}
MODEL = {"Tiggo 4 Pro": 971500490, "Tiggo 7 Pro": 971500497, "CS35": 971488369}
DICT_VAL = {  # attr id -> {название: dictionary_value_id}
    22916: {"Volkswagen": 58175, "Chery": 58105, "Changan": 58104},
    22917: {"Tiggo 4 Pro (2020 - по н.в.) Внедорожник": 971500490, "Tiggo 7 Pro, I (2020 - по н.в.) Внедорожник": 971500497,
            "CS35 (2012 - по н.в.) Внедорожник": 971488369},
}

# что менять: offer_id -> {name, model_name(9048), brand, model, alt(11031), hashtags}
PLAN = {
    "Chery Tigo 4 PRO_VT": {
        "name": "Втулка рулевой рейки Chery Tiggo 4 Pro (Чери Тигго 4 Про), усиленная, капрон/полиамид, OEM CY9001KIT-PST",
        "9048": "Chery Tiggo 4 Pro (втулка усиленная)", 22916: "Chery", 22917: "Tiggo 4 Pro (2020 - по н.в.) Внедорожник",
        "tags": "#втулка_рулевой_рейки #чери_тигго_4_про #chery_tiggo_4_pro #ремкомплект_рулевой_рейки #усиленная_втулка #cy9001kit_pst #рулевая_рейка_чери #капроновая_втулка #сайлентблок_рулевой_рейки"},
    "VT_CheryTigg07pro": {
        "name": "Втулка рулевой рейки Chery Tiggo 7 Pro / Pro Max (Чери Тигго 7 Про), внутренний диаметр 26 мм, усиленная",
        "9048": "Chery Tiggo 7 Pro (втулка 26 мм)", 22916: "Chery", 22917: "Tiggo 7 Pro, I (2020 - по н.в.) Внедорожник",
        "tags": "#втулка_рулевой_рейки #чери_тигго_7_про #chery_tiggo_7_pro #тигго_7_про_макс #ремкомплект_рулевой_рейки #сайлентблок_рулевой_рейки #рулевая_рейка_чери #втулка_чери_тигго #chery_tiggo_7_pro_max"},
    "Ch35_vt01": {
        "name": "Втулка рулевой рейки Changan CS35 (Чанган CS35), OEM S111F260401-0100, полиамид/стекловолокно",
        "9048": "Changan CS35 (втулка рулевой рейки)", 22916: "Changan", 22917: "CS35 (2012 - по н.в.) Внедорожник",
        "tags": "#втулка_рулевой_рейки #чанган_cs35 #changan_cs35 #ремкомплект_рулевой_рейки #s111f260401_0100 #рулевая_рейка_чанган #сайлентблок_рулевой_рейки #втулка_рейки_cs35"},
    "Polo-sedan": {
        "name": "Ремкомплект рулевой рейки Volkswagen Polo Sedan (втулка и толкатель), OEM 6RU423057N, усиленный",
        "9048": "Volkswagen Polo Sedan (ремкомплект 6RU423057N)", 22916: "Volkswagen",
        "11031": "6RU423057, 6RU423057M, 6RU423057L, 6RU423057K, 6RU423057J, SB-6099",
        "tags": "#втулка_рулевой_рейки #ремкомплект_рулевой_рейки #поло_седан #volkswagen_polo #polo_sedan #6ru423057 #6ru423057n #толкатель_рулевой_рейки #упорная_втулка #рулевая_рейка_поло #втулка_рейки_поло_седан #фольксваген_поло"},
    "Lopatka_Hitachi_10/8.5": {  # карточка работает, меняем только хэштеги
        "tags": "#мешалка_для_хлебопечки #лопатка_для_хлебопечки #тестомес #hitachi_hb_b301 #hitachi_hb_e303 #hitachi_hb_c103 #запчасти_для_хлебопечки #лопатка_hitachi"},
    "Uplotnitel_50": {
        "name": "Уплотнительная силиконовая резинка для крышки термоса и бутылки, диаметр 50 мм, 1 шт.",
        "tags": "#резинка_для_термоса #уплотнитель_для_термоса #прокладка_крышки_термоса #силиконовое_кольцо #уплотнительное_кольцо_50_мм #крышка_термоса #резинка_для_крышки"},
}


def call(path, body):
    r = requests.post(BASE + path, headers=H, json=body, timeout=60)
    return r.status_code, r.json() if r.text else {}


def merge_tags(new, old):
    out = []
    for t in (new + " " + old).split():
        if t.startswith("#") and t.lower() not in [x.lower() for x in out]: out.append(t)
    return " ".join(out[:30])


def setv(attrs, aid, value, dict_id=None):
    attrs[:] = [a for a in attrs if a["id"] != aid]
    v = {"value": value}
    if dict_id: v["dictionary_value_id"] = dict_id
    attrs.append({"id": aid, "complex_id": 0, "values": [v]})


def build(card, plan, price):
    attrs = json.loads(json.dumps(card["attributes"]))
    old_tags = next((a["values"][0]["value"] for a in attrs if a["id"] == 23171), "")
    if "tags" in plan: setv(attrs, 23171, merge_tags(plan["tags"], old_tags))
    if "9048" in plan: setv(attrs, 9048, plan["9048"])
    if "11031" in plan: setv(attrs, 11031, plan["11031"])
    for aid in (22916, 22917):
        if aid in plan: setv(attrs, aid, plan[aid], DICT_VAL[aid][plan[aid]])
    item = {"offer_id": card["offer_id"], "description_category_id": card["description_category_id"], "type_id": card["type_id"],
            "name": plan.get("name", card["name"]), "attributes": attrs, "images": card.get("images") or [], "primary_image": card.get("primary_image") or "",
            "height": card["height"], "depth": card["depth"], "width": card["width"], "dimension_unit": card["dimension_unit"],
            "weight": card["weight"], "weight_unit": card["weight_unit"], "complex_attributes": card.get("complex_attributes") or [],
            "price": price["price"], "old_price": price["old_price"] or "0", "currency_code": "RUB"}
    if card.get("barcode"): item["barcode"] = card["barcode"]
    if card.get("color_image"): item["color_image"] = card["color_image"]
    if card.get("pdf_list"): item["pdf_list"] = card["pdf_list"]
    return item


def live_cards(offers):
    s, r = call("/v3/product/info/list", {"offer_id": offers})
    prices = {i["offer_id"]: {"price": i["price"], "old_price": i["old_price"], "min_price": i["min_price"]} for i in r["items"]}
    ids = {i["offer_id"]: str(i["id"]) for i in r["items"]}
    s, r = call("/v4/product/info/attributes", {"filter": {"offer_id": offers, "visibility": "ALL"}, "limit": 100})
    return {c["offer_id"]: c for c in r["result"]}, prices


def show(offer, old, new):
    print(f"\n== {offer}")
    if old["name"] != new["name"]: print("  название:", old["name"], "\n        →", new["name"])
    o = {a["id"]: a["values"][0]["value"] for a in old["attributes"]}
    n = {a["id"]: a["values"][0]["value"] for a in new["attributes"] if a["values"]}
    for k in sorted(set(o) | set(n)):
        if o.get(k) != n.get(k) and k != 11254: print(f"  атрибут {k}: {str(o.get(k))[:70]!r} → {str(n.get(k))[:110]!r}")


def restore_prices(offers, prices):
    """import обнуляет old_price/min_price: возвращаем значения, что были до правки."""
    body = {"prices": [{"offer_id": o, "price": prices[o]["price"].split(".")[0], "old_price": (prices[o]["old_price"] or "0").split(".")[0],
                        "min_price": (prices[o]["min_price"] or "0").split(".")[0], "currency_code": "RUB"} for o in offers]}
    s, r = call("/v1/product/import/prices", body)
    print("prices restore", s, json.dumps(r, ensure_ascii=False)[:300])


def wait(task):
    for _ in range(20):
        time.sleep(3)
        s, r = call("/v1/product/import/info", {"task_id": task})
        items = r.get("result", {}).get("items", [])
        if items and all(i["status"] not in ("pending", "processing") for i in items): return items
    return items


if __name__ == "__main__":
    args = sys.argv[1:]
    mode = "dry"
    if args and args[0] in ("--apply", "--rollback"): mode, args = args[0][2:], args[1:]
    offers = args or list(PLAN)
    if mode == "rollback":
        old = {c["offer_id"]: c for c in json.load(open(BACKUP, encoding="utf-8"))["result"]}
        cards, prices = live_cards(offers)
        items = [build(old[o], {}, prices[o]) for o in offers]
        for it, o in zip(items, offers): it["name"] = old[o]["name"]
        s, r = call("/v3/product/import", {"items": items}); print("rollback", s, r)
        if s == 200:
            [print(i["offer_id"], i["status"], i.get("errors")) for i in wait(r["result"]["task_id"])]
            time.sleep(5); restore_prices(offers, prices)
        sys.exit()
    cards, prices = live_cards(offers)
    items = []
    for o in offers:
        it = build(cards[o], PLAN[o], prices[o]); show(o, cards[o], it); items.append(it)
    if mode == "apply":
        s, r = call("/v3/product/import", {"items": items}); print("\nimport", s, json.dumps(r, ensure_ascii=False)[:300])
        if s == 200:
            for i in wait(r["result"]["task_id"]): print(i["offer_id"], i["status"], json.dumps(i.get("errors"), ensure_ascii=False)[:400])
            time.sleep(5); restore_prices(offers, prices)
    else:
        print("\nDRY-RUN: ничего не изменено. Для применения: --apply <offer_id>")
