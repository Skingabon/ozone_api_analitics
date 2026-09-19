"""Добавление фото в карточки Ozon: новое главное фото с названием авто ставится ПЕРВЫМ, все прежние фото остаются.

  python collector/apply_media.py Toy_VT_Camry             # проверка (dry-run) для перечисленных карточек
  python collector/apply_media.py --apply Toy_VT_Camry     # применить
Порядок: [новое главное] + [новые доп. слайды] + [прежнее главное] + [прежние доп. фото]. Ничего не удаляется, максимум 30 фото.
Файлы берутся из data/img/ozon/<offer>/ (и data/img/out/<slug>_N.png для 4 полных наборов), кладутся на Яндекс Диск
в /AVTO/OZON/<offer>/ и передаются Ozon прямыми ссылками (Ozon скачивает и хранит копию).
"""
import os, re, sys, time
from pathlib import Path
import requests
import yadisk_sync as Y
import apply_cards as A
import make_infographics_all as MA

ROOT = Path(__file__).resolve().parent.parent
FULL = {"Polo-sedan": "polo", "VT_CheryTigg07pro": "tiggo7pro", "Chery Tigo 4 PRO_VT": "tiggo4pro", "Ch35_vt01": "cs35"}
DISK = "/AVTO/OZON"


def new_files(o):
    """Локальные новые слайды по порядку: 01_main, 02_compat[, 03, 04]."""
    d = ROOT / "data/img/ozon" / MA.safe(o)
    files = [d / "01_main.png", d / "02_compat.png"]
    if o in FULL:
        for n in (3, 4): files.append(ROOT / "data/img/out" / f"{FULL[o]}_{n}.png")
    return [f for f in files if f.exists()]


def disk_links(o, files):
    base = f"{DISK}/{MA.safe(o)}"
    for d in ("/AVTO", DISK, base): Y.ensure_dir(d)
    names = []
    for i, f in enumerate(files, 1):
        name = f"{i:02d}_{f.stem.split('_', 1)[-1] if f.stem[:2].isdigit() else f.stem}{f.suffix.lower()}"
        st = Y.upload(f, f"{base}/{name}")
        names.append(name)
    Y.req("PUT", "/resources/publish", params={"path": base})
    info = Y.req("GET", "/resources", params={"path": base, "fields": "public_url,public_key"}).json()
    key = info.get("public_key") or info.get("public_url")
    links = []
    for n in names:
        r = Y.req("GET", "/public/resources/download", params={"public_key": key, "path": "/" + n})
        links.append(r.json()["href"])
    return info.get("public_url"), links


def main(apply, offers):
    live, prices = A.live_cards(offers)
    items, report = [], []
    for o in offers:
        files = new_files(o)
        if not files: print(o, "нет слайдов, пропуск"); continue
        card = live[o]
        old = ([card["primary_image"]] if card.get("primary_image") else []) + list(card.get("images") or [])
        if any("yandex" in u for u in old): print(o, "уже есть загруженные с Диска ссылки в карточке, проверьте вручную");
        print(f"{o[:26]:26} прежних фото {len(old)}, новых слайдов {len(files)} → всего {min(30, len(old) + len(files))}")
        if not apply: continue
        public, links = disk_links(o, files)
        it = A.build(card, {}, prices[o])
        new_main, extra = links[0], links[1:]
        it["primary_image"] = new_main
        it["images"] = (extra + old)[:29]
        items.append(it); report.append((o, public))
    if not apply or not items: print("DRY-RUN" if not apply else "нечего применять"); return
    s, r = A.call("/v3/product/import", {"items": items}); print("import", s, r)
    if s == 200:
        for i in A.wait(r["result"]["task_id"]): print(" ", i["offer_id"], i["status"], [e.get("description", "")[:90] for e in i.get("errors", [])])
        time.sleep(5); A.restore_prices([i["offer_id"] for i in items], prices)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--all" in sys.argv:   # все карточки втулок, кроме уже сделанных и отложенных (слабые исходные фото)
        SKIP = {"VTRENAULT01", "TK_CheryTigo4PRO", "Toy_VT_Camry"}
        args = [o for o in MA.INFO if o not in SKIP]
    main("--apply" in sys.argv, args)
