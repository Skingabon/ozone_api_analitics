"""Раскладка фото и видео товаров по папкам Яндекс Диска: /AVTO/TOVARY/<группа>/{Foto,Video}.

  python collector/yadisk_sync.py            # проверка: что будет загружено
  python collector/yadisk_sync.py --upload   # загрузить недостающее (существующие файлы и папки не трогаются)
  python collector/yadisk_sync.py --publish  # открыть по ссылке только папки групп и сохранить ссылки в data/media_map.json
Токен: YANDEX_DISK_TOKEN в .env. Ничего не удаляется и не перезаписывается.
"""
import json, os, sys, time
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
H = {"Authorization": "OAuth " + os.environ["YANDEX_DISK_TOKEN"]}
API = "https://cloud-api.yandex.net/v1/disk"
BASE = "/AVTO/TOVARY"
A = Path(r"D:\3D\Auto")
IMG = {".jpg", ".jpeg", ".png", ".webp"}
VID = {".mp4", ".mov"}
MAX_VIDEO_MB = 120     # крупные исходники не грузим

# группа: (локальные папки, карточки Ozon, для которых подходит)
GROUPS = {
    "Chery_Tiggo_7_Pro": ([A / "Chery Tiggo/CheryTiggo 7 PRO"], ["VT_CheryTigg07pro"]),
    "Chery_Tiggo_4_Pro": ([A / "Chery Tiggo/Media"], ["Chery Tigo 4 PRO_VT"]),                     # TK-подпапка ниже отдельно
    "Chery_Tiggo_4_Pro_Tolkatel": ([A / "Chery Tiggo/Media/TK"], ["TK_CheryTigo4PRO"]),
    "Changan_CS35": ([A / "Changan/Media"], ["Ch35_vt01", "Changan-cs35-Plus"]),
    "Changan_CS35_Pylnik": ([A / "Changan/Changan CS35/VT_Pilnic"], ["vt_ChanganCS35_reika"]),
    "Geely_Atlas": ([A / "Geely Atlas/Фото"], ["VTTK_GeelyAtlas"]),
    "Kia_Ceed": ([A / "Kia/Ceed"], ["KiaCeed_vt01"]),
    "Kia_Hyundai_Solaris_Rio": ([A / "Kia/RioSolaris"], ["Kia_Hyundai_VT/TK", "Kia_Hyundai_VT", "Kia_Hyundai_TK", "KiaHyundai_Origin"]),
    "Renault_Megane": ([A / "Renault/Megane"], ["VTRENAULT01", "VTRENAULT02", "VTRenault02_PA"]),
    "Renault_Zaglushka_8201052009": ([A / "Renault/Zaglush_8201052009"], ["8201052009"]),
    "Renault_Largus_Otopitel": ([A / "Renault/Кожух отопителя"], ["Largus-otopitel"]),
    "VW_Polo": ([A / "Volkswagen/POLO NEW", A / "Volkswagen/Polo"], ["Polo-sedan", "6RU423057-PoloSedan", "VW_TK_POLO"]),
    "Toyota_Corolla": ([A / "NEW_SD/Toyota/Corolla"], ["Toy_VT_korolla_e140/150", "Toy_VT_korolla_e120_e130"]),
    "Gidrozatvor": ([Path(r"D:\3D\GidroZatvor")], ["GZ_1_kon"]),
    "Vorota_CAME_shestern": ([Path(r"D:\3D\Shest")], ["Vorota-Came_shest"]),
}
EXCLUDE = {"Chery_Tiggo_4_Pro": ["TK"]}   # подпапки, которые относятся к другой группе


def files_of(group):
    out, seen = [], set()
    for src in GROUPS[group][0]:
        for dp, dn, fn in os.walk(src):
            rel = Path(dp).relative_to(src).parts
            if rel and rel[0] in EXCLUDE.get(group, []): continue
            for f in sorted(fn):
                p = Path(dp) / f; e = p.suffix.lower()
                kind = "Foto" if e in IMG else "Video" if e in VID else None
                if not kind: continue
                mb = p.stat().st_size / 1e6
                if kind == "Video" and mb > MAX_VIDEO_MB: continue
                name = f
                if name in seen: name = f"{'_'.join(rel[-1:]) or 'x'}_{f}"
                seen.add(name); out.append((p, kind, name))
    return out


def req(method, path, **kw):
    for a in range(4):
        r = requests.request(method, API + path, headers=H, timeout=60, **kw)
        if r.status_code in (429, 500, 502, 503): time.sleep(2 ** a); continue
        return r
    return r


def ensure_dir(path):
    r = req("PUT", "/resources", params={"path": path})
    return r.status_code in (201, 409)     # 409 = уже существует


def exists_size(path):
    r = req("GET", "/resources", params={"path": path, "fields": "size,type"})
    return r.json().get("size") if r.status_code == 200 else None


def upload(local, remote):
    r = req("GET", "/resources/upload", params={"path": remote, "overwrite": "false"})
    if r.status_code == 409: return "exists"
    r.raise_for_status()
    import subprocess   # curl надёжнее requests на медленном канале
    out = subprocess.run(["curl", "-s", "-m", "3000", "-o", os.devnull, "-w", "%{http_code}", "-T", str(local), r.json()["href"]],
                         capture_output=True, text=True).stdout.strip()
    return "ok" if out in ("201", "202") else f"err {out}"


def main(mode):
    total = 0; plan = {}
    for g in GROUPS:
        fl = files_of(g); plan[g] = fl
        n_i = sum(1 for _, k, _ in fl if k == "Foto"); n_v = sum(1 for _, k, _ in fl if k == "Video")
        mb = sum(p.stat().st_size for p, _, _ in fl) / 1e6; total += mb
        print(f"{g:32} фото {n_i:3} видео {n_v} {mb:7.1f} МБ  → {', '.join(GROUPS[g][1])[:60]}")
    print(f"ИТОГО {total:.0f} МБ")
    if mode == "upload":
        for d in ("/AVTO", BASE): ensure_dir(d)
        done = skip = err = 0
        for g, fl in plan.items():
            for sub in ("", "/Foto", "/Video"): ensure_dir(f"{BASE}/{g}{sub}")
            for p, kind, name in fl:
                remote = f"{BASE}/{g}/{kind}/{name}"
                t0 = time.time(); st = upload(p, remote)
                print(f"    {g}/{kind}/{name[:40]} {p.stat().st_size/1e6:.1f} МБ {st} {time.time()-t0:.0f}с", flush=True)
                if st == "ok": done += 1
                elif st == "exists": skip += 1
                else: err += 1; print("  ОШИБКА", g, name, st)
            print(f"  {g}: загружено {done}, уже было {skip}, ошибок {err}", flush=True)
    if mode == "publish":
        out = {}
        for g in plan:
            r = req("PUT", "/resources/publish", params={"path": f"{BASE}/{g}"})
            info = req("GET", "/resources", params={"path": f"{BASE}/{g}", "limit": 200}).json()
            emb = info.get("_embedded", {}).get("items", [])
            out[g] = {"public_url": info.get("public_url"), "offers": GROUPS[g][1], "public_key": info.get("public_key")}
            print(g, out[g]["public_url"])
        (ROOT / "data/media_map.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main("upload" if "--upload" in sys.argv else "publish" if "--publish" in sys.argv else "plan")
