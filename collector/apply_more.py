"""Подбор Kia/Hyundai по данным конкурентов + исправление технических «Названий модели» (9048)."""
import re, sys, time
import apply_cards as A
import apply_fit as F

KIA = ["Kia_Hyundai_VT/TK", "Kia_Hyundai_VT", "Kia_Hyundai_TK", "KiaHyundai_Origin"]
ROWS = [("Hyundai", 58126, "Solaris", r"^Solaris, I "), ("Kia", 58134, "Rio", r"^Rio, III"),
        ("Kia", 58134, "Soul", r"^Soul, I "), ("Kia", 58134, "Venga", r"^Venga")]
F.BR.update({"Hyundai": 58126, "Kia": 58134})
for o in KIA: F.FIT[o] = [(b, q, p) for b, _, q, p in ROWS]

N9048 = {
    "6RU423057-PoloSedan": "Volkswagen Polo Sedan (втулка 6RU423057)",
    "Toy_VT_Camry": "Toyota Camry XV50 (втулка рулевой рейки)",
    "TK_CheryTigo4PRO": "Chery Tiggo 4 Pro (толкатель рулевой рейки)",
    "vt_ChanganCS35_reika": "Changan CS35 (втулка под пыльник 36 мм)",
    "VTTK_GeelyAtlas": "Geely Atlas (втулка и толкатель рулевой рейки)",
    "VTRenault_Duster_PA": "Renault Duster (втулка рулевой рейки)",
    "Changan-cs35-Plus": "Changan CS35 Plus (втулка рулевой рейки)",
}

def main(apply):
    offers = KIA + list(N9048)
    live, prices = A.live_cards(sorted(set(offers)))
    items = []
    for o in sorted(set(offers)):
        card = live[o]; it = A.build(card, {}, prices[o])
        cx = [c for c in (card.get("complex_attributes") or []) if not (c.get("complex_id") == F.CX or any(x.get("complex_id") == F.CX for x in c.get("attributes", [])))]
        note = []
        if o in KIA:
            rows, desc = F.rows_for(o); cx += rows; note.append(f"подбор {len(rows)} строк")
        else:
            cx = card.get("complex_attributes") or []
        it["complex_attributes"] = cx
        if o in N9048:
            A.setv(it["attributes"], 9048, N9048[o]); note.append("9048 → " + N9048[o])
        print(f"{o[:24]:24}", " | ".join(note)); items.append(it)
    if not apply: print("DRY-RUN"); return
    s, r = A.call("/v3/product/import", {"items": items}); print("import", s, r)
    if s == 200:
        for i in A.wait(r["result"]["task_id"]):
            if i["status"] != "imported" or i.get("errors"): print(i["offer_id"], i["status"], [e.get("description", "")[:100] for e in i.get("errors", [])])
        time.sleep(5); A.restore_prices([it["offer_id"] for it in items], prices)

if __name__ == "__main__":
    main("--apply" in sys.argv)
