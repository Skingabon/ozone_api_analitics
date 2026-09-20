"""Правила -> рекомендации (data/tasks_seed.json). id стабильные, чтобы статусы не сбрасывались."""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = json.load(open(ROOT / "data/metrics.json", encoding="utf-8"))
P, K, today = M["products"], M["kpi"], date.today().isoformat()
tasks = []
def add(id, type, priority, title, desc):
    tasks.append({"id": id, "type": type, "priority": priority, "title": title, "description": desc,
                  "created": today, "done": False, "done_at": None, "source": "auto"})

cr = M.get("cost_ratio")
if cr and cr["max"] < 0.10:
    add("data-cost-check", "Данные", "high", "Проверить себестоимость",
        f"Себестоимость составляет {cr['min']*100:.1f}–{cr['max']*100:.1f}% от цены на Ozon при комиссии Ozon около 45–50%. "
        "Похоже на подстановку по формуле, а не реальные закупочные цены. Прибыль в дашбордах может быть завышена.")

canc = M["cancel"]; late = canc["reasons"].get("Вы не отгрузили заказ вовремя", 0)
if K["cancelled"] / max(K["orders"], 1) > 0.15:
    add("cancel-rate", "Заказы и логистика", "high", f"Снизить долю отмен ({K['cancelled']} из {K['orders']})",
        f"{late} заказов отменено из-за несвоевременной отгрузки. Проверить график сборки и лимиты FBS, "
        "включить уведомления о новых заказах, рассмотреть перевод ходовых позиций на FBO.")
sd = M["overhead"].get("DefectFineShipmentDelayRate", 0) + M["overhead"].get("DefectFineErrors", 0)
if sd < 0:
    add("fines-delay", "Расходы", "high", f"Устранить штрафы за просрочки и ошибки ({sd:.0f} ₽)",
        "Штрафы за нарушение сроков отгрузки и ошибки в отправлениях. Отгружать в день заказа, проверять комплектность.")
if M["overhead"].get("AcceleratedReviewCollection"):
    add("paid-reviews", "Расходы", "medium", "Оценить окупаемость платных отзывов",
        f"Ускоренный сбор отзывов: {M['overhead']['AcceleratedReviewCollection']:.0f} ₽. Сравнить с ростом заказов по этим товарам.")
for r in P:
    if r["units"] > 0 and r["profit"] is not None and r["profit"] < 0:
        add(f"loss-{r['offer_id']}", "Цены", "high", f"Убыточный товар: {r['offer_id']}",
            f"Прибыль {r['profit']:.0f} ₽ при выручке {r['sales']:.0f} ₽ (комиссия {r['commission_pct']}%, логистика {-r['delivery']:.0f} ₽). "
            "Поднять цену, снизить участие в акциях или вывести из продажи.")
    if r["commission_pct"] and r["commission_pct"] >= 45:
        add(f"comm-{r['offer_id']}", "Цены", "medium", f"Высокая комиссия {r['commission_pct']}%: {r['offer_id']}",
            "Проверить категорию и комиссию в кабинете, пересмотреть цену и участие в акциях.")
zero = [r["offer_id"] for r in P if r["stock"] == 0]
if zero:
    add("stock-zero", "Остатки", "medium", f"Нулевой остаток: {len(zero)} тов.", "Пополнить или скрыть карточки: " + ", ".join(zero))
nosale = [r for r in P if r["units"] == 0 and r["stock"] > 0]
if nosale:
    add("no-sales", "Карточки и продвижение", "high", f"{len(nosale)} товаров с остатком без продаж за 30 дней",
        "Обновить заголовки, фото, характеристики, подключить продвижение. Начать с 5 самых дорогих в закупке позиций.")
top = P[0] if P else None
if top and K["sales"] and top["sales"] / K["sales"] > 0.4:
    add("top-dependence", "Карточки и продвижение", "medium", f"Зависимость от одного товара: {top['offer_id']} ({top['sales']/K['sales']*100:.0f}% выручки)",
        "Вложиться в масштабирование хита (реклама, отзывы) и выровнять ассортимент, чтобы снизить риск.")
S = M.get("savings")
if S:
    add("comm-review", "Расходы", "high", f"Разобраться с комиссией {S['commission_pct']}% ({S['commission_sum']:.0f} ₽ за период)",
        f"Ставки 45–52% для запчастей необычно высоки. Проверить тарифы категорий в кабинете (Финансы → Тарифы), корректность категорий карточек, при расхождении написать в поддержку. Каждые −5 п.п. дают около {S['sensitivity'][1]['gain']} ₽ в месяц.")
    add("returns-cut", "Карточки и продвижение", "medium", "Снизить возвраты «товар не подошёл»",
        "Указать совместимость с моделями и годами авто, размеры, добавить схему установки и фото с размерами.")
    add("paid-services", "Расходы", "medium", "Пересмотреть платные услуги (Звёздные товары, ускоренные отзывы)",
        "Оставить только те, что дают рост заказов по хитам. Потенциал около 380 ₽ в месяц.")
CD = M.get("cards")
if CD:
    for o, c in sorted(CD["content"].items(), key=lambda x: x[1]["priority"]):
        add(f"card-{o}", "Карточки и продвижение", "high" if c["priority"] <= 3 else "medium", f"Обновить карточку {o}",
            "Название: " + c["title"] + ". Заполнить: " + ", ".join(c["attributes"]) + ". Хэштеги и подробности на странице «Карточки».")
    deep = [r for r in CD["rows"] if r.get("discount_pct") and r["discount_pct"] >= 30]
    if deep:
        add("promo-deep", "Цены", "high", f"Убрать из акций товары со скидкой 30% и больше ({len(deep)} шт.)",
            "Автоучастие отдаёт от 30% прайса: " + ", ".join(f"{r['offer_id']} (−{r['discount_pct']}%)" for r in deep) + ". Отключить в кабинете Ozon → Акции или поднять цену.")
    add("video-pdf", "Карточки и продвижение", "medium", "Загрузить видео установки и PDF для хитов", "Для Polo-sedan, Chery Tiggo 7 Pro, Chery Tiggo 4 Pro, Changan CS35: видео 30–60 секунд и инструкция.")
    add("reviews-push", "Карточки и продвижение", "high", "Набрать отзывы по хитам", "Вложение в посылку с просьбой оставить отзыв, отвечать на низкие оценки. Цель: 4.7+ и 30+ отзывов на хитах.")
Q = M.get("quality")
if Q:
    if Q["discount_new"]:
        ends = sorted({t["end_at"][:10] for t in Q["discount_new"]})[0]
        add("discount-requests", "Цены", "high", f"Ответить на заявки на скидку ({len(Q['discount_new'])} шт., первая истекает {ends})",
            "Покупатели просят скидку около 5% на 1 штуку. Открыть в кабинете Ozon → Акции → Заявки на скидку и принять или отклонить. Детали на странице «Качество».")
    sc = next((r for r in Q["ratings"] if r["key"] == "rating_review_avg_score_total"), None)
    if sc and Q["premium_threshold"] and sc["value"] < Q["premium_threshold"]:
        add("rating-premium", "Карточки и продвижение", "medium", f"Довести оценку товаров с {sc['value']} до {Q['premium_threshold']}",
            "Порог даёт статус Premium и доступ к аналитике запросов и отзывам. Нужны свежие хорошие отзывы: вложение в посылку и корректные описания без завышенных обещаний.")
    for c in [x for x in Q["content"] if x["sales"] > 0 and x["rating"] < 85][:6]:
        add(f"content-{c['offer_id']}", "Карточки и продвижение", "medium", f"Поднять контент-рейтинг {c['offer_id']} ({c['rating']})",
            "Главное: " + "; ".join(m["what"] for m in c["improve"][:2]) + ".")
PR = M.get("promos")
if PR:
    rm = sorted({p["offer_id"] for p in PR["participation"] if p["advice"] == "remove"})
    if rm:
        add("promo-remove", "Цены", "high", f"Убрать из акций: {len(rm)} тов. с невыгодной скидкой",
            "Советую убрать: " + ", ".join(rm) + ". Детали и причины на странице «Акции».")
    jn = sorted({c["offer_id"] for c in PR["candidates"] if c["advice"] == "join"})
    if jn:
        add("promo-join", "Цены", "low", f"Можно подключить к акциям с небольшой скидкой ({len(jn)} тов.)",
            "Скидка почти незаметна, а видимость выше: " + ", ".join(jn[:12]) + ". Список на странице «Акции».")
    if PR["changes"]["added"]:
        add("promo-readded", "Цены", "medium", f"Ozon вернул товары в акции ({len(PR['changes']['added'])} шт.), автоочистка убрала скидки от 20%",
            "С прошлой проверки добавлены: " + ", ".join(f"{x['offer_id']} ({x['action'][:24]})" for x in PR["changes"]["added"][:8]) + ".")
PZ = M.get("prices")
if PZ:
    if PZ["kpi"].get("auto_add_unwanted"):
        add("auto-add-off", "Цены", "high", f"Автодобавление в акции снова включено у {PZ['kpi']['auto_add_unwanted']} тов.",
            "Пока эта настройка включена, Ozon сам возвращает товары в акции со скидкой. Отключение: кабинет → Цены и акции → выбрать товары → «Автоматически добавлять в акции Ozon» → выключить. Список на странице «Цены».")
    low = [r["offer_id"] for r in PZ["rows"] if r["breakeven"] and r["price"] < r["breakeven"]]
    if low:
        add("price-below-breakeven", "Цены", "high", f"Цена ниже безубыточной: {', '.join(low[:5])}",
            "Продажа по этим ценам не покрывает комиссию, логистику и себестоимость. Безубыточная цена и цена для маржи 30% на странице «Цены».")
add("acct-monthly", "Бухгалтерия", "low", "Сверить баланс и начисления за месяц",
    "Сверить раздел «Бухгалтерия» с отчётом о реализации в кабинете Ozon и выплатами на счёт.")
(ROOT / "data/tasks_seed.json").write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(tasks), "задач:"); [print(" -", t["priority"], t["type"], "|", t["title"]) for t in tasks]
