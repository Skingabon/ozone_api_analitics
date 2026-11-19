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

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
H = {"Client-Id": os.environ["OZON_SELLER_CLIENT_ID"], "Api-Key": os.environ["OZON_SELLER_API_KEY"]}
BASE = "https://api-seller.ozon.ru"
BACKUP = ROOT / "data/backup/attributes_before_2026-11-19.json"   # снимок карточек до правки: --rollback вернёт его

BRAND = {"Volkswagen": 58175, "Chery": 58105, "Changan": 58104}
MODEL = {"Tiggo 4 Pro": 971500490, "Tiggo 7 Pro": 971500497, "CS35": 971488369}
DICT_VAL = {  # attr id -> {название: dictionary_value_id}
    22916: {"Volkswagen": 58175, "Chery": 58105, "Changan": 58104, "Renault": 58158},
    22917: {"Tiggo 4 Pro (2020 - по н.в.) Внедорожник": 971500490, "Tiggo 7 Pro, I (2020 - по н.в.) Внедорожник": 971500497,
            "CS35 (2012 - по н.в.) Внедорожник": 971488369,
            "Duster, II (2019 - по н.в.) Внедорожник": 971489266,
            "Duster, II Рестайлинг (2021 - по н.в.) Внедорожник": 971489267},
}

# что менять: offer_id -> {name, "9048" = «Название модели», "11031" = альт. артикулы, 22916/22917 = марка/модель, tags}
# Заголовок на витрине Ozon собирается как «Бренд + Тип + Название модели (9048)», поэтому «ремкомплект»
# пишется и в name, и в 9048. Значения 9048 должны оставаться разными: одинаковые Ozon сливает в одну карточку.
# Хэштеги не перечисляются заново, merge_tags() добавляет новые к существующим и обрезает до 30.
PLAN = {
    "VTRENAULT01": {
        "name": "Ремкомплект рулевой рейки Renault Megane II, Megane III, Scenic, Clio (Рено Меган, Сценик, Клио), втулка усиленная, OEM 7700799093",
        "9048": "Renault Megane II III, Scenic, Clio (ремкомплект рейки, усиленная втулка)",
        "tags": "#ремкомплект_рулевой_рейки #ремкомплект_рейки_меган #втулка_рено #втулка_рено_меган"},
    "6RU423057-PoloSedan": {
        "name": "Ремкомплект рулевой рейки VW Polo Sedan (Поло седан), втулка усиленная, OEM 6RU423057",
        "9048": "Volkswagen Polo Sedan (ремкомплект рейки, втулка 6RU423057)",
        "tags": "#ремкомплект_рулевой_рейки #ремкомплект_рейки_поло #втулка_поло_седан"},
    "VW_TK_POLO": {
        "name": "Ремкомплект рулевой рейки VW Polo Sedan, Skoda Fabia II, Skoda Rapid, прижимная втулка (толкатель), OEM 6RU423057",
        "9048": "Volkswagen Polo Sedan, Skoda Fabia II, Rapid (ремкомплект рейки, прижимная втулка)",
        "11031": "6RU423057, 6RU423057M, 6RU423057L, 6RU423057K, 6RU423057J, SB-6099",
        "tags": "#ремкомплект_рулевой_рейки #skoda_fabia_2 #прижимная_втулка_поло"},
    "Toy_VT_korolla_e140/150": {
        "name": "Ремкомплект рулевой рейки Toyota Corolla E140, E150, Auris (Тойота Королла, Аурис), втулка, OEM HLM00003",
        "9048": "Toyota Corolla E140 E150, Auris (ремкомплект рейки, втулка)",
        "tags": "#ремкомплект_рулевой_рейки #hlm00003 #втулка_королла"},
    "Toy_VT_korolla_e120_e130": {
        "name": "Ремкомплект рулевой рейки Toyota Corolla E120, E130 (Тойота Королла), втулка, OEM L-M6081",
        "9048": "Toyota Corolla E120 E130 (ремкомплект рейки, втулка)",
        "tags": "#ремкомплект_рулевой_рейки #l_m6081 #втулка_королла_е120"},
    "Toy_VT_Camry": {
        "name": "Ремкомплект рулевой рейки Toyota Camry XV50, Highlander, Lexus ES (Тойота Камри, Хайлендер, Лексус), втулка, OEM 7912DL",
        "9048": "Toyota Camry XV50, Highlander, Lexus ES (ремкомплект рейки, втулка)",
        "tags": "#ремкомплект_рулевой_рейки #7912dl #втулка_камри"},
    "Kia_Hyundai_VT/TK": {
        "9048": "Hyundai Solaris, Kia Rio, Soul, Venga (ремкомплект рейки: втулка + толкатель)",
        "tags": "#ремкомплект_рулевой_рейки #втулка_и_толкатель"},
    "VTRENAULT02": {
        "name": "Ремкомплект рулевой рейки Renault Megane II, Megane III, Clio (Рено Меган, Клио), втулка усиленная, OEM 7700799093",
        "9048": "Renault Megane II III, Clio (ремкомплект рейки, втулка усиленная, вариант 2)",
        "tags": "#ремкомплект_рулевой_рейки #рено_меган_3 #ремкомплект_рейки_рено"},
    "Kia_Hyundai_VT": {
        "name": "Ремкомплект рулевой рейки Hyundai Solaris, Kia Rio, Soul, Venga, втулка, OEM 565212K000",
        "9048": "Hyundai Solaris, Kia Rio, Soul, Venga (ремкомплект рейки, только втулка)",
        "tags": "#ремкомплект_рулевой_рейки #565212k000"},
    "Kia_Hyundai_TK": {
        "name": "Ремкомплект рулевой рейки Hyundai Solaris, Kia Rio, прижимная втулка (упор вала, толкатель), OEM 565223X000, 565222K000",
        "9048": "Hyundai Solaris, Kia Rio (ремкомплект рейки, упор вала / толкатель)",
        "tags": "#ремкомплект_рулевой_рейки #прижимная_втулка_солярис"},
    "KiaCeed_vt01": {
        "name": "Ремкомплект рулевой рейки Kia Ceed JD / CD, Cerato, Hyundai i30, Avante (Киа Сид, Серато, Хендай), втулка, OEM 565213X000",
        "9048": "Kia Ceed JD CD, Cerato, Hyundai i30 (ремкомплект рейки, втулка)",
        "tags": "#ремкомплект_рулевой_рейки #hyundai_avante #втулка_киа_сид"},
    "H3_vt03": {
        "name": "Ремкомплект рулевой рейки Hummer H3 (Хаммер Н3), втулка, OEM 15132764, 25861412",
        "9048": "Hummer H3 (ремкомплект рейки, втулка)",
        "tags": "#ремкомплект_рулевой_рейки #втулка_хаммер"},
    "Ch35_vt01": {
        "name": "Ремкомплект рулевой рейки Changan CS35 (Чанган CS35), втулка, полиамид/стекловолокно, OEM S1010560101",
        "9048": "Changan CS35 (ремкомплект рейки, втулка)",
        "7324": "S1010560101", "11031": "3401100W02AC, 3401100W02AB, S1010560101AB"},
    "VT-Hyundai-i40": {
        "name": "Ремкомплект рулевой рейки Hyundai i40, Santa Fe, Sonata VI (Хендай Ай40, Санта Фе, Соната), втулка, OEM 565213Q000",
        "9048": "Hyundai i40, Santa Fe, Sonata VI (ремкомплект рейки, втулка)",
        "tags": "#ремкомплект_рулевой_рейки #втулка_ай40"},
    "VTRenault02_PA": {
        "name": "Ремкомплект рулевой рейки Renault Megane II (Рено Меган 2), Clio, втулка усиленная, наружный диаметр 33 мм, OEM 7700799093",
        "9048": "Renault Megane II, Clio (ремкомплект рейки, втулка PA 33 мм)",
        "tags": "#ремкомплект_рулевой_рейки #ремкомплект_рейки_меган_2"},
    "VTRenault_Duster_PA": {
        "name": "Ремкомплект рулевой рейки Renault Duster II (Рено Дастер 2), втулка усиленная, капрон, OEM 7700799093",
        "9048": "Renault Duster II (ремкомплект рейки, втулка капрон)",
        # Третьего поколения в словаре Ozon нет (просмотрены все 9852 значения атрибута 22917), а вариант
        # «Duster, II (2017 - 2021)» импорт отбрасывает с attribute_hierarchy_fail «значение неактуально».
        "fitment": ("Renault", ["Duster, II (2019 - по н.в.) Внедорожник",
                                "Duster, II Рестайлинг (2021 - по н.в.) Внедорожник"]),
        "tags": "#ремкомплект_рулевой_рейки #втулка_дастер #ремкомплект_рейки_дастер #рено_дастер_2 #renault_duster_2"},
    "Chery Tigo 4 PRO_VT": {
        "name": "Ремкомплект рулевой рейки Chery Tiggo 4 Pro (Чери Тигго 4 Про), втулка усиленная, капрон/полиамид, OEM CY9001KIT-PST",
        "9048": "Chery Tiggo 4 Pro (ремкомплект рейки, втулка усиленная)"},
    "TK_CheryTigo4PRO": {   # толкатель, не втулка — «ремкомплект» в название не пишем
        "name": "Толкатель рулевой рейки Chery Tiggo 4 Pro (Чери Тигго 4 Про), полиамид, OEM 201000094AA",
        "7324": "201000094AA", "11031": "S201000094AA",
        "tags": "#толкатель_тигго_4_про #201000094aa #упор_вала_тигго"},
    "KiaHyundai_Origin": {
        "name": "Ремкомплект рулевой рейки Hyundai Solaris, Kia Rio, Soul, Venga, втулка, OEM 565551Y600",
        "9048": "Hyundai Solaris, Kia Rio, Soul, Venga (ремкомплект рейки, втулка 565551Y600)",
        "tags": "#ремкомплект_рулевой_рейки #hyundai_solaris #kia_rio #565551y600"},
    "Changan-cs35-Plus": {
        "name": "Ремкомплект рулевой рейки Changan CS35 Plus (Чанган CS35 Плюс), втулка, OEM S111F260401-0100",
        "9048": "Changan CS35 Plus (ремкомплект рейки, втулка)",
        "tags": "#ремкомплект_рулевой_рейки #cs35_plus #втулка_cs35_плюс"},
    "VTTK_GeelyAtlas": {
        "name": "Ремкомплект рулевой рейки Geely Atlas (Джили Атлас), втулка и толкатель, усиленные, капролон (полиамид), OEM 4036004200",
        "9048": "Geely Atlas (ремкомплект рейки: втулка и толкатель)",
        "7324": "4036004200"},
    "VT_CheryTigg07pro": {
        "name": "Ремкомплект рулевой рейки Chery Tiggo 7 Pro / Pro Max (Чери Тигго 7 Про), втулка усиленная, внутренний диаметр 26 мм, OEM 201000167AA",
        "9048": "Chery Tiggo 7 Pro / Pro Max (ремкомплект рейки, втулка 26 мм)",
        "7324": "201000167AA", "11031": "201000094AA"},
    "vt_ChanganCS35_reika": {
        "name": "Ремкомплект рулевой рейки Changan CS35 (Чанган CS35), втулка под пыльник, полиамид, OEM S1010560101",
        "9048": "Changan CS35 (ремкомплект рейки, втулка под пыльник)",
        "7324": "S1010560101", "11031": "3401100W02AC, 3401100W02AB, S1010560101AB",
        "tags": "#ремкомплект_рулевой_рейки #ремкомплект_рейки_cs35 #втулка_чанган_cs35"},
}


TIMEOUT = (10, 60)   # (connect, read), как в collect.py: SYN до api-seller.ozon.ru теряются регулярно, а 60 с на connect делали каждую неудачу минутной


def call(path, body, method="POST"):
    """Возвращает (status_code, json). Повторяет на обрыв связи и на 429/5xx, те же 4 попытки с паузами 1/2/4 с,
    что и call() в collect.py. Повтор безопасен и для изменяющих вызовов: import, activate и deactivate
    идемпотентны по offer_id/product_id. Наружу всегда отдаётся кортеж: исключение не рвёт ежедневный прогон."""
    last = (599, {"_error": "нет ответа"})
    for attempt in range(4):
        try:
            r = requests.request(method, BASE + path, headers=H, json=body, timeout=TIMEOUT)
        except requests.RequestException as e:
            last = (599, {"_error": f"{type(e).__name__}: {e}"[:300]})
        else:
            if r.status_code == 429 or r.status_code >= 500:
                last = (r.status_code, {"_error": f"HTTP {r.status_code}", "_body": r.text[:300]})
            else:
                try:
                    return r.status_code, r.json() if r.text else {}
                except ValueError:
                    return r.status_code, {"_body": r.text[:300]}   # 502 от чужого прокси приходит HTML'ом
        if attempt < 3: time.sleep(2 ** attempt)
    return last


def merge_tags(new, old):
    out = []
    for t in (new + " " + old).split():
        if not t.startswith("#"): continue
        if sum(c.isdigit() for c in t) > 9:   # Ozon BR_hashtag_too_much_numbers: «укажите не больше 9 цифр», иначе импорт карточки отклоняется целиком
            print(f"    хэштег отброшен (>9 цифр, Ozon его не принимает): {t}")
            continue
        if t.lower() not in [x.lower() for x in out]: out.append(t)
    return " ".join(out[:30])


def setv(attrs, aid, value, dict_id=None):
    attrs[:] = [a for a in attrs if a["id"] != aid]
    v = {"value": value}
    if dict_id: v["dictionary_value_id"] = dict_id
    attrs.append({"id": aid, "complex_id": 0, "values": [v]})


def normalize_complex(cx):
    """Ozon отдаёт блок «Применимость» (complex 100003) плоским списком значений, а принимает строками
    {"attributes":[марка, модель]}. Плоская отправка блок сбрасывает, конвертируем."""
    flat = [c for c in cx if c.get("complex_id") == 100003 and "id" in c]
    rest = [c for c in cx if not (c.get("complex_id") == 100003 and "id" in c)]
    brands = next((c["values"] for c in flat if c["id"] == 22916), [])
    models = next((c["values"] for c in flat if c["id"] == 22917), [])
    rows = [{"attributes": [{"complex_id": 100003, "id": 22916, "values": [b]}, {"complex_id": 100003, "id": 22917, "values": [m]}]}
            for b, m in zip(brands, models)]
    return rest + rows


def build(card, plan, price):
    attrs = json.loads(json.dumps(card["attributes"]))
    old_tags = next((a["values"][0]["value"] for a in attrs if a["id"] == 23171), "")
    if "tags" in plan: setv(attrs, 23171, merge_tags(plan["tags"], old_tags))
    for aid in (9048, 11031, 7324):   # свободный текст: «Название модели», альтернативные артикулы, OEM-номер
        if str(aid) in plan: setv(attrs, aid, plan[str(aid)])
    for aid in (22916, 22917):
        if aid in plan: setv(attrs, aid, plan[aid], DICT_VAL[aid][plan[aid]])
    item = {"offer_id": card["offer_id"], "description_category_id": card["description_category_id"], "type_id": card["type_id"],
            "name": plan.get("name", card["name"]), "attributes": attrs, "images": card.get("images") or [], "primary_image": card.get("primary_image") or "",
            "height": card["height"], "depth": card["depth"], "width": card["width"], "dimension_unit": card["dimension_unit"],
            "weight": card["weight"], "weight_unit": card["weight_unit"], "complex_attributes": normalize_complex(card.get("complex_attributes") or []),
            "price": price["price"], "old_price": price["old_price"] or "0", "currency_code": "RUB"}
    if card.get("barcode"): item["barcode"] = card["barcode"]
    if card.get("color_image"): item["color_image"] = card["color_image"]
    if card.get("pdf_list"): item["pdf_list"] = card["pdf_list"]
    if "fitment" in plan:   # блок «Применимость»: строка на каждую модель, марка в каждой строке повторяется
        brand, models = plan["fitment"]
        item["complex_attributes"] += [{"attributes": [
            {"complex_id": 100003, "id": 22916, "values": [{"dictionary_value_id": DICT_VAL[22916][brand], "value": brand}]},
            {"complex_id": 100003, "id": 22917, "values": [{"dictionary_value_id": DICT_VAL[22917][m], "value": m}]}]}
            for m in models]
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
    co, cn = len(old.get("complex_attributes") or []), len(new.get("complex_attributes") or [])
    if co != cn: print(f"  применимость: строк {co} → {cn}")


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
