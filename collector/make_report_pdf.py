"""Отчёт по магазину в PDF (для чтения и отправки на почту): data/report/Otchet_HomeHelp_<дата>.pdf

  python collector/make_report_pdf.py
Берёт data/metrics.json (после конвейера), data/tasks_live.json (задачи с сайта; необязательно). HTML печатается в PDF через Chrome.
Персональные данные (ИНН, ФИО, ключи, пароли) в отчёт не попадают.
"""
import html, json, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # cron/редирект: иначе cp1251 и кракозябры вместо кириллицы

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/report"; OUT.mkdir(parents=True, exist_ok=True)
M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
try: TASKS = json.load(open(ROOT / "data/tasks_live.json", encoding="utf-8"))
except Exception: TASKS = M.get("tasks_seed", [])
CHROME = next(p for p in ("C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe") if Path(p).exists())

e = lambda s: html.escape(str(s if s is not None else ""))
rub = lambda v: "—" if v is None else f"{round(v):,}".replace(",", " ") + " ₽"
num = lambda v: "—" if v is None else f"{round(v):,}".replace(",", " ")
date = datetime.now().strftime("%d.%m.%Y")

K, P, S, Q, PR, PZ = M["kpi"], M["products"], M["savings"], M["quality"], M["promos"], M["prices"]
margin = K["profit_total"] / K["sales"] * 100 if K["sales"] else 0


def table(head, rows, right=()):
    th = "".join(f"<th class='{'r' if i in right else ''}'>{e(h)}</th>" for i, h in enumerate(head))
    tr = "".join("<tr>" + "".join(f"<td class='{'r' if i in right else ''}'>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"


def kpis(items):
    return "<div class='kpis'>" + "".join(f"<div class='k'><div class='l'>{e(l)}</div><div class='v'>{e(v)}</div><div class='s'>{e(s)}</div></div>" for l, v, s in items) + "</div>"


# --- 1. Итоги
sec1 = kpis([("Выручка за 30 дней", rub(K["sales"]), f"{K['orders']} заказов, отменено {K['cancelled']}"),
             ("Прибыль после себестоимости", rub(K["profit_total"]), f"маржа {margin:.0f}%"),
             ("Общие расходы (штрафы и пр.)", rub(K["overhead"]), "не привязаны к товарам"),
             ("Товаров с продажами", f"{K['sku_sold']} из {K['sku_total']}", f"остаток {num(K['stock_units'])} шт"),
             ("Баланс к выплате", rub(K["closing_balance"]), "на конец периода")])
warn = ""
if M.get("cost_ratio") and M["cost_ratio"]["max"] < 0.10:
    warn = f"<div class='warn'><b>Важно:</b> себестоимость в таблице составляет {M['cost_ratio']['min']*100:.1f}–{M['cost_ratio']['max']*100:.1f}% от цены при комиссии Ozon около 47–52%. Похоже, введены не реальные закупочные цены: прибыль в отчёте может быть завышена. Проверьте таблицу себестоимости.</div>"

# --- 2. Товары
sold = [p for p in P if p["units"] > 0]
sec2 = table(["Товар", "Продано, шт", "Выручка", "Комиссия", "Логистика", "Прибыль", "Маржа"],
             [[f"<b>{e(p['offer_id'])}</b>", num(p["units"]), rub(p["sales"]), f"{p['commission_pct'] or '—'}%", rub(-p["delivery"]), rub(p["profit"]), f"{p['margin_pct']}%" if p["margin_pct"] is not None else "—"] for p in sold], right=(1, 2, 3, 4, 5, 6))
top = sold[0] if sold else None
sec2 += f"<p class='note'>{('Один товар (' + e(top['offer_id']) + ') даёт ' + f'{top['sales']/K['sales']*100:.0f}% выручки.') if top and K['sales'] else ''} Без продаж за 30 дней {K['sku_total'] - K['sku_sold']} товаров, при этом на остатках {num(K['stock_units'])} шт.</p>"

# --- 3. Что сделано
done = [
 ("Карточки", "Названия, «Название модели», хэштеги и описания по единой схеме у всех карточек втулок и деталей: убраны нарушающие правила Ozon фразы (про конкурентов, связь вне площадки, выдуманный отзыв), добавлены симптомы, совместимость, размеры, установка, вопросы и ответы. Температура и срок эксплуатации по вашим данным."),
 ("Подбор по авто", "Марка и модель автомобиля (блок «Применимость») заполнены у 23 карточек по поколениям из названий и данным конкурентов. Kia/Hyundai различены между собой, Picanto убран из названий как неподтверждённый."),
 ("ТН ВЭД", "Втулки рулевой рейки: 8708 94 990 9; мешалка для хлебопечки: 8516 90 000 0; резиновое кольцо: 3926 90 970 9; крепление отопителя: 8708 99 970 9; заглушка ГРМ: 8409 91 000 8. Коды подобраны по справочнику Ozon, итог нужно согласовать с брокером."),
 ("Фото", "У 25 карточек втулок главным стало фото с названием автомобиля (единый фирменный стиль), вторым слайдом идёт «Подходит для». Все прежние фото сохранены. Материалы разложены на Яндекс Диске по товарам (130 файлов)."),
 ("Акции", "Убраны из акций со скидкой 20% и больше все товары, включая ручные («Распродажа стока»). Автодобавление в акции выключено у 21 товара (оставлено у 4 с выгодным бустом). Каждое утро запускается автоочистка автоскидок от 20%. Отклонены 6 заявок покупателей на скидку."),
 ("Цены", "Мешалка Hitachi: с 2 500 до 2 100 ₽ (раньше продавалась по ~1 800 ₽ из-за акций). Остальные цены не менялись."),
 ("Отчёты", "Сайт с 12 разделами (хаб задач, дашборд, товары, карточки, идеи, качество, медиа, акции, цены, экономия, бухгалтерия), данные обновляются каждое утро на сервере."),
]
sec3 = "<ul>" + "".join(f"<li><b>{e(a)}.</b> {e(b)}</li>" for a, b in done) + "</ul>"

# --- 4. Расходы и потенциал
S_it = sorted(S["items"], key=lambda s: -s["potential"])
sec4 = f"<p>Комиссия Ozon за период: <b>{rub(S['commission_sum'])}</b> ({S['commission_pct']}% выручки). Резерв без роста продаж: <b>{rub(S['expense_only_potential'])}</b> в месяц, с учётом упущенных заказов: <b>{rub(S['total_potential'])}</b> (около +{S['total_potential']/S['current_profit']*100:.0f}% к прибыли).</p>"
sec4 += table(["Направление", "Сейчас тратим", "Потенциал", "Уверенность"], [[e(s["lever"]), rub(s["current"]), rub(s["potential"]), e(s["confidence"])] for s in S_it], right=(1, 2))
sec4 += "<p class='note'>Оценки за 30 дней; фактический результат зависит от действий и объёма продаж.</p>"

# --- 5. Акции и цены
kp = PR["kpi"]; kz = PZ["kpi"]
sec5 = kpis([("Товаров в акциях", str(kp["products"]), f"{kp["participations"]} участий, средняя скидка {kp["avg_discount"]}%"),
             ("Советую убрать", str(kp["remove_products"]), "участий с невыгодной скидкой"),
             ("Автодобавление в акции", f"{kz['auto_add']} из {kz['products']}", "оставлено у товаров с выгодным бустом"),
             ("Баллы Ozon в цене покупателя", f"{kz['avg_points_share']}%", "доля скидки, которую платит Ozon")])
rows5 = [[f"<b>{e(r['offer_id'])}</b>", rub(r["price"]), rub(r["buyer_paid"]), rub(r["ozon_points"]), rub(r["breakeven"]), rub(r["price_m30"]), rub(r["profit_unit"])] for r in PZ["rows"] if r["orders"]]
sec5 += "<h3>Цены проданных товаров</h3>" + table(["Товар", "Ваша цена", "Покупатель платит", "Баллы Ozon", "Безубыточная", "Цена для маржи 30%", "Прибыль/шт"], rows5, right=(1, 2, 3, 4, 5, 6))
sec5 += "<p class='note'>«Покупатель платит» и «Баллы Ozon» — средние по фактическим заказам. Вы получаете с заказа вашу цену за вычетом комиссии и логистики; баллы за скидки финансирует Ozon.</p>"

# --- 6. Качество
sc = next((r for r in Q["ratings"] if r["key"] == "rating_review_avg_score_total"), None)
sec6 = kpis([("Оценка товаров", str(sc["value"]) if sc else "—", f"порог Premium {Q['premium_threshold']}"),
             ("Контент-рейтинг карточек", str(Q["content_avg"]), "в среднем, из 100"),
             ("Индекс ошибок FBS", str(Q["fbs_index"]["index"]), "период " + str(Q["fbs_index"]["from"]) + " — " + str(Q["fbs_index"]["to"])),
             ("Заявок на скидку", str(len(Q["discount_new"])), "ждут ответа")])
top_c = [c for c in Q["content"] if c["sales"] > 0][:6]
sec6 += "<h3>Контент-рейтинг проданных товаров и что его поднимет</h3>" + table(["Товар", "Рейтинг", "Что даст рост"], [[f"<b>{e(c['offer_id'])}</b>", str(c["rating"]), e("; ".join(m["what"] for m in c["improve"][:2]) or "всё выполнено")] for c in top_c], right=(1,))
sec6 += "<p class='note'>Главные рычаги везде одни: видео карточки, 8 и больше изображений, заполнение 70% атрибутов. Отзывы, вопросы и поисковые запросы через API недоступны без подписки Premium.</p>"

# --- 7. Задачи
pr = {"high": 0, "medium": 1, "low": 2}
open_t = sorted([t for t in TASKS if not t.get("done")], key=lambda t: (pr.get(t["priority"], 3), t["type"]))
lab = {"high": "высокий", "medium": "средний", "low": "низкий"}
sec7 = f"<p>Открыто {len(open_t)} задач, выполнено {len(TASKS) - len(open_t)}. Ниже открытые с высоким и средним приоритетом.</p>"
sec7 += table(["Приоритет", "Тип", "Задача"], [[e(lab.get(t["priority"], t["priority"])), e(t["type"]), f"<b>{e(t['title'])}</b>"] for t in open_t if t["priority"] in ("high", "medium")][:26])

# --- 8. Что нужно от вас
need = ["Загрузить видео установки в карточки втулок (файлы лежат на Яндекс Диске, AVTO/TOVARY).",
        "Проверить таблицу себестоимости: значения 3–5% от цены выглядят заниженными, от них зависит прибыль во всех разделах.",
        "Ответить на заявки покупателей на скидку (кабинет Ozon → Акции), если появятся новые.",
        "Подтвердить у брокера ТН ВЭД для втулок, мешалки, кольца, крепления отопителя и заглушки ГРМ.",
        "Фото для Toy_VT_Camry: в карточке только мелкие снимки, главный слайд не сделан.",
        "Продавать резинку наборами 5–10 шт. по 400–600 ₽ либо вывести из продажи: при 400 ₽ она почти не приносит прибыли.",
        "Решить, нужна ли подписка Premium: она открывает отзывы, вопросы, поисковые запросы и показы (до порога не хватает 0,03 к оценке товаров)."]
sec8 = "<ol>" + "".join(f"<li>{e(x)}</li>" for x in need) + "</ol>"

CSS = """
@page{size:A4;margin:16mm 14mm}
*{box-sizing:border-box}body{font:11.5px/1.5 'Segoe UI',Arial,sans-serif;color:#1b2430;margin:0}
h1{font-size:24px;margin:0 0 2px}h2{font-size:16px;margin:22px 0 8px;padding-bottom:4px;border-bottom:2px solid #2e9e40;color:#14622a;break-after:avoid}
h3{font-size:13px;margin:14px 0 6px}.sub{color:#6b7684;margin-bottom:14px}
.kpis{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.k{flex:1 1 30%;min-width:150px;border:1px solid #dfe5ea;border-radius:8px;padding:8px 10px}
.k .l{color:#6b7684;font-size:10.5px}.k .v{font-size:19px;font-weight:700}.k .s{font-size:10px;color:#6b7684}
table{width:100%;border-collapse:collapse;margin:6px 0;font-size:10.5px}th,td{padding:4px 6px;border-bottom:1px solid #e3e7ec;text-align:left;vertical-align:top}
th{color:#6b7684;font-size:9.5px;text-transform:uppercase;letter-spacing:.03em}td.r,th.r{text-align:right;white-space:nowrap}
tr{break-inside:avoid}.note{color:#6b7684;font-size:10px;margin:4px 0}.warn{border:1px solid #d97706;background:#fff8ed;border-radius:8px;padding:8px 10px;margin:10px 0}
ul,ol{margin:6px 0 6px 18px;padding:0}li{margin:3px 0}
"""
body = (f"<h1>Магазин HomeHelp на Ozon: отчёт</h1><div class='sub'>Данные за 30 дней на {date}. Сформирован автоматически из отчётов на сервере.</div>"
        f"{warn}<h2>1. Итоги периода</h2>{sec1}<h2>2. Продажи и прибыль по товарам</h2>{sec2}<h2>3. Что сделано</h2>{sec3}"
        f"<h2>4. Расходы и потенциал экономии</h2>{sec4}<h2>5. Акции и цены</h2>{sec5}<h2>6. Качество и рейтинг</h2>{sec6}"
        f"<h2>7. Открытые задачи</h2>{sec7}<h2>8. Что нужно от вас</h2>{sec8}")
name = f"Otchet_HomeHelp_kratko_{datetime.now().strftime('%Y-%m-%d')}"
hp = OUT / f"{name}.html"; hp.write_text(f"<!doctype html><html lang='ru'><head><meta charset='utf-8'><title>Отчёт HomeHelp {date}</title><style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
pdf = OUT / f"{name}.pdf"
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file:///" + str(hp).replace("\\", "/")], check=True, capture_output=True)
print("готово:", pdf, round(pdf.stat().st_size / 1024), "КБ")
