"""Главные фото с названием авто (01_main) и слайд совместимости (02_compat) для ВСЕХ карточек втулок.
Существующие 4 набора (polo, tiggo7pro, tiggo4pro, cs35) не перезаписываются: они собираются make_infographics.py.

  python collector/make_infographics_all.py            # все карточки
  python collector/make_infographics_all.py Toy_VT_Camry
Результат: data/img/ozon/<offer_safe>/01_main.png, 02_compat.png  (1200x1600)
"""
import json, re, sys
from pathlib import Path
import make_infographics as MI
import apply_cards as A
import apply_bushings as B

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

OUT = MI.ROOT / "data/img/ozon"; OUT.mkdir(parents=True, exist_ok=True)

# offer: (что за деталь, автомобили (кратко), OEM, плашки, индекс фото на подложке)
INFO = {
    "Polo-sedan": ("Ремкомплект рулевой рейки", "VOLKSWAGEN POLO SEDAN", "OEM 6RU423057N", ["Втулка + толкатель", "Сделано в России"], 2),
    "VT_CheryTigg07pro": ("Втулка рулевой рейки", "CHERY TIGGO 7 PRO / PRO MAX", "", ["Полиамид", "Ø 26 мм", "Сделано в России"], 0),
    "Chery Tigo 4 PRO_VT": ("Втулка рулевой рейки", "CHERY TIGGO 4 PRO", "OEM CY9001KIT-PST", ["Усиленная", "Полиамид / капрон", "Сделано в России"], 0),
    "Ch35_vt01": ("Втулка рулевой рейки", "CHANGAN CS35", "OEM S111F260401-0100", ["Полиамид", "Сделано в России"], 1),
    "6RU423057-PoloSedan": ("Втулка рулевой рейки", "VOLKSWAGEN POLO SEDAN", "OEM 6RU423057", ["Усиленная", "Сделано в России"], 0),
    "VW_TK_POLO": ("Прижимная втулка (толкатель)", "VW POLO SEDAN · SKODA RAPID · FABIA II", "OEM 6RU423057", ["Сделано в России"], 0),
    "Toy_VT_korolla_e140/150": ("Втулка рулевой рейки", "TOYOTA COROLLA E140 / E150", "OEM HLM00003", ["Сделано в России"], 0),
    "Toy_VT_korolla_e120_e130": ("Втулка рулевой рейки", "TOYOTA COROLLA E120 / E130", "OEM L-M6081", ["Сделано в России"], 0),
    "Toy_VT_Camry": ("Втулка рулевой рейки", "TOYOTA CAMRY XV50 · HIGHLANDER · LEXUS ES", "OEM 7912DL", ["Сделано в России"], 0),
    "Kia_Hyundai_VT/TK": ("Ремкомплект рулевой рейки", "SOLARIS · RIO · SOUL · VENGA", "OEM 565212K000", ["Втулка + упор вала", "Сделано в России"], 0),
    "VTRENAULT02": ("Втулка рулевой рейки", "RENAULT MEGANE II · III · CLIO", "OEM 7700799093", ["Усиленная", "Сделано в России"], 0),
    "Kia_Hyundai_VT": ("Втулка рулевой рейки", "HYUNDAI SOLARIS · KIA RIO · SOUL · VENGA", "OEM 565212K000", ["Сделано в России"], 0),
    "Kia_Hyundai_TK": ("Прижимная втулка (упор вала)", "HYUNDAI SOLARIS · KIA RIO", "OEM 565223X000", ["Сделано в России"], 0),
    "KiaCeed_vt01": ("Втулка рулевой рейки", "KIA CEED · CERATO · HYUNDAI i30", "OEM 565213X000", ["Сделано в России"], 0),
    "H3_vt03": ("Втулка рулевой рейки", "HUMMER H3", "OEM 15132764", ["Сделано в России"], 0),
    "VT-Hyundai-i40": ("Втулка рулевой рейки", "HYUNDAI i40 · SANTA FE · SONATA VI", "OEM 565213Q000", ["Сделано в России"], 0),
    "VTRENAULT01": ("Втулка рулевой рейки усиленная", "RENAULT MEGANE II · III · SCENIC · CLIO", "OEM 7700799093", ["Усиленная", "Сделано в России"], 0),
    "VTRenault02_PA": ("Втулка рулевой рейки усиленная", "RENAULT MEGANE II · CLIO", "OEM 7700799093", ["Полиамид", "Сделано в России"], 0),
    "VTRenault_Duster_PA": ("Втулка рулевой рейки усиленная", "RENAULT DUSTER", "OEM 7700799093", ["Капрон", "Сделано в России"], 0),
    "KiaHyundai_Origin": ("Втулка рулевой рейки", "HYUNDAI SOLARIS · KIA RIO · SOUL · VENGA", "OEM 565551Y600", ["Сделано в России"], 0),
    "TK_CheryTigo4PRO": ("Толкатель рулевой рейки", "CHERY TIGGO 4 PRO", "", ["Полиамид", "Сделано в России"], 0),
    "Changan-cs35-Plus": ("Втулка рулевой рейки", "CHANGAN CS35 PLUS", "OEM S111F260401-0100", ["Сделано в России"], 0),
    "VTTK_GeelyAtlas": ("Втулка и толкатель рулевой рейки", "GEELY ATLAS", "", ["Капролон (полиамид)", "Сделано в России"], 0),
    "vt_ChanganCS35_reika": ("Втулка под пыльник рулевой рейки", "CHANGAN CS35", "", ["Полиамид", "Сделано в России"], 0),
    "Largus-otopitel": ("Кольцо крепления мотора отопителя", "RENAULT LARGUS · LOGAN · DUSTER", "OEM 272972719R", ["Сделано в России"], 0),
    "8201052009": ("Заглушка кожуха ремня ГРМ", "RENAULT LOGAN", "OEM 8201052009", ["Полиамид", "Сделано в России"], 0),
}


def safe(o): return re.sub(r"[^\w\-]+", "_", o)


def slide_main(title, car, oem, pills, photo):
    size = 64 if len(car) <= 30 else 50
    pl = "".join(f"<div class='pill'>{p}</div>" for p in pills)
    return MI.page(f"<h1>{title}</h1><h2 style='font-size:{size}px'>{car}</h2>"
                   f"<div class='photo'><div class='bg' style='background-image:url({photo})'></div><img src='{photo}'></div>"
                   f"<div class='pills'>{pl}</div>" + (f"<div class='foot'>{oem}</div>" if oem else ""))


def slide_compat(car_lines, oem, photo):
    fit = "".join(f"<div class='li'>{n}</div>" for n in car_lines)
    return MI.page(f"<h1>Подходит для</h1><div class='card'>{fit}</div>"
                   f"<div class='photo' style='margin-top:34px'><div class='bg' style='background-image:url({photo})'></div><img src='{photo}'></div>"
                   f"<div class='note'>Сверьте номер на рулевой рейке" + (f" ({oem.replace('OEM ', '')})" if oem else "") + ".</div>")


def main(only):
    offers = [o for o in INFO if not only or o in only]
    live, _ = A.live_cards(offers)
    for o in offers:
        title, car, oem, pills, idx = INFO[o]
        c = live[o]; imgs = ([c["primary_image"]] if c.get("primary_image") else []) + list(c.get("images") or [])
        photo = imgs[min(idx, len(imgs) - 1)]
        d = OUT / safe(o); d.mkdir(exist_ok=True)
        lines = B.fit_lines(c) or [car.title()]
        for name, html in (("01_main", slide_main(title, car, oem, pills, photo)), ("02_compat", slide_compat(lines, oem, imgs[min(1, len(imgs) - 1)]))):
            hp = d / f"{name}.html"; hp.write_text(html, encoding="utf-8"); MI.shot(hp, d / f"{name}.png")
        print(o, "→", d.name, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
