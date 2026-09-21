"use strict";
/* Полный отчёт: все разделы сайта подряд, на первой странице оглавление со ссылками на каждый раздел. Печатается в PDF (Ctrl+P или collector/make_full_report.py). */
window.buildReport = async (D, fns) => {
  const SECTIONS = [
    ["hub", "Хаб", "Хаб отчётов и задач", "Все задачи со статусами, приоритетами и историей (сделано или нет)"],
    ["dashboard", "Дашборд", "Дашборд магазина", "Выручка, прибыль, расходы, начисления и заказы по дням, причины отмен"],
    ["products", "Товары", "Товары и прибыль", "Все товары: цена, остаток, продажи, комиссия, логистика, себестоимость, прибыль"],
    ["cards", "Карточки", "Карточки: аудит и акции", "SEO-аудит, сравнение с конкурентами, готовые тексты, состояние карточек"],
    ["ideas", "Идеи", "Что печатать и продавать", "Ниши для 3D-печати, калькулятор окупаемости, план проверки"],
    ["quality", "Качество", "Качество и рейтинг", "Рейтинг продавца, контент-рейтинг карточек, заявки на скидку, компенсации"],
    ["media", "Медиа", "Фото и видео товаров", "Папки Яндекс Диска по товарам и списки видео"],
    ["promos", "Акции", "Акции Ozon", "Где товары в акциях, что убрать, куда вступить, изменения за сутки"],
    ["prices", "Цены", "Цены на товары", "Цена продавца, что платит покупатель, баллы Ozon, безубыточная цена"],
    ["savings", "Экономия", "Снижение расходов", "Где и как сократить расходы, сколько это даст"],
    ["accounting", "Бухгалтерия", "Бухгалтерия", "Баланс, движение денег по неделям, услуги Ozon, начисления"],
  ];
  // задачи: живые с сервера (файл рядом), иначе из расчёта
  let tasks = null;
  try { const r = await fetch("tasks_live.json", { cache: "no-store" }); if (r.ok) tasks = await r.json(); } catch { }
  const realFetch = window.fetch.bind(window);
  window.fetch = (u, o) => (String(u).indexOf("api/tasks") === 0 && tasks)
    ? Promise.resolve(new Response(JSON.stringify(tasks), { status: 200, headers: { "Content-Type": "application/json" } })) : realFetch(u, o);

  const K = D.kpi, margin = K.sales ? K.profit_total / K.sales * 100 : 0;
  const app = document.getElementById("app");
  app.innerHTML = `<section class="cover" id="toc"><div class="cover-h">HomeHelp · Ozon</div><h1 style="font-size:34px">Полный отчёт по магазину</h1>
    <p class="mut">Данные за 30 дней · обновлено ${esc(new Date(D.generated_at).toLocaleString("ru-RU"))}</p>
    <div class="grid kpis" style="margin:18px 0">${kpi("Выручка", rub(K.sales), `${K.orders} заказов, отменено ${K.cancelled}`)}${kpi("Прибыль после себестоимости", rub(K.profit_total), `маржа ${margin.toFixed(0)}%`, cls(K.profit_total))}${kpi("Общие расходы", rub(K.overhead), "штрафы и прочее", cls(K.overhead))}${kpi("Товаров с продажами", `${K.sku_sold} из ${K.sku_total}`, `остаток ${num(K.stock_units)} шт`)}${kpi("Баланс к выплате", rub(K.closing_balance), "на конец периода")}</div>
    ${D.cost_ratio && D.cost_ratio.max < 0.10 ? `<div class="banner">Себестоимость составляет ${(D.cost_ratio.min * 100).toFixed(1)}–${(D.cost_ratio.max * 100).toFixed(1)}% от цены: похоже, введены не реальные закупочные цены, прибыль может быть завышена. Проверьте таблицу себестоимости.</div>` : ""}
    <h2>Оглавление</h2><p class="mut" style="font-size:13px">Нажмите на название раздела, чтобы перейти к нему. В каждом разделе сверху есть ссылка «← Оглавление».</p>
    <ol class="toc">${SECTIONS.map(([k, n, , d]) => `<li><a href="#sec-${k}">${esc(n)}</a><span class="mut"> — ${esc(d)}</span></li>`).join("")}</ol></section>`;

  let i = 0;
  for (const [key, name, title] of SECTIONS) {
    i++;
    const sec = document.createElement("section");
    sec.className = "rp"; sec.id = "sec-" + key;
    sec.innerHTML = `<div class="rp-top"><a href="#toc">← Оглавление</a> <span class="mut">· ${i} из ${SECTIONS.length}</span></div><h1>${i}. ${esc(title)}</h1><div id="c"></div>`;
    app.appendChild(sec);
    try { await fns[key](D); } catch (e) { sec.querySelector("#c").innerHTML = `<p class="bad">Раздел не удалось собрать: ${esc(e.message)}</p>`; }
    sec.querySelectorAll("[id]").forEach(el => el.removeAttribute("id"));   // освободить id для следующего раздела
    sec.id = "sec-" + key;
  }
  // ссылки на страницы сайта -> внутренние ссылки отчёта; на csv-файлы -> обычный текст
  const map = { "index.html": "hub" }; SECTIONS.forEach(([k]) => (map[k + ".html"] = k));
  app.querySelectorAll("a[href]").forEach(a => {
    const h = a.getAttribute("href");
    if (map[h]) a.setAttribute("href", "#sec-" + map[h]);
    else if (/\.csv$/.test(h)) { const s = document.createElement("span"); s.innerHTML = a.innerHTML; a.replaceWith(s); }
  });
  document.body.dataset.ready = "1";
};
