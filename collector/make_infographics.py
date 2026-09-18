"""Фирменная инфографика Homehelp для карточек: HTML -> PNG 1200x1600 (headless Chrome).

  python collector/make_infographics.py          # собрать всё в data/img/out
Фото берутся из текущих карточек (data/raw/attributes.json); тексты — только факты из карточек.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/img/out"; OUT.mkdir(parents=True, exist_ok=True)
CHROME = next(p for p in ("C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe") if Path(p).exists())
A = {a["offer_id"]: a for a in json.load(open(ROOT / "data/raw/attributes.json", encoding="utf-8"))["result"]}

# фирменные цвета Homehelp: зелёный фон карточек, белый логотип-ромб, акцент жёлтый
CSS = """
*{box-sizing:border-box;margin:0}body{width:1200px;height:1600px;font-family:'Segoe UI',Arial,sans-serif;color:#fff;overflow:hidden;
background:linear-gradient(160deg,#37a548 0%,#1f8236 55%,#14622a 100%);position:relative}
.pat{position:absolute;inset:0;opacity:.09;background-image:linear-gradient(45deg,#fff 25%,transparent 25%,transparent 75%,#fff 75%),linear-gradient(45deg,#fff 25%,transparent 25%,transparent 75%,#fff 75%);background-size:120px 120px;background-position:0 0,60px 60px}
.logo{position:absolute;top:56px;left:64px;display:flex;align-items:center;gap:16px;z-index:3}
.dia{width:46px;height:46px;border:6px solid #fff;transform:rotate(45deg);border-radius:6px}
.logo b{font-size:44px;letter-spacing:.5px}.logo i{font-size:24px;font-style:normal;opacity:.9;display:block;margin-top:-4px}
.wrap{position:absolute;inset:150px 64px 64px;z-index:2;display:flex;flex-direction:column}
h1{font-size:88px;line-height:1.02;font-weight:800;text-shadow:0 3px 12px rgba(0,0,0,.25)}
h2{font-size:64px;line-height:1.1;font-weight:800;color:#ffe15a;margin-top:14px;text-shadow:0 3px 10px rgba(0,0,0,.25)}
.photo{flex:1;margin:34px 0;background:#fff;border-radius:36px;box-shadow:0 18px 50px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;overflow:hidden;min-height:0}
.photo{position:relative}.photo .bg{position:absolute;inset:-40px;background-size:cover;background-position:center;filter:blur(28px) brightness(.9)}.photo img{position:relative;max-width:100%;max-height:100%;object-fit:contain}
.pills{display:flex;gap:16px;flex-wrap:wrap}.pill{background:rgba(255,255,255,.95);color:#14622a;border-radius:999px;padding:18px 32px;font-size:36px;font-weight:700}
.foot{margin-top:22px;font-size:34px;opacity:.95}
.card{background:#fff;color:#16321b;border-radius:32px;padding:38px 44px;box-shadow:0 14px 40px rgba(0,0,0,.3);margin-top:22px}
.li{font-size:50px;font-weight:700;padding:26px 0;border-bottom:3px solid #e3efe5;display:flex;justify-content:space-between;gap:24px}
.li:last-child{border:0}.li span{color:#2e9e40;white-space:nowrap}
.row{display:flex;justify-content:space-between;font-size:46px;padding:22px 0;border-bottom:3px solid #e3efe5}.row:last-child{border:0}.row b{color:#1f8236}
.ck{font-size:48px;font-weight:700;padding:24px 0;display:flex;gap:24px;align-items:flex-start;line-height:1.15}.ck:before{content:"✓";color:#fff;background:#2e9e40;border-radius:50%;min-width:62px;height:62px;display:flex;align-items:center;justify-content:center;font-size:40px}
.note{font-size:30px;opacity:.9;margin-top:auto}
"""

def page(body):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='pat'></div><div class='logo'><div class='dia'></div><div><b>Homehelp</b><i>надёжно</i></div></div><div class='wrap'>{body}</div></body></html>"

def imgs(o):
    a = A[o]; return ([a["primary_image"]] if a.get("primary_image") else []) + list(a.get("images") or [])

CARDS = {
    "Polo-sedan": {"slug": "polo", "title": "Ремкомплект рулевой рейки", "car": "VOLKSWAGEN POLO SEDAN", "years": "2014–2020",
        "main": 2, "second": 4, "third": 3, "oem": "OEM 6RU423057N", "pills": ["Втулка + толкатель", "Сделано в России"],
        "fit": [("Volkswagen Polo Sedan", "2014–2020")], "kit": ["Втулка рулевой рейки", "Толкатель (упорная втулка)"],
        "dims": [("Внутренний диаметр", "25 мм"), ("Длина / ширина", "24,7 × 24,7 мм"), ("Высота", "24 мм"), ("Толщина стенки", "3,1 мм"), ("Материал", "Пластик, стекловолокно"), ("Вес детали", "40 г")]},
    "VT_CheryTigg07pro": {"slug": "tiggo7pro", "title": "Втулка рулевой рейки", "car": "CHERY TIGGO 7 PRO / PRO MAX", "years": "с 2020 г.",
        "main": 0, "second": 3, "third": 1, "oem": "", "pills": ["Полиамид", "Ø 26 мм", "Сделано в России"],
        "fit": [("Chery Tiggo 7 Pro", "с 2020"), ("Chery Tiggo 7 Pro Max", "с 2022")], "kit": ["Втулка рулевой рейки, 1 шт."],
        "dims": [("Внутренний диаметр", "26 мм"), ("Длина / ширина", "30,2 × 34,6 мм"), ("Толщина стенки", "3,5 мм"), ("Материал", "Полиамид, стекловолокно"), ("Вес детали", "50 г")]},
    "Chery Tigo 4 PRO_VT": {"slug": "tiggo4pro", "title": "Втулка рулевой рейки", "car": "CHERY TIGGO 4 PRO", "years": "с 2020 г.",
        "main": 0, "second": 4, "third": 2, "oem": "OEM CY9001KIT-PST", "pills": ["Усиленная", "Полиамид / капрон", "Сделано в России"],
        "fit": [("Chery Tiggo 4 Pro", "с 2020")], "kit": ["Втулка усиленная рулевой рейки, 1 шт."],
        "dims": [("Внутренний диаметр", "25 мм"), ("Длина / ширина", "34 × 34 мм"), ("Высота", "18 мм"), ("Толщина стенки", "4,4 мм"), ("Вес детали", "30 г")]},
    "Ch35_vt01": {"slug": "cs35", "title": "Втулка рулевой рейки", "car": "CHANGAN CS35", "years": "с 2012 г.",
        "main": 1, "second": 2, "third": 3, "oem": "OEM S111F260401-0100", "pills": ["Полиамид", "Сделано в России"],
        "fit": [("Changan CS35", "с 2012")], "kit": ["Втулка рулевой рейки, 1 шт."],
        "dims": [("Внутренний диаметр", "24 мм"), ("Высота", "26 мм"), ("Материал", "Полиамид, стекловолокно"), ("Вес детали", "50 г")]},
}

def slides(o, c):
    im = imgs(o); main = im[c["main"]]; sec = im[c["second"]]
    pills = "".join(f"<div class='pill'>{p}</div>" for p in c["pills"])
    s1 = page(f"<h1>{c['title']}</h1><h2>{c['car']}</h2><div class='photo'><div class='bg' style='background-image:url({main})'></div><img src='{main}'></div><div class='pills'>{pills}</div>" + (f"<div class='foot'>{c['oem']}</div>" if c["oem"] else ""))
    fit = "".join(f"<div class='li'>{n}<span>{y}</span></div>" for n, y in c["fit"])
    s2 = page(f"<h1>Подходит для</h1><div class='card'>{fit}</div><div class='photo' style='margin-top:34px'><div class='bg' style='background-image:url({im[c["third"]]})'></div><img src='{im[c["third"]]}'></div><div class='note'>Совместимость проверяйте по OEM-номеру рейки" + (f" ({c['oem'].replace('OEM ', '')})" if c["oem"] else "") + ".</div>")
    rows = "".join(f"<div class='row'>{k}<b>{v}</b></div>" for k, v in c["dims"])
    s3 = page(f"<h1>Размеры и материал</h1><div class='photo' style='margin:28px 0'><div class='bg' style='background-image:url({sec})'></div><img src='{sec}'></div><div class='card' style='margin-top:0'>{rows}</div><div class='note'>Размеры получены замером штангенциркулем.</div>")
    kit = "".join(f"<div class='ck'>{k}</div>" for k in c["kit"])
    why = ["Своя конструкция: деталь моделируем и изготавливаем сами", "Размеры указаны по реальным замерам", "Материал: " + next(v for k, v in c["dims"] if k == "Материал") if any(k == "Материал" for k, _ in c["dims"]) else "Прочный инженерный пластик", "Сделано в России"]
    s4 = page(f"<h1>В комплекте</h1><div class='card'>{kit}</div><h1 style='margin-top:56px'>Почему Homehelp</h1><div class='card'>" + "".join(f"<div class='ck'>{w}</div>" for w in why) + "</div>")
    return [s1, s2, s3, s4]

def shot(html_path, png_path):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,1600", "--virtual-time-budget=15000",
                    f"--screenshot={png_path}", "file:///" + str(html_path).replace("\\", "/")], check=True, capture_output=True)

if __name__ == "__main__":
    only = sys.argv[1:]
    for o, c in CARDS.items():
        if only and o not in only: continue
        for n, html in enumerate(slides(o, c), 1):
            hp = OUT / f"{c['slug']}_{n}.html"; hp.write_text(html, encoding="utf-8")
            shot(hp, OUT / f"{c['slug']}_{n}.png"); print(f"{c['slug']}_{n}.png")
