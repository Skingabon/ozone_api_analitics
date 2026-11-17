"""ТН ВЭД 8708949909 (части рулевых механизмов, прочие) для втулок рулевой рейки.

  python collector/apply_tnved.py            # проверка
  python collector/apply_tnved.py --apply    # применить
Код выбран по словарю Ozon: 8708 94 910 9 — только штампованные стальные детали, 8708 94 990 9 — прочие (пластик).
Итоговая классификация остаётся за декларантом/таможенным брокером.
"""
import sys, time
import apply_cards as A

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

CODE = "8708949909"
NOT_STEERING = {"Largus-otopitel", "8201052009"}   # крепление мотора печки, заглушка кожуха ГРМ


def main(apply):
    s, r = A.call("/v1/description-category/attribute/values/search",
                  {"attribute_id": 22232, "description_category_id": 17028756, "type_id": 971109202, "value": CODE, "limit": 5})
    hit = next(x for x in r["result"] if x["value"].startswith(CODE))
    print("значение словаря:", hit["id"], hit["value"][:120])
    import json
    cards = json.load(open(A.ROOT / "data/raw/attributes.json", encoding="utf-8"))["result"]
    offers = [c["offer_id"] for c in cards if c["description_category_id"] == 17028756 and c["offer_id"] not in NOT_STEERING]
    live, prices = A.live_cards(offers)
    items = []
    for o in offers:
        it = A.build(live[o], {}, prices[o])
        it["complex_attributes"] = live[o].get("complex_attributes") or []
        it["attributes"] = [a for a in it["attributes"] if a["id"] != 22232] + [
            {"id": 22232, "complex_id": 0, "values": [{"dictionary_value_id": hit["id"], "value": hit["value"]}]}]
        items.append(it)
    print(len(items), "карточек:", ", ".join(offers))
    if not apply: print("DRY-RUN"); return
    s, r = A.call("/v3/product/import", {"items": items}); print("import", s, r)
    if s == 200:
        for i in A.wait(r["result"]["task_id"]):
            if i["status"] != "imported" or i.get("errors"): print(i["offer_id"], i["status"], [e.get("description", "")[:100] for e in i.get("errors", [])])
        time.sleep(5); A.restore_prices(offers, prices)


if __name__ == "__main__":
    main("--apply" in sys.argv)
