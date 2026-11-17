r"""TK_CheryTigo4PRO: главное фото и слайд совместимости на реальных фото толкателя из D:\3D\Auto\Chery Tiggo\Media\TK.
Прежние фото карточки остаются; новые: [главный слайд] + [совместимость] + прежние + [доп. фото толкателя]."""
import shutil, sys, time
from pathlib import Path
import apply_cards as A
import apply_media as AM
import make_infographics_all as MA
import make_infographics as MI

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

O = "TK_CheryTigo4PRO"
SRC = Path(r"D:\3D\Auto\Chery Tiggo\Media\TK")
MAIN, COMPAT = "IMG_20250109_150131_806@1133214300.jpg", "IMG_20250109_150145_221@1319403442.jpg"
EXTRA = ["IMG_20250109_150047_758@-263650916.jpg", "IMG_20250109_150100_822@-711193800.jpg", "photo_5435999197716407128_y(1).jpg"]
title, car, oem, pills, _ = MA.INFO[O]
d = AM.ROOT / "data/img/ozon" / MA.safe(O)
for n, f in (("main_photo.jpg", MAIN), ("compat_photo.jpg", COMPAT)): shutil.copy(SRC / f, d / n)
for name, html in (("01_main", MA.slide_main(title, car, oem, pills, "main_photo.jpg")),
                   ("02_compat", MA.slide_compat(["Chery Tiggo 4 Pro (2020–н.в.)"], oem, "compat_photo.jpg"))):
    hp = d / f"{name}.html"; hp.write_text(html, encoding="utf-8"); MI.shot(hp, d / f"{name}.png"); print(name, "готов")
apply = "--apply" in sys.argv
if not apply: print("DRY-RUN: слайды собраны (data/img/ozon/TK_CheryTigo4PRO), в Ozon ничего не отправлено"); sys.exit()
live, prices = A.live_cards([O]); card = live[O]
old = ([card["primary_image"]] if card.get("primary_image") else []) + list(card.get("images") or [])
files = [d / "01_main.png", d / "02_compat.png"] + [SRC / f for f in EXTRA]
public, links = AM.disk_links(O, files)
it = A.build(card, {}, prices[O])
it["primary_image"] = links[0]; it["images"] = ([links[1]] + old + links[2:])[:29]
s, r = A.call("/v3/product/import", {"items": [it]}); print("import", s)
for i in A.wait(r["result"]["task_id"]): print(i["offer_id"], i["status"], [e.get("description", "")[:90] for e in i.get("errors", [])])
time.sleep(5); A.restore_prices([O], prices)
