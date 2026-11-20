"use strict";
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const rub = v => v == null ? "—" : Math.round(v).toLocaleString("ru-RU") + " ₽";
const num = v => v == null ? "—" : Number(v).toLocaleString("ru-RU");
const cls = v => v == null ? "" : v < 0 ? "bad" : v > 0 ? "good" : "";
const page = document.body.dataset.page;

const NAV = [["index.html", "Хаб", "hub"], ["dashboard.html", "Дашборд", "dashboard"], ["products.html", "Товары", "products"], ["cards.html", "Карточки", "cards"], ["ideas.html", "Идеи", "ideas"], ["quality.html", "Качество", "quality"], ["media.html", "Медиа", "media"], ["promos.html", "Акции", "promos"], ["prices.html", "Цены", "prices"], ["savings.html", "Экономия", "savings"], ["accounting.html", "Бухгалтерия", "accounting"], ["admin.html", "Админ", "admin"]];
function shell(title, upd, alert) {
  $("#app").innerHTML = `<header><div class="wrap"><span class="logo">HomeHelp · Ozon</span><nav>${NAV.map(n => `<a href="${n[0]}" class="${n[2] === page ? "on" : ""}">${n[1]}${n[2] === "admin" && alert ? `<i class="dot ${alert.cls}" title="${esc(alert.text)}"></i>` : ""}</a>`).join("")}</nav><span class="upd">${upd || ""}</span></div></header><main><div class="wrap"><h1>${title}</h1><div id="c"></div></div></main>`;
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

/* ---------- Период и пересчёт агрегатов ---------- */
const PERIOD_KEY = "ozonPeriod", GRID_KEY = "ozonGridFilters";
const PRINT = () => !!window.__PRINT__;
const rnd = v => v == null ? null : Math.round(v * 100) / 100;
const rnd1 = v => v == null ? null : Math.round(v * 10) / 10;
let PER = null, RANGE = null;

function dataRange(D) {
  const ks = [...Object.keys(D.days || {}), ...Object.keys(D.orders_day || {}), ...Object.keys(D.cancel_day || {})];
  for (const o of Object.values(D.product_days || {})) ks.push(...Object.keys(o));
  if (!ks.length) return null;
  return { min: ks.reduce((a, b) => a < b ? a : b), max: ks.reduce((a, b) => a > b ? a : b) };
}
function initPeriod(D) {
  RANGE = dataRange(D);
  const full = RANGE ? { preset: "all", from: RANGE.min, to: RANGE.max } : null;
  if (!RANGE) { PER = null; return; }
  PER = full;
  if (PRINT()) return;
  try {
    const s = JSON.parse(localStorage.getItem(PERIOD_KEY) || "null");
    if (s && s.from && s.to && s.from <= s.to && s.from >= RANGE.min && s.to <= RANGE.max) PER = s;
  } catch { }
}
function savePeriod() { try { localStorage.setItem(PERIOD_KEY, JSON.stringify(PER)); } catch { } }
const inWin = d => PER ? (d >= PER.from && d <= PER.to) : true;
const periodDays = () => PER ? Math.round((new Date(PER.to) - new Date(PER.from)) / 86400000) + 1 : 0;
const periodLabel = () => {
  if (!PER) return "весь период";
  const f = s => s.slice(8, 10) + "." + s.slice(5, 7);
  return `${f(PER.from)}–${f(PER.to)} (${periodDays()} дн.)`;
};
function sumRange(map) { let s = 0; for (const d in (map || {})) if (inWin(d)) s += map[d]; return s; }
function sumRangeBy(map) {
  const out = {};
  for (const d in (map || {})) if (inWin(d)) for (const k in map[d]) out[k] = (out[k] || 0) + map[d][k];
  return out;
}

/* Пересчёт товаров под выбранный период из суточного среза product_days.
   Формулы те же, что в analyze.py: net = s + c + d + f, profit = net − себестоимость. */
function aggProducts(D) {
  const pd = D.product_days || {};
  return (D.products || []).map(p => {
    let u = 0, s = 0, c = 0, dl = 0, f = 0, r = 0;
    const days = pd[p.offer_id] || {};
    for (const d in days) {
      if (!inWin(d)) continue;
      const v = days[d];
      u += v.u || 0; s += v.s || 0; c += v.c || 0; dl += v.d || 0; f += v.f || 0; r += v.r || 0;
    }
    const net = s + c + dl + f;
    const cogs = p.unit_cost == null ? null : p.unit_cost * u;
    const profit = cogs == null ? null : net - cogs;
    return { ...p, units: Math.round(u), returns: Math.round(r), sales: rnd(s), commission: rnd(c), delivery: rnd(dl), item_fees: rnd(f),
      net_before_cost: rnd(net), cogs: cogs == null ? null : rnd(cogs), profit: profit == null ? null : rnd(profit),
      margin_pct: profit != null && s > 0 ? rnd1(profit / s * 100) : null,
      commission_pct: s > 0 ? rnd1(-c / s * 100) : null };
  });
}

/* Все производные от периода данные одним объектом — считается один раз на отрисовку раздела. */
function aggregates(D) {
  if (!D.product_days) return { P: D.products || [], kpi: D.kpi, by_type: D.by_type || {}, days: D.days || {}, orders_day: D.orders_day || {}, cancel_reasons: (D.cancel || {}).reasons || {}, partial: true };
  const P = aggProducts(D);
  const oh = sumRangeBy(D.overhead_day), fees = sumRangeBy(D.fees_day);
  const sum = (a, k) => a.reduce((s, p) => s + (p[k] || 0), 0);
  const sales = sum(P, "sales"), profit = sum(P, "profit"), commission = sum(P, "commission"), delivery = sum(P, "delivery");
  const overhead = Object.values(oh).reduce((a, b) => a + b, 0);
  const by_type = { "Продажи (реализация)": rnd(sales), "Комиссия": rnd(commission), "Логистика и доставка": rnd(delivery) };
  for (const src of [fees, oh]) for (const k in src) by_type[k] = rnd((by_type[k] || 0) + src[k]);
  const days = {}, orders_day = {}, cancel_reasons = {};
  for (const d in (D.days || {})) if (inWin(d)) days[d] = D.days[d];
  for (const d in (D.orders_day || {})) if (inWin(d)) orders_day[d] = D.orders_day[d];
  for (const d in (D.cancel_reason_day || {})) if (inWin(d)) for (const k in D.cancel_reason_day[d]) cancel_reasons[k] = (cancel_reasons[k] || 0) + D.cancel_reason_day[d][k];
  return {
    P, days, orders_day, cancel_reasons, by_type, overhead: rnd(overhead), partial: false,
    kpi: { ...D.kpi, orders: sumRange(D.orders_day), cancelled: sumRange(D.cancel_day), sales: rnd(sales),
      profit_products: rnd(profit), overhead: rnd(overhead), profit_total: rnd(profit + overhead),
      sku_sold: P.filter(p => p.units > 0).length }
  };
}

/* Панель периода. fixed — пояснение для разделов, где период не влияет на данные. */
function periodBar(D, opts = {}) {
  if (PRINT() || !RANGE) return "";
  const dis = opts.fixed ? " disabled" : "";
  const presets = [["7", 7], ["14", 14], ["30", 30]].map(([n, days]) =>
    `<button type="button" class="pbtn${PER.preset === n ? " on" : ""}" data-days="${days}"${dis}>${n} дней</button>`).join("");
  return `<div class="period" id="period">
    <span class="pl">Период:</span>
    <span class="pbtns">${presets}<button type="button" class="pbtn${PER.preset === "all" ? " on" : ""}" data-preset="all"${dis}>весь (${periodDaysCalc(RANGE)} дн.)</button></span>
    <label class="pdate">с <input type="date" id="pfrom" value="${PER.from}" min="${RANGE.min}" max="${RANGE.to}"${dis}></label>
    <label class="pdate">по <input type="date" id="pto" value="${PER.to}" min="${RANGE.min}" max="${RANGE.to}"${dis}></label>
    <span class="mut" id="pinfo">${opts.fixed ? esc(opts.fixed) : `данные пересчитаны за ${periodLabel()}`}</span>
    </div>`;
}
const periodDaysCalc = r => Math.round((new Date(r.max) - new Date(r.min)) / 86400000) + 1;

function mountPeriod(D, rerender) {
  const bar = $("#period");
  if (!bar) return;
  const apply = p => { PER = p; savePeriod(); rerender(); };
  bar.querySelectorAll(".pbtn[data-days]").forEach(b => b.onclick = () => {
    const n = +b.dataset.days;
    const to = RANGE.max;
    const from0 = new Date(to); from0.setDate(from0.getDate() - (n - 1));
    const from = from0.toISOString().slice(0, 10) < RANGE.min ? RANGE.min : from0.toISOString().slice(0, 10);
    apply({ preset: String(n), from, to });
  });
  const all = bar.querySelector('.pbtn[data-preset="all"]');
  if (all) all.onclick = () => apply({ preset: "all", from: RANGE.min, to: RANGE.max });
  const fi = $("#pfrom"), ti = $("#pto");
  const custom = () => {
    if (!fi.value || !ti.value || fi.value > ti.value) return;
    apply({ preset: "custom", from: fi.value, to: ti.value });
  };
  if (fi) fi.onchange = custom;
  if (ti) ti.onchange = custom;
}

/* ---------- Таблицы с сортировкой и фильтрами по столбцам ---------- */
const parseNum = s => { const n = parseFloat(String(s).replace(/\s/g, "").replace(",", ".")); return isNaN(n) ? null : n; };
/* Число из готовой ячейки («1 234 ₽», «48 %», «−3 210 ₽»): нужно колонкам, у которых нет ключа сортировки k. */
const numFromText = s => { const m = String(s).replace(/\u2212/g, "-").replace(/\s/g, "").replace(",", ".").match(/^[+-]?\d+(\.\d+)?/); return m ? parseFloat(m[0]) : null; };
function numMatch(v, q) {
  if (v == null || v === "") return false;
  const s = String(q).trim().toLowerCase();
  let m;
  if ((m = s.match(/^([<>]=?)\s*(-?[\d\s.,]+)$/))) {
    const n = parseNum(m[2]); if (n == null) return false;
    const ge = m[1].endsWith("=");
    return m[1][0] === ">" ? (ge ? v >= n : v > n) : (ge ? v <= n : v < n);
  }
  if ((m = s.match(/^(-?[\d\s.,]+)\s*[-–]\s*(-?[\d\s.,]+)$/))) {
    const a = parseNum(m[1]), b = parseNum(m[2]);
    if (a == null || b == null) return false;
    return v >= Math.min(a, b) && v <= Math.max(a, b);
  }
  const n = parseNum(s);
  return n == null ? String(v).toLowerCase().includes(s) : v === n;
}
const ENT = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'" };
function cellText(c, r) {
  if (c.t) return String(c.t(r) ?? "");
  return String(c.f(r) ?? "").replace(/<[^>]*>/g, " ").replace(/&(amp|lt|gt|quot|#39);/g, e => ENT[e]).replace(/\s+/g, " ").trim();
}
const gridStore = () => { try { return JSON.parse(localStorage.getItem(GRID_KEY) || "{}"); } catch { return {}; } };
function gridSave(id, f) { try { const s = gridStore(); s[id] = f; localStorage.setItem(GRID_KEY, JSON.stringify(s)); } catch { } }
let GRID_N = 0;

/* Единая таблица: сортировка кликом по заголовку + фильтр в каждой колонке.
   Текст — подстрока; числа — «>1000», «<50», «>=10», диапазон «100-500».
   Фильтры хранятся в localStorage под id таблицы. В печатной версии (report.html)
   рисуется обычная таблица без полей ввода — иначе они попали бы в PDF. */
function dataGrid(el, cols, rows, opts = {}) {
  const host = typeof el === "string" ? $(el) : el;
  if (!host) return null;
  const id = opts.id || host.id || "g" + (++GRID_N);
  const sortable = opts.sortable !== false, filterable = opts.filters !== false && !PRINT();
  const st = { sort: null, dir: -1, f: filterable ? Object.assign({}, gridStore()[id] || {}) : {} };

  const pass = r => cols.every((c, i) => {
    const q = (st.f[i] || "").trim();
    if (!q) return true;
    if (c.n) return numMatch(c.k ? c.k(r) : numFromText(cellText(c, r)), q);
    return cellText(c, r).toLowerCase().includes(q.toLowerCase());
  });
  const bodyHtml = () => {
    const v = rows.filter(pass);
    if (st.sort != null && cols[st.sort] && cols[st.sort].k) {
      const k = cols[st.sort].k, d = st.dir;
      v.sort((a, b) => { const x = k(a), y = k(b); return ((x == null) - (y == null)) || ((x > y ? 1 : x < y ? -1 : 0) * d); });
    }
    if (opts.onCount) opts.onCount(v.length, rows.length);
    return v.map(r => `<tr>${cols.map(c => `<td class="${c.n ? "n " : ""}${c.c ? c.c(r) : ""}">${c.f(r)}</td>`).join("")}</tr>`).join("")
      || `<tr><td colspan="${cols.length}" class="mut">Ничего не найдено — ослабьте фильтры столбцов</td></tr>`;
  };
  const headRow = () => `<tr>${cols.map((c, i) => `<th class="${c.n ? "n " : ""}${sortable && c.k ? " sort" : ""}${st.sort === i ? " on" : ""}" data-i="${i}">${c.h}${st.sort === i ? `<span class="arr">${st.dir > 0 ? "▲" : "▼"}</span>` : ""}</th>`).join("")}</tr>`;
  const filterRow = () => filterable ? `<tr class="frow">${cols.map((c, i) => `<th class="${c.n ? "n " : ""}"><input data-i="${i}" value="${esc(st.f[i] || "")}" placeholder="${c.n ? ">100 · 100-500" : "фильтр"}" title="${c.n ? "Числовой фильтр: >1000, <50, >=10, диапазон 100-500" : "Поиск подстроки"}"></th>`).join("")}</tr>` : "";

  host.innerHTML = `<div class="scroll${opts.scrollY ? " scroll-y" : ""}"><table><thead>${headRow()}${filterRow()}</thead><tbody>${bodyHtml()}</tbody></table></div>` +
    (filterable ? `<p class="note">Фильтры столбцов: текст — подстрока, числа — <code>&gt;1000</code>, <code>&lt;50</code>, <code>&gt;=10</code>, диапазон <code>100-500</code>. Пустое поле — без ограничения, значения запоминаются в этом браузере.</p>` : "");
  const thead = host.querySelector("thead"), tb = host.querySelector("tbody");

  const bindSort = () => thead.querySelectorAll("tr:first-child th.sort").forEach(th => th.onclick = () => {
    const i = +th.dataset.i;
    if (st.sort === i) st.dir = -st.dir; else { st.sort = i; st.dir = -1; }
    thead.querySelector("tr:first-child").outerHTML = headRow();   // перерисовываем только строку заголовков: поля фильтров не теряют фокус
    tb.innerHTML = bodyHtml();
    bindSort();
  });
  if (sortable) bindSort();
  if (filterable) thead.querySelectorAll(".frow input").forEach(inp => inp.oninput = () => {
    st.f[inp.dataset.i] = inp.value; gridSave(id, st.f); tb.innerHTML = bodyHtml();
  });
  return { refresh(nr) { rows = nr; tb.innerHTML = bodyHtml(); }, state: st };
}

/* ---------- Дашборд ---------- */
function dashboard(D) {
  const A = aggregates(D), K = A.kpi, P = A.P;
  const margin = K.sales ? K.profit_total / K.sales * 100 : 0;
  const warn = D.cost_ratio && D.cost_ratio.max < 0.10 ? `<div class="banner">Себестоимость составляет ${(D.cost_ratio.min * 100).toFixed(1)}–${(D.cost_ratio.max * 100).toFixed(1)}% от цены — прибыль может быть завышена. Проверьте закупочные цены (задача в хабе).</div>` : "";
  const topProfit = P.filter(p => p.profit != null && p.units > 0).sort((a, b) => b.profit - a.profit);
  const byType = Object.entries(A.by_type).sort((a, b) => a[1] - b[1]);
  $("#c").innerHTML = periodBar(D) + warn + `<div class="grid kpis">
    ${kpi("Выручка", rub(K.sales), `${periodLabel()}: ${K.orders} заказов, отменено ${K.cancelled}`)}
    ${kpi("Прибыль после себестоимости", rub(K.profit_total), `маржа ${margin.toFixed(1)}%`, cls(K.profit_total))}
    ${kpi("Общие расходы (штрафы и пр.)", rub(K.overhead), "не привязаны к товарам", cls(K.overhead))}
    ${kpi("Товаров с продажами", `${K.sku_sold} из ${K.sku_total}`, `остаток ${num(K.stock_units)} шт — на дату отчёта`)}
    ${kpi("Баланс к выплате", rub(K.closing_balance), "на дату отчёта, от периода не зависит")}</div>
  <div class="grid two"><div class="card"><h2>Начисления по дням, чистая сумма</h2>${dayChart(A.days, "net", "var(--bar)")}</div>
  <div class="card"><h2>Заказы по дням</h2>${dayChart(Object.fromEntries(Object.entries(A.orders_day).map(([k, v]) => [k, { n: v }])), "n", "var(--acc)")}</div></div>
  <div class="grid two"><div class="card"><h2>Прибыль по товарам</h2>${bars(topProfit.map(p => [p.offer_id, p.profit]), { signed: true })}<p class="note">Выручка − комиссия − логистика − сборы − себестоимость. Цена и остаток — на дату отчёта.</p></div>
  <div class="card"><h2>Куда уходят деньги</h2>${bars(byType.map(([k, v]) => [k, v]), { signed: true })}</div></div>
  <div class="card"><h2>Причины отмен</h2>${bars(Object.entries(A.cancel_reasons).sort((a, b) => b[1] - a[1]), { fmt: v => v + " шт" })}</div>`;
}

/* ---------- Товары ---------- */
function products(D) {
  const rows = aggregates(D).P;
  const cols = [
    { h: "Артикул", f: r => `<b>${esc(r.offer_id)}</b><div class="mut" style="font-size:12px">${esc(r.name.slice(0, 70))}</div>`, k: r => r.offer_id, t: r => r.offer_id + " " + r.name },
    { h: "Цена", n: 1, f: r => rub(r.price), k: r => r.price },
    { h: "Остаток", n: 1, f: r => num(r.stock), k: r => r.stock },
    { h: "Продано", n: 1, f: r => num(r.units), k: r => r.units },
    { h: "Выручка", n: 1, f: r => rub(r.sales), k: r => r.sales },
    { h: "Комиссия", n: 1, f: r => r.commission_pct == null ? "—" : r.commission_pct + "%", k: r => r.commission_pct },
    { h: "Логистика", n: 1, f: r => rub(r.delivery), k: r => r.delivery },
    { h: "Себестоимость", n: 1, f: r => rub(r.cogs), k: r => r.cogs },
    { h: "Прибыль", n: 1, f: r => rub(r.profit), c: r => cls(r.profit), k: r => r.profit },
    { h: "Маржа", n: 1, f: r => r.margin_pct == null ? "—" : r.margin_pct + "%", c: r => cls(r.margin_pct), k: r => r.margin_pct }];
  // Отдельные поля поиска и выпадающий список убраны: их заменяют фильтры столбцов —
  // «Продано» = 0 вместе с «Остаток» > 0 дают «без продаж, но с остатком», «Прибыль» < 0 — убыточные.
  $("#c").innerHTML = periodBar(D) + `<div class="card"><h2>Товары и прибыль <span class="mut" id="cnt" style="font-weight:400;font-size:13px"></span></h2><div id="t"></div>
    <p class="note">Продано, выручка, комиссия, логистика, себестоимость, прибыль и маржа пересчитаны за выбранный период. Цена и остаток — на дату формирования отчёта.</p></div>`;
  dataGrid("#t", cols, rows, { id: "products", onCount: (n, all) => { const c = $("#cnt"); if (c) c.textContent = `— показано ${n} из ${all}`; } });
}

/* ---------- Бухгалтерия ---------- */
function accounting(D) {
  const b = D.balance, t = b.total, cf = b.cashflows, A = aggregates(D);
  const money = m => m && m.value != null ? m.value : null;
  const cfRows = D.cash_flow.map(w => ({ p: w.period.begin.slice(0, 10) + " — " + w.period.end.slice(0, 10), b: w.period.begin.slice(0, 10), e: w.period.end.slice(0, 10), ...w }))
    .filter(w => !PER || (w.e >= PER.from && w.b <= PER.to));   // недельный срез попадает в период, если пересекается с ним
  const cols = [{ h: "Период", f: r => r.p, k: r => r.b, t: r => r.p }, { h: "Заказы", n: 1, f: r => rub(r.orders_amount), k: r => r.orders_amount }, { h: "Возвраты", n: 1, f: r => rub(r.returns_amount), c: r => cls(r.returns_amount), k: r => r.returns_amount },
    { h: "Комиссия", n: 1, f: r => rub(r.commission_amount), k: r => r.commission_amount }, { h: "Услуги", n: 1, f: r => rub(r.services_amount), k: r => r.services_amount }, { h: "Доставка/возвраты", n: 1, f: r => rub(r.item_delivery_and_return_amount), k: r => r.item_delivery_and_return_amount }];
  const services = (cf.services || []).map(s => [s.name, money(s.amount) ?? s.amount?.value ?? 0]);
  $("#c").innerHTML = periodBar(D) + `<div class="grid kpis">
    ${kpi("Остаток на начало", rub(t.opening_balance.value), "за весь собранный период")}${kpi("Начислено", rub(t.accrued.value), "за весь собранный период", cls(t.accrued.value))}
    ${kpi("Выплачено", rub((t.payments || []).reduce((s, p) => s + p.value, 0)), "за весь собранный период")}${kpi("Остаток на конец", rub(t.closing_balance.value), "на дату отчёта")}</div>
  <div class="grid two"><div class="card"><h2>Продажи и возвраты</h2>${bars([["Продажи", money(cf.sales.amount)], ["Комиссия с продаж", money(cf.sales.fee)], ["Возвраты", money(cf.returns.amount)], ["Комиссия по возвратам", money(cf.returns.fee)]].filter(x => x[1] != null), { signed: true })}<p class="note">Баланс Ozon отдаёт одним блоком за весь собранный период, поэтому фильтр периода на эти две карточки не влияет.</p></div>
  <div class="card"><h2>Услуги Ozon</h2>${services.length ? bars(services, { signed: true }) : "<p class=mut>Нет данных</p>"}<p class="note">Тоже из баланса за весь собранный период.</p></div></div>
  <div class="card"><h2>Движение денег по неделям</h2><div id="cf"></div><p class="note">Показаны недели, пересекающиеся с выбранным периодом.</p></div>
  <div class="card"><h2>Начисления по типам за период</h2>${bars(Object.entries(A.by_type).sort((a, b) => a[1] - b[1]), { signed: true })}</div>
  <div class="card"><h2>Выгрузки для бухгалтера</h2><p><a href="accruals.csv" download>Начисления (CSV)</a> · <a href="products.csv" download>Прибыль по товарам (CSV)</a></p><p class="note">Файлы в кодировке UTF-8 с разделителем «;», открываются в Excel. Выгружаются всегда за весь собранный период (30 дней), фильтр периода на них не влияет.</p></div>`;
  dataGrid("#cf", cols, cfRows, { id: "accounting-cashflow" });
}

/* ---------- Экономия ---------- */
function savings(D) {
  const S = D.savings, sv = S.items.slice().sort((a, b) => b.potential - a.potential);
  const conf = { "высокая": "good", "средняя": "warn", "низкая": "mut" };
  const pctUp = S.current_profit > 0 ? Math.round(S.total_potential / S.current_profit * 100) : 0;
  const leverCols = [
    { h: "Направление и что делать", f: s => `<b>${esc(s.lever)}</b><div class="mut" style="font-size:13px">${esc(s.how)}</div><div class="note">${esc(s.basis)}</div>`, t: s => `${s.lever} ${s.how} ${s.basis}` },
    { h: "Сейчас тратим", n: 1, f: s => rub(s.current), k: s => s.current },
    { h: "Потенциал", n: 1, f: s => `<b class="good">${rub(s.potential)}</b>`, k: s => s.potential },
    { h: "Уверенность", f: s => `<span class="${conf[s.confidence] || ""}">${esc(s.confidence)}</span>`, k: s => s.confidence, t: s => s.confidence }];
  $("#c").innerHTML = periodBar(D, { fixed: "Расчёт экономии выполняется на сервере за 30 дней: фильтр периода на этот раздел не влияет." }) + `<div class="grid kpis">
    ${kpi("Комиссия Ozon за период", rub(S.commission_sum), `${S.commission_pct}% от выручки`, "bad")}
    ${kpi("Резерв без роста продаж", rub(S.expense_only_potential), "штрафы, убыточные, услуги, возвраты", "good")}
    ${kpi("Резерв с учётом упущенных заказов", rub(S.total_potential), `≈ +${pctUp}% к текущей прибыли (${rub(S.current_profit)})`, "good")}</div>
  <div class="card"><h2>Где сократить расходы и что это даст (₽ в месяц)</h2><div id="svlev"></div><p class="note">${esc(S.note)}</p></div>
  <div class="grid two"><div class="card"><h2>Комиссия: что даст снижение</h2><p class="mut" style="font-size:14px">Комиссия зависит от категории товара и утверждается Ozon; от схемы (FBO/FBS/rFBS) она не меняется. Ниже — эффект на текущем объёме продаж.</p><div id="svsens"></div>
    <p class="note">Ставки 45–52% для запчастей необычно высоки. Проверьте в кабинете (Финансы → Тарифы) актуальную ставку категории и, если она не совпадает, обратитесь в поддержку с номерами отправлений. Точную причину по API определить нельзя.</p></div>
  <div class="card"><h2>Логистика: расходы по услугам</h2>${bars(S.logistics.map(x => [`${x.name} (${x.count})`, x.sum]), { signed: true })}<p class="note">В скобках — число операций.</p></div></div>
  <div class="card"><h2>Категории и ставки комиссии</h2><div id="svcat"></div><p class="note">Проверьте, что карточки лежат в правильной категории: неверная категория даёт другую ставку и хуже ранжируется.</p></div>`;
  dataGrid("#svlev", leverCols, sv, { id: "savings-levers" });
  dataGrid("#svsens", [{ h: "Снижение ставки", f: r => "−" + r.points + " п.п.", k: r => r.points }, { h: "Экономия в месяц", n: 1, f: r => rub(r.gain), c: () => "good", k: r => r.gain }], S.sensitivity, { id: "savings-sensitivity" });
  dataGrid("#svcat", [{ h: "Категория", f: r => esc(r.name), k: r => r.name, t: r => r.name }, { h: "Товаров", n: 1, f: r => r.products, k: r => r.products }, { h: "Ставка", n: 1, f: r => r.percent == null ? "—" : r.percent + "%", k: r => r.percent }, { h: "Выручка", n: 1, f: r => rub(r.sales), k: r => r.sales }, { h: "Комиссия", n: 1, f: r => rub(r.commission), k: r => r.commission }], S.categories, { id: "savings-categories" });
}

/* ---------- Карточки ---------- */
function cards(D) {
  const C = D.cards, A = aggregates(D);
  const unitsOf = Object.fromEntries(A.P.map(p => [p.offer_id, p.units]));
  const rows = C.rows.map(r => ({ ...r, units: unitsOf[r.offer_id] ?? r.units }));   // «Продано» — за выбранный период
  const sev = { high: "p-high", medium: "p-medium", low: "p-low" }, sevT = { high: "критично", medium: "важно", low: "желательно" };
  const inActs = rows.filter(r => r.actions.length), disc = inActs.filter(r => r.discount_pct != null);
  const avgDisc = disc.length ? Math.round(disc.reduce((s, r) => s + r.discount_pct, 0) / disc.length) : 0;
  const noKey = rows.filter(r => r.missing_key.some(k => k === "Марка" || k === "Модель")).length;   // подпись KPI именно про марку/модель, а missing_key шире
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
  $("#c").innerHTML = periodBar(D, { fixed: "Аудит карточек, цены и акции — текущее состояние. От периода зависит только колонка «Продано»." }) + (C.applied ? `<div class="card" style="border-color:var(--good)"><b class="good">Правки внесены ${esc(C.applied.date)}.</b> ${esc(C.applied.text)}</div>` : "") + `<div class="grid kpis">
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
  dataGrid("#pt", priceCols, rp, { id: "cards-prices" });
  dataGrid("#ht", health, rows.slice(), { id: "cards-health" });
}

/* ---------- Идеи ---------- */
function ideas(D) {
  const I = D.ideas, vc = { "продолжать": "good", "расширять": "good", "делать": "good", "только комплектами": "warn", "менять формат": "warn", "гипотеза, проверить": "warn", "не рекомендуется": "bad" };
  const med = (D.cards && D.cards.median_delivery) || 100;
  const rowsN = I.niches.map(n => `<div class="card"><h2>${esc(n.name)} <span class="tag ${vc[n.verdict] === "bad" ? "p-high" : vc[n.verdict] === "warn" ? "p-medium" : ""}">${esc(n.verdict)}</span></h2>
    <div class="grid two"><div><b>Что видно на Ozon</b><p style="font-size:14px">${esc(n.evidence)}</p><p class="note">Статус данных: ${esc(n.status)}. Цены на витрине: ${esc(n.price)}.</p></div>
    <div><b>Риски</b><p style="font-size:14px">${esc(n.risk)}</p><b>Что делать</b><p style="font-size:14px" class="${vc[n.verdict] || ""}">${esc(n.action)}</p></div></div></div>`).join("");
  $("#c").innerHTML = periodBar(D, { fixed: "Идеи и калькулятор не зависят от периода: ниши сняты вручную, калькулятор считает по введённым значениям." }) + `<div class="card"><h2>Принципы отбора</h2><ul>${I.principles.map(p => `<li>${esc(p)}</li>`).join("")}</ul></div>
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
  const Q = D.quality, A = aggregates(D), gs = { OK: "good", WARNING: "warn", CRITICAL: "bad" };
  const salesOf = Object.fromEntries(A.P.map(p => [p.offer_id, p.sales]));
  const score = Q.ratings.find(r => r.key === "rating_review_avg_score_total");
  const prog = Q.ratings.find(r => r.key.includes("progress") || r.name.includes("прогрессив"));
  const need = Q.premium_threshold && score ? (Q.premium_threshold - score.value) : null;
  const rateCols = [{ h: "Группа", f: r => esc(r.group), k: r => r.group, t: r => r.group }, { h: "Показатель", f: r => esc(r.name), k: r => r.name, t: r => r.name },
    { h: "Сейчас", n: 1, f: r => r.value, k: r => r.value }, { h: "Было", n: 1, f: r => r.past, k: r => r.past },
    { h: "Статус", f: r => `<span class="${gs[r.status] || "mut"}">${esc({ OK: "норма", WARNING: "внимание", CRITICAL: "критично", UNKNOWN_STATUS: "нет данных" }[r.status] || r.status)}</span>`, k: r => r.status, t: r => r.status }];
  const cRows = Q.content.map(r => ({ ...r, sales: salesOf[r.offer_id] ?? r.sales }));   // продажи — за выбранный период
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
  $("#c").innerHTML = periodBar(D, { fixed: "Рейтинги, заявки на скидку, оборачиваемость и компенсации Ozon отдаёт готовыми — от периода зависит только колонка «Продажи» в контент-рейтинге." }) + `<div class="grid kpis">
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
  dataGrid("#rt", rateCols, Q.ratings, { id: "quality-ratings" });
  dataGrid("#ct", cCols, cRows, { id: "quality-content" });
  if ($("#dt")) dataGrid("#dt", dCols, dt, { id: "quality-discounts" });
  if ($("#tv")) dataGrid("#tv", tCols, Q.turnover, { id: "quality-turnover" });
  if ($("#cp")) dataGrid("#cp", cpCols, Q.compensation, { id: "quality-compensation" });
}

/* ---------- Медиа ---------- */
function media(D) {
  const M = D.media || {}, groups = Object.entries(M.groups || {});
  const byOffer = {};
  groups.forEach(([g, v]) => (v.offers || []).forEach(o => (byOffer[o] = byOffer[o] || []).push([g, v])));
  const rows = aggregates(D).P.slice().sort((a, b) => b.sales - a.sales);
  const link = (g, v) => v.public_url ? `<a href="${esc(v.public_url)}" target="_blank" rel="noopener">${esc(g.replace(/_/g, " "))}</a>` : esc(g);
  const cols = [{ h: "Товар", f: r => `<b>${esc(r.offer_id)}</b><div class="mut" style="font-size:12px">${esc(r.name.slice(0, 60))}</div>`, k: r => r.offer_id, t: r => r.offer_id + " " + r.name },
    { h: "Продажи", n: 1, f: r => rub(r.sales), k: r => r.sales },
    { h: "Папки с фото и видео на Яндекс Диске", f: r => (byOffer[r.offer_id] || []).map(([g, v]) => link(g, v)).join("<br>") || `<span class=mut>нет материалов</span>`, t: r => (byOffer[r.offer_id] || []).map(([g]) => g).join(" ") }];
  const gCols = [{ h: "Папка", f: r => link(r[0], r[1]), k: r => r[0], t: r => r[0] }, { h: "Фото", n: 1, f: r => r[1].photos ?? "—", k: r => r[1].photos }, { h: "Видео", n: 1, f: r => r[1].videos ?? "—", k: r => r[1].videos },
    { h: "Видео (имя файла)", f: r => (r[1].video_files || []).map(v => `<div style="font-size:12px">${esc(v)}</div>`).join("") || "—", t: r => (r[1].video_files || []).join(" ") },
    { h: "Подходит для карточек", f: r => esc((r[1].offers || []).join(", ")), t: r => (r[1].offers || []).join(" ") }];
  $("#c").innerHTML = periodBar(D, { fixed: "Список материалов не зависит от периода; продажи в таблице пересчитаны за выбранный период." }) + `<div class="card"><p style="font-size:14px">Фото и видео хранятся на Яндекс Диске (папка AVTO/TOVARY). Одни и те же материалы можно использовать в разных карточках. Видео и фото добавляются в карточку в кабинете Ozon (блок «Фото» и «Озон.Видео», загрузка с компьютера или по ссылке на Яндекс Диск). В текст описания и в характеристики внешние ссылки вставлять нельзя.</p></div>
  <div class="card"><h2>Материалы по карточкам</h2><div id="mt"></div></div>
  <div class="card"><h2>Папки</h2><div id="mg"></div></div>`;
  dataGrid("#mt", cols, rows, { id: "media-by-offer" });
  if (groups.length) dataGrid("#mg", gCols, groups, { id: "media-folders" }); else $("#mg").innerHTML = "<p class=mut>Папки ещё не опубликованы</p>";
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
  $("#c").innerHTML = periodBar(D, { fixed: "Акции — текущее состояние участия и цен, период на них не влияет. Изменения показаны за последние сутки." }) + `<div class="grid kpis">
    ${kpi("Товаров в акциях", K.products, `${K.participations} участий, средняя скидка ${K.avg_discount}%`, K.products ? "warn" : "good")}
    ${kpi("Советую убрать", K.remove_products, `${K.remove} участий с невыгодной скидкой`, K.remove ? "bad" : "good")}
    ${kpi("Стоит подключить", K.join, "акции с небольшой скидкой", K.join ? "good" : "")}</div>
  ${ch.since ? `<div class="card"><h2>Что изменилось с ${esc(ch.since)}</h2>${ch.added.length ? `<p class="bad"><b>Добавлено (Ozon мог добавить сам):</b></p><ul>${ch.added.map(chTxt).join("")}</ul>` : ""}${ch.removed.length ? `<p class="good"><b>Убрано:</b></p><ul>${ch.removed.map(chTxt).join("")}</ul>` : ""}${(ch.cleaned || []).length ? `<p class="good"><b>Автоочистка убрала сегодня (скидка от ${P.autoclean.threshold}%):</b></p><ul>${ch.cleaned.map(x => `<li><b>${esc(x.offer_id)}</b>: ${esc(x.action)} (−${x.discount}%)</li>`).join("")}</ul>` : ""}${!ch.added.length && !ch.removed.length && !(ch.cleaned || []).length ? "<p class=mut>Изменений нет.</p>" : ""}</div>` : ""}
  <div class="card"><p style="font-size:14px"><b>Автоочистка включена:</b> каждое утро после сбора данных из акций убираются товары с автоскидкой от ${P.autoclean.threshold}% (ручные добавления не трогаются). Последний запуск: ${esc(P.autoclean.last || "ещё не запускалась")}${P.autoclean.error ? ` <span class=bad>· ошибка: ${esc(P.autoclean.error)}</span>` : ""}. Чтобы оставить конкретный товар в акции, добавьте его артикул в файл audit/promo_keep.json.</p></div>
  <div class="card"><h2>Акции Ozon</h2><div id="ta"></div></div>
  <div class="card"><h2>Где товары участвуют сейчас</h2>${P.participation.length ? `<div id="tp"></div>` : "<p class=good>Ни один товар не участвует в акциях.</p>"}<p class="note">${esc(P.note)} Порог совета «убрать»: скидка от 15% и продажи не окупают потерю, либо продажа в убыток.</p></div>
  <div class="card"><h2>Куда можно вступить</h2><div id="tc"></div></div>`;
  dataGrid("#ta", aCols, P.actions, { id: "promos-actions" });
  if ($("#tp")) dataGrid("#tp", pCols, P.participation.slice(), { id: "promos-participation" });
  dataGrid("#tc", cCols, P.candidates.filter(c => c.advice !== "skip" || c.discount < 40), { id: "promos-candidates" });
}

/* ---------- Цены ---------- */
function prices(D) {
  const P = D.prices, K = P.kpi;
  const rows = P.rows.slice();
  const cols = [{ h: "Товар", f: r => `<b>${esc(r.offer_id)}</b>`, k: r => r.offer_id },
    { h: "Ваша цена", n: 1, f: r => rub(r.price), k: r => r.price },
    { h: "Зачёркнутая", n: 1, f: r => rub(r.old_price) }, { h: "Мин.", n: 1, f: r => rub(r.min_price) },
    { h: "С учётом акций", n: 1, f: r => rub(r.effective), c: r => r.effective < r.price * 0.98 ? "bad" : "", k: r => r.effective },
    { h: "Покупатель платит (ср.)", n: 1, f: r => r.buyer_paid == null ? "—" : rub(r.buyer_paid), k: r => r.buyer_paid },
    { h: "Баллы Ozon (ср.)", n: 1, f: r => r.ozon_points == null ? "—" : rub(r.ozon_points) + ` <span class="mut">(${r.points_share}%)</span>`, k: r => r.ozon_points },
    { h: "Автодобавление в акции", f: r => r.auto_add ? (r.auto_add_keep ? "<span class=good>включено (намеренно)</span>" : "<span class=warn>включено</span>") : "<span class=mut>выключено</span>", k: r => r.auto_add ? 1 : 0 },
    { h: "Безубыточная", n: 1, f: r => r.breakeven == null ? "—" : rub(r.breakeven), c: r => r.breakeven != null && r.price < r.breakeven ? "bad" : "", k: r => r.breakeven },
    { h: "Цена для маржи 30%", n: 1, f: r => r.price_m30 == null ? "—" : rub(r.price_m30), k: r => r.price_m30 },
    { h: "Прибыль/шт", n: 1, f: r => r.profit_unit == null ? "—" : rub(r.profit_unit), c: r => r.profit_unit != null && r.profit_unit < 0 ? "bad" : "", k: r => r.profit_unit },
    { h: "Заметки", f: r => r.notes.map(n => `<div style="font-size:12px">${esc(n)}</div>`).join("") }];
  $("#c").innerHTML = periodBar(D, { fixed: "Цены, баллы Ozon и безубыточность — текущие значения из API, период на них не влияет." }) + `<div class="grid kpis">
    ${kpi("Товаров", K.products, "цены из API Ozon")}
    ${kpi("Автодобавление в акции", `${K.auto_add} из ${K.products}`, K.auto_add_unwanted ? `${K.auto_add_unwanted} включено без вашего решения` : "включено только там, где выгоден буст", K.auto_add_unwanted ? "warn" : "good")}
    ${kpi("Баллы Ozon в цене покупателя", K.avg_points_share + "%", "в среднем по заказам: столько скидки платит Ozon", "")}
    ${kpi("Цена ниже безубыточной", K.below_breakeven, "с учётом себестоимости", K.below_breakeven ? "bad" : "good")}</div>
  <div class="card"><h2>Цены на товары</h2><div id="tp"></div><p class="note">${esc(P.note)} Безубыточная цена = (логистика + себестоимость) / (1 − комиссия). «Цена для маржи 30%» считается так же с запасом 30% от цены. Себестоимость взята из вашей таблицы.</p></div>`;
  dataGrid("#tp", cols, rows, { id: "prices" });
}

/* ---------- Админ ---------- */
const ST = { ok: ["ok", "обновлено успешно"], warn: ["warn", "обновлено с предупреждениями"], errors: ["bad", "обновлено, но данные с ошибками"], failed: ["bad", "прогон завершился ошибкой"], stale: ["bad", "данные устарели"], running: ["run", "идёт обновление"], never: ["", "журнал прогонов пуст"] };
const LEGEND = {
  ok: "Все шаги отработали с кодом 0, данные пересобраны и опубликованы.",
  warn: "Прогон отработал, но есть отклонения: раздел не обновился, отчёт собран раньше сырья или в журнале есть строки ошибок.",
  errors: "Прогон отработал, но данные повреждены: Ozon вернул ошибку по разделу, отчёт пустой или сырьё не обновилось.",
  failed: "Шаг run_daily.sh завершился с ненулевым кодом — детали в журнале прогона.",
  stale: "Отчёт старше 26 часов: ежедневный прогон в 06:00 не состоялся.",
  running: "Прогон идёт прямо сейчас, сбор занимает около часа.",
  never: "data/runs.json не найден: журнал ведётся с момента выкладки этой версии run_daily.sh, первая запись появится после ближайшего прогона в 06:00."
};
const badge = (st, label) => `<span class="badge ${(ST[st] || [""])[0]}">${esc(label || (ST[st] || ["", st])[1])}</span>`;
const dt = s => s ? new Date(s).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
const hms = s => s == null ? "—" : s >= 60 ? `${Math.floor(s / 60)} мин ${s % 60} с` : `${s} с`;
const plural = (n, f) => `${n} ` + f[n % 10 === 1 && n % 100 !== 11 ? 0 : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? 1 : 2];

function admin(D) {
  const H = D.health;
  if (!H) {
    $("#c").innerHTML = `<div class="banner">Состояние обновления неизвестно: в data.json нет раздела health. Он появляется после прогона обновлённым server/run_daily.sh (шаги collector/run_log.py и collector/health.py).</div>`;
    return;
  }
  const L = H.last_run || {}, steps = L.steps || [], bad = steps.filter(s => s.rc);
  const LV = { critical: "критично", warn: "внимание", info: "инфо" };
  $("#c").innerHTML = `<div class="grid kpis">
    ${kpi("Состояние обновления", badge(H.status, H.label), `следующий запуск: ${esc(H.next_run)}`)}
    ${kpi("Последний прогон", dt(L.started_at), !L.started_at ? "прогонов ещё не было" : L.finished_at ? `${esc(L.duration || "—")} · без ошибок: ${steps.length - bad.length} из ${steps.length}` : "идёт сейчас", bad.length ? "bad" : "")}
    ${kpi("Отчёт собран", dt(H.report_generated_at), H.report_age ? `${esc(H.report_age)}${H.period ? ` · данные за ${esc(H.period[0])} — ${esc(H.period[1])}` : ""}` : "нет data/metrics.json", H.report_generated_at ? "" : "bad")}
    ${kpi("Уведомления", `${H.counts.critical + H.counts.warn}`, `критичных: ${H.counts.critical}, внимания: ${H.counts.warn}, инфо: ${H.counts.info}`, H.counts.critical ? "bad" : H.counts.warn ? "warn" : "good")}</div>

  <div class="card"><h2>Уведомления об ошибках</h2>${H.errors.length
      ? `<div class="alerts">${H.errors.map(e => `<div class="alert ${esc(e.level)}"><b><span class="tag lv-${esc(e.level)}">${LV[e.level] || esc(e.level)}</span> ${esc(e.title)}</b>${e.detail ? `<div class="mut" style="font-size:13px">${esc(e.detail)}</div>` : ""}</div>`).join("")}</div>`
      : `<p class="good">Ошибок нет: прогон отработал, все разделы собраны заново.</p>`}
    <p class="note">Источники: коды возврата шагов run_daily.sh, признак <code>_error</code> в data/raw/*.json (при 429/5xx/400 от Ozon collect.py выходит с кодом 0 — иначе эти сбои не увидеть), строки ERROR из /var/log/ozon-update.log, возраст отчёта и сырья.</p></div>

  <div class="card"><h2>Последний прогон по шагам</h2>${steps.length
      ? `<div class="scroll"><table><thead><tr><th>Шаг</th><th>Результат</th><th class="n">Длительность</th><th>Завершён</th></tr></thead><tbody>${steps.map(s => `<tr><td><code>${esc(s.name)}</code></td><td>${s.rc ? `<span class="tag p-high">код ${s.rc}</span>` : `<span class="tag">ok</span>`}</td><td class="n">${hms(s.s)}</td><td>${dt(s.at)}</td></tr>`).join("")}</tbody></table></div>`
      : `<p class="mut">Шаги не записаны: прогон начат, но run_log.py ещё не вызывался.</p>`}</div>

  <div class="card"><h2>История обновлений <span class="mut" id="runcnt" style="font-weight:400;font-size:13px"></span></h2><div id="runs"></div>
    <p class="note">В журнале data/runs.json хранится ${H.counts.runs} ${plural(H.counts.runs, ["прогон", "прогона", "прогонов"])}, показываются последние ${H.runs.length}.</p></div>

  ${H.log_tail && H.log_tail.length ? `<div class="card"><h2>Строки ошибок из журнала</h2><pre class="log">${H.log_tail.map(esc).join("\n")}</pre><p class="note">/var/log/ozon-update.log, последний прогон.</p></div>` : ""}

  <div class="card"><h2>Что означают статусы</h2><div class="scroll"><table><thead><tr><th>Статус</th><th>Когда ставится</th></tr></thead><tbody>${Object.keys(ST).map(k => `<tr><td>${badge(k, (H.legend || {})[k])}</td><td>${esc(LEGEND[k])}</td></tr>`).join("")}</tbody></table></div>
    <p class="note">Автообновление: cron <code>0 6 * * *</code> → <code>/opt/ozon/app/run_daily.sh</code>, журнал <code>/var/log/ozon-update.log</code>. Снимок состояния делается во время прогона, поэтому страница показывает данные на момент последней публикации. PDF-отчёты (make_report_pdf.py, make_full_report.py) в автообновление не входят — они собираются вручную.</p></div>`;

  const runCols = [
    { h: "Начало", f: r => dt(r.started_at), k: r => r.started_at, t: r => r.started_at },
    { h: "Завершение", f: r => r.finished_at ? dt(r.finished_at) : `<span class="mut">идёт</span>`, k: r => r.finished_at, t: r => r.finished_at || "идёт" },
    { h: "Длительность", n: 1, f: r => esc(r.duration || "—"), k: r => r.duration_s },
    { h: "Статус", f: r => r.status === "ok" ? `<span class="tag">успешно</span>` : r.status === "failed" ? `<span class="tag p-high">ошибка</span>` : r.finished_at ? `<span class="tag p-medium">не закрыт</span>` : `<span class="tag p-medium">идёт</span>`, k: r => r.status, t: r => r.status || "не закрыт" },
    { h: "Шаги с ошибкой", f: r => { const b = (r.steps || []).filter(x => x.rc); return b.length ? `<span class="bad">${b.map(x => esc(x.name)).join(", ")}</span>` : `<span class="mut">${(r.steps || []).length} без ошибок</span>`; }, t: r => (r.steps || []).filter(x => x.rc).map(x => x.name).join(", ") }];
  dataGrid("#runs", runCols, H.runs, { id: "admin-runs", scrollY: true, onCount: (n, all) => { const c = $("#runcnt"); if (c) c.textContent = `— показано ${n} из ${all}`; } });
}

/* ---------- Хаб ---------- */
const TYPES_KEY = "type";
async function hub(D) {
  let tasks = [], live = true;
  try { const r = await fetch("api/tasks", { cache: "no-store" }); if (!r.ok) throw 0; tasks = await r.json(); }
  catch { live = false; tasks = D.tasks_seed || []; }
  const types = [...new Set(tasks.map(t => t.type))].sort();
  const reports = [["dashboard.html", "Дашборд", "Выручка, прибыль, расходы, отмены"], ["products.html", "Товары", "Прибыль и маржа по каждому артикулу"], ["cards.html", "Карточки и акции", "Аудит SEO, конкуренты, готовые тексты, цены в акциях"], ["ideas.html", "Идеи для печати", "Что ещё печатать и продавать: спрос, конкуренты, калькулятор"], ["quality.html", "Качество и рейтинг", "Рейтинг продавца, контент-рейтинг, заявки на скидку, компенсации"], ["media.html", "Фото и видео", "Папки Яндекс Диска по товарам"], ["promos.html", "Акции", "Где товары в акциях, что убрать, куда вступить (обновляется ежедневно)"], ["prices.html", "Цены на товары", "Цена продавца, что платит покупатель, баллы Ozon, безубыточная цена"], ["savings.html", "Экономия расходов", "Комиссии, штрафы, логистика: сколько можно сэкономить"], ["accounting.html", "Бухгалтерия", "Баланс, движение денег, начисления"], ["accruals.csv", "Начисления (CSV)", "Выгрузка для учёта"], ["products.csv", "Прибыль по товарам (CSV)", "Выгрузка для Excel"]];
  $("#c").innerHTML = periodBar(D, { fixed: "Период действует в разделах с данными (Дашборд, Товары, Бухгалтерия и др.). Даты ниже — отдельный фильтр истории задач." }) + `<div class="grid reports" style="margin-bottom:18px">${reports.map(r => `<a href="${r[0]}"><b>${r[1]}</b><span>${r[2]}</span></a>`).join("")}</div>
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
  if (page !== "report") shell("Загрузка…");
  let D; try { D = await (await fetch("data.json", { cache: "no-store" })).json(); } catch { $("#c").innerHTML = "<p class=bad>Не удалось загрузить данные</p>"; return; }
  if (page === "report") { window.__PRINT__ = true; initPeriod(D); await window.buildReport(D, { hub, dashboard, products, cards, ideas, quality, media, promos, prices, savings, accounting }); return; }
  const upd = "Обновлено: " + new Date(D.generated_at).toLocaleString("ru-RU");
  const T = { hub: "Хаб отчётов и задач", dashboard: "Дашборд магазина", products: "Товары и прибыль", accounting: "Бухгалтерия", savings: "Снижение расходов", cards: "Карточки: аудит и акции", ideas: "Что печатать и продавать", quality: "Качество и рейтинг", media: "Фото и видео товаров", promos: "Акции Ozon", prices: "Цены на товары", admin: "Админ: состояние обновления" };
  const st = D.health && D.health.status;
  const ha = !st || st === "ok" || st === "running" ? null
    : { cls: st === "warn" ? "warn" : "bad", text: `${D.health.label}: ${plural(D.health.counts.critical, ["критичная ошибка", "критичных ошибки", "критичных ошибок"])}, ${plural(D.health.counts.warn, ["предупреждение", "предупреждения", "предупреждений"])}` };
  initPeriod(D);
  const FNS = { hub, dashboard, products, accounting, savings, cards, ideas, quality, media, promos, prices, admin };
  const render = () => { shell(T[page], upd, ha); FNS[page](D); mountPeriod(D, render); };   // смена периода перерисовывает раздел целиком
  render();
})();
