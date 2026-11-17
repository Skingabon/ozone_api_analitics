"""Подбор по авто (комплексный атрибут «Применимость», complex_id 100003) и ТН ВЭД.

  python collector/apply_fit.py            # проверка (dry-run)
  python collector/apply_fit.py --apply    # применить ко всем из плана

Марка/Модель — строки составного блока: одна строка = одна модификация авто. Регулярки выбирают строки
справочника Ozon по названию поколения из карточки. ТН ВЭД берётся из карточек той же марки, иначе из
большинства карточек рулевых втулок (8703101100).
"""
import json, re, sys, time
from pathlib import Path
import apply_cards as A

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

ROOT = Path(__file__).resolve().parent.parent
CX = 100003           # complex_id блока «Применимость»
TN_ID = 22232

BR = {"Volkswagen": 58175, "Skoda": 58166, "Chery": 58105, "Changan": 58104, "Hyundai": 58126, "Kia": 58134, "Hummer": 58125,
      "Geely": 58119, "Toyota": 58174, "Renault": 58158}

POLO = ("Volkswagen", "Polo", r"^Polo, V Рестайлинг \(2014 - 2020\) Седан$")
FIT = {
    "Polo-sedan": [POLO], "6RU423057-PoloSedan": [POLO],
    "VW_TK_POLO": [POLO, ("Skoda", "Fabia", r"^Fabia, II( Рестайлинг)? \("), ("Skoda", "Rapid", r"^Rapid, I( Рестайлинг)? \(")],
    "Chery Tigo 4 PRO_VT": [("Chery", "Tiggo 4 Pro", r"^Tiggo 4 Pro \(")],
    "TK_CheryTigo4PRO": [("Chery", "Tiggo 4 Pro", r"^Tiggo 4 Pro \(")],
    "VT_CheryTigg07pro": [("Chery", "Tiggo 7 Pro", r"^Tiggo 7 Pro( Max|,)")],
    "Ch35_vt01": [("Changan", "CS35", r"^CS35 \(2012")],
    "vt_ChanganCS35_reika": [("Changan", "CS35", r"^CS35 \(2012")],
    "Changan-cs35-Plus": [("Changan", "CS35", r"^CS35PLUS")],
    "VT-Hyundai-i40": [("Hyundai", "i40", r"^i40, I "), ("Hyundai", "Santa Fe", r"^Santa Fe, III"), ("Hyundai", "Sonata", r"^Sonata, VI \(YF\)")],
    "H3_vt03": [("Hummer", "H3", r"^H3 \(2005")],
    "VTTK_GeelyAtlas": [("Geely", "Atlas", r"^Atlas, I( Рестайлинг)? \(")],
    "Toy_VT_korolla_e120_e130": [("Toyota", "Corolla", r"^Corolla, IX \(E120, E130\)")],
    "Toy_VT_korolla_e140/150": [("Toyota", "Corolla", r"^Corolla, X \(E140")],
    "Toy_VT_Camry": [("Toyota", "Camry", r"^Camry, VII \(XV50\)")],
    "KiaCeed_vt01": [("Kia", "Ceed", r"^Ceed, (II|III)( Рестайлинг)? \(")],
    "VTRENAULT01": [("Renault", "Megane", r"^Megane, (II|III)[ (]")],
    "VTRENAULT02": [("Renault", "Megane", r"^Megane, (II|III)[ (]")],
    "VTRenault02_PA": [("Renault", "Megane", r"^Megane, (II|III)[ (]")],
}
# Kia/Hyundai: поколения по данным конкурентов (Solaris I 2010-2017, Rio III 2011-2017, Soul I, Venga)
_KIA = [("Hyundai", "Solaris", r"^Solaris, I "), ("Kia", "Rio", r"^Rio, III"), ("Kia", "Soul", r"^Soul, I "), ("Kia", "Venga", r"^Venga")]
for _o in ("Kia_Hyundai_VT/TK", "Kia_Hyundai_VT", "Kia_Hyundai_TK", "KiaHyundai_Origin"):
    FIT[_o] = list(_KIA)
# ТН ВЭД: правило «как у карточек той же марки, иначе как у большинства втулок»
TN_BRAND = {"Chery": "8409990009", "Changan": "8409990009", "Geely": "8409990009", "Hummer": "8409990009"}
TN_DEFAULT = "8703101100"
TN_TARGET = ["6RU423057-PoloSedan", "Polo-sedan", "VTRenault02_PA", "VTRenault_Duster_PA", "Chery Tigo 4 PRO_VT", "KiaHyundai_Origin",
             "TK_CheryTigo4PRO", "VTTK_GeelyAtlas", "VT_CheryTigg07pro", "vt_ChanganCS35_reika"]
TN_CHINA = {"Chery Tigo 4 PRO_VT", "TK_CheryTigo4PRO", "VTTK_GeelyAtlas", "VT_CheryTigg07pro", "vt_ChanganCS35_reika"}
# без сохранения марки/модели (поколение в названии не указано) — ждут решения владельца
PENDING = ["VTRenault_Duster_PA", "Largus-otopitel", "8201052009"]

_cache = {}
def dic(text):
    if text not in _cache:
        s, r = A.call("/v1/description-category/attribute/values/search",
                      {"attribute_id": 22917, "description_category_id": 17028756, "type_id": 971109202, "value": text, "limit": 100})
        _cache[text] = [(x["id"], x["value"]) for x in r.get("result", [])]
    return _cache[text]


def rows_for(offer):
    rows, desc = [], []
    for brand, q, pat in FIT[offer]:
        hits = [(i, v) for i, v in dic(q) if re.search(pat, v)]
        for i, v in hits:
            rows.append({"attributes": [
                {"complex_id": CX, "id": 22916, "values": [{"dictionary_value_id": BR[brand], "value": brand}]},
                {"complex_id": CX, "id": 22917, "values": [{"dictionary_value_id": i, "value": v}]}]})
            desc.append(f"{brand} {v}")
    return rows, desc


def tn_values():
    out = {}
    for c in json.load(open(ROOT / "data/raw/attributes.json", encoding="utf-8"))["result"]:
        for a in c["attributes"]:
            if a["id"] == TN_ID and a["values"]:
                v = a["values"][0]; out.setdefault(v["value"][:10], v)
    return out


def main(apply):
    TN = tn_values()
    offers = [x for x in sys.argv[1:] if not x.startswith("--")] or sorted(set(FIT) | set(TN_TARGET))
    cards, prices = A.live_cards(offers)
    items, report = [], []
    for o in offers:
        card = cards[o]
        it = A.build(card, {}, prices[o])
        def is_fit(c):  # строка блока «Применимость» в любом из двух форматов
            return c.get("complex_id") == CX or any(x.get("complex_id") == CX for x in c.get("attributes", []))
        cx = [c for c in (card.get("complex_attributes") or []) if not is_fit(c)]
        note = []
        if o in FIT:
            rows, desc = rows_for(o)
            if not rows: note.append("ПРОПУСК: в справочнике не найдено строк");
            else:
                cx += rows; note.append(f"подбор: {len(rows)} строк (" + "; ".join(desc[:3]) + ("…" if len(desc) > 3 else "") + ")")
        else:
            cx = card.get("complex_attributes") or []
        it["complex_attributes"] = cx
        if o in TN_TARGET and not any(a["id"] == TN_ID for a in card["attributes"]):
            code = TN_BRAND.get(("Chery" if o in TN_CHINA else ""), None) or ("8409990009" if o in TN_CHINA else TN_DEFAULT)
            v = TN[code]
            it["attributes"].append({"id": TN_ID, "complex_id": 0, "values": [{"dictionary_value_id": v["dictionary_value_id"], "value": v["value"]}]})
            note.append("ТН ВЭД " + code)
        report.append((o, note)); items.append(it)
    for o, n in report: print(f"{o[:26]:26} {' | '.join(n)}")
    print("\nБЕЗ ПОДБОРА (поколение не указано в названии):", ", ".join(PENDING))
    if not apply: print("\nDRY-RUN"); return
    ok = [it for it, (o, n) in zip(items, report) if n and "ПРОПУСК" not in " ".join(n)]
    s, r = A.call("/v3/product/import", {"items": ok}); print("\nimport", s, json.dumps(r, ensure_ascii=False)[:200])
    if s == 200:
        for i in A.wait(r["result"]["task_id"]): print(i["offer_id"], i["status"], json.dumps([e.get("description", "")[:80] for e in i.get("errors", [])], ensure_ascii=False))
        time.sleep(5); A.restore_prices([it["offer_id"] for it in ok], prices)


if __name__ == "__main__":
    main("--apply" in sys.argv)
