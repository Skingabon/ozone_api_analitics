"use strict";
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const rub = v => v == null ? "—" : Math.round(v).toLocaleString("ru-RU") + " ₽";
const num = v => v == null ? "—" : Number(v).toLocaleString("ru-RU");
const cls = v => v == null ? "" : v < 0 ? "bad" : v > 0 ? "good" : "";
const page = document.body.dataset.page;

const NAV = [["index.html", "Хаб", "hub"], ["dashboard.html", "Дашборд", "dashboard"], ["products.html", "Товары", "products"], ["cards.html", "Карточки", "cards"], ["ideas.html", "Идеи", "ideas"], ["quality.html", "Качество", "quality"], ["media.html", "Медиа", "media"], ["promos.html", "Акции", "promos"], ["savings.html", "Экономия", "savings"], ["accounting.html", "Бухгалтерия", "accounting"]];
function shell(title, upd) {
  $("#app").innerHTML = `<header><div class="wrap"><span class="logo">HomeHelp · Ozon</span><nav>${NAV.map(n => `<a href="${n[0]}" class="${n[2] === page ? "on" : ""}">${n[1]}</a>`).join("")}</nav><span class="upd">${upd || ""}</span></div></header><main><div class="wrap"><h1>${title}</h1><div id="c"></div></div></main>`;
}

function bars(items, { fmt = rub, signed = false } = {}) {
  const max = Math.max(...items.map(i => Math.abs(i[1])), 1);
  return `<div class="bars">${items.map(([l, v]) => `<div class="row"><span class="lab" title="${esc(l)}">${esc(l)}</span><span class="track"><span class="fill ${signed ? (v < 0 ? "neg" : "pos") : ""}" style="display:block;width:${Math.abs(v) / max * 100}%"></span></span><span class="val ${signed ? cls(v) : ""}">${fmt(v)}</span></div>`).join("")}</div>`;
}

function dayChart(days, key, color) {
  const ks = Object.keys(days); if (!ks.length) return "<p class=mut>Нет данных</p>";
  const vals = ks.map(k => days[k][key] || 0), max = Math.max(...vals, 1), min = Math.min(...vals, 0);
  const W = 720, H = 180, bw = W / ks.length, span = max - min || 1, y0 = H - 20 - (0 - min) / span * (H - 30);
  const rects = ks.map((k, i) => { const v = vals[i], h = Math.abs(v) / span * (H - 30); return `<rect x="${i * bw + 1}" y="${v >= 0 ? y0 - h : y0}" width="${Math.max(bw - 2, 1)}" height="${Math.max(h, 1)}" fill="${v >= 0 ? color : "var(--bad)"}"><title>${k}: ${rub(v)}</title></rect>`; }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="График по дням"><line x1="0" x2="${W}" y1="${y0}" y2="${y0}" stroke="var(--line)"/>${rects}<text x="0" y="${H - 4}">${ks[0]}</text><text x="${W}" y="${H - 4}" text-anchor="end">${ks[ks.length - 1]}</text></svg>`;
}

function kpi(l, v, s = "", c = "") { return `<div class="card kpi"><div class="l">${l}</div><div class="v ${c}">${v}</div><div class="s">${s}</div></div>`; }

function table(cols, rows, { sortable = true } = {}) {
  return `<div class="scroll"><table><thead><tr>${cols.map((c, i) => `<th class="${c.n ? "n " : ""}${sortable ? "sort" : ""}" data-i="${i}">${c.h}</th>`).join("")}</tr></thead><tbody>${rows.map(r => `<tr>${cols.map(c => `<td class="${c.n ? "n " : ""}${c.c ? c.c(r) : ""}">${c.f(r)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function makeSortable(root, cols, rows, redraw) {
  let dir = 1, last = -1;
  root.querySelectorAll("th.sort").forEach(th => th.onclick = () => {
    const i = +th.dataset.i, c = cols[i]; if (!c.k) return;
    dir = last === i ? -dir : -1; last = i;
    rows.sort((a, b) => { const x = c.k(a), y = c.k(b); return (x == null) - (y == null) || (x > y ? 1 : x < y ? -1 : 0) * dir; });
    redraw();
  });
}

/* ---------- Дашборд ---------- */
function dashboard(D) {
  const K = D.kpi, P = D.products;
  const margin = K.sales ? K.profit_total / K.sales * 100 : 0;
  const warn = D.cost_ratio && D.cost_ratio.max < 0.10 ? `<div class="banner">Себестоимость составляет ${(D.cost_ratio.min * 100).toFixed(1)}–${(D.cost_ratio.max * 100).toFixed(1)}% от цены — прибыль может быть завышена. Проверьте закупочные цены (задача в хабе).</div>` : "";
  const topProfit = P.filter(p => p.profit != null && p.units > 0).sort((a, b) => b.profit - a.profit);
  const byType = Object.entries(D.by_type).sort((a, b) => a[1] - b[1]);
  $("#c").innerHTML = warn + `<div class="grid kpis">
    ${kpi("Выручка (30 дн.)", rub(K.sales), `${K.orders} заказов, отменено ${K.cancelled}`)}
    ${kpi("Прибыль после себестоимости", rub(K.profit_total), `маржа ${margin.toFixed(1)}%`, cls(K.profit_total))}
    ${kpi("Общие расходы (штрафы и пр.)", rub(K.overhead), "не привязаны к товарам", cls(K.overhead))}
    ${kpi("Товаров с продажами", `${K.sku_sold} из ${K.sku_total}`, `остаток ${num(K.stock_units)} шт`)}
    ${kpi("Баланс к выплате", rub(K.closing_balance), "на конец периода")}</div>
  <div class="grid two"><div class="card"><h2>Начисления по дням, чистая сумма</h2>${dayChart(D.days, "net", "var(--bar)")}</div>
  <div class="card"><h2>Заказы по дням</h2>${dayChart(Object.fromEntries(Object.entries(D.orders_day).map(([k, v]) => [k, { n: v }])), "n", "var(--acc)")}</div></div>
  <div class="grid two"><div class="card"><h2>Прибыль по товарам</h2>${bars(topProfit.map(p => [p.offer_id, p.profit]), { signed: true })}<p class="note">Выручка − комиссия − логистика − сборы − себестоимость.</p></div>
  <div class="card"><h2>Куда уходят деньги</h2>${bars(byType.map(([k, v]) => [k, v]), { signed: true })}</div></div>
  <div class="card"><h2>Причины отмен</h2>${bars(Object.entries(D.cancel.reasons).sort((a, b) => b[1] - a[1]), { fmt: v => v + " шт" })}</div>`;
}

/* ---------- Товары ---------- */
function products(D) {
  const rows = D.products.slice();
  const cols = [
    { h: "Артикул", f: r => `<b>${esc(r.offer_id)}</b><div class="mut" style="font-size:12px">${esc(r.name.slice(0, 70))}</div>`, k: r => r.offer_id },
    { h: "Цена", n: 1, f: r => rub(r.price), k: r => r.price },
    { h: "Остаток", n: 1, f: r => num(r.stock), k: r => r.stock },
    { h: "Продано", n: 1, f: r => num(r.units), k: r => r.units },
    { h: "Выручка", n: 1, f: r => rub(r.sales), k: r => r.sales },
    { h: "Комиссия", n: 1, f: r => r.commission_pct == null ? "—" : r.commission_pct + "%", k: r => r.commission_pct },
    { h: "Логистика", n: 1, f: r => rub(r.delivery), k: r => r.delivery },
    { h: "Себестоимость", n: 1, f: r => rub(r.cogs), k: r => r.cogs },
    { h: "Прибыль", n: 1, f: r => rub(r.profit), c: r => cls(r.profit), k: r => r.profit },
    { h: "Маржа", n: 1, f: r => r.margin_pct == null ? "—" : r.margin_pct + "%", c: r => cls(r.margin_pct), k: r => r.margin_pct }];
  $("#c").innerHTML = `<div class="filters"><label>Поиск<input id="q" placeholder="артикул или название"></label><label>Показать<select id="f"><option value="all">все</option><option value="sold">с продажами</option><option value="nosale">без продаж (есть остаток)</option><option value="loss">убыточные</option></select></label></div><div class="card" id="t"></div>`;
  const draw = () => {
    const q = $("#q").value.toLowerCase(), f = $("#f").value;
    const v = rows.filter(r => (!q || (r.offer_id + r.name).toLowerCase().includes(q)) && (f === "all" || (f === "sold" && r.units > 0) || (f === "nosale" && r.units === 0 && r.stock > 0) || (f === "loss" && r.profit < 0)));
    $("#t").innerHTML = table(cols, v); makeSortable($("#t"), cols, rows, draw);
  };
  $("#q").oninput = draw; $("#f").onchange = draw; draw();
}

/* ---------- Бухгалтерия ---------- */
function accounting(D) {
  const b = D.balance, t = b.total, cf = b.cashflows;
  const money = m => m && m.value != null ? m.value : null;
  const cfRows = D.cash_flow.map(w => ({ p: w.period.begin.slice(0, 10) + " — " + w.period.end.slice(0, 10), ...w }));
  const cols = [{ h: "Период", f: r => r.p }, { h: "Заказы", n: 1, f: r => rub(r.orders_amount) }, { h: "Возвраты", n: 1, f: r => rub(r.returns_amount), c: r => cls(r.returns_amount) },
    { h: "Комиссия", n: 1, f: r => rub(r.commission_amount) }, { h: "Услуги", n: 1, f: r => rub(r.services_amount) }, { h: "Доставка/возвраты", n: 1, f: r => rub(r.item_delivery_and_return_amount) }];
  const services = (cf.services || []).map(s => [s.name, money(s.amount) ?? s.amount?.value ?? 0]);
  $("#c").innerHTML = `<div class="grid kpis">
    ${kpi("Остаток на начало", rub(t.opening_balance.value))}${kpi("Начислено", rub(t.accrued.value), "", cls(t.accrued.value))}
    ${kpi("Выплачено", rub((t.payments || []).reduce((s, p) => s + p.value, 0)))}${kpi("Остаток на конец", rub(t.closing_balance.value))}</div>
  <div class="grid two"><div class="card"><h2>Продажи и возвраты</h2>${bars([["Продажи", money(cf.sales.amount)], ["Комиссия с продаж", money(cf.sales.fee)], ["Возвраты", money(cf.returns.amount)], ["Комиссия по возвратам", money(cf.returns.fee)]].filter(x => x[1] != null), { signed: true })}</div>
  <div class="card"><h2>Услуги Ozon</h2>${services.length ? bars(services, { signed: true }) : "<p class=mut>Нет данных</p>"}</div></div>
  <div class="card"><h2>Движение денег по неделям</h2>${table(cols, cfRows, { sortable: false })}</div>
  <div class="card"><h2>Начисления по типам за период</h2>${bars(Object.entries(D.by_type).sort((a, b) => a[1] - b[1]), { signed: true })}</div>
  <div class="card"><h2>Выгрузки для бухгалтера</h2><p><a href="accruals.csv" download>Начисления (CSV)</a> · <a href="products.csv" download>Прибыль по товарам (CSV)</a></p><p class="note">Файлы в кодировке UTF-8 с разделителем «;», открываются в Excel.</p></div>`;
}

/* ---------- Экономия ---------- */
function savings(D) {
  const S = D.savings, sv = S.items.slice().sort((a, b) => b.potential - a.potential);
  const conf = { "высокая": "good", "средняя": "warn", "низкая": "mut" };
  const rows = sv.map(s => `<tr><td><b>${esc(s.lever)}</b><div class="mut" style="font-size:13px">${esc(s.how)}</div><div class="note">${esc(s.basis)}</div></td><td class="n">${rub(s.current)}</td><td class="n good"><b>${rub(s.potential)}</b></td><td class="${conf[s.confidence] || ""}">${esc(s.confidence)}</td></tr>`).join("");
  const pctUp = S.current_profit > 0 ? Math.round(S.total_potential / S.current_profit * 100) : 0;
  $("#c").innerHTML = `<div class="grid kpis">
    ${kpi("Комиссия Ozon за период", rub(S.commission_sum), `${S.commission_pct}% от выручки`, "bad")}
    ${kpi("Резерв без роста продаж", rub(S.expense_only_potential), "штрафы, убыточные, услуги, возвраты", "good")}
    ${kpi("Резерв с учётом упущенных заказов", rub(S.total_potential), `≈ +${pctUp}% к текущей прибыли (${rub(S.current_profit)})`, "good")}</div>
  <div class="card"><h2>Где сократить расходы и что это даст (₽ в месяц)</h2><div class="scroll"><table><thead><tr><th>Направление и что делать</th><th class="n">Сейчас тратим</th><th class="n">Потенциал</th><th>Уверенность</th></tr></thead><tbody>${rows}</tbody></table></div><p class="note">${esc(S.note)}</p></div>
  <div class="grid two"><div class="card"><h2>Комиссия: что даст снижение</h2><p class="mut" style="font-size:14px">Комиссия зависит от категории товара и утверждается Ozon; от схемы (FBO/FBS/rFBS) она не меняется. Ниже — эффект на текущем объёме продаж.</p>${table([{ h: "Снижение ставки", f: r => "−" + r.points + " п.п." }, { h: "Экономия в месяц", n: 1, f: r => rub(r.gain), c: () => "good" }], S.sensitivity, { sortable: false })}
    <p class="note">Ставки 45–52% для запчастей необычно высоки. Проверьте в кабинете (Финансы → Тарифы) актуальную ставку категории и, если она не совпадает, обратитесь в поддержку с номерами отправлений. Точную причину по API определить нельзя.</p></div>
  <div class="card"><h2>Логистика: расходы по услугам</h2>${bars(S.logistics.map(x => [`${x.name} (${x.count})`, x.sum]), { signed: true })}<p class="note">В скобках — число операций.</p></div></div>
  <div class="card"><h2>Категории и ставки комиссии</h2>${table([{ h: "Категория", f: r => esc(r.name) }, { h: "Товаров", n: 1, f: r => r.products }, { h: "Ставка", n: 1, f: r => r.percent == null ? "—" : r.percent + "%" }, { h: "Выручка", n: 1, f: r => rub(r.sales) }, { h: "Комиссия", n: 1, f: r => rub(r.commission) }], S.categories, { sortable: false })}<p class="note">Проверьте, что карточки лежат в правильной категории: неверная категория даёт другую ставку и хуже ранжируется.</p></div>`;
}

/* ---------- Карточки ---------- */
function cards(D) {
  const C = D.cards, rows = C.rows;
  const sev = { high: "p-high", medium: "p-medium", low: "p-low" }, sevT = { high: "критично", medium: "важно", low: "желательно" };
  const inActs = rows.filter(r => r.actions.length), disc = inActs.filter(r => r.discount_pct != null);
  const avgDisc = disc.length ? Math.round(disc.reduce((s, r) => s + r.discount_pct, 0) / disc.length) : 0;
  const noKey = rows.filter(r => r.missing_key.length).length;
  const priceCols = [
    { h: "Товар", f: r => `<b>${esc(r.offer_id)}</b>`, k: r => r.offer_id },
    { h: "Прайс", n: 1, f: r => rub(r.list_price), k: r => r.list_price },
    { h: "В акциях", n: 1, f: r => r.action_low == null ? "нет" : rub(r.action_low), k: r => r.action_low },
    { h: "Скидка", n: 1, f: r => r.discount_pct == null ? "—" : r.discount_pct + "%", c: r => r.discount_pct >= 30 ? "bad" : "", k: r => r.discount_pct },
    { h: "Комиссия", n: 1, f: r => r.commission_pct + "%", k: r => r.commission_pct },
    { h: "Чистыми по прайсу", n: 1, f: r => rub(r.net_list), k: r => r.net_list },
    { h: "Чистыми в акции", n: 1, f: r => rub(r.net_action), k: r => r.net_action },
    { h: "Потеря на единице", n: 1, f: r => r.net_action == null ? "—" : rub(r.net_action - r.net_list), c: r => r.net_action != null && r.net_action < r.net_list ? "bad" : "", k: r => r.net_action == null ? null : r.net_action - r.net_list },
    { h: "Акции", f: r => r.actions.length ? r.actions.map(a => `<div class="mut" style="font-size:12px">${esc(a.action)} — ${rub(a.price)}${a.mode === "MANUAL" ? " (вручную)" : ""}</div>`).join("") : "—" }];
  const health = [
    { h: "Товар", f: r => `<b>${esc(r.offer_id)}</b>`, k: r => r.offer_id },
    { h: "Оценка", n: 1, f: r => r.score + "/100", c: r => r.score < 60 ? "bad" : r.score < 80 ? "warn" : "good", k: r => r.score },
    { h: "Продано", n: 1, f: r => r.units, k: r => r.units },
    { h: "Хэштегов", n: 1, f: r => r.hashtags + "/30", c: r => r.hashtags < 8 ? "bad" : "", k: r => r.hashtags },
    { h: "Фото", n: 1, f: r => r.photos, k: r => r.photos },
    { h: "Описание", n: 1, f: r => r.desc_len + " симв.", k: r => r.desc_len },
    { h: "Не заполнено (подбор по авто)", f: r => r.missing_key.length ? esc(r.missing_key.join(", ")) : "<span class=good>всё заполнено</span>" }];
  const compBlocks = C.competitors.map(c => `<div class="card"><h2>${esc(c.offer_id)}: запрос «${esc(c.query)}»</h2>
    <p style="font-size:14px"><b>Ваша карточка:</b> ${esc(c.mine.title)}${c.mine.price ? ` — <b>${rub(c.mine.price)}</b>, рейтинг ${c.mine.rating ?? "—"}, отзывов ${c.mine.reviews ?? "—"}` : ""}</p>
    ${table([{ h: "Конкурент", f: r => esc(r.title) }, { h: "Цена", n: 1, f: r => rub(r.price) }, { h: "Рейтинг", n: 1, f: r => r.rating ?? "—" }, { h: "Отзывов", n: 1, f: r => r.reviews ?? "—" }], c.others, { sortable: false })}
    <p class="note">${esc(c.note)}</p></div>`).join("");
  const order = Object.entries(C.content).sort((a, b) => a[1].priority - b[1].priority);
  const rowOf = o => rows.find(r => r.offer_id === o) || {};
  const cardBlocks = order.map(([o, c]) => { const r = rowOf(o); return `<div class="card"><h2>${c.priority}. ${esc(o)} <span class="tag">оценка ${r.score ?? "—"}/100</span> <span class="tag">продано ${r.units ?? 0}</span></h2>
    <div class="grid two"><div><b>Что не так</b><ul>${c.problems.map(p => `<li>${esc(p)}</li>`).join("")}</ul>
      ${r.queries && r.queries.length ? `<b>Реальные запросы (30 дн., пользователей)</b>${bars(r.queries.slice(0, 6).map(x => [x.q, x.users]), { fmt: v => num(v) })}` : ""}</div>
    <div><b>Как сейчас</b><p class="mut" style="font-size:14px">${esc(r.name)}</p>
      <b>Предлагаемое название</b><p style="font-size:14px">${esc(c.title)}</p>
      <b>Поле «Название модели» (9048)</b><p style="font-size:14px">${esc(c.model_name_9048)}</p>
      <b>Хэштеги</b><p class="mut" style="font-size:13px;word-break:break-word">${esc(c.hashtags)}</p>
      <b>Заполнить</b><ul>${Object.entries(c.attributes).map(([k, v]) => `<li><b>${esc(k)}:</b> ${esc(v)}</li>`).join("")}</ul>
      ${c.extra.length ? `<b>Ещё</b><ul>${c.extra.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}</div></div></div>`; }).join("");
  $("#c").innerHTML = (C.applied ? `<div class="card" style="border-color:var(--good)"><b class="good">Правки внесены ${esc(C.applied.date)}.</b> ${esc(C.applied.text)}</div>` : "") + `<div class="grid kpis">
    ${kpi("Товаров в акциях", `${inActs.length} из ${rows.length}`, "почти все включены автоматически", inActs.length > rows.length / 2 ? "warn" : "")}
    ${kpi("Средняя скидка в акциях", avgDisc + "%", "от вашего прайса, платите вы", avgDisc >= 25 ? "bad" : "")}
    ${kpi("Карточек без марки/модели авто", `${noKey}`, "не попадают в подбор по автомобилю", noKey ? "bad" : "good")}
    ${kpi("Логистика на единицу", rub(C.median_delivery), "медиана по проданным товарам")}</div>
  <div class="card"><h2>Главные проблемы карточек</h2>${C.systemic.map(x => `<div style="margin:10px 0"><span class="tag ${sev[x.severity]}">${sevT[x.severity]}</span> <b>${esc(x.title)}</b><div style="font-size:14px;margin-top:4px">${esc(x.text)}</div><div class="good" style="font-size:14px;margin-top:4px"><b>Что сделать:</b> ${esc(x.fix)}</div></div>`).join("")}</div>
  <div class="card"><h2>Цены и участие в акциях</h2><div id="pt"></div><p class="note">«Чистыми» = цена × (1 − комиссия) − логистика на единицу, без себестоимости. Акционная цена — то, что получаете вы; покупатель платит меньше за счёт баллов Ozon, но скидку от прайса оплачиваете вы.</p></div>
  <div class="card"><h2>Что делать с акциями</h2><ul>${Object.entries(C.actions_advice).map(([k, v]) => `<li><b>${esc(k)}.</b> ${esc(v)}</li>`).join("")}</ul></div>
  <div class="card"><h2>Состояние карточек</h2><div id="ht"></div></div>
  <h2 style="margin-top:22px">Сравнение с конкурентами (выдача Ozon на ${esc(C.checked_at)})</h2>${compBlocks}
  <h2 style="margin-top:22px">Готовые правки по карточкам, по убыванию важности</h2>${cardBlocks}
  <p class="note">Тексты и значения атрибутов подготовлены по данным карточек и выдачи. Совместимость по годам и OEM-номера перед загрузкой сверьте по каталогу.</p>`;
  const rp = rows.slice().sort((a, b) => (b.discount_pct ?? -1) - (a.discount_pct ?? -1));
  const drawP = () => { $("#pt").innerHTML = table(priceCols, rp); makeSortable($("#pt"), priceCols, rp, drawP); }; drawP();
  const rh = rows.slice(); const drawH = () => { $("#ht").innerHTML = table(health, rh); makeSortable($("#ht"), health, rh, drawH); }; drawH();
}

/* ---------- Идеи ---------- */
function ideas(D) {
  const I = D.ideas, vc = { "продолжать": "good", "расширять": "good", "делать": "good", "только комплектами": "warn", "менять формат": "warn", "гипотеза, проверить": "warn", "не рекомендуется": "bad" };
  const med = (D.cards && D.cards.median_delivery) || 100;
  const rowsN = I.niches.map(n => `<div class="card"><h2>${esc(n.name)} <span class="tag ${vc[n.verdict] === "bad" ? "p-high" : vc[n.verdict] === "warn" ? "p-medium" : ""}">${esc(n.verdict)}</span></h2>
    <div class="grid two"><div><b>Что видно на Ozon</b><p style="font-size:14px">${esc(n.evidence)}</p><p class="note">Статус данных: ${esc(n.status)}. Цены на витрине: ${esc(n.price)}.</p></div>
    <div><b>Риски</b><p style="font-size:14px">${esc(n.risk)}</p><b>Что делать</b><p style="font-size:14px" class="${vc[n.verdict] || ""}">${esc(n.action)}</p></div></div></div>`).join("");
  $("#c").innerHTML = `<div class="card"><h2>Принципы отбора</h2><ul>${I.principles.map(p => `<li>${esc(p)}</li>`).join("")}</ul></div>
  <div class="card"><h2>Калькулятор: окупится ли товар на Ozon</h2>
    <div class="filters">
      <label>Цена, которую получаете (после скидок), ₽<input id="k_p" type="number" value="1200" min="0"></label>
      <label>Себестоимость печати, ₽<input id="k_c" type="number" value="150" min="0"></label>
      <label>Комиссия, %<input id="k_k" type="number" value="48" min="0" max="90"></label>
      <label>Логистика, ₽<input id="k_l" type="number" value="${med}" min="0"></label>
      <label>Упаковка, ₽<input id="k_u" type="number" value="15" min="0"></label>
      <label>Нужная маржа, %<input id="k_m" type="number" value="30" min="0" max="80"></label></div>
    <div class="grid kpis" id="k_out"></div><p class="note">Комиссия и логистика по умолчанию взяты из ваших фактических начислений. Отмены, возвраты и штрафы в расчёт не входят.</p></div>
  <h2 style="margin-top:22px">Ниши</h2>${rowsN}
  <div class="card"><h2>План проверки на 30 дней</h2><ol>${I.test_plan.map(p => `<li>${esc(p)}</li>`).join("")}</ol></div>
  <p class="note">Данные выдачи Ozon сняты вручную ${esc(I.checked_at)}: цена и число отзывов показывают спрос, но не точные продажи.</p>`;
  const calc = () => {
    const v = id => parseFloat($("#" + id).value) || 0, p = v("k_p"), c = v("k_c"), k = v("k_k") / 100, l = v("k_l"), u = v("k_u"), m = v("k_m") / 100;
    const net = p * (1 - k) - l - u - c, mg = p ? net / p * 100 : 0, denom = 1 - k - m, minP = denom > 0 ? (l + u + c) / denom : null;
    $("#k_out").innerHTML = kpi("Прибыль с единицы", rub(net), "", cls(net)) + kpi("Маржа", mg.toFixed(1) + "%", "от цены", mg >= m * 100 ? "good" : mg > 0 ? "warn" : "bad") + kpi("Мин. цена для нужной маржи", minP == null ? "невозможно" : rub(minP), "при заданных расходах");
  };
  document.querySelectorAll("#k_p,#k_c,#k_k,#k_l,#k_u,#k_m").forEach(e => e.oninput = calc); calc();
}

/* ---------- Качество ---------- */
function quality(D) {
  const Q = D.quality, gs = { OK: "good", WARNING: "warn", CRITICAL: "bad" };
  const score = Q.ratings.find(r => r.key === "rating_review_avg_score_total");
  const prog = Q.ratings.find(r => r.key.includes("progress") || r.name.includes("прогрессив"));
  const need = Q.premium_threshold && score ? (Q.premium_threshold - score.value) : null;
  const rateCols = [{ h: "Группа", f: r => esc(r.group) }, { h: "Показатель", f: r => esc(r.name) },
    { h: "Сейчас", n: 1, f: r => r.value, k: r => r.value }, { h: "Было", n: 1, f: r => r.past },
    { h: "Статус", f: r => `<span class="${gs[r.status] || "mut"}">${esc({ OK: "норма", WARNING: "внимание", CRITICAL: "критично", UNKNOWN_STATUS: "нет данных" }[r.status] || r.status)}</span>` }];
  const cRows = Q.content.slice();
  const cCols = [{ h: "Товар", f: r => `<b>${esc(r.offer_id)}</b>`, k: r => r.offer_id },
    { h: "Контент-рейтинг", n: 1, f: r => r.rating, c: r => r.rating < 60 ? "bad" : r.rating < 80 ? "warn" : "good", k: r => r.rating },
    { h: "Продажи", n: 1, f: r => rub(r.sales), k: r => r.sales },
    { h: "Что даст рост (по убыванию эффекта)", f: r => r.improve.length ? r.improve.map(m => `<div style="font-size:13px">${esc(m.what)} <span class="mut">(${esc(m.group)})</span></div>`).join("") : "<span class=good>всё выполнено</span>" }];
  const dt = Q.discount_new.map(t => ({ ...t, end: (t.end_at || "").slice(0, 10) }));
  const dCols = [{ h: "Товар", f: r => `<b>${esc(r.offer_id)}</b>` }, { h: "Сейчас", n: 1, f: r => rub(r.original) }, { h: "Просят", n: 1, f: r => rub(r.requested) },
    { h: "Скидка", n: 1, f: r => r.discount + "%" }, { h: "Штук", n: 1, f: r => r.qty }, { h: "Ваш минимум", n: 1, f: r => rub(r.min_auto) }, { h: "Ответить до", f: r => esc(r.end) }];
  const tCols = [{ h: "Товар", f: r => `<b>${esc(r.offer_id)}</b>` }, { h: "Остаток на складе Ozon", n: 1, f: r => num(r.stock) }, { h: "Продаж в день", n: 1, f: r => r.ads == null ? "—" : r.ads },
    { h: "Хватит на дней", n: 1, f: r => r.idc == null ? "—" : Math.round(r.idc) }, { h: "Оценка", f: r => esc({ GRADES_GREEN: "норма", GRADES_NOSALES: "нет продаж", GRADES_CRITICAL: "критично", GRADES_SURPLUS: "избыток", GRADES_DEFICIT: "дефицит" }[r.grade] || r.grade) }];
  const cpCols = [{ h: "Месяц", f: r => esc(r.month) }, { h: "Тип", f: r => esc(r.type) }, { h: "Товар", f: r => esc(r.offer_id) }, { h: "Штук", n: 1, f: r => r.qty }, { h: "Сумма", n: 1, f: r => rub(r.amount) }];
  const fbs = Q.fbs_index;
  $("#c").innerHTML = `<div class="grid kpis">
    ${kpi("Оценка товаров", score ? score.value : "—", Q.premium_threshold ? `до статуса Premium (${Q.premium_threshold}) не хватает ${need > 0 ? need.toFixed(2) : 0}` : "", score && score.value >= (Q.premium_threshold || 5) ? "good" : "warn")}
    ${kpi("Средний контент-рейтинг", Q.content_avg, "по всем карточкам, из 100", Q.content_avg < 70 ? "warn" : "")}
    ${kpi("Индекс ошибок FBS", fbs.index ?? "—", `${esc(fbs.from || "")} — ${esc(fbs.to || "")}`, (fbs.index || 0) > 1 ? "bad" : "good")}
    ${kpi("Заявок на скидку", Q.discount_new.length, "ждут вашего ответа", Q.discount_new.length ? "warn" : "")}</div>
  ${prog && prog.status === "CRITICAL" ? `<div class="banner">Показатель «${esc(prog.name)}» в критическом состоянии. Проверьте причину в кабинете Ozon (раздел «Рейтинг»): чаще всего это отмены и просрочки отгрузки.</div>` : ""}
  <div class="card"><h2>Рейтинг продавца</h2><div id="rt"></div><p class="note">Оценка отзывов Ozon пересчитывается по скользящему окну. Порог Premium даёт дополнительные возможности в кабинете, включая аналитику поисковых запросов и работу с отзывами.</p></div>
  <div class="card"><h2>Контент-рейтинг карточек</h2><div id="ct"></div><p class="note">Показывает, насколько полно заполнена карточка по оценке Ozon. Самый сильный рычаг почти везде: видео карточки и заполнение оставшихся атрибутов.</p></div>
  ${Q.discount_new.length ? `<div class="card"><h2>Заявки покупателей на скидку (ждут ответа)</h2><div id="dt"></div><p class="note">Каждая заявка на 1 штуку. Если ответить не успеть, заявка истекает сама. Согласие снижает цену этой единицы. Решение по цене остаётся за вами. Всего за период заявок: ${Object.entries(Q.discount_counts).map(([k, v]) => `${esc(k)} ${v}`).join(", ")}.</p></div>` : ""}
  <div class="grid two"><div class="card"><h2>Оборачиваемость (склады Ozon)</h2>${Q.turnover.length ? `<div id="tv"></div>` : "<p class=mut>Нет данных</p>"}<p class="note">Считается только по товарам, лежащим на складах Ozon (FBO). Товары на вашем складе (FBS) здесь не видны.</p></div>
  <div class="card"><h2>Компенсации от Ozon</h2>${Q.compensation.length ? `<div id="cp"></div>` : "<p class=mut>Начисленных компенсаций за последние 3 месяца нет.</p>"}<p class="note">${esc(Q.compensation_note)}</p></div></div>`;
  const drawR = () => { $("#rt").innerHTML = table(rateCols, Q.ratings, { sortable: false }); }; drawR();
  const drawC = () => { $("#ct").innerHTML = table(cCols, cRows); makeSortable($("#ct"), cCols, cRows, drawC); }; drawC();
  if ($("#dt")) $("#dt").innerHTML = table(dCols, dt, { sortable: false });
  if ($("#tv")) $("#tv").innerHTML = table(tCols, Q.turnover, { sortable: false });
  if ($("#cp")) $("#cp").innerHTML = table(cpCols, Q.compensation, { sortable: false });
}

/* ---------- Медиа ---------- */
function media(D) {
  const M = D.media || {}, groups = Object.entries(M.groups || {});
  const byOffer = {};
  groups.forEach(([g, v]) => (v.offers || []).forEach(o => (byOffer[o] = byOffer[o] || []).push([g, v])));
  const rows = D.products.slice().sort((a, b) => b.sales - a.sales);
  const link = (g, v) => v.public_url ? `<a href="${esc(v.public_url)}" target="_blank" rel="noopener">${esc(g.replace(/_/g, " "))}</a>` : esc(g);
  const cols = [{ h: "Товар", f: r => `<b>${esc(r.offer_id)}</b><div class="mut" style="font-size:12px">${esc(r.name.slice(0, 60))}</div>` },
    { h: "Продажи", n: 1, f: r => rub(r.sales) },
    { h: "Папки с фото и видео на Яндекс Диске", f: r => (byOffer[r.offer_id] || []).map(([g, v]) => link(g, v)).join("<br>") || `<span class=mut>нет материалов</span>` }];
  const gCols = [{ h: "Папка", f: r => link(r[0], r[1]) }, { h: "Фото", n: 1, f: r => r[1].photos ?? "—" }, { h: "Видео", n: 1, f: r => r[1].videos ?? "—" },
    { h: "Видео (имя файла)", f: r => (r[1].video_files || []).map(v => `<div style="font-size:12px">${esc(v)}</div>`).join("") || "—" },
    { h: "Подходит для карточек", f: r => esc((r[1].offers || []).join(", ")) }];
  $("#c").innerHTML = `<div class="card"><p style="font-size:14px">Фото и видео хранятся на Яндекс Диске (папка AVTO/TOVARY). Одни и те же материалы можно использовать в разных карточках. Видео и фото добавляются в карточку в кабинете Ozon (блок «Фото» и «Озон.Видео», загрузка с компьютера или по ссылке на Яндекс Диск). В текст описания и в характеристики внешние ссылки вставлять нельзя.</p></div>
  <div class="card"><h2>Материалы по карточкам</h2><div id="mt"></div></div>
  <div class="card"><h2>Папки</h2><div id="mg"></div></div>`;
  $("#mt").innerHTML = table(cols, rows, { sortable: false });
  $("#mg").innerHTML = groups.length ? table(gCols, groups, { sortable: false }) : "<p class=mut>Папки ещё не опубликованы</p>";
}

/* ---------- Акции ---------- */
function promos(D) {
  const P = D.promos, K = P.kpi;
  const adv = { remove: ["Убрать", "bad"], keep: ["Оставить", "good"], check: ["Проверить", "warn"], join: ["Участвовать", "good"], skip: ["Не участвовать", "bad"], maybe: ["На ваше усмотрение", "warn"] };
  const tag = a => `<span class="${adv[a][1]}"><b>${adv[a][0]}</b></span>`;
  const aCols = [{ h: "Акция", f: r => `<b>${esc(r.title)}</b><div class="mut" style="font-size:12px">${esc(r.start)} — ${esc(r.end)}</div>` },
    { h: "Участвуют", n: 1, f: r => r.in }, { h: "Доступно ещё", n: 1, f: r => r.potential },
    { h: "Советую убрать", n: 1, f: r => r.remove_advised, c: r => r.remove_advised ? "bad" : "" }];
  const pCols = [{ h: "Товар", f: r => `<b>${esc(r.offer_id)}</b>`, k: r => r.offer_id }, { h: "Акция", f: r => esc(r.action) },
    { h: "Прайс", n: 1, f: r => rub(r.price), k: r => r.price }, { h: "В акции", n: 1, f: r => rub(r.action_price), k: r => r.action_price },
    { h: "Скидка", n: 1, f: r => r.discount + "%", c: r => r.discount >= 15 ? "bad" : "", k: r => r.discount },
    { h: "Буст показов", n: 1, f: r => r.boost == null ? "—" : "+" + Math.round(r.boost) + "%", k: r => r.boost },
    { h: "Прибыль/шт по прайсу", n: 1, f: r => r.profit_list == null ? "—" : rub(r.profit_list) }, { h: "Прибыль/шт в акции", n: 1, f: r => r.profit_action == null ? "—" : rub(r.profit_action), c: r => r.profit_action != null && r.profit_action < 0 ? "bad" : "" },
    { h: "Режим", f: r => r.mode === "MANUAL" ? "вручную" : "авто" }, { h: "Совет", f: r => `${tag(r.advice)}<div style="font-size:12px">${esc(r.why)}</div>` }];
  const cCols = [{ h: "Товар", f: r => `<b>${esc(r.offer_id)}</b>`, k: r => r.offer_id }, { h: "Акция", f: r => esc(r.action) },
    { h: "Прайс", n: 1, f: r => rub(r.price) }, { h: "Цена в акции", n: 1, f: r => rub(r.max_price) }, { h: "Скидка", n: 1, f: r => r.discount + "%" }, { h: "Буст", n: 1, f: r => r.boost == null ? "—" : "+" + Math.round(r.boost) + "%" },
    { h: "Совет", f: r => `${tag(r.advice)}<div style="font-size:12px">${esc(r.why)}</div>` }];
  const ch = P.changes, chTxt = x => `<li><b>${esc(x.offer_id)}</b>: ${esc(x.action)}</li>`;
  $("#c").innerHTML = `<div class="grid kpis">
    ${kpi("Товаров в акциях", K.products, `${K.participations} участий, средняя скидка ${K.avg_discount}%`, K.products ? "warn" : "good")}
    ${kpi("Советую убрать", K.remove_products, `${K.remove} участий с невыгодной скидкой`, K.remove ? "bad" : "good")}
    ${kpi("Стоит подключить", K.join, "акции с небольшой скидкой", K.join ? "good" : "")}</div>
  ${ch.since ? `<div class="card"><h2>Что изменилось с ${esc(ch.since)}</h2>${ch.added.length ? `<p class="bad"><b>Добавлено (Ozon мог добавить сам):</b></p><ul>${ch.added.map(chTxt).join("")}</ul>` : ""}${ch.removed.length ? `<p class="good"><b>Убрано:</b></p><ul>${ch.removed.map(chTxt).join("")}</ul>` : ""}${(ch.cleaned || []).length ? `<p class="good"><b>Автоочистка убрала сегодня (скидка от ${P.autoclean.threshold}%):</b></p><ul>${ch.cleaned.map(x => `<li><b>${esc(x.offer_id)}</b>: ${esc(x.action)} (−${x.discount}%)</li>`).join("")}</ul>` : ""}${!ch.added.length && !ch.removed.length && !(ch.cleaned || []).length ? "<p class=mut>Изменений нет.</p>" : ""}</div>` : ""}
  <div class="card"><p style="font-size:14px"><b>Автоочистка включена:</b> каждое утро после сбора данных из акций убираются товары с автоскидкой от ${P.autoclean.threshold}% (ручные добавления не трогаются). Последний запуск: ${esc(P.autoclean.last || "ещё не запускалась")}${P.autoclean.error ? ` <span class=bad>· ошибка: ${esc(P.autoclean.error)}</span>` : ""}. Чтобы оставить конкретный товар в акции, добавьте его артикул в файл audit/promo_keep.json.</p></div>
  <div class="card"><h2>Акции Ozon</h2><div id="ta"></div></div>
  <div class="card"><h2>Где товары участвуют сейчас</h2>${P.participation.length ? `<div id="tp"></div>` : "<p class=good>Ни один товар не участвует в акциях.</p>"}<p class="note">${esc(P.note)} Порог совета «убрать»: скидка от 15% и продажи не окупают потерю, либо продажа в убыток.</p></div>
  <div class="card"><h2>Куда можно вступить</h2><div id="tc"></div></div>`;
  $("#ta").innerHTML = table(aCols, P.actions, { sortable: false });
  if ($("#tp")) { const rp = P.participation.slice(); const dp = () => { $("#tp").innerHTML = table(pCols, rp); makeSortable($("#tp"), pCols, rp, dp); }; dp(); }
  const rc = P.candidates.filter(c => c.advice !== "skip" || c.discount < 40); const dc = () => { $("#tc").innerHTML = table(cCols, rc); }; dc();
}

/* ---------- Хаб ---------- */
const TYPES_KEY = "type";
async function hub(D) {
  let tasks = [], live = true;
  try { const r = await fetch("api/tasks", { cache: "no-store" }); if (!r.ok) throw 0; tasks = await r.json(); }
  catch { live = false; tasks = D.tasks_seed || []; }
  const types = [...new Set(tasks.map(t => t.type))].sort();
  const reports = [["dashboard.html", "Дашборд", "Выручка, прибыль, расходы, отмены"], ["products.html", "Товары", "Прибыль и маржа по каждому артикулу"], ["cards.html", "Карточки и акции", "Аудит SEO, конкуренты, готовые тексты, цены в акциях"], ["ideas.html", "Идеи для печати", "Что ещё печатать и продавать: спрос, конкуренты, калькулятор"], ["quality.html", "Качество и рейтинг", "Рейтинг продавца, контент-рейтинг, заявки на скидку, компенсации"], ["media.html", "Фото и видео", "Папки Яндекс Диска по товарам"], ["promos.html", "Акции", "Где товары в акциях, что убрать, куда вступить (обновляется ежедневно)"], ["savings.html", "Экономия расходов", "Комиссии, штрафы, логистика: сколько можно сэкономить"], ["accounting.html", "Бухгалтерия", "Баланс, движение денег, начисления"], ["accruals.csv", "Начисления (CSV)", "Выгрузка для учёта"], ["products.csv", "Прибыль по товарам (CSV)", "Выгрузка для Excel"]];
  $("#c").innerHTML = `<div class="grid reports" style="margin-bottom:18px">${reports.map(r => `<a href="${r[0]}"><b>${r[1]}</b><span>${r[2]}</span></a>`).join("")}</div>
  ${live ? "" : `<div class="banner">Сервер задач недоступен: список только для чтения, изменения не сохранятся.</div>`}
  <div class="card"><h2>Задачи и история</h2>
  <div class="filters"><label>С даты<input type="date" id="d1"></label><label>По дату<input type="date" id="d2"></label>
  <label>Тип<select id="ty"><option value="">все</option>${types.map(t => `<option>${esc(t)}</option>`).join("")}</select></label>
  <label>Статус<select id="st"><option value="">все</option><option value="0">не сделано</option><option value="1">сделано</option></select></label>
  <button id="add" class="pri" ${live ? "" : "disabled"}>+ Задача</button></div><div id="tl"></div></div>`;
  const draw = () => {
    const d1 = $("#d1").value, d2 = $("#d2").value, ty = $("#ty").value, st = $("#st").value;
    const v = tasks.filter(t => (!d1 || t.created >= d1) && (!d2 || t.created <= d2) && (!ty || t.type === ty) && (st === "" || (st === "1") === !!t.done))
      .sort((a, b) => (a.done - b.done) || ({ high: 0, medium: 1, low: 2 }[a.priority] - { high: 0, medium: 1, low: 2 }[b.priority]) || b.created.localeCompare(a.created));
    $("#tl").innerHTML = `<div class="scroll"><table><thead><tr><th>Сделано</th><th>Задача</th><th>Тип</th><th>Приоритет</th><th>Создана</th><th>Выполнена</th></tr></thead><tbody>${v.map(t => `<tr class="${t.done ? "done" : ""}"><td><input type="checkbox" data-id="${esc(t.id)}" ${t.done ? "checked" : ""} ${live ? "" : "disabled"}></td><td><div class="t"><b>${esc(t.title)}</b></div><div class="mut" style="font-size:13px">${esc(t.description)}</div></td><td><span class="tag">${esc(t.type)}</span></td><td><span class="tag p-${esc(t.priority)}">${{ high: "высокий", medium: "средний", low: "низкий" }[t.priority] || esc(t.priority)}</span></td><td>${esc(t.created)}</td><td>${esc(t.done_at || "—")}</td></tr>`).join("") || `<tr><td colspan=6 class=mut>Нет задач по фильтру</td></tr>`}</tbody></table></div>`;
    $("#tl").querySelectorAll("input[type=checkbox]").forEach(cb => cb.onchange = async () => {
      const t = tasks.find(x => x.id === cb.dataset.id);
      try { const r = await fetch("api/tasks/" + encodeURIComponent(t.id), { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ done: cb.checked }) }); if (!r.ok) throw 0; Object.assign(t, await r.json()); }
      catch { cb.checked = !cb.checked; alert("Не удалось сохранить"); }
      draw();
    });
  };
  ["d1", "d2", "ty", "st"].forEach(i => $("#" + i).onchange = draw);
  $("#add").onclick = async () => {
    const title = prompt("Название задачи"); if (!title) return;
    const type = prompt("Тип задачи", types[0] || "Прочее") || "Прочее";
    const r = await fetch("api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, type, description: "", priority: "medium" }) });
    if (r.ok) { tasks.push(await r.json()); draw(); } else alert("Не удалось создать");
  };
  draw();
}

(async () => {
  shell("Загрузка…");
  let D; try { D = await (await fetch("data.json", { cache: "no-store" })).json(); } catch { $("#c").innerHTML = "<p class=bad>Не удалось загрузить данные</p>"; return; }
  const upd = "Обновлено: " + new Date(D.generated_at).toLocaleString("ru-RU");
  const T = { hub: "Хаб отчётов и задач", dashboard: "Дашборд магазина", products: "Товары и прибыль", accounting: "Бухгалтерия", savings: "Снижение расходов", cards: "Карточки: аудит и акции", ideas: "Что печатать и продавать", quality: "Качество и рейтинг", media: "Фото и видео товаров", promos: "Акции Ozon" };
  shell(T[page], upd);
  ({ hub, dashboard, products, accounting, savings, cards, ideas, quality, media, promos }[page])(D);
})();
