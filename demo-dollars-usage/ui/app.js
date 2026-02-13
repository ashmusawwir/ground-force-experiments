// ---------------------------------------------------------------------------
// Ambassador display name mapping (DB name/username → real name)
// ---------------------------------------------------------------------------

const AMBASSADOR_DISPLAY_NAMES = {
  "user_1ef1d1ea": "Arslan Ansari",
  "owaisferoz1": "Owais Feroz",
  "Muhammad Zahid": "Muhammad Zahid",
};

// ---------------------------------------------------------------------------
// Indexes (built once from raw data)
// ---------------------------------------------------------------------------

const IDX = {
  recipients: new Map(),    // recipient_id → overview row
  notes: new Map(),         // recipient_id → note distribution row
  activity: new Map(),      // recipient_id → activity row
  ambassadors: [],          // ambassador summary rows
  appOpens: new Map(),      // recipient_id → app opens row
  timing: new Map(),        // recipient_id → timing row
  appOpensDetailed: new Map(), // recipient_id → detailed app opens with timestamps
};

function buildIndexes() {
  IDX.recipients.clear();
  IDX.notes.clear();
  IDX.activity.clear();
  IDX.ambassadors = [];
  IDX.appOpens.clear();
  IDX.timing.clear();
  IDX.appOpensDetailed.clear();

  for (const r of (RAW.recipient_overview || [])) {
    r.ambassador_name = AMBASSADOR_DISPLAY_NAMES[r.ambassador_name] || r.ambassador_name;
    IDX.recipients.set(r.recipient_id, r);
  }
  for (const n of (RAW.note_distribution || [])) {
    IDX.notes.set(n.recipient_id, n);
  }
  for (const a of (RAW.recipient_activity || [])) {
    IDX.activity.set(a.recipient_id, a);
  }
  IDX.ambassadors = (RAW.ambassador_summary || []).map(a => ({
    ...a,
    ambassador_name: AMBASSADOR_DISPLAY_NAMES[a.ambassador_name] || a.ambassador_name,
  }));
  for (const ao of (RAW.app_opens || [])) {
    IDX.appOpens.set(ao.recipient_id || ao.user_id, ao);
  }
  for (const t of (RAW.recipient_timing || [])) {
    IDX.timing.set(t.recipient_id, t);
  }
  for (const d of (RAW.app_opens_detailed || [])) {
    IDX.appOpensDetailed.set(d.recipient_id, d);
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(n, d) { return d > 0 ? Math.round(n / d * 100) : 0; }
function fmtDollar(n) { return "$" + (typeof n === "number" ? n.toFixed(2) : n); }
function fmtCompact(n) {
  if (Math.abs(n) >= 1000) return (n / 1000).toFixed(1) + "k";
  if (n === 0) return "0";
  return n.toFixed(2);
}

function fmtHours(h) {
  if (h == null) return "\u2014";
  if (h < 1) return "<1h";
  if (h <= 48) return Math.round(h) + "h";
  return (h / 24).toFixed(1) + "d";
}

function getNonOnboarded() {
  return [...IDX.recipients.entries()].filter(([_, r]) => !r.is_onboarded);
}

// ---------------------------------------------------------------------------
// "Understands the Product" scoring
//
// Binary: any qualifying action (excluding cycling) = understood.
// Qualifying: CN send to non-ambassador, card spend, bank transfer, ZCE order.
// Excluded: sending $5 back to ambassador (cycling).
// ---------------------------------------------------------------------------

function scoreRecipient(recipientId) {
  const act = IDX.activity.get(recipientId);
  if (!act) return { understood: false, actions: [], cycling: false };

  const actions = [];
  // Cycling = sent back 100% of received value (full round-trip).
  // Partial send-back is just the ambassador demoing how to send.
  const recip = IDX.recipients.get(recipientId);
  const totalReceived = recip ? (recip.total_received || 0) : 0;
  const hasCycling = (act.cn_send_to_amb_count || 0) > 0
    && (act.cn_send_to_amb_volume || 0) >= totalReceived;

  if ((act.cn_send_to_others_count || 0) > 0) actions.push("cn_send");
  if ((act.card_count || 0) > 0) actions.push("card_spend");
  if ((act.bt_count || 0) > 0) actions.push("bank_transfer");
  if ((act.zce_count || 0) > 0) actions.push("zce_order");

  return {
    understood: actions.length > 0,
    actions,
    cycling: hasCycling,
  };
}

// ---------------------------------------------------------------------------
// Card 1: Who received demo dollars? (ALL recipients)
// ---------------------------------------------------------------------------

function renderCard1() {
  const el = document.getElementById("card1-stats");
  if (!el) return;

  const total = IDX.recipients.size;
  const onboarded = [...IDX.recipients.values()].filter(r => r.is_onboarded).length;
  const notOnboarded = total - onboarded;
  const totalGiven = [...IDX.recipients.values()].reduce((s, r) => s + (r.total_received || 0), 0);

  el.innerHTML = [
    { label: "Total Recipients", value: total },
    { label: "Onboarded as Merchant", value: onboarded, sub: pct(onboarded, total) + "% conversion" },
    { label: "Not Onboarded", value: notOnboarded },
    { label: "Total $ Given Out", value: fmtDollar(totalGiven) },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");
}

// ---------------------------------------------------------------------------
// Card 2: How did they get the $5? (ALL recipients)
// ---------------------------------------------------------------------------

function renderCard2() {
  const statsEl = document.getElementById("card2-stats");
  const breakdownEl = document.getElementById("card2-breakdown");
  if (!statsEl) return;

  const notes = [...IDX.notes.values()];
  const total = notes.length;
  const single5 = notes.filter(n => n.pattern === "single_5").length;
  const multiple = notes.filter(n => n.pattern === "multiple_notes").length;
  const other = notes.filter(n => n.pattern === "other").length;
  const avgAmount = total > 0 ? notes.reduce((s, n) => s + (n.total_amount || 0), 0) / total : 0;

  statsEl.innerHTML = [
    { label: "Single $5 Note", value: single5, sub: pct(single5, total) + "% of recipients" },
    { label: "Multiple Notes", value: multiple, sub: pct(multiple, total) + "% of recipients" },
    { label: "Other Amount", value: other, sub: pct(other, total) + "% of recipients" },
    { label: "Avg Amount Received", value: fmtDollar(avgAmount) },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");

  if (breakdownEl && total > 0) {
    const pctSingle = pct(single5, total);
    const pctMultiple = pct(multiple, total);
    const pctOther = pct(other, total);
    breakdownEl.innerHTML = `
      <div style="margin-top:1rem;">
        <div style="display:flex;height:28px;border-radius:8px;overflow:hidden;font-size:0.75rem;font-weight:600;">
          ${pctSingle > 0 ? `<div style="width:${pctSingle}%;background:var(--zar-gold);color:white;display:flex;align-items:center;justify-content:center;">$5 single (${pctSingle}%)</div>` : ""}
          ${pctMultiple > 0 ? `<div style="width:${pctMultiple}%;background:var(--blue);color:white;display:flex;align-items:center;justify-content:center;">Split (${pctMultiple}%)</div>` : ""}
          ${pctOther > 0 ? `<div style="width:${pctOther}%;background:var(--text-secondary);color:white;display:flex;align-items:center;justify-content:center;">Other (${pctOther}%)</div>` : ""}
        </div>
      </div>`;
  }
}

// ---------------------------------------------------------------------------
// Transition block: scope narrows to non-onboarded after Card 2
// ---------------------------------------------------------------------------

function renderTransition() {
  const el = document.getElementById("transition-block");
  if (!el) return;

  const total = IDX.recipients.size;
  const onboarded = [...IDX.recipients.values()].filter(r => r.is_onboarded).length;
  const nonOnboarded = total - onboarded;

  el.innerHTML = `
    <p>Of the <strong>${total}</strong> recipients, <strong>${onboarded}</strong> became merchants &mdash; success.
    Now let's focus on the remaining <strong>${nonOnboarded}</strong> who received the demo but didn't onboard.</p>
    <p class="intro-period">Cards 3&ndash;5 and the verdict below analyze only non-onboarded recipients.</p>`;
}

// ---------------------------------------------------------------------------
// Card 3: Did they open the app? (NON-ONBOARDED only)
// ---------------------------------------------------------------------------

function renderCard3() {
  const el = document.getElementById("card3-content");
  if (!el) return;

  if (IDX.appOpens.size === 0 && IDX.appOpensDetailed.size === 0) {
    el.innerHTML = `<div class="no-data">App open data not available (Amplitude query not run or no data returned)</div>`;
    return;
  }

  const nonOnboarded = getNonOnboarded();
  const total = nonOnboarded.length;
  const nonOnboardedIds = new Set(nonOnboarded.map(([rid]) => rid));
  const hasDetailed = IDX.appOpensDetailed.size > 0;

  // Brand recall definition
  let html = `<div class="inline-definition">
    <strong>What counts as brand recall?</strong> Opening the app 2+ hours after receiving demo dollars. By then, the ambassador has left &mdash; the recipient is returning on their own because they remembered Zar.
  </div>`;

  if (hasDetailed) {
    // Detailed brand recall analysis with time windows
    let brandRecallCount = 0;    // 2h+ opens
    let sameDayReturn = 0;       // 2-24h
    let nextDayReturn = 0;       // 24h+
    let neverReturned = 0;
    let duringVisit = 0;         // 0-2h
    let multiDayRecall = 0;      // 72h+

    const windowCounts = { visit: 0, sameDay: 0, nextDay: 0, multiDay: 0 };

    for (const [rid] of nonOnboarded) {
      const detail = IDX.appOpensDetailed.get(rid);
      if (!detail || !detail.opens || detail.opens.length === 0) {
        neverReturned++;
        continue;
      }

      const opens = detail.opens;
      let hasBrandRecall = false;
      let hasSameDay = false;
      let hasNextDay = false;
      let hasMultiDay = false;
      let hasVisit = false;

      for (const o of opens) {
        const h = o.hours_after_demo;
        if (h < 2) hasVisit = true;
        else if (h < 24) { hasSameDay = true; hasBrandRecall = true; }
        else if (h < 72) { hasNextDay = true; hasBrandRecall = true; }
        else { hasMultiDay = true; hasBrandRecall = true; }
      }

      if (hasVisit) windowCounts.visit++;
      if (hasSameDay) windowCounts.sameDay++;
      if (hasNextDay) windowCounts.nextDay++;
      if (hasMultiDay) windowCounts.multiDay++;

      if (hasBrandRecall) brandRecallCount++;
      if (hasSameDay) sameDayReturn++;
      if (hasNextDay || hasMultiDay) nextDayReturn++;
      if (!hasBrandRecall && !hasVisit) neverReturned++;
      else if (!hasBrandRecall) { /* only during visit, no return */ neverReturned++; }
    }

    html += `<div class="stat-grid">
      <div class="stat-box">
        <div class="stat-label">Brand Recall (2h+ opens)</div>
        <div class="stat-value">${brandRecallCount}</div>
        <div class="stat-sub">${pct(brandRecallCount, total)}% of ${total} non-onboarded</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Same-Day Returns (2\u201324h)</div>
        <div class="stat-value">${sameDayReturn}</div>
        <div class="stat-sub">Came back on their own</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Next-Day+ Returns (24h+)</div>
        <div class="stat-value">${nextDayReturn}</div>
        <div class="stat-sub">Remembered the next day</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Never Returned</div>
        <div class="stat-value">${neverReturned}</div>
        <div class="stat-sub">${pct(neverReturned, total)}% of non-onboarded</div>
      </div>
    </div>`;

    // Distribution bars by time window
    const windows = [
      { label: "During visit (0\u20132h)", count: windowCounts.visit, cls: "fill-cn" },
      { label: "Same-day return (2\u201324h)", count: windowCounts.sameDay, cls: "fill-bt" },
      { label: "Next-day recall (24\u201372h)", count: windowCounts.nextDay, cls: "fill-card" },
      { label: "Multi-day recall (72h+)", count: windowCounts.multiDay, cls: "fill-zce" },
      { label: "Never opened app", count: neverReturned, cls: "" },
    ];
    const maxW = Math.max(...windows.map(w => w.count), 1);

    html += `<div class="signal-bars" style="margin-top:1rem;">${
      windows.map(w => {
        const widthPct = Math.max((w.count / maxW) * 100, w.count > 0 ? 8 : 0);
        const fillStyle = w.cls
          ? `class="signal-bar-fill ${w.cls}"`
          : `class="signal-bar-fill" style="background:var(--text-secondary);"`;
        return `<div class="signal-bar">
          <span class="signal-bar-label recall-window-label">${w.label}</span>
          <div class="signal-bar-track">
            <div ${fillStyle} style="width:${widthPct}%;${!w.cls ? 'background:var(--text-secondary);' : ''}">${w.count} of ${total}</div>
          </div>
        </div>`;
      }).join("")
    }</div>
    <p style="margin-top:0.5rem;font-size:0.75rem;color:var(--text-secondary);font-style:italic;">One recipient may appear in multiple time windows</p>`;

  } else {
    // Fallback: count-only display (no detailed timestamps)
    const withOpens = [...IDX.appOpens.entries()]
      .filter(([rid, ao]) => nonOnboardedIds.has(rid) && (ao.opens || ao.app_opens || 0) > 0)
      .length;

    html += `<div class="stat-grid">
      <div class="stat-box">
        <div class="stat-label">Recipients who Opened App</div>
        <div class="stat-value">${withOpens}</div>
        <div class="stat-sub">${pct(withOpens, total)}% of ${total} non-onboarded</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">Never Opened App</div>
        <div class="stat-value">${total - withOpens}</div>
        <div class="stat-sub">${pct(total - withOpens, total)}% of ${total} non-onboarded</div>
      </div>
    </div>
    <p style="margin-top:0.75rem;font-size:0.8rem;color:var(--text-secondary);font-style:italic;">Detailed timestamp data not available. Showing total app open counts only. Run Amplitude batch fetch for full brand recall analysis.</p>`;
  }

  el.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Card 4: Did they use the $5? (NON-ONBOARDED only)
// ---------------------------------------------------------------------------

function renderCard4() {
  const defEl = document.getElementById("card4-definition");
  const statsEl = document.getElementById("card4-stats");
  const pillsEl = document.getElementById("card4-activity-pills");
  if (!statsEl) return;

  if (defEl) {
    defEl.innerHTML = `<div class="inline-definition">
      <strong>What counts as &ldquo;using&rdquo; the $5?</strong> Any active feature: sending money to someone, card purchase, bank transfer, or currency exchange. Just holding the balance doesn&rsquo;t count. Sending it back to the ambassador (cycling) is tracked separately.
    </div>`;
  }

  const nonOnboarded = getNonOnboarded();
  const total = nonOnboarded.length;

  let anyActivity = 0;
  let cnSendToOthers = 0;
  let cardUsers = 0;
  let btUsers = 0;
  let zceUsers = 0;
  let cyclingOnly = 0;
  let noActivity = 0;
  let totalCycling = 0;
  let securedCount = 0;

  for (const [rid, recip] of nonOnboarded) {
    const score = scoreRecipient(rid);
    const act = IDX.activity.get(rid);
    if (score.understood) {
      anyActivity++;
    } else if (score.cycling && !score.understood) {
      cyclingOnly++;
    } else {
      noActivity++;
    }
    if (recip.is_secured) securedCount++;
    if (act) {
      if ((act.cn_send_to_others_count || 0) > 0) cnSendToOthers++;
      if ((act.card_count || 0) > 0) cardUsers++;
      if ((act.bt_count || 0) > 0) btUsers++;
      if ((act.zce_count || 0) > 0) zceUsers++;
      if ((act.cn_send_to_amb_count || 0) > 0) totalCycling++;
    }
  }

  statsEl.innerHTML = [
    { label: "Used the $5 (Any Feature)", value: anyActivity, sub: pct(anyActivity, total) + "% of " + total + " non-onboarded" },
    { label: "Cycling Only (Sent Back)", value: cyclingOnly, sub: pct(cyclingOnly, total) + "% of non-onboarded" },
    { label: "No Activity", value: noActivity, sub: pct(noActivity, total) + "% of non-onboarded" },
    { label: "Secured Account", value: securedCount, sub: pct(securedCount, total) + "% have email or phone" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");

  if (pillsEl) {
    pillsEl.innerHTML = `
      <div class="activity-pills">
        <span class="pill pill-cn"><span class="pill-count">${cnSendToOthers}</span> Sent Cash Note</span>
        <span class="pill pill-card"><span class="pill-count">${cardUsers}</span> Card Spend</span>
        <span class="pill pill-bt"><span class="pill-count">${btUsers}</span> Bank Transfer</span>
        <span class="pill pill-zce"><span class="pill-count">${zceUsers}</span> ZCE Order</span>
        <span class="pill pill-cycling"><span class="pill-count">${totalCycling}</span> Cycling (excluded)</span>
      </div>`;
  }
}

// ---------------------------------------------------------------------------
// Detail Table: Per-recipient raw data (NON-ONBOARDED only)
// ---------------------------------------------------------------------------

const DETAIL_SORT = { col: 11, asc: true };  // default sort: verdict (Understood first)
const VERDICT_ORDER = { "Understood": 0, "Cycling": 1, "Passive": 2 };
const DETAIL_COLUMNS = [
  { key: "recipient_name", label: "Recipient", numeric: false },
  { key: "ambassador_name", label: "Ambassador", numeric: false },
  { key: "account_created_date", label: "Demo Date", numeric: false },
  { key: "total_received", label: "Received", numeric: true },
  { key: "hours_to_act", label: "Hours to Act", numeric: true },
  { key: "cn_send_to_others", label: "CN to Others", numeric: true },
  { key: "card", label: "Card Spend", numeric: true },
  { key: "bt", label: "Bank Transfer", numeric: true },
  { key: "zce", label: "ZCE", numeric: true },
  { key: "cycling", label: "Cycling", numeric: true },
  { key: "is_secured", label: "Secured", numeric: false },
  { key: "verdict", label: "Verdict", numeric: false },
];

function renderDetailTable() {
  const headEl = document.getElementById("detail-table-head");
  const bodyEl = document.getElementById("detail-table-body");
  if (!headEl || !bodyEl) return;

  const nonOnboarded = getNonOnboarded();
  const rows = nonOnboarded.map(([rid, recip]) => {
    const act = IDX.activity.get(rid) || {};
    const score = scoreRecipient(rid);
    let verdict, verdictClass;
    if (score.understood) {
      verdict = "Understood"; verdictClass = "badge-understood";
    } else if (score.cycling) {
      verdict = "Cycling"; verdictClass = "badge-cycling";
    } else {
      verdict = "Passive"; verdictClass = "badge-passive";
    }
    const timing = IDX.timing.get(rid);
    const hoursToAct = timing && timing.hours_to_first_activity != null
      ? timing.hours_to_first_activity : null;
    return {
      recipient_id: rid,
      recipient_name: recip.recipient_name || rid.substring(0, 8) + "...",
      recipient_phone: recip.recipient_phone || null,
      ambassador_name: recip.ambassador_name || "Unknown",
      account_created_date: recip.account_created_date || "",
      total_received: recip.total_received || 0,
      hours_to_act: hoursToAct,
      cn_send_to_others: act.cn_send_to_others_count || 0,
      cn_send_to_others_vol: act.cn_send_to_others_volume || 0,
      card: act.card_count || 0,
      card_vol: act.card_volume || 0,
      bt: act.bt_count || 0,
      bt_vol: act.bt_volume || 0,
      zce: act.zce_count || 0,
      zce_vol: act.zce_volume || 0,
      cycling: act.cn_send_to_amb_count || 0,
      cycling_vol: act.cn_send_to_amb_volume || 0,
      is_secured: recip.is_secured || false,
      verdict,
      verdictClass,
    };
  });

  // Render header
  headEl.innerHTML = DETAIL_COLUMNS.map((col, i) => {
    const arrow = i === DETAIL_SORT.col ? ` <span class="sort-arrow">${DETAIL_SORT.asc ? "&#9650;" : "&#9660;"}</span>` : "";
    return `<th data-col="${i}">${col.label}${arrow}</th>`;
  }).join("");

  // Sort — custom order for verdict column, nulls last for days_to_act
  const col = DETAIL_COLUMNS[DETAIL_SORT.col];
  const sorted = [...rows].sort((a, b) => {
    if (col.key === "verdict") {
      const av = VERDICT_ORDER[a.verdict] ?? 9, bv = VERDICT_ORDER[b.verdict] ?? 9;
      return DETAIL_SORT.asc ? av - bv : bv - av;
    }
    if (col.key === "is_secured") {
      const av = a.is_secured ? 0 : 1, bv = b.is_secured ? 0 : 1;
      return DETAIL_SORT.asc ? av - bv : bv - av;
    }
    if (col.key === "hours_to_act") {
      const av = a.hours_to_act, bv = b.hours_to_act;
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return DETAIL_SORT.asc ? av - bv : bv - av;
    }
    const av = a[col.key], bv = b[col.key];
    if (typeof av === "string") return DETAIL_SORT.asc ? av.localeCompare(bv) : bv.localeCompare(av);
    return DETAIL_SORT.asc ? av - bv : bv - av;
  });

  bodyEl.innerHTML = sorted.map(r => {
    const fmtCnt = (cnt, vol) => cnt > 0 ? `${cnt} <span style="color:var(--text-secondary);font-size:0.7rem;">(${fmtDollar(vol)})</span>` : "\u2014";
    const phoneLine = r.recipient_phone ? `<div style="font-size:0.65rem;color:var(--text-secondary);">${r.recipient_phone}</div>` : "";
    const securedBadge = r.is_secured
      ? '<span style="color:var(--green);font-weight:600;">&#10003;</span>'
      : '<span style="color:var(--text-secondary);">\u2014</span>';
    const hoursCell = r.hours_to_act != null
      ? `<span style="font-weight:500;">${fmtHours(r.hours_to_act)}</span>`
      : '\u2014';
    return `<tr>
      <td><span title="${r.recipient_id}">${r.recipient_name}</span>${phoneLine}</td>
      <td>${r.ambassador_name}</td>
      <td>${r.account_created_date}</td>
      <td>${fmtDollar(r.total_received)}</td>
      <td>${hoursCell}</td>
      <td>${fmtCnt(r.cn_send_to_others, r.cn_send_to_others_vol)}</td>
      <td>${fmtCnt(r.card, r.card_vol)}</td>
      <td>${fmtCnt(r.bt, r.bt_vol)}</td>
      <td>${fmtCnt(r.zce, r.zce_vol)}</td>
      <td>${fmtCnt(r.cycling, r.cycling_vol)}</td>
      <td style="text-align:center;">${securedBadge}</td>
      <td><span class="${r.verdictClass}">${r.verdict}</span></td>
    </tr>`;
  }).join("");

  // Sort click handler
  headEl.querySelectorAll("th").forEach(th => {
    th.addEventListener("click", () => {
      const ci = parseInt(th.dataset.col);
      if (DETAIL_SORT.col === ci) DETAIL_SORT.asc = !DETAIL_SORT.asc;
      else { DETAIL_SORT.col = ci; DETAIL_SORT.asc = DETAIL_COLUMNS[ci].numeric ? false : true; }
      renderDetailTable();
    });
  });
}

// ---------------------------------------------------------------------------
// CSV download for revisit targets
// ---------------------------------------------------------------------------

function downloadRevisitCSV(targets) {
  const actionLabels = { cn_send: "P2P", card_spend: "Card", bank_transfer: "BT", zce_order: "ZCE" };
  const headers = ["Recipient", "Phone", "Ambassador", "Business Name", "Location", "Demo Date", "Actions", "Total Txns", "Secured"];
  const rows = targets.map(r => [
    r.recipient_name,
    r.recipient_phone || "",
    r.ambassador_name,
    r.business_name || "",
    r.location_lat != null && r.location_lng != null ? `${r.location_lat},${r.location_lng}` : "",
    r.date,
    r.actions.map(a => actionLabels[a] || a).join("; "),
    r.cn_send_to_others_count + r.card_count + r.bt_count + r.zce_count,
    r.is_secured ? "Yes" : "No",
  ]);
  const csvContent = [headers, ...rows]
    .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "revisit_targets.csv";
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Verdict: Who understood the product? (NON-ONBOARDED only)
// ---------------------------------------------------------------------------

function renderVerdict() {
  const statsEl = document.getElementById("verdict-stats");
  const signalsEl = document.getElementById("verdict-signals");
  const headEl = document.getElementById("verdict-table-head");
  const bodyEl = document.getElementById("verdict-table-body");
  if (!statsEl) return;

  const nonOnboarded = getNonOnboarded();
  const total = nonOnboarded.length;
  let understood = 0;
  let notUnderstood = 0;
  const actionCounts = { cn_send: 0, card_spend: 0, bank_transfer: 0, zce_order: 0 };
  const revisitTargets = [];

  for (const [rid, recip] of nonOnboarded) {
    const score = scoreRecipient(rid);
    if (score.understood) {
      understood++;
      for (const a of score.actions) actionCounts[a]++;
      const act = IDX.activity.get(rid) || {};
      revisitTargets.push({
        recipient_id: rid,
        recipient_name: recip.recipient_name || rid.substring(0, 8) + "...",
        recipient_phone: recip.recipient_phone || null,
        ambassador_name: recip.ambassador_name || "Unknown",
        date: recip.account_created_date || "",
        actions: score.actions,
        cn_send_to_others_count: act.cn_send_to_others_count || 0,
        card_count: act.card_count || 0,
        bt_count: act.bt_count || 0,
        zce_count: act.zce_count || 0,
        business_name: recip.business_name || null,
        location_lat: recip.location_lat || null,
        location_lng: recip.location_lng || null,
        is_secured: recip.is_secured || false,
      });
    } else {
      notUnderstood++;
    }
  }

  statsEl.innerHTML = [
    { label: "Understood the Product", value: understood, sub: pct(understood, total) + "% of " + total + " non-onboarded" },
    { label: "Did Not Understand", value: notUnderstood, sub: "Passive or cycling only" },
    { label: "Revisit Targets", value: revisitTargets.length, sub: "Worth a second visit" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");

  // Signal bars
  if (signalsEl && understood > 0) {
    const actionLabels = {
      cn_send: { label: "Sent Cash Note (P2P)", cls: "fill-cn" },
      card_spend: { label: "Card Purchase", cls: "fill-card" },
      bank_transfer: { label: "Bank Transfer", cls: "fill-bt" },
      zce_order: { label: "ZCE Order", cls: "fill-zce" },
    };
    const maxCount = Math.max(...Object.values(actionCounts), 1);

    signalsEl.innerHTML = `<div class="signal-bars">${
      Object.entries(actionCounts).map(([key, count]) => {
        const info = actionLabels[key];
        const widthPct = Math.max((count / maxCount) * 100, count > 0 ? 8 : 0);
        return `<div class="signal-bar">
          <span class="signal-bar-label">${info.label}</span>
          <div class="signal-bar-track">
            <div class="signal-bar-fill ${info.cls}" style="width:${widthPct}%">${count} of ${understood}</div>
          </div>
        </div>`;
      }).join("")
    }</div>
    <p style="margin-top:0.5rem;font-size:0.75rem;color:var(--text-secondary);font-style:italic;">Note: one recipient may appear in multiple categories</p>`;
  }

  // Revisit targets table
  if (headEl && bodyEl) {
    if (revisitTargets.length === 0) {
      headEl.innerHTML = "";
      bodyEl.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-secondary);padding:2rem;">No revisit targets found</td></tr>';
      return;
    }

    // Download CSV button
    const tableWrap = headEl.closest(".table-wrap");
    if (tableWrap) {
      const titleEl = tableWrap.previousElementSibling;
      if (titleEl && titleEl.classList.contains("table-title") && !titleEl.querySelector(".download-btn")) {
        titleEl.style.display = "flex";
        titleEl.style.alignItems = "center";
        titleEl.style.justifyContent = "space-between";
        const btn = document.createElement("button");
        btn.className = "download-btn";
        btn.textContent = "Download CSV";
        btn.addEventListener("click", function() { downloadRevisitCSV(revisitTargets); });
        titleEl.appendChild(btn);
      }
    }

    const cols = ["Recipient", "Ambassador", "Business Name", "Location", "Demo Date", "Actions", "Total Txns", "Secured", "Verdict"];
    headEl.innerHTML = cols.map(c => `<th>${c}</th>`).join("");

    bodyEl.innerHTML = revisitTargets.map(r => {
      const actionBadges = r.actions.map(a => {
        const labels = { cn_send: "P2P", card_spend: "Card", bank_transfer: "BT", zce_order: "ZCE" };
        const classes = { cn_send: "pill-cn", card_spend: "pill-card", bank_transfer: "pill-bt", zce_order: "pill-zce" };
        return `<span class="pill ${classes[a]}" style="padding:0.15rem 0.4rem;font-size:0.7rem;">${labels[a]}</span>`;
      }).join(" ");
      const totalTxns = r.cn_send_to_others_count + r.card_count + r.bt_count + r.zce_count;
      const bizName = r.business_name || "\u2014";
      const locationCell = r.location_lat != null && r.location_lng != null
        ? `<a href="https://maps.google.com/?q=${r.location_lat},${r.location_lng}" target="_blank" style="color:var(--blue);text-decoration:none;font-size:0.75rem;">${r.location_lat.toFixed(4)}, ${r.location_lng.toFixed(4)}</a>`
        : "\u2014";
      const phoneLine = r.recipient_phone ? `<div style="font-size:0.65rem;color:var(--text-secondary);">${r.recipient_phone}</div>` : "";
      const securedBadge = r.is_secured
        ? '<span style="color:var(--green);font-weight:600;">&#10003;</span>'
        : '<span style="color:var(--text-secondary);">\u2014</span>';
      return `<tr>
        <td><span title="${r.recipient_id}">${r.recipient_name}</span>${phoneLine}</td>
        <td>${r.ambassador_name}</td>
        <td>${bizName}</td>
        <td>${locationCell}</td>
        <td>${r.date}</td>
        <td>${actionBadges}</td>
        <td>${totalTxns}</td>
        <td style="text-align:center;">${securedBadge}</td>
        <td><span class="badge-understood">Revisit</span></td>
      </tr>`;
    }).join("");
  }
}

// ---------------------------------------------------------------------------
// Timing Card: When Do They Act?
// ---------------------------------------------------------------------------

function renderTimingCard() {
  const defEl = document.getElementById("timing-definition");
  const statsEl = document.getElementById("timing-stats");
  const distEl = document.getElementById("timing-distribution");
  const recEl = document.getElementById("timing-recommendation");
  if (!statsEl) return;

  // Inline definition
  if (defEl) {
    defEl.innerHTML = `<div class="inline-definition">
      <strong>What&rsquo;s a qualifying action?</strong> Sending a cash note to someone (not the ambassador), making a card purchase, bank transfer, or ZCE order. Receiving money or sending it back to the ambassador doesn&rsquo;t count.
    </div>`;
  }

  // Collect timing data for all recipients who acted
  const allHours = [];
  for (const [rid, t] of IDX.timing) {
    if (t.hours_to_first_activity != null) {
      allHours.push(t.hours_to_first_activity);
    }
  }

  const total = IDX.timing.size;
  const acted = allHours.length;
  const neverActed = total - acted;

  if (acted === 0) {
    statsEl.innerHTML = '<div class="no-data">No timing data available</div>';
    return;
  }

  // Stats in hours
  const sortedHours = [...allHours].sort((a, b) => a - b);
  const medianH = sortedHours[Math.floor(sortedHours.length / 2)];
  const avgH = sortedHours.reduce((s, h) => s + h, 0) / sortedHours.length;
  const within1h = allHours.filter(h => h <= 1).length;
  const within24h = allHours.filter(h => h <= 24).length;

  statsEl.innerHTML = [
    { label: "Median Hours to Act", value: fmtHours(medianH) },
    { label: "Avg Hours to Act", value: fmtHours(avgH) },
    { label: "Acted Within 1 Hour", value: within1h, sub: pct(within1h, acted) + "% of those who acted" },
    { label: "Acted Within 24 Hours", value: within24h, sub: pct(within24h, acted) + "% of those who acted" },
  ].map(c => `<div class="stat-box">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value">${c.value}</div>
    ${c.sub ? `<div class="stat-sub">${c.sub}</div>` : ""}
  </div>`).join("");

  // Distribution buckets in hours
  if (distEl) {
    const buckets = [
      { label: "Under 1 hour", count: allHours.filter(h => h <= 1).length, cls: "fill-cn" },
      { label: "1\u20136 hours", count: allHours.filter(h => h > 1 && h <= 6).length, cls: "fill-bt" },
      { label: "6\u201324 hours", count: allHours.filter(h => h > 6 && h <= 24).length, cls: "fill-card" },
      { label: "24\u201348 hours", count: allHours.filter(h => h > 24 && h <= 48).length, cls: "fill-zce" },
      { label: "48+ hours", count: allHours.filter(h => h > 48).length, cls: "fill-zce" },
      { label: "Never acted", count: neverActed, cls: "" },
    ];
    const maxCount = Math.max(...buckets.map(b => b.count), 1);

    distEl.innerHTML = `<div class="signal-bars" style="margin-top:1rem;">${
      buckets.map(b => {
        const widthPct = Math.max((b.count / maxCount) * 100, b.count > 0 ? 8 : 0);
        const fillStyle = b.cls
          ? `class="signal-bar-fill ${b.cls}"`
          : `class="signal-bar-fill" style="background:var(--text-secondary);"`;
        return `<div class="signal-bar">
          <span class="signal-bar-label">${b.label}</span>
          <div class="signal-bar-track">
            <div ${fillStyle} style="width:${widthPct}%;${!b.cls ? 'background:var(--text-secondary);' : ''}">${b.count} of ${total}</div>
          </div>
        </div>`;
      }).join("")
    }</div>`;
  }

  // Recommendation in hours
  if (recEl && acted > 0) {
    const p80idx = Math.min(Math.ceil(sortedHours.length * 0.8) - 1, sortedHours.length - 1);
    const p95idx = Math.min(Math.ceil(sortedHours.length * 0.95) - 1, sortedHours.length - 1);
    const revisitH = sortedHours[p80idx];
    const giveUpH = Math.max(sortedHours[p95idx], revisitH + 1);

    const giveUpLabel = giveUpH <= 48 ? Math.ceil(giveUpH) + " hours" : (giveUpH / 24).toFixed(0) + " days";

    recEl.innerHTML = `
      <div class="recommendation-box">
        <div class="rec-rule"><strong>Rule:</strong> Revisit <strong>the next day</strong>.</div>
        <div class="rec-detail">${pct(within24h, acted)}% of engaged recipients act within 24 hours.
          If no activity by ${giveUpLabel}, the demo didn&rsquo;t land &mdash; move on.</div>
      </div>`;
  }
}

// ---------------------------------------------------------------------------
// Amount Card: Is $5 the Right Amount?
// ---------------------------------------------------------------------------

function renderAmountCard() {
  const compEl = document.getElementById("amount-comparison");
  const insightEl = document.getElementById("amount-insight");
  if (!compEl) return;

  // Group recipients by demo amount
  const amountBuckets = new Map();
  for (const [rid, recip] of IDX.recipients) {
    const amt = recip.total_received || 0;
    let key;
    if (amt >= 4.99) key = "$5.00";
    else if (amt >= 0.99) key = "$1.00";
    else key = "$0.01";

    if (!amountBuckets.has(key)) amountBuckets.set(key, { total: 0, understood: 0 });
    const bucket = amountBuckets.get(key);
    bucket.total++;
    if (scoreRecipient(rid).understood) bucket.understood++;
  }

  // Sort by amount descending
  const sortedAmounts = [...amountBuckets.entries()].sort((a, b) => {
    const av = parseFloat(a[0].replace("$", "")), bv = parseFloat(b[0].replace("$", ""));
    return bv - av;
  });

  const tableRows = sortedAmounts.map(([amt, data]) => {
    const rate = data.total > 0 ? pct(data.understood, data.total) : 0;
    const sampleLabel = data.total >= 10 ? '<span class="sample-solid">Solid</span>'
      : data.total >= 5 ? '<span class="sample-tiny">Small (n=' + data.total + ')</span>'
      : '<span class="sample-tiny">Tiny (n=' + data.total + ')</span>';
    return `<tr>
      <td style="font-weight:600;">${amt}</td>
      <td>${data.total}</td>
      <td>${data.understood}</td>
      <td style="font-weight:600;">${rate}%</td>
      <td>${sampleLabel}</td>
    </tr>`;
  }).join("");

  compEl.innerHTML = `
    <table class="amount-table">
      <thead><tr>
        <th>Amount</th><th>Recipients</th><th>Understood</th><th>Rate</th><th>Sample Size</th>
      </tr></thead>
      <tbody>${tableRows}</tbody>
    </table>`;

  // Insight
  if (insightEl) {
    const smallSamples = sortedAmounts.filter(([_, d]) => d.total < 5);
    if (smallSamples.length > 0) {
      insightEl.innerHTML = `
        <div class="insight-box">
          <strong>Note on sample sizes:</strong> With only ${smallSamples.map(([a, d]) => d.total + " at " + a).join(" and ")} recipients,
          these numbers are directional. But the pattern is clear: $5 gives enough value for recipients to explore.
          Sub-$1 amounts don't register as "real money" worth engaging with.
        </div>`;
    }
  }
}

// ---------------------------------------------------------------------------
// Ambassador Breakdown table
// ---------------------------------------------------------------------------

const AMB_SORT = { col: 2, asc: false };
const AMB_COLUMNS = [
  { key: "ambassador_name", label: "Ambassador", numeric: false },
  { key: "notes_sent", label: "Notes Sent", numeric: true },
  { key: "unique_recipients", label: "Recipients", numeric: true },
  { key: "total_given", label: "$ Given", numeric: true },
  { key: "onboarded_count", label: "Onboarded", numeric: true },
  { key: "conversion_rate", label: "Conv. %", numeric: true },
  { key: "understood_count", label: "Understood", numeric: true },
];

function renderAmbassadorTable() {
  const headEl = document.getElementById("ambassador-table-head");
  const bodyEl = document.getElementById("ambassador-table-body");
  if (!headEl || !bodyEl) return;

  // Enrich ambassador data with "understood" counts
  const rows = IDX.ambassadors.map(a => {
    let understoodCount = 0;
    for (const [rid, recip] of IDX.recipients) {
      if (recip.ambassador_id === a.ambassador_id) {
        if (scoreRecipient(rid).understood) understoodCount++;
      }
    }
    return { ...a, understood_count: understoodCount };
  });

  if (rows.length === 0) {
    headEl.innerHTML = "";
    bodyEl.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-secondary);padding:2rem;">No ambassador data</td></tr>';
    return;
  }

  // Render header
  headEl.innerHTML = AMB_COLUMNS.map((col, i) => {
    const arrow = i === AMB_SORT.col ? ` <span class="sort-arrow">${AMB_SORT.asc ? "&#9650;" : "&#9660;"}</span>` : "";
    return `<th data-col="${i}">${col.label}${arrow}</th>`;
  }).join("");

  // Sort
  const col = AMB_COLUMNS[AMB_SORT.col];
  const sorted = [...rows].sort((a, b) => {
    const av = a[col.key], bv = b[col.key];
    if (typeof av === "string") return AMB_SORT.asc ? av.localeCompare(bv) : bv.localeCompare(av);
    return AMB_SORT.asc ? av - bv : bv - av;
  });

  bodyEl.innerHTML = sorted.map(r => `<tr>
    <td>${r.ambassador_name}</td>
    <td>${r.notes_sent}</td>
    <td>${r.unique_recipients}</td>
    <td>${fmtDollar(r.total_given)}</td>
    <td>${r.onboarded_count}</td>
    <td>${r.conversion_rate}%</td>
    <td>${r.understood_count}</td>
  </tr>`).join("");

  // Sort click handler
  headEl.querySelectorAll("th").forEach(th => {
    th.addEventListener("click", () => {
      const ci = parseInt(th.dataset.col);
      if (AMB_SORT.col === ci) AMB_SORT.asc = !AMB_SORT.asc;
      else { AMB_SORT.col = ci; AMB_SORT.asc = AMB_COLUMNS[ci].numeric ? false : true; }
      renderAmbassadorTable();
    });
  });
}

// ---------------------------------------------------------------------------
// Executive Summary
// ---------------------------------------------------------------------------

function renderExecutiveSummary() {
  const el = document.getElementById("exec-summary");
  if (!el) return;

  const total = IDX.recipients.size;
  const onboarded = [...IDX.recipients.values()].filter(r => r.is_onboarded).length;
  const nonOnboarded = getNonOnboarded();
  const nonOnboardedTotal = nonOnboarded.length;

  // Count understood
  let understood = 0;
  for (const [rid] of nonOnboarded) {
    if (scoreRecipient(rid).understood) understood++;
  }

  // Brand recall (from detailed data if available)
  const hasDetailed = IDX.appOpensDetailed.size > 0;
  let brandRecallCount = 0;
  if (hasDetailed) {
    const nonOnboardedIds = new Set(nonOnboarded.map(([rid]) => rid));
    for (const [rid, detail] of IDX.appOpensDetailed) {
      if (!nonOnboardedIds.has(rid)) continue;
      if (detail.opens && detail.opens.some(o => o.hours_after_demo >= 2)) brandRecallCount++;
    }
  }

  // Timing stats
  const allHours = [];
  for (const [rid, t] of IDX.timing) {
    if (t.hours_to_first_activity != null) allHours.push(t.hours_to_first_activity);
  }
  const acted = allHours.length;
  const sortedHours = [...allHours].sort((a, b) => a - b);
  const medianH = acted > 0 ? sortedHours[Math.floor(sortedHours.length / 2)] : null;
  const within24h = allHours.filter(h => h <= 24).length;

  // Amount effectiveness
  let fiveDollarRate = 0, subDollarRate = 0;
  const fiveBucket = { total: 0, understood: 0 };
  const subBucket = { total: 0, understood: 0 };
  for (const [rid, recip] of IDX.recipients) {
    const amt = recip.total_received || 0;
    if (amt >= 4.99) {
      fiveBucket.total++;
      if (scoreRecipient(rid).understood) fiveBucket.understood++;
    } else if (amt < 1) {
      subBucket.total++;
      if (scoreRecipient(rid).understood) subBucket.understood++;
    }
  }
  fiveDollarRate = fiveBucket.total > 0 ? pct(fiveBucket.understood, fiveBucket.total) : 0;
  subDollarRate = subBucket.total > 0 ? pct(subBucket.understood, subBucket.total) : 0;

  // Revisit timing
  const p80idx = acted > 0 ? Math.min(Math.ceil(sortedHours.length * 0.8) - 1, sortedHours.length - 1) : 0;
  const p95idx = acted > 0 ? Math.min(Math.ceil(sortedHours.length * 0.95) - 1, sortedHours.length - 1) : 0;
  const revisitH = acted > 0 ? sortedHours[p80idx] : 0;
  const giveUpH = acted > 0 ? Math.max(sortedHours[p95idx], revisitH + 1) : 0;

  const bullets = [];

  bullets.push(`<strong>${understood} of ${nonOnboardedTotal}</strong> non-onboarded demo recipients (${pct(understood, nonOnboardedTotal)}%) used at least one Zar feature beyond receiving money.`);

  if (hasDetailed) {
    bullets.push(`<strong>${pct(brandRecallCount, nonOnboardedTotal)}%</strong> showed brand recall &mdash; they opened the app on their own after the ambassador left (2+ hours later).`);
  }

  if (acted > 0) {
    bullets.push(`<strong>${pct(within24h, acted)}%</strong> of engaged recipients acted within 24 hours. Median time to first action: <strong>${fmtHours(medianH)}</strong>.`);
  }

  if (fiveBucket.total >= 5) {
    bullets.push(`<strong>$5 demos</strong> outperform smaller amounts: ${fiveDollarRate}% engagement rate${subBucket.total >= 2 ? " vs " + subDollarRate + "% for sub-$1" : ""}.`);
  }

  if (acted > 0) {
    const giveUpLabel = giveUpH <= 48 ? Math.ceil(giveUpH) + " hours" : (giveUpH / 24).toFixed(0) + " days";
    bullets.push(`<strong>Recommendation:</strong> Revisit <strong>the next day</strong>. If no activity by ${giveUpLabel}, move on.`);
  }

  el.innerHTML = `<ul class="exec-bullets">${bullets.map(b => `<li class="exec-bullet"><span>${b}</span></li>`).join("")}</ul>`;
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

(function init() {
  buildIndexes();
  renderExecutiveSummary();
  renderCard1();
  renderCard2();
  renderTransition();
  renderCard3();
  renderCard4();
  renderDetailTable();
  renderVerdict();
  renderTimingCard();
  renderAmountCard();
  renderAmbassadorTable();
})();
