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
add("acct-monthly", "Бухгалтерия", "low", "Сверить баланс и начисления за месяц",
    "Сверить раздел «Бухгалтерия» с отчётом о реализации в кабинете Ozon и выплатами на счёт.")
(ROOT / "data/tasks_seed.json").write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(tasks), "задач:"); [print(" -", t["priority"], t["type"], "|", t["title"]) for t in tasks]
