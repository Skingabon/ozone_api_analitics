"""Материал резинки (резина) и ТН ВЭД для мешалки Hitachi и резинки для термоса.

  python collector/apply_mat_tn.py [--apply]
Мешалка: 8516900000 (части электронагревательных приборов; хлебопечки = 8516 60 900 0).
Резинка: 9617000009 (части термосов, кроме стеклянных колб); «Резина» в словаре «Материал корпуса» отсутствует,
поэтому атрибут очищается, материал указан в названии/описании.
"""
import sys, time
import apply_cards as A
import apply_texts as T


def tn(cat, typ, code):
    s, r = A.call("/v1/description-category/attribute/values/search", {"attribute_id": 22232, "description_category_id": cat, "type_id": typ, "value": code, "limit": 5})
    return next(x for x in r["result"] if x["value"].startswith(code))


def main(apply):
    offers = ["Lopatka_Hitachi_10/8.5", "Uplotnitel_50"]
    live, prices = A.live_cards(offers)
    items = []
    for o in offers:
        it = A.build(live[o], {}, prices[o])
        if o == "Uplotnitel_50":
            v = tn(17027928, 99447, "9617000009")
            it["name"] = T.UPL_NAME; A.setv(it["attributes"], 4180, T.UPL_NAME)
            A.setv(it["attributes"], 4191, T.TEXTS[o]); A.setv(it["attributes"], 23171, T.UPL_TAGS)
            it["attributes"] = [a for a in it["attributes"] if a["id"] != 22011]
        else:
            v = tn(53968796, 970667753, "8516900000")
        A.setv(it["attributes"], 22232, v["value"], v["id"])
        print(o, "→", v["value"][:70]); items.append(it)
    if not apply: print("DRY-RUN"); return
    s, r = A.call("/v3/product/import", {"items": items}); print("import", s, r)
    if s == 200:
        for i in A.wait(r["result"]["task_id"]): print(i["offer_id"], i["status"], [e.get("description", "")[:100] for e in i.get("errors", [])])
        time.sleep(5); A.restore_prices(offers, prices)


if __name__ == "__main__":
    main("--apply" in sys.argv)
