// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ONBOARD_COLUMNS = [
  { key: "city", label: "City", numeric: false },
  { key: "business_name", label: "Business Name", numeric: false },
  { key: "onboarder_name", label: "Onboarder", numeric: false },
  { key: "onboarding_date", label: "Onboard Date", numeric: false },
  { key: "users_onboarded", label: "Users Onboarded", numeric: true },
  { key: "activated_users", label: "Activated", numeric: true },
  { key: "transacting_users", label: "Transacting", numeric: true },
  { key: "secure_users", label: "Secured (Email/Phone)", numeric: true },
  { key: "onboarded_tier1", label: "Tier 1 (Pre Jan 28)", numeric: true },
  { key: "onboarded_tier2", label: "Tier 2 (Jan 28+)", numeric: true },
  { key: "activated_tier2", label: "Activated T2", numeric: true },
  { key: "earnings", label: "Earnings ($)", numeric: true },
];

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const S = {
  tab: "overview",
  startDate: "",
  endDate: "",
  cities: new Set(),
  merchantOnbSort: { col: 4, asc: false },
  activationUserSort: { col: 4, asc: false },
};

// ---------------------------------------------------------------------------
// Indexes (built once from granular data)
// ---------------------------------------------------------------------------

const IDX = {
  merchants: new Map(),        // merchant_id → static row
  onboardings: new Map(),      // merchant_id → [onboarding rows]
  activations: new Map(),      // merchant_id → [activation rows]
  dailyActivity: new Map(),    // merchant_id → [daily activity rows]
  txnBreakdown: new Map(),     // "merchant_id:user_id" → txn breakdown row
  invitations: new Map(),      // "merchant_id:user_id" → {referral_count, cn_onboarding_count}
  firstTransactions: new Map(), // "merchant_id:user_id" → first debit/credit row
  cycling: new Map(),          // "merchant_id:user_id" → cycling row
  fraudSummary: [],            // merchant_fraud_summary rows
};

function buildIndexes() {
  IDX.merchants.clear();
  IDX.onboardings.clear();
  IDX.activations.clear();
  IDX.dailyActivity.clear();
  IDX.txnBreakdown.clear();
  IDX.invitations.clear();
  IDX.firstTransactions.clear();
  IDX.cycling.clear();
  IDX.fraudSummary = [];

  const CITY_MAP = { "Punjab": "Lahore", "Sindh": "Karachi" };
  for (const m of (RAW.merchant_static || [])) {
    if (CITY_MAP[m.city]) m.city = CITY_MAP[m.city];
    IDX.merchants.set(m.merchant_id, m);
  }
  for (const o of (RAW.user_onboardings || [])) {
    if (!IDX.onboardings.has(o.merchant_id)) IDX.onboardings.set(o.merchant_id, []);
    IDX.onboardings.get(o.merchant_id).push(o);
  }
  for (const a of (RAW.user_activations || [])) {
    if (!IDX.activations.has(a.merchant_id)) IDX.activations.set(a.merchant_id, []);
    IDX.activations.get(a.merchant_id).push(a);
  }
  for (const d of (RAW.merchant_daily_activity || [])) {
    if (!IDX.dailyActivity.has(d.merchant_id)) IDX.dailyActivity.set(d.merchant_id, []);
    IDX.dailyActivity.get(d.merchant_id).push(d);
  }
  for (const t of (RAW.user_txn_breakdown || [])) {
    IDX.txnBreakdown.set(t.merchant_id + ":" + t.user_id, t);
  }
  for (const inv of (RAW.user_invitations || [])) {
    IDX.invitations.set(inv.merchant_id + ":" + inv.user_id, inv);
  }
  for (const ft of (RAW.user_first_transactions || [])) {
    IDX.firstTransactions.set(ft.merchant_id + ":" + ft.user_id, ft);
  }
  for (const c of (RAW.user_cycling || [])) {
    IDX.cycling.set(c.merchant_id + ":" + c.user_id, c);
  }
  IDX.fraudSummary = RAW.merchant_fraud_summary || [];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pktToday() {
  const now = new Date();
  const pkt = new Date(now.getTime() + (5 * 60 * 60 * 1000));
  return pkt.toISOString().slice(0, 10);
}

function addDays(dateStr, n) {
  const d = new Date(dateStr + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function fmtDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00Z");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

function medianOf(arr) {
  if (arr.length === 0) return 0;
  const m = Math.floor(arr.length / 2);
  return arr.length % 2 === 1 ? arr[m] : +((arr[m - 1] + arr[m]) / 2).toFixed(1);
}

function fmtCompact(n) {
  if (Math.abs(n) >= 1000) return (n / 1000).toPrecision(2) + "k";
  if (Math.abs(n) >= 100) return Math.round(n).toString();
  if (n === 0) return "0";
  return n.toFixed(2);
}

function daysBetween(dateStr1, dateStr2) {
  const d1 = new Date(dateStr1 + "T00:00:00Z");
  const d2 = new Date(dateStr2 + "T00:00:00Z");
  return Math.round(Math.abs(d2 - d1) / (1000 * 60 * 60 * 24));
}

function mondayOf(dateStr) {
  const d = new Date(dateStr + "T00:00:00Z");
  const day = d.getUTCDay(); // 0=Sun..6=Sat
  const diff = day === 0 ? 6 : day - 1;
  d.setUTCDate(d.getUTCDate() - diff);
  return d.toISOString().slice(0, 10);
}

function fmtDaysOrHours(days) {
  if (days === 0) return "< 1 day";
  if (days < 1) return Math.round(days * 24) + " hours";
  return days + (days === 1 ? " day" : " days");
}

// ---------------------------------------------------------------------------
// Calendar date range picker
// ---------------------------------------------------------------------------

const yesterday = addDays(pktToday(), -1);
const CAL = { viewYear: 0, viewMonth: 0, selecting: false, tempStart: "" };

function getMinDate() {
  if (RAW.merchant_static) {
    const dates = [];
    for (const m of RAW.merchant_static) if (m.onboarding_date) dates.push(m.onboarding_date);
    for (const d of (RAW.merchant_daily_activity || [])) if (d.date) dates.push(d.date);
    dates.sort();
    return dates.length > 0 ? dates[0] : addDays(yesterday, -27);
  }
  const dates = (RAW.merchant_summary || []).map(m => m.onboarding_date).filter(Boolean).sort();
  return dates.length > 0 ? dates[0] : addDays(yesterday, -27);
}
function getMaxDate() {
  if (RAW.merchant_static) {
    const dates = [];
    for (const d of (RAW.merchant_daily_activity || [])) if (d.date) dates.push(d.date);
    for (const o of (RAW.user_onboardings || [])) if (o.date) dates.push(o.date);
    dates.sort();
    return dates.length > 0 ? dates[dates.length - 1] : yesterday;
  }
  return yesterday;
}

function renderCalendar() {
  const grid = document.getElementById("calendar-grid");
  if (!grid) return;
  grid.querySelectorAll(".cal-day").forEach(el => el.remove());

  const label = document.getElementById("cal-month-label");
  const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  label.textContent = monthNames[CAL.viewMonth] + " " + CAL.viewYear;

  const minDate = getMinDate();
  const maxDate = getMaxDate();
  const today = pktToday();

  const firstOfMonth = new Date(Date.UTC(CAL.viewYear, CAL.viewMonth, 1));
  const daysInMonth = new Date(Date.UTC(CAL.viewYear, CAL.viewMonth + 1, 0)).getUTCDate();

  let startDow = firstOfMonth.getUTCDay() - 1;
  if (startDow < 0) startDow = 6;

  const prevMonthDays = new Date(Date.UTC(CAL.viewYear, CAL.viewMonth, 0)).getUTCDate();
  for (let i = startDow - 1; i >= 0; i--) {
    const day = prevMonthDays - i;
    const m = CAL.viewMonth === 0 ? 11 : CAL.viewMonth - 1;
    const y = CAL.viewMonth === 0 ? CAL.viewYear - 1 : CAL.viewYear;
    const ds = `${y}-${String(m + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    grid.appendChild(createDayCell(day, ds, true, minDate, maxDate, today));
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const ds = `${CAL.viewYear}-${String(CAL.viewMonth + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    grid.appendChild(createDayCell(d, ds, false, minDate, maxDate, today));
  }

  const totalCells = startDow + daysInMonth;
  const trailing = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
  for (let d = 1; d <= trailing; d++) {
    const m = CAL.viewMonth === 11 ? 0 : CAL.viewMonth + 1;
    const y = CAL.viewMonth === 11 ? CAL.viewYear + 1 : CAL.viewYear;
    const ds = `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    grid.appendChild(createDayCell(d, ds, true, minDate, maxDate, today));
  }
}

function createDayCell(dayNum, dateStr, otherMonth, minDate, maxDate, today) {
  const div = document.createElement("div");
  div.className = "cal-day";
  div.textContent = dayNum;
  div.dataset.date = dateStr;

  if (otherMonth) div.classList.add("other-month");
  if (dateStr < minDate || dateStr > maxDate) {
    div.classList.add("disabled");
    return div;
  }
  if (dateStr === today) div.classList.add("today");

  const rangeStart = CAL.selecting ? CAL.tempStart : S.startDate;
  const rangeEnd = CAL.selecting ? "" : S.endDate;
  if (rangeStart && rangeEnd) {
    if (dateStr === rangeStart) div.classList.add("range-start");
    if (dateStr === rangeEnd) div.classList.add("range-end");
    if (dateStr > rangeStart && dateStr < rangeEnd) div.classList.add("in-range");
  } else if (rangeStart && dateStr === rangeStart) {
    div.classList.add("range-start", "range-end");
  }

  div.addEventListener("click", (e) => { e.stopPropagation(); onDayClick(dateStr); });
  return div;
}

function onDayClick(dateStr) {
  if (!CAL.selecting) {
    CAL.selecting = true;
    CAL.tempStart = dateStr;
    renderCalendar();
  } else {
    CAL.selecting = false;
    if (dateStr < CAL.tempStart) {
      S.startDate = dateStr;
      S.endDate = CAL.tempStart;
    } else {
      S.startDate = CAL.tempStart;
      S.endDate = dateStr;
    }
    CAL.tempStart = "";
    updateDateRangeLabel();
    closeDatePicker();
    recalc();
  }
}

function updateDateRangeLabel() {
  const el = document.getElementById("date-range-label");
  if (el) el.textContent = fmtDate(S.startDate) + " – " + fmtDate(S.endDate);
}

function openDatePicker() {
  const d = new Date(S.endDate + "T00:00:00Z");
  CAL.viewYear = d.getUTCFullYear();
  CAL.viewMonth = d.getUTCMonth();
  CAL.selecting = false;
  CAL.tempStart = "";
  renderCalendar();
  document.getElementById("date-range-popup").classList.add("open");
}

function closeDatePicker() {
  document.getElementById("date-range-popup").classList.remove("open");
  CAL.selecting = false;
  CAL.tempStart = "";
}

function applyPreset(preset) {
  const max = getMaxDate();
  let start;
  if (preset === "7d") start = addDays(max, -6);
  else if (preset === "14d") start = addDays(max, -13);
  else if (preset === "30d") start = addDays(max, -29);
  else if (preset === "mtd") {
    const d = new Date(max + "T00:00:00Z");
    start = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-01`;
  } else return;

  const minDate = getMinDate();
  if (start < minDate) start = minDate;
  S.startDate = start;
  S.endDate = max;
  updateDateRangeLabel();
  closeDatePicker();
  recalc();
}

// ---------------------------------------------------------------------------
// City filter
// ---------------------------------------------------------------------------

function getAllCities() {
  const cities = new Set();
  if (RAW.merchant_static) {
    for (const m of RAW.merchant_static) if (m.city) cities.add(m.city);
  } else {
    for (const m of (RAW.merchant_summary || [])) if (m.city) cities.add(m.city);
  }
  return [...cities].sort();
}

function renderCitySelect() {
  const sel = document.getElementById("city-select");
  sel.innerHTML = "";
  const allCities = getAllCities();
  const isAll = S.cities.size === allCities.length;

  const allOpt = document.createElement("option");
  allOpt.value = "__all__";
  allOpt.textContent = "All Cities";
  sel.appendChild(allOpt);

  for (const city of allCities) {
    const opt = document.createElement("option");
    opt.value = city;
    opt.textContent = city;
    sel.appendChild(opt);
  }

  sel.value = isAll ? "__all__" : [...S.cities][0];
}

// ---------------------------------------------------------------------------
// Data: build merchant data
// ---------------------------------------------------------------------------

function buildMerchantData() {
  // Legacy fallback: if no granular data, use old merchant_summary
  if (!RAW.merchant_static) {
    const raw = RAW.merchant_summary || [];
    const CITY_MAP = { "Punjab": "Lahore", "Sindh": "Karachi" };
    for (const m of raw) { if (CITY_MAP[m.city]) m.city = CITY_MAP[m.city]; }
    const rows = raw.filter(m => S.cities.has(m.city));
    for (const m of rows) {
      m.cohort = (m.onboarding_date >= S.startDate && m.onboarding_date <= S.endDate) ? "New" : "Existing";
      const t1 = m.onboarded_tier1 || 0;
      const t2 = m.onboarded_tier2 || 0;
      const at2 = m.activated_tier2 || 0;
      m.onboarded_tier1 = t1;
      m.onboarded_tier2 = t2;
      m.activated_tier2 = at2;
      m.earnings = t1 * 1.0 + t2 * 0.5 + at2 * 0.5;
      if (t1 === 0 && t2 === 0 && m.users_onboarded > 0) {
        if (m.onboarding_date < "2026-01-28") {
          m.onboarded_tier1 = m.users_onboarded;
          m.earnings = m.users_onboarded * 1.0;
        } else {
          m.onboarded_tier2 = m.users_onboarded;
          m.earnings = m.users_onboarded * 0.5;
        }
      }
      m.activated_users = m.activated_users || 0;
    }
    return rows;
  }

  // Granular data: filter + re-aggregate by date range
  const rows = [];
  const TIER2_DATE = "2026-01-28";

  for (const [mid, m] of IDX.merchants) {
    if (!S.cities.has(m.city)) continue;

    // Sum daily activity in date range
    const dailyRows = (IDX.dailyActivity.get(mid) || []).filter(d => d.date >= S.startDate && d.date <= S.endDate);
    let cn_count = 0, cn_volume = 0, zce_count = 0, zce_volume = 0;
    let bt_count = 0, bt_volume = 0, card_count = 0, card_volume = 0;
    for (const d of dailyRows) {
      cn_count += d.cn_count || 0;
      cn_volume += d.cn_volume || 0;
      zce_count += d.zce_count || 0;
      zce_volume += d.zce_volume || 0;
      bt_count += d.bt_count || 0;
      bt_volume += d.bt_volume || 0;
      card_count += d.card_count || 0;
      card_volume += d.card_volume || 0;
    }

    // Filter onboardings by date range
    const onbRows = (IDX.onboardings.get(mid) || []).filter(o => o.date >= S.startDate && o.date <= S.endDate);
    const users_onboarded = onbRows.length;
    const onboardedUserIds = new Set(onbRows.map(o => o.user_id));
    const transacting_users = onbRows.filter(o => o.is_transacting).length;
    const secure_users = onbRows.filter(o => o.is_secure).length;

    // Filter activations: must be for users onboarded in range AND activation date in range
    const actRows = (IDX.activations.get(mid) || []).filter(a => onboardedUserIds.has(a.user_id) && a.date >= S.startDate && a.date <= S.endDate);
    const activated_users = actRows.length;

    // Tier split based on onboarding date
    const tier1_onboarded = onbRows.filter(o => o.date < TIER2_DATE).length;
    const tier2_onboarded = onbRows.filter(o => o.date >= TIER2_DATE).length;
    // Activated tier2: activations for users onboarded on/after tier2 date
    const tier2UserIds = new Set(onbRows.filter(o => o.date >= TIER2_DATE).map(o => o.user_id));
    const activated_tier2 = actRows.filter(a => tier2UserIds.has(a.user_id)).length;
    const earnings = tier1_onboarded * 1.0 + tier2_onboarded * 0.5 + activated_tier2 * 0.5;

    // Cohort
    const cohort = (m.onboarding_date >= S.startDate && m.onboarding_date <= S.endDate) ? "New" : "Existing";

    rows.push({
      merchant_id: mid,
      business_name: m.business_name,
      city: m.city,
      latitude: m.latitude,
      longitude: m.longitude,
      status: m.status,
      onboarding_date: m.onboarding_date,
      onboarder_username: m.onboarder_username,
      onboarder_name: m.onboarder_name,
      cohort,
      cn_count, cn_volume: +cn_volume.toFixed(2),
      zce_count, zce_volume: +zce_volume.toFixed(2),
      bt_count, bt_volume: +bt_volume.toFixed(2),
      card_count, card_volume: +card_volume.toFixed(2),
      has_user_activity: dailyRows.length > 0,
      users_onboarded,
      activated_users,
      transacting_users,
      secure_users,
      onboarded_tier1: tier1_onboarded,
      onboarded_tier2: tier2_onboarded,
      activated_tier2,
      earnings,
    });
  }

  return rows;
}

// ---------------------------------------------------------------------------
// Render: sortable table
// ---------------------------------------------------------------------------

function renderSortableTable(headId, bodyId, footId, columns, rows, sortState, recalcFn) {
  const headTr = document.getElementById(headId);
  const tbody = document.getElementById(bodyId);
  const tfoot = document.getElementById(footId);
  if (!headTr || !tbody || !tfoot) return;

  headTr.innerHTML = "";
  columns.forEach((col, i) => {
    const th = document.createElement("th");
    th.textContent = col.label;
    if (i === sortState.col) {
      th.innerHTML += ` <span class="sort-arrow">${sortState.asc ? "&#9650;" : "&#9660;"}</span>`;
    }
    th.addEventListener("click", () => {
      if (sortState.col === i) sortState.asc = !sortState.asc;
      else { sortState.col = i; sortState.asc = col.numeric ? false : true; }
      recalcFn();
    });
    headTr.appendChild(th);
  });

  const col = columns[sortState.col];
  const sorted = [...rows].sort((a, b) => {
    const av = a[col.key], bv = b[col.key];
    if (typeof av === "string") return sortState.asc ? av.localeCompare(bv) : bv.localeCompare(av);
    if (typeof av === "boolean") return sortState.asc ? (av === bv ? 0 : av ? -1 : 1) : (av === bv ? 0 : av ? 1 : -1);
    return sortState.asc ? av - bv : bv - av;
  });

  tbody.innerHTML = "";
  for (const r of sorted) {
    const tr = document.createElement("tr");
    let cells = "";
    for (const c of columns) {
      const val = r[c.key];
      if (c.formatter) {
        cells += `<td>${c.formatter(val, r)}</td>`;
      } else if (c.key === "earnings") {
        cells += `<td>$${(typeof val === "number" ? Math.round(val) : val)}</td>`;
      } else if (c.key.endsWith("_volume")) {
        cells += `<td>$${(typeof val === "number" ? val.toFixed(2) : val)}</td>`;
      } else if (typeof val === "boolean") {
        cells += `<td>${val ? "Yes" : "No"}</td>`;
      } else {
        cells += `<td>${val}</td>`;
      }
    }
    tr.innerHTML = cells;
    tbody.appendChild(tr);
  }

  const numDimCols = columns.filter(c => !c.numeric).length;
  let footCells = `<td colspan="${numDimCols}"><strong>Total (${rows.length})</strong></td>`;
  for (const c of columns) {
    if (!c.numeric) continue;
    if (c.noSum) { footCells += `<td>-</td>`; continue; }
    const sum = rows.reduce((s, r) => s + (typeof r[c.key] === "number" ? r[c.key] : 0), 0);
    if (c.key === "earnings") {
      footCells += `<td>$${Math.round(sum)}</td>`;
    } else if (c.key.endsWith("_volume")) {
      footCells += `<td>$${sum.toFixed(2)}</td>`;
    } else if (c.formatter) {
      footCells += `<td>${c.formatter(sum)}</td>`;
    } else {
      footCells += `<td>${sum}</td>`;
    }
  }
  tfoot.innerHTML = `<tr class="totals-row">${footCells}</tr>`;
}

// ---------------------------------------------------------------------------
// Render: onboarding summary stats
// ---------------------------------------------------------------------------

function renderOnbSummaryStats(rows) {
  const el = document.getElementById("onb-summary-stats");
  if (!el) return;
  const totalOnboarded = rows.reduce((s, r) => s + r.users_onboarded, 0);
  const totalActivated = rows.reduce((s, r) => s + r.activated_users, 0);
  const totalTransacting = rows.reduce((s, r) => s + r.transacting_users, 0);
  const totalSecure = rows.reduce((s, r) => s + r.secure_users, 0);
  const totalEarnings = rows.reduce((s, r) => s + r.earnings, 0);
  el.innerHTML = [
    { label: "Total Users Onboarded", value: totalOnboarded, sub: "" },
    { label: "Activated (Returned to Merchant)", value: totalActivated + " (" + (totalOnboarded ? (totalActivated / totalOnboarded * 100).toPrecision(2) : 0) + "%)", sub: "Same-merchant return transaction" },
    { label: "Transacting (Any Platform)", value: totalTransacting + " (" + (totalOnboarded ? (totalTransacting / totalOnboarded * 100).toPrecision(2) : 0) + "%)", sub: "CN send, card, bank transfer, or ZCE" },
    { label: "Secured Accounts (Email/Phone)", value: totalSecure + " (" + (totalOnboarded ? (totalSecure / totalOnboarded * 100).toPrecision(2) : 0) + "%)", sub: "" },
    { label: "Total Merchant Earnings", value: "$" + Math.round(totalEarnings), sub: "Tier 1: $1/onboard | Tier 2: $0.50 + $0.50/activated" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");
}

// ---------------------------------------------------------------------------
// Render: onboarding merchants vs others
// ---------------------------------------------------------------------------

function renderOnboardingComparison(rows) {
  const headTr = document.getElementById("onb-comparison-head");
  const tbody = document.getElementById("onb-comparison-body");
  if (!headTr || !tbody) return;

  const onbGroup = rows.filter(r => r.users_onboarded > 0);
  const otherGroup = rows.filter(r => r.users_onboarded === 0);

  function agg(arr) {
    const zceCount = arr.reduce((s, r) => s + r.zce_count, 0);
    const zceVol = arr.reduce((s, r) => s + r.zce_volume, 0);
    const cnCount = arr.reduce((s, r) => s + r.cn_count, 0);
    const cnVol = arr.reduce((s, r) => s + r.cn_volume, 0);
    const cardCount = arr.reduce((s, r) => s + r.card_count, 0);
    const medZce = medianOf(arr.filter(r => r.zce_volume > 0).map(r => r.zce_volume).sort((a, b) => a - b));
    const medCn = medianOf(arr.filter(r => r.cn_volume > 0).map(r => r.cn_volume).sort((a, b) => a - b));
    return { count: arr.length, zceCount, zceVol, medZce, cnCount, cnVol, medCn, cardCount };
  }

  const onb = agg(onbGroup);
  const other = agg(otherGroup);
  const total = agg(rows);

  const cols = ["Group", "Count", "% of Total", "Orders", "Orders ($)", "Median $ Sold", "CN Txns", "CN Total ($)", "CN Median $", "Card Txns"];
  headTr.innerHTML = cols.map(c => `<th>${c}</th>`).join("");

  function row(label, g, cls) {
    const pct = rows.length > 0 ? Math.round(g.count / rows.length * 100) : 0;
    return `<tr${cls ? ' class="' + cls + '"' : ''}>
      <td><strong>${label}</strong></td>
      <td>${g.count}</td>
      <td>${pct}%</td>
      <td>${g.zceCount}</td>
      <td>$${fmtCompact(g.zceVol)}</td>
      <td>$${fmtCompact(g.medZce)}</td>
      <td>${g.cnCount}</td>
      <td>$${fmtCompact(g.cnVol)}</td>
      <td>$${fmtCompact(g.medCn)}</td>
      <td>${g.cardCount}</td>
    </tr>`;
  }

  tbody.innerHTML = row("Onboarding Merchants", onb, "") + row("Others", other, "") + row("Total", total, "totals-row");
}

// ---------------------------------------------------------------------------
// Render: users overview (formerly transacting users deep dive)
// ---------------------------------------------------------------------------

function renderUsersOverview(rows) {
  const statsEl = document.getElementById("transacting-summary-stats");
  if (!statsEl) return;

  const totalOnboarded = rows.reduce((s, r) => s + r.users_onboarded, 0);
  const totalActivated = rows.reduce((s, r) => s + r.activated_users, 0);
  const totalTransacting = rows.reduce((s, r) => s + r.transacting_users, 0);
  const totalSecure = rows.reduce((s, r) => s + r.secure_users, 0);

  statsEl.innerHTML = [
    { label: "Total Users Onboarded", value: totalOnboarded },
    { label: "Activated (Returned to Merchant)", value: totalActivated + " (" + (totalOnboarded ? (totalActivated / totalOnboarded * 100).toPrecision(2) : 0) + "%)" },
    { label: "Transacting (Any Platform)", value: totalTransacting + " (" + (totalOnboarded ? (totalTransacting / totalOnboarded * 100).toPrecision(2) : 0) + "%)" },
    { label: "Secured (Email/Phone)", value: totalSecure + " (" + (totalOnboarded ? (totalSecure / totalOnboarded * 100).toPrecision(2) : 0) + "%)" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
  </div>`).join("");
}

// ---------------------------------------------------------------------------
// Shared: collect activation data for both cards
// ---------------------------------------------------------------------------

function collectActivationData() {
  const daysArr = [];
  const amountArr = [];
  let cnActivations = 0;
  let orderActivations = 0;
  let totalActivations = 0;
  let hasTxnFields = false;
  const activatedUserKeys = new Set();
  let securedActivatedCount = 0;

  for (const [mid, actList] of IDX.activations) {
    const m = IDX.merchants.get(mid);
    if (!m || !S.cities.has(m.city)) continue;

    const onbRows = (IDX.onboardings.get(mid) || []).filter(o => o.date >= S.startDate && o.date <= S.endDate);
    const onbUserIds = new Set(onbRows.map(o => o.user_id));
    const onbDateMap = new Map();
    const onbSecureMap = new Map();
    for (const o of onbRows) {
      onbDateMap.set(o.user_id, o.date);
      onbSecureMap.set(o.user_id, o.is_secure);
    }

    for (const a of actList) {
      if (!onbUserIds.has(a.user_id)) continue;
      if (a.date < S.startDate || a.date > S.endDate) continue;
      totalActivations++;
      const userKey = mid + ":" + a.user_id;
      activatedUserKeys.add(userKey);

      if (onbSecureMap.get(a.user_id)) securedActivatedCount++;

      const onbDate = a.onboard_date || onbDateMap.get(a.user_id);
      if (onbDate && a.date) {
        daysArr.push(daysBetween(onbDate, a.date));
      }

      if (a.amount !== undefined && a.amount !== null) {
        hasTxnFields = true;
        amountArr.push(Number(a.amount));
      }
      if (a.txn_type === "cash_note") cnActivations++;
      else if (a.txn_type === "order") orderActivations++;
    }
  }

  return { daysArr, amountArr, cnActivations, orderActivations, totalActivations, activatedUserKeys, securedActivatedCount, hasTxnFields };
}

// ---------------------------------------------------------------------------
// Render: activation event (Card 2)
// ---------------------------------------------------------------------------

function renderActivationEvent(data) {
  const statsEl = document.getElementById("activation-event-stats");
  if (!statsEl) return;

  const { daysArr, amountArr, cnActivations, orderActivations, totalActivations, hasTxnFields } = data;

  if (!hasTxnFields && totalActivations > 0) {
    statsEl.innerHTML = `<div class="stat-box" style="grid-column: 1 / -1;">
      <div class="stat-label">Cache Regeneration Required</div>
      <div class="stat-value" style="font-size:0.95rem;color:var(--text-secondary);">
        Run the cache update to populate activation transaction details (amount, txn_type, onboard_date).
      </div>
    </div>`;
    return;
  }

  if (totalActivations === 0) {
    statsEl.innerHTML = `<div class="stat-box" style="grid-column: 1 / -1;">
      <div class="stat-label">No Activations</div>
      <div class="stat-value" style="font-size:0.95rem;color:var(--text-secondary);">
        No activation events found for the current date range and city filter.
      </div>
    </div>`;
    return;
  }

  const medDays = daysArr.length > 0 ? medianOf([...daysArr].sort((a, b) => a - b)) : "N/A";
  const medAmount = amountArr.length > 0 ? medianOf([...amountArr].sort((a, b) => a - b)) : "N/A";
  const cnPct = totalActivations > 0 ? Math.round(cnActivations / totalActivations * 100) : 0;
  const orderPct = totalActivations > 0 ? Math.round(orderActivations / totalActivations * 100) : 0;

  const medTimeLabel = (typeof medDays === "number" && medDays < 1) ? "Median Time to Activation" : "Median Time to Activation";
  const medTimeValue = medDays === "N/A" ? medDays : fmtDaysOrHours(medDays);

  statsEl.innerHTML = [
    { label: medTimeLabel, value: medTimeValue, sub: "From onboarding to first return" },
    { label: "Cash Note Activations", value: cnActivations + " (" + cnPct + "%)", sub: "" },
    { label: "Order Activations", value: orderActivations + " (" + orderPct + "%)", sub: "" },
    { label: "Median Transaction Value", value: medAmount === "N/A" ? medAmount : "$" + medAmount, sub: "" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");
}

// ---------------------------------------------------------------------------
// Render: activated users' patterns (Card 3)
// ---------------------------------------------------------------------------

function renderActivatedPatterns(data) {
  const statsEl = document.getElementById("activated-patterns-stats");
  if (!statsEl) return;

  const { totalActivations, activatedUserKeys, securedActivatedCount } = data;

  if (totalActivations === 0) {
    statsEl.innerHTML = `<div class="stat-box" style="grid-column: 1 / -1;">
      <div class="stat-label">No Activated Users</div>
      <div class="stat-value" style="font-size:0.95rem;color:var(--text-secondary);">
        No activated users found for the current date range and city filter.
      </div>
    </div>`;
    return;
  }

  const securedPct = totalActivations > 0 ? Math.round(securedActivatedCount / totalActivations * 100) : 0;

  // Build per-user spending array
  const perUserSpending = [];
  let invitedOthers = 0;
  for (const key of activatedUserKeys) {
    const tb = IDX.txnBreakdown.get(key);
    if (tb) {
      perUserSpending.push((tb.cn_volume || 0) + (tb.card_volume || 0) + (tb.bt_volume || 0));
    } else {
      perUserSpending.push(0);
    }
    if (IDX.invitations.has(key)) invitedOthers++;
  }

  const avgSpending = perUserSpending.length > 0 ? +(perUserSpending.reduce((s, v) => s + v, 0) / perUserSpending.length).toFixed(2) : 0;
  const medSpending = perUserSpending.length > 0 ? medianOf([...perUserSpending].sort((a, b) => a - b)) : 0;
  const invitedPct = totalActivations > 0 ? Math.round(invitedOthers / totalActivations * 100) : 0;

  statsEl.innerHTML = [
    { label: "Secured Accounts", value: securedActivatedCount + " (" + securedPct + "%)", sub: "Email or phone on file" },
    { label: "Avg Spending on Platform", value: "$" + avgSpending, sub: "Card, cash note, bank transfer" },
    { label: "Median Spending on Platform", value: "$" + medSpending, sub: "" },
    { label: "Invited Others", value: invitedOthers + " (" + invitedPct + "%)", sub: "Activated users who onboarded new users" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");
}

// ---------------------------------------------------------------------------
// Shared: collect all onboarded user data for Cards 4-5
// ---------------------------------------------------------------------------

function collectAllOnboardedData() {
  const allUserKeys = new Set();
  const onbDateMap = new Map(); // "merchant_id:user_id" → onboard date
  let totalOnboarded = 0;
  let securedCount = 0;

  for (const [mid, m] of IDX.merchants) {
    if (!S.cities.has(m.city)) continue;
    const onbRows = (IDX.onboardings.get(mid) || []).filter(o => o.date >= S.startDate && o.date <= S.endDate);
    for (const o of onbRows) {
      const key = mid + ":" + o.user_id;
      allUserKeys.add(key);
      onbDateMap.set(key, o.date);
      totalOnboarded++;
      if (o.is_secure) securedCount++;
    }
  }

  return { allUserKeys, onbDateMap, totalOnboarded, securedCount };
}

// ---------------------------------------------------------------------------
// Render: all users first transactions (Card 4)
// ---------------------------------------------------------------------------

function renderAllUsersTransactions(allData) {
  const statsEl = document.getElementById("all-users-txn-stats");
  if (!statsEl) return;

  const { allUserKeys, onbDateMap, totalOnboarded } = allData;

  if (totalOnboarded === 0) {
    statsEl.innerHTML = `<div class="stat-box" style="grid-column: 1 / -1;">
      <div class="stat-label">No Onboarded Users</div>
      <div class="stat-value" style="font-size:0.95rem;color:var(--text-secondary);">
        No onboarded users found for the current date range and city filter.
      </div>
    </div>`;
    return;
  }

  const debitDays = [];
  const creditDays = [];
  const creditAmounts = [];
  const debitTypeCounts = {};

  for (const key of allUserKeys) {
    const ft = IDX.firstTransactions.get(key);
    if (!ft) continue;
    const onbDate = onbDateMap.get(key);

    if (ft.first_debit_date && onbDate) {
      debitDays.push(daysBetween(onbDate, ft.first_debit_date));
      const t = ft.first_debit_type || "unknown";
      debitTypeCounts[t] = (debitTypeCounts[t] || 0) + 1;
    }

    if (ft.first_credit_date && onbDate) {
      creditDays.push(daysBetween(onbDate, ft.first_credit_date));
      if (ft.first_credit_amount) creditAmounts.push(Number(ft.first_credit_amount));
    }
  }

  const medDebitDays = debitDays.length > 0 ? medianOf([...debitDays].sort((a, b) => a - b)) : null;
  const medCreditDays = creditDays.length > 0 ? medianOf([...creditDays].sort((a, b) => a - b)) : null;
  const medCreditAmt = creditAmounts.length > 0 ? medianOf([...creditAmounts].sort((a, b) => a - b)) : null;

  // Most common debit type
  let topDebitType = "N/A";
  let topDebitPct = "";
  let debitBreakdownSub = "";
  const totalDebits = debitDays.length;
  if (totalDebits > 0) {
    const typeLabels = { cn_send: "Cash Note", card: "Card", bank_transfer: "Bank Transfer", zce_order: "ZCE Order" };
    const entries = Object.entries(debitTypeCounts).sort((a, b) => b[1] - a[1]);
    const [topType, topCount] = entries[0];
    topDebitType = typeLabels[topType] || topType;
    topDebitPct = Math.round(topCount / totalDebits * 100) + "%";
    debitBreakdownSub = entries.map(([t, c]) => (typeLabels[t] || t) + ": " + c + " (" + Math.round(c / totalDebits * 100) + "%)").join(", ");
  }

  statsEl.innerHTML = [
    { label: "Median Time to First Debit", value: medDebitDays !== null ? fmtDaysOrHours(medDebitDays) : "N/A", sub: totalDebits + " of " + totalOnboarded + " users had a debit" },
    { label: "Source of First Debit", value: topDebitType + (topDebitPct ? " (" + topDebitPct + ")" : ""), sub: debitBreakdownSub },
    { label: "Median Time to First Credit", value: medCreditDays !== null ? fmtDaysOrHours(medCreditDays) : "N/A", sub: creditDays.length + " of " + totalOnboarded + " users received a credit" },
    { label: "Median First Credit Amount", value: medCreditAmt !== null ? "$" + medCreditAmt : "N/A", sub: "" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");
}

// ---------------------------------------------------------------------------
// Render: all users patterns (Card 5)
// ---------------------------------------------------------------------------

function renderAllUsersPatterns(allData) {
  const statsEl = document.getElementById("all-users-patterns-stats");
  if (!statsEl) return;

  const { allUserKeys, totalOnboarded, securedCount } = allData;

  if (totalOnboarded === 0) {
    statsEl.innerHTML = `<div class="stat-box" style="grid-column: 1 / -1;">
      <div class="stat-label">No Onboarded Users</div>
      <div class="stat-value" style="font-size:0.95rem;color:var(--text-secondary);">
        No onboarded users found for the current date range and city filter.
      </div>
    </div>`;
    return;
  }

  const securedPct = totalOnboarded > 0 ? Math.round(securedCount / totalOnboarded * 100) : 0;

  // Build per-user spending array
  const perUserSpending = [];
  let invitedOthers = 0;
  for (const key of allUserKeys) {
    const tb = IDX.txnBreakdown.get(key);
    if (tb) {
      perUserSpending.push((tb.cn_volume || 0) + (tb.card_volume || 0) + (tb.bt_volume || 0));
    } else {
      perUserSpending.push(0);
    }
    if (IDX.invitations.has(key)) invitedOthers++;
  }

  const avgSpending = perUserSpending.length > 0 ? +(perUserSpending.reduce((s, v) => s + v, 0) / perUserSpending.length).toFixed(2) : 0;
  const medSpending = perUserSpending.length > 0 ? medianOf([...perUserSpending].sort((a, b) => a - b)) : 0;
  const invitedPct = totalOnboarded > 0 ? Math.round(invitedOthers / totalOnboarded * 100) : 0;

  statsEl.innerHTML = [
    { label: "Secured Accounts", value: securedCount + " (" + securedPct + "%)", sub: "Email or phone on file" },
    { label: "Avg Spending on Platform", value: "$" + avgSpending, sub: "Card, cash note, bank transfer" },
    { label: "Median Spending on Platform", value: "$" + medSpending, sub: "" },
    { label: "Invited Others", value: invitedOthers + " (" + invitedPct + "%)", sub: "Onboarded users who invited new users" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");
}

// ---------------------------------------------------------------------------
// Render: user-level activation details table
// ---------------------------------------------------------------------------

const ACTIVATION_USER_COLUMNS = [
  { key: "user_id_short", label: "User ID", numeric: false,
    formatter: (v, r) => `<span class="uid-cell" title="${r.user_id}">${v}</span>` },
  { key: "business_name", label: "Merchant", numeric: false },
  { key: "onboard_date", label: "Onboard Date", numeric: false },
  { key: "activation_date", label: "Activation Date", numeric: false },
  { key: "days_to_activation", label: "Days to Activation", numeric: true, noSum: true,
    formatter: (v) => fmtDaysOrHours(v) },
  { key: "activation_amount", label: "Activation ($)", numeric: true,
    formatter: (v) => "$" + (typeof v === "number" ? v.toFixed(2) : v) },
  { key: "activation_type", label: "Type", numeric: false },
  { key: "total_spending", label: "Total Spending ($)", numeric: true,
    formatter: (v) => "$" + (typeof v === "number" ? v.toFixed(2) : v) },
  { key: "total_transactions", label: "Total Txns", numeric: true },
  { key: "is_secure", label: "Secured", numeric: false },
  { key: "invited_count", label: "Invited", numeric: true },
];

function renderActivationUserTable() {
  const headEl = document.getElementById("activation-user-head");
  if (!headEl) return;

  const rows = [];

  for (const [mid, actList] of IDX.activations) {
    const m = IDX.merchants.get(mid);
    if (!m || !S.cities.has(m.city)) continue;

    const onbRows = (IDX.onboardings.get(mid) || []).filter(o => o.date >= S.startDate && o.date <= S.endDate);
    const onbUserIds = new Set(onbRows.map(o => o.user_id));
    const onbDateMap = new Map();
    const onbSecureMap = new Map();
    for (const o of onbRows) {
      onbDateMap.set(o.user_id, o.date);
      onbSecureMap.set(o.user_id, o.is_secure);
    }

    for (const a of actList) {
      if (!onbUserIds.has(a.user_id)) continue;
      if (a.date < S.startDate || a.date > S.endDate) continue;
      if (a.amount === undefined || a.amount === null) continue;

      const userKey = mid + ":" + a.user_id;
      const onbDate = a.onboard_date || onbDateMap.get(a.user_id) || "";
      const daysToAct = onbDate && a.date ? daysBetween(onbDate, a.date) : 0;

      // Txn breakdown
      const tb = IDX.txnBreakdown.get(userKey);
      const totalSpending = tb ? (tb.cn_volume || 0) + (tb.card_volume || 0) + (tb.bt_volume || 0) : 0;
      const totalTxns = tb ? (tb.cn_count || 0) + (tb.card_count || 0) + (tb.bt_count || 0) : 0;

      // Invitations
      const inv = IDX.invitations.get(userKey);
      const invitedCount = inv ? (inv.referral_count || 0) + (inv.cn_onboarding_count || 0) : 0;

      // Secured
      const isSecure = onbSecureMap.get(a.user_id) ? "Yes" : "No";

      rows.push({
        user_id: a.user_id,
        user_id_short: a.user_id.substring(0, 8) + "...",
        business_name: m.business_name || "Unknown",
        onboard_date: onbDate,
        activation_date: a.date,
        days_to_activation: daysToAct,
        activation_amount: Number(a.amount),
        activation_type: a.txn_type === "cash_note" ? "Cash Note" : a.txn_type === "order" ? "Order" : a.txn_type || "",
        total_spending: +totalSpending.toFixed(2),
        total_transactions: totalTxns,
        is_secure: isSecure,
        invited_count: invitedCount,
      });
    }
  }

  if (rows.length === 0) {
    document.getElementById("activation-user-body").innerHTML =
      '<tr><td colspan="11" style="text-align:center;color:var(--text-secondary);padding:2rem;">No activation data for current filters</td></tr>';
    document.getElementById("activation-user-foot").innerHTML = "";
    headEl.innerHTML = "";
    return;
  }

  renderSortableTable(
    "activation-user-head", "activation-user-body", "activation-user-foot",
    ACTIVATION_USER_COLUMNS, rows, S.activationUserSort, recalc
  );
}

// ---------------------------------------------------------------------------
// Render: merchant retention chart
// ---------------------------------------------------------------------------

Chart.register(ChartDataLabels);
let retentionChartInstance = null;

function renderMerchantRetention(rows) {
  const canvas = document.getElementById("retentionChart");
  if (!canvas) return;

  if (retentionChartInstance) { retentionChartInstance.destroy(); retentionChartInstance = null; }

  if (rows.length === 0) {
    canvas.parentElement.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:300px;color:var(--text-secondary);">No merchants for current filters</div>';
    return;
  }

  const onbRegistered = new Map();
  const othRegistered = new Map();
  const cityMerchants = new Set();
  for (const r of rows) {
    cityMerchants.add(r.merchant_id);
    const weekStart = mondayOf(r.onboarding_date);
    if (r.users_onboarded > 0) onbRegistered.set(r.merchant_id, weekStart);
    else othRegistered.set(r.merchant_id, weekStart);
  }

  const weekActivity = new Map();
  for (const r of (RAW.merchant_retention || [])) {
    if (!cityMerchants.has(r.merchant_id)) continue;
    if (!weekActivity.has(r.week_start)) weekActivity.set(r.week_start, new Set());
    weekActivity.get(r.week_start).add(r.merchant_id);
  }

  const weeks = [...weekActivity.keys()].sort().filter(w => w >= "2026-01-05");

  if (weeks.length === 0) {
    canvas.parentElement.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:300px;color:var(--text-secondary);">No retention data available</div>';
    return;
  }

  const labels = [];
  const onbPcts = [];
  const othPcts = [];
  const onbCounts = [];
  const othCounts = [];

  for (const w of weeks) {
    const activeSet = weekActivity.get(w);

    let onbTotal = 0, onbActive = 0;
    for (const [mid, regWeek] of onbRegistered) {
      if (regWeek <= w) {
        onbTotal++;
        if (activeSet.has(mid)) onbActive++;
      }
    }

    let othTotal = 0, othActive = 0;
    for (const [mid, regWeek] of othRegistered) {
      if (regWeek <= w) {
        othTotal++;
        if (activeSet.has(mid)) othActive++;
      }
    }

    labels.push(fmtDate(w));
    onbPcts.push(onbTotal > 0 ? Math.round(onbActive / onbTotal * 100) : 0);
    othPcts.push(othTotal > 0 ? Math.round(othActive / othTotal * 100) : 0);
    onbCounts.push({ active: onbActive, total: onbTotal });
    othCounts.push({ active: othActive, total: othTotal });
  }

  retentionChartInstance = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Onboarding",
          data: onbPcts,
          backgroundColor: "#16a34a",
          borderRadius: 6,
          datalabels: { anchor: "end", align: "top", color: "#16a34a", font: { weight: "bold", size: 10 }, formatter: (v, ctx) => v + "%\n(n=" + onbCounts[ctx.dataIndex].total + ")" }
        },
        {
          label: "Others",
          data: othPcts,
          backgroundColor: "#9ca3af",
          borderRadius: 6,
          datalabels: { anchor: "end", align: "top", color: "#6B6B6B", font: { weight: "bold", size: 10 }, formatter: (v, ctx) => v + "%\n(n=" + othCounts[ctx.dataIndex].total + ")" }
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
        tooltip: {
          backgroundColor: "#1A1A1A",
          callbacks: {
            afterLabel: (ctx) => {
              const counts = ctx.datasetIndex === 0 ? onbCounts[ctx.dataIndex] : othCounts[ctx.dataIndex];
              return counts.active + " / " + counts.total + " merchants";
            }
          }
        }
      },
      scales: {
        y: { beginAtZero: true, max: 110, title: { display: true, text: "Retention %", color: "#6B6B6B" }, grid: { color: "#E8E3DB" } },
        x: { grid: { display: false } }
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

function switchTab(tab) {
  S.tab = tab;
  document.querySelectorAll("#tab-bar button").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  document.querySelectorAll("[data-tab]").forEach(el => {
    if (el.closest("#tab-bar")) return; // skip the buttons themselves
    el.style.display = el.dataset.tab === tab ? "" : "none";
  });
  recalc();
}

// ---------------------------------------------------------------------------
// Render: overview stats
// ---------------------------------------------------------------------------

function renderOverviewStats(rows) {
  const el = document.getElementById("overview-stats");
  if (!el) return;

  const participating = rows.filter(r => r.users_onboarded > 0);
  const totalBase = rows.length;
  const pctParticipating = totalBase > 0 ? parseFloat((participating.length / totalBase * 100).toPrecision(2)) : "0";
  const usersOnboarded = rows.reduce((s, r) => s + r.users_onboarded, 0);
  const avgPerMerchant = participating.length > 0 ? parseFloat((usersOnboarded / participating.length).toPrecision(2)) : "0";
  const medPerMerchant = medianOf(participating.map(r => r.users_onboarded).sort((a, b) => a - b));
  const totalSpent = rows.reduce((s, r) => s + r.earnings, 0);
  const cac = usersOnboarded > 0 ? parseFloat((totalSpent / usersOnboarded).toPrecision(2)) : "0";

  el.innerHTML = [
    { label: "Participating Merchants", value: participating.length, sub: "Onboarded at least 1 user" },
    { label: "% of Total Base", value: pctParticipating + "%", sub: "" },
    { label: "Users Onboarded", value: usersOnboarded, sub: "" },
    { label: "Avg Users / Part. Merchant", value: avgPerMerchant, sub: "" },
    { label: "Median Users / Part. Merchant", value: medPerMerchant, sub: "" },
    { label: "Total $ Spent", value: "$" + Math.round(totalSpent), sub: "" },
    { label: "CAC", value: "$" + cac, sub: "Cost per user onboarded" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");

  // Finding callout
  const findingEl = document.getElementById("overview-finding");
  if (findingEl && participating.length > 0) {
    const activatedTotal = rows.reduce((s, r) => s + r.activated_users, 0);
    const activationRate = usersOnboarded > 0 ? parseFloat((activatedTotal / usersOnboarded * 100).toPrecision(2)) : "0";
    findingEl.innerHTML = `<strong>Key Finding:</strong> ${participating.length} of ${totalBase} merchants (${pctParticipating}%) are participating. ${usersOnboarded} users onboarded at $${cac} CAC. Activation rate: ${activationRate}%.`;
    findingEl.style.display = "";
  } else if (findingEl) {
    findingEl.style.display = "none";
  }
}

// ---------------------------------------------------------------------------
// Render: merchant map
// ---------------------------------------------------------------------------

let merchantMap = null;
let merchantMapMarkers = [];

function renderMerchantMap(rows, resetBounds) {
  const container = document.getElementById("merchant-map-container");
  if (!container) return;

  const withCoords = rows.filter(r => r.latitude && r.longitude);

  if (withCoords.length === 0) {
    if (merchantMap) { merchantMap.remove(); merchantMap = null; }
    merchantMapMarkers = [];
    container.innerHTML = '<div class="map-no-data">No merchant location data available</div>';
    return;
  }

  if (!merchantMap) {
    container.innerHTML = "";
    merchantMap = L.map(container).setView([31.5, 74.3], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 18,
    }).addTo(merchantMap);

    // Legend
    const legend = L.control({ position: "bottomright" });
    legend.onAdd = function () {
      const div = L.DomUtil.create("div", "map-legend");
      div.innerHTML =
        '<i style="background:#16a34a"></i> Participating<br>' +
        '<i style="background:#9ca3af"></i> Inactive';
      return div;
    };
    legend.addTo(merchantMap);
  }

  // Clear old markers
  for (const m of merchantMapMarkers) merchantMap.removeLayer(m);
  merchantMapMarkers = [];

  const bounds = [];
  for (const r of withCoords) {
    const isParticipating = r.users_onboarded > 0;
    const color = isParticipating ? "#16a34a" : "#9ca3af";
    const radius = isParticipating ? 8 : 5;
    const opacity = isParticipating ? 0.8 : 0.3;
    const latlng = [r.latitude, r.longitude];
    bounds.push(latlng);

    const marker = L.circleMarker(latlng, {
      radius: radius,
      color: color,
      fillColor: color,
      fillOpacity: opacity,
      weight: 1,
    });

    const popup = `<strong>${r.business_name || "Unknown"}</strong><br>` +
      `City: ${r.city || "N/A"}<br>` +
      `Users onboarded: ${r.users_onboarded || 0}`;
    marker.bindPopup(popup);
    marker.addTo(merchantMap);
    merchantMapMarkers.push(marker);
  }

  if (resetBounds && bounds.length > 0) {
    merchantMap.fitBounds(bounds, { padding: [30, 30] });
  }

  // Fix tile rendering after tab switch
  setTimeout(() => merchantMap.invalidateSize(), 100);
}

// ---------------------------------------------------------------------------
// Render: onboarding quality (red card — users deepdive)
// ---------------------------------------------------------------------------

function renderOnboardingQuality(allData) {
  const insightEl = document.getElementById("onboarding-quality-insight");
  const tierEl = document.getElementById("onboarding-quality-tier-split");
  if (!insightEl || !tierEl) return;

  const { allUserKeys, onbDateMap, totalOnboarded } = allData;
  const TIER2_DATE = "2026-01-28";

  if (totalOnboarded === 0) {
    insightEl.innerHTML = "No onboarded users found for the current date range and city filter.";
    tierEl.innerHTML = "";
    return;
  }

  let cycledBack = 0;
  let neverReturned = 0;
  let activityOver1 = 0;

  // Tier split counters
  let tier1Total = 0, tier1Cycled = 0, tier1Never = 0, tier1Over1 = 0;
  let tier2Total = 0, tier2Cycled = 0, tier2Never = 0, tier2Over1 = 0;

  for (const key of allUserKeys) {
    const cyclingRow = IDX.cycling.get(key);
    const tbRow = IDX.txnBreakdown.get(key);
    const onbDate = onbDateMap.get(key);
    const isTier1 = onbDate < TIER2_DATE;

    if (isTier1) tier1Total++; else tier2Total++;

    // Cycled back: sent CN to merchant
    if (cyclingRow && cyclingRow.sent_cn_to_merchant === true) {
      cycledBack++;
      if (isTier1) tier1Cycled++; else tier2Cycled++;
    }

    // Never returned: no txn breakdown entry AND no cycling activity
    const hasTxnActivity = !!tbRow;
    const hasCyclingActivity = cyclingRow && cyclingRow.sent_cn_to_merchant === true;
    if (!hasTxnActivity && !hasCyclingActivity) {
      neverReturned++;
      if (isTier1) tier1Never++; else tier2Never++;
    }

    // Activity > $1
    if (tbRow) {
      const total = (tbRow.cn_volume || 0) + (tbRow.card_volume || 0) + (tbRow.bt_volume || 0);
      if (total > 1.0) {
        activityOver1++;
        if (isTier1) tier1Over1++; else tier2Over1++;
      }
    }
  }

  const pct = (n, d) => d > 0 ? Math.round(n / d * 100) : 0;

  insightEl.innerHTML = `<strong>Onboarding Quality:</strong> ${cycledBack} of ${totalOnboarded} users (${pct(cycledBack, totalOnboarded)}%) cycled cash back to their merchant. ${neverReturned} (${pct(neverReturned, totalOnboarded)}%) never returned at all. Only ${activityOver1} (${pct(activityOver1, totalOnboarded)}%) had activity &gt; $1.`;

  // Tier split table
  tierEl.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:0.82rem;">
      <thead>
        <tr>
          <th style="text-align:left;">Period</th>
          <th>Onboarded</th>
          <th>Cycled Back</th>
          <th>%</th>
          <th>Never Returned</th>
          <th>%</th>
          <th>Activity > $1</th>
          <th>%</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Tier 1</strong> (pre Jan 28)</td>
          <td style="text-align:center;">${tier1Total}</td>
          <td style="text-align:center;">${tier1Cycled}</td>
          <td style="text-align:center;">${pct(tier1Cycled, tier1Total)}%</td>
          <td style="text-align:center;">${tier1Never}</td>
          <td style="text-align:center;">${pct(tier1Never, tier1Total)}%</td>
          <td style="text-align:center;">${tier1Over1}</td>
          <td style="text-align:center;">${pct(tier1Over1, tier1Total)}%</td>
        </tr>
        <tr>
          <td><strong>Tier 2</strong> (Jan 28+)</td>
          <td style="text-align:center;">${tier2Total}</td>
          <td style="text-align:center;">${tier2Cycled}</td>
          <td style="text-align:center;">${pct(tier2Cycled, tier2Total)}%</td>
          <td style="text-align:center;">${tier2Never}</td>
          <td style="text-align:center;">${pct(tier2Never, tier2Total)}%</td>
          <td style="text-align:center;">${tier2Over1}</td>
          <td style="text-align:center;">${pct(tier2Over1, tier2Total)}%</td>
        </tr>
        <tr class="totals-row">
          <td><strong>Total</strong></td>
          <td style="text-align:center;">${totalOnboarded}</td>
          <td style="text-align:center;">${cycledBack}</td>
          <td style="text-align:center;">${pct(cycledBack, totalOnboarded)}%</td>
          <td style="text-align:center;">${neverReturned}</td>
          <td style="text-align:center;">${pct(neverReturned, totalOnboarded)}%</td>
          <td style="text-align:center;">${activityOver1}</td>
          <td style="text-align:center;">${pct(activityOver1, totalOnboarded)}%</td>
        </tr>
      </tbody>
    </table>`;
}

// ---------------------------------------------------------------------------
// Render: fraud signals (merchant deepdive)
// ---------------------------------------------------------------------------

function renderFraudSignals() {
  const insightEl = document.getElementById("fraud-insight");
  const headEl = document.getElementById("fraud-head");
  const bodyEl = document.getElementById("fraud-body");
  if (!insightEl || !headEl || !bodyEl) return;

  const rows = IDX.fraudSummary.filter(r => {
    const m = IDX.merchants.get(r.merchant_id);
    return m && S.cities.has(m.city);
  });

  if (rows.length === 0) {
    insightEl.innerHTML = "No fraud signal data available. Run fraud queries to populate.";
    headEl.innerHTML = "";
    bodyEl.innerHTML = "";
    return;
  }

  const totalMerchants = rows.length;
  const withCycling = rows.filter(r => r.cycled_count > 0).length;
  const withExactMatch = rows.filter(r => r.exact_match_count > 0).length;
  const highBurst = rows.filter(r => r.max_per_hour >= 5).length;

  insightEl.innerHTML = `<strong>Fraud Signals:</strong> ${totalMerchants} merchants with 3+ onboardings. ${withCycling} have cycling activity, ${withExactMatch} have exact amount matches, ${highBurst} have 5+ onboards/hour bursts.`;

  const cols = ["Merchant", "Onboarded", "Cycled", "Exact Matches", "Avg Min to Cycle", "Max/Hour"];
  headEl.innerHTML = cols.map(c => `<th>${c}</th>`).join("");

  bodyEl.innerHTML = rows.map(r => {
    const burstStyle = r.max_per_hour >= 5 ? ' style="color:var(--red);font-weight:600;"' : "";
    return `<tr>
      <td>${r.business_name || "Unknown"}</td>
      <td>${r.total_onboarded}</td>
      <td>${r.cycled_count}</td>
      <td>${r.exact_match_count}</td>
      <td>${r.avg_seconds_to_cycle > 0 ? (r.avg_seconds_to_cycle / 60).toFixed(1) : "-"}</td>
      <td${burstStyle}>${r.max_per_hour}</td>
    </tr>`;
  }).join("");
}

// ---------------------------------------------------------------------------
// Recalc
// ---------------------------------------------------------------------------

function recalc() {
  const rows = buildMerchantData();

  if (S.tab === "overview") {
    renderOverviewStats(rows);
    renderMerchantMap(rows, true);
  } else if (S.tab === "merchant-deepdive") {
    renderOnbSummaryStats(rows);
    renderSortableTable("onb-table-head", "onb-table-body", "onb-table-foot", ONBOARD_COLUMNS, rows.filter(r => r.users_onboarded > 0), S.merchantOnbSort, recalc);
    renderOnboardingComparison(rows);
    renderMerchantRetention(rows);
    renderFraudSignals();
  } else if (S.tab === "users-deepdive") {
    renderUsersOverview(rows);
    const actData = collectActivationData();
    renderActivationEvent(actData);
    renderActivatedPatterns(actData);
    const allData = collectAllOnboardedData();
    renderOnboardingQuality(allData);
    renderAllUsersTransactions(allData);
    renderAllUsersPatterns(allData);
    renderActivationUserTable();
  }
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

document.getElementById("date-range-trigger").addEventListener("click", () => {
  const popup = document.getElementById("date-range-popup");
  if (popup.classList.contains("open")) closeDatePicker();
  else openDatePicker();
});

document.getElementById("cal-prev-month").addEventListener("click", () => {
  CAL.viewMonth--;
  if (CAL.viewMonth < 0) { CAL.viewMonth = 11; CAL.viewYear--; }
  renderCalendar();
});

document.getElementById("cal-next-month").addEventListener("click", () => {
  CAL.viewMonth++;
  if (CAL.viewMonth > 11) { CAL.viewMonth = 0; CAL.viewYear++; }
  renderCalendar();
});

document.querySelector(".date-range-presets").addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  applyPreset(e.target.dataset.preset);
});

document.getElementById("city-select").addEventListener("change", (e) => {
  const val = e.target.value;
  if (val === "__all__") {
    S.cities = new Set(getAllCities());
  } else {
    S.cities = new Set([val]);
  }
  renderCitySelect();
  recalc();
});

document.getElementById("tab-bar").addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  switchTab(e.target.dataset.tab);
});

document.addEventListener("click", (e) => {
  const picker = document.getElementById("date-range-picker");
  if (!picker.contains(e.target)) closeDatePicker();
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

(function init() {
  buildIndexes();
  S.startDate = "2026-01-01";
  S.endDate = yesterday;
  updateDateRangeLabel();
  S.cities = new Set(getAllCities());
  renderCitySelect();
  recalc();
})();
