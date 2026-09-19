"""Полное оформление VTTK_GeelyAtlas: название, хэштеги, описание, единая строка подбора."""
import sys, time
import apply_cards as A
import apply_texts as T

O = "VTTK_GeelyAtlas"
NAME = "Втулка и толкатель рулевой рейки Geely Atlas (Джили Атлас), усиленные, капролон (полиамид)"
TAGS = ("#втулка_рулевой_рейки #толкатель_рулевой_рейки #geely_atlas #джили_атлас #ремкомплект_рулевой_рейки #рулевая_рейка_geely "
        "#рулевая_рейка_джили_атлас #втулка_geely_atlas #сайлентблок_рулевой_рейки #усиленная_втулка #втулка")
TEXT = T.auto(
    "<b>Втулка и толкатель рулевой рейки Geely Atlas.</b> Усиленная деталь без резиновых вставок, конструкция доработана по замечаниям мастеров сервисов.",
    T.SYMPTOMS,
    ["Geely Atlas (первое поколение, с 2016 г.)"],
    ["втулка рулевой рейки", "толкатель"],
    ["внутренний диаметр: 27 мм", "высота: 18 мм", "толщина стенки: 4,1 мм",
     "материал: капролон (полиамид), стоек к разбавленным кислотам и щелочам, растворам солей, мылам, маслам и спиртам"],
    "Для ремонта достаточно этого комплекта: втулка и толкатель. Рейку нужно снять, разобрать и очистить от остатков старой втулки.",
    ["Производится на нашем оборудовании"],
    [("Нужно ли что-то ещё для ремонта?", "Нет, в комплекте втулка и толкатель."),
     ("Как понять, что деталь подойдёт?", T.COMPAT_HOW)],
    "ремкомплект рулевой рейки Geely Atlas, втулка рейки Джили Атлас, толкатель рулевой рейки, усиленная втулка.")
# сроки и температуру для этой карточки владелец не подтверждал, поэтому их здесь нет
TEXT = TEXT.replace("<li>Подтверждённый срок эксплуатации — 2 года</li>", "")


def main(apply):
    live, prices = A.live_cards([O]); card = live[O]
    it = A.build(card, {"name": NAME}, prices[O])
    A.setv(it["attributes"], 4180, NAME)
    A.setv(it["attributes"], 4191, TEXT); A.setv(it["attributes"], 23171, TAGS)
    cx = [c for c in it["complex_attributes"] if not any(x.get("complex_id") == 100003 for x in c.get("attributes", []))]
    cx.append({"attributes": [{"complex_id": 100003, "id": 22916, "values": [{"dictionary_value_id": 58119, "value": "Geely"}]},
                              {"complex_id": 100003, "id": 22917, "values": [{"dictionary_value_id": 971484999, "value": "Atlas, I (2016 - по н.в.) Внедорожник"}]}]})
    it["complex_attributes"] = cx
    print(NAME, "|", len(TEXT), "симв. |", len(TAGS.split()), "тегов")
    if not apply: print("DRY-RUN"); return
    s, r = A.call("/v3/product/import", {"items": [it]}); print("import", s)
    for i in A.wait(r["result"]["task_id"]): print(i["offer_id"], i["status"], [e.get("description", "")[:100] for e in i.get("errors", [])])
    time.sleep(5); A.restore_prices([O], prices)


if __name__ == "__main__":
    main("--apply" in sys.argv)
