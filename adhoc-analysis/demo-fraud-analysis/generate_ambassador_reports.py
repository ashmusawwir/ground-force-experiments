"""
Ambassador Fraud Report Generator — 2026-03-05
Generates individual HTML reports + master summary for all active ambassadors.

Usage:
    cd adhoc-analysis
    python3 generate_ambassador_reports.py
    python3 generate_ambassador_reports.py --data fraud_data_20260305.json  # use specific cache

Outputs:
    ambassador-fraud-20260305-{phone}.html  (one per ambassador)
    ambassador-fraud-20260305-summary.html  (master overview)

To refresh data (re-run queries via Rube MCP):
    See ambassador_fraud_queries.py for all SQL.
    Save new query results as a JSON cache with keys: qa, qb, qc, qd, qe, qf, qg, qh
"""

import json, os, sys
from collections import defaultdict
from datetime import date as Date

# Unicode constants (avoid backslash-in-f-string-expression issue on Python < 3.12)
EM = '\u2014'  # em dash —
EN = '\u2013'  # en dash –

DATA_FILE = 'fraud_data_20260305.json'
if len(sys.argv) > 2 and sys.argv[1] == '--data':
    DATA_FILE = sys.argv[2]

# ── Ambassador discovery (from discovery query, run 2026-03-05) ──────────────
AMBASSADORS = [
    {'id': '019c70c1-4a67-7858-b4ae-ee3edecd0988', 'phone': '+923018597735',
     'username': 'happy_griffin_1631', 'role_date': '2026-02-20'},
    {'id': '019c22a2-b069-7ca5-8e53-51ff09f6fe8f', 'phone': '+923051078922',
     'username': 'umer2700', 'role_date': '2026-02-03'},
    {'id': '019c9e3b-f2e7-7182-98c2-ec31f16dd780', 'phone': '+923122320011',
     'username': 'stormy_raccoon_4878', 'role_date': '2026-02-27'},
    {'id': '019bfeae-4ab6-77ef-8fe5-7fb91c7755ce', 'phone': '+923132697794',
     'username': 'user_1ef1d1ea', 'role_date': '2026-01-28'},
    {'id': '019c8ed4-73da-7d10-8723-8dbf57eac2bc', 'phone': '+923412900060',
     'username': 'mighty_robin_3902', 'role_date': '2026-02-24'},
    {'id': '019c8ee0-c02c-75a0-ac4c-cf707f020d19', 'phone': '+923458781746',
     'username': 'ilyas_khan', 'role_date': '2026-02-24'},
    {'id': '019c22a1-07a6-7c67-889e-5c655fe8ae11', 'phone': None,
     'username': 'owaisferoz1', 'role_date': '2026-02-03'},
]

TRUSTED_SENDERS = {'Qasim Fazal Lashkarwala', 'Turab Abbas'}
REPORT_DATE = '2026-03-05'
PERIOD_START = Date.fromisoformat('2026-02-26')


# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_date(s):
    if not s: return '—'
    try:
        return Date.fromisoformat(s[:10]).strftime('%b %-d, %Y')
    except Exception:
        return s[:10]


def phone_slug(phone):
    if not phone: return None
    return phone.replace('+', '').replace(' ', '')


# ── CSS (shared across all files) ────────────────────────────────────────────
CSS = """<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --zar-gold:#B8992E;--zar-gold-light:#CBAF4A;--zar-gold-dark:#9A7E24;
    --bg:#F5F0E8;--card:#FFFFFF;--border:#E8E3DB;--text:#1A1A1A;--muted:#6B6B6B;
    --green:#16a34a;--green-bg:rgba(22,163,74,0.08);
    --amber:#d97706;--amber-bg:rgba(217,119,6,0.07);
    --red:#dc2626;--red-bg:rgba(220,38,38,0.08);
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--text);padding:32px 20px;line-height:1.5;display:flex;flex-direction:column;align-items:center}
  .page{width:100%;max-width:860px}
  .header{text-align:center;margin-bottom:28px}
  .header h1{font-family:'DM Sans',sans-serif;font-size:1.75rem;font-weight:700;margin-bottom:6px}
  .header p{font-size:0.82rem;color:var(--muted);font-family:monospace;letter-spacing:0.02em}
  .verdict-badge{display:inline-flex;align-items:center;gap:8px;margin-top:14px;padding:8px 20px;border-radius:999px;font-family:'DM Sans',sans-serif;font-size:1rem;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#fff}
  .verdict-green{background:var(--green);box-shadow:0 2px 12px rgba(22,163,74,0.25)}
  .verdict-amber{background:var(--amber);box-shadow:0 2px 12px rgba(217,119,6,0.3)}
  .card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:1.4rem 1.6rem;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.04)}
  .card-title{font-family:'DM Sans',sans-serif;font-size:0.95rem;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}
  .card-title .dot{width:8px;height:8px;border-radius:50%;background:var(--zar-gold);flex-shrink:0}
  .stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
  .stat-box{background:var(--bg);border-radius:12px;padding:14px 12px;text-align:center}
  .stat-value{font-family:'DM Sans',sans-serif;font-size:1.35rem;font-weight:700;color:var(--zar-gold-dark);line-height:1.2;margin-bottom:4px}
  .stat-value.small{font-size:0.95rem}.stat-value.red{color:var(--red)}
  .stat-label{font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.05em;font-weight:600}
  .table-wrap{overflow-x:auto}
  table{width:100%;border-collapse:collapse;font-size:0.82rem}
  th{background:var(--bg);color:var(--muted);font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em;padding:0.55rem 0.75rem;text-align:left;border-bottom:1px solid var(--border)}
  td{padding:0.55rem 0.75rem;text-align:left;border-bottom:1px solid var(--border)}
  tr:last-child td{border-bottom:none}
  tr.sig-clear td:last-child{color:var(--green);font-weight:600}
  tr.sig-watch td{background:var(--amber-bg)}
  tr.sig-watch td:last-child{color:var(--amber);font-weight:600}
  tr.suspect-row td{background:rgba(184,153,46,0.13);font-weight:600}
  tr.suspect-row td:first-child::after{content:" \u2605";color:var(--zar-gold)}
  .rank{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:6px;background:linear-gradient(135deg,var(--zar-gold),var(--zar-gold-light));color:white;font-size:0.7rem;font-weight:700}
  .insight{padding:0.9rem 1.1rem;border-radius:0 12px 12px 0;font-size:0.84rem;line-height:1.6;margin-bottom:0}
  .insight-green{background:var(--green-bg);border-left:3px solid var(--green)}
  .insight-green strong{color:var(--green)}
  .insight-amber{background:var(--amber-bg);border-left:3px solid var(--amber)}
  .insight-amber strong{color:var(--amber)}
  .insight-gold{background:linear-gradient(135deg,rgba(184,153,46,0.08),rgba(184,153,46,0.02));border-left:3px solid var(--zar-gold)}
  .insight-gold strong{color:var(--zar-gold-dark)}
  footer{margin-top:28px;padding-bottom:12px;font-size:0.7rem;color:var(--muted);text-align:center}
  @media(max-width:768px){.stat-grid{grid-template-columns:repeat(2,1fr)}.stat-value{font-size:1.1rem}table{font-size:0.74rem}th,td{padding:0.4rem 0.5rem}.card{padding:1rem 1.1rem}}
  @media print{body{padding:0;background:#fff}.card{box-shadow:none;page-break-inside:avoid}}
</style>"""


# ── Per-ambassador report ─────────────────────────────────────────────────────
def generate_report(amb, qa_idx, qb_idx, qc_rows, qd_idx, qe_idx, qf_idx, qg_idx, qh_idx):
    aid = amb['id']
    phone = amb['phone']
    username = amb['username']
    role_date = amb['role_date']
    phone_str = phone or '(no phone)'

    ov = qa_idx.get(aid, {})
    total_demos = ov.get('total_demos', 0)
    total_usd = ov.get('total_usd', 0)
    first_demo = ov.get('first_demo_date', '')
    last_demo = ov.get('last_demo_date', '')
    max_per_day = ov.get('max_per_day', 0)
    active_days = ov.get('active_days', 0)
    total_recipients = ov.get('total_recipients', 0)
    account_created = ov.get('account_created', '')

    if first_demo and last_demo:
        fd_dt = Date.fromisoformat(first_demo[:10])
        ld_dt = Date.fromisoformat(last_demo[:10])
        window_days = (ld_dt - fd_dt).days + 1
        window_label = f"{fmt_date(first_demo)} \u2013 {fmt_date(last_demo)}"
        window_sub = f"Active Window ({window_days} days)"
    else:
        window_label, window_sub = '\u2014', 'Active Window'

    timeline = sorted(qb_idx.get(aid, []), key=lambda x: x['demo_date'], reverse=True)

    ob_all = qd_idx.get(aid, [])
    ob_by_phone = {}
    for r in ob_all:
        ph = r['phone_number']
        if ph not in ob_by_phone or r['pathway'] == 'PE':
            ob_by_phone[ph] = r
    ob_dedup = sorted(ob_by_phone.values(), key=lambda x: x['onboarded_date'])
    n_onboarded = len(ob_dedup)
    pathways = set(r['pathway'] for r in ob_dedup)
    pathway_label = ' + '.join(sorted(pathways)) if pathways else 'none'

    peer_rank = next((r['rank'] for r in qc_rows if r['id'] == aid), '?')
    n_peers = len(qc_rows)

    self_spend = qf_idx.get(aid, [])
    loop = qg_idx.get(aid, [])
    loop_total = sum(r['amount_usd'] for r in loop)
    incoming = qh_idx.get(aid, [])
    unknown_sources = [r for r in incoming if r['sender_name'].strip() not in TRUSTED_SENDERS
                       and r['sender_name'].strip() != '']
    trusted_sources = [r for r in incoming if r['sender_name'].strip() in TRUSTED_SENDERS]

    watch_signals = []
    if max_per_day >= 5: watch_signals.append('burst')
    if self_spend: watch_signals.append('self_spend')
    if loop_total > 1: watch_signals.append('money_loop')
    if unknown_sources: watch_signals.append('unknown_dcn')

    verdict = 'Elevated Risk' if len(watch_signals) >= 3 else 'Low Fraud Risk'
    verdict_class = 'verdict-amber' if len(watch_signals) >= 3 else 'verdict-green'
    verdict_icon = '\u26a0' if len(watch_signals) >= 3 else '\u2713'

    rec_activity = qe_idx.get(aid, [])[:50]

    parts = [f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ambassador Fraud Investigation \u2014 {phone_str}</title>
{CSS}
</head>
<body>
<div class="page">

  <!-- 1. Header -->
  <div class="header">
    <h1>Ambassador Fraud Investigation</h1>
    <p>{phone_str} &nbsp;&bull;&nbsp; {username} &nbsp;&bull;&nbsp; User <code>{aid}</code> &nbsp;&bull;&nbsp; Investigated {REPORT_DATE}</p>
    <div><span class="verdict-badge {verdict_class}"><span class="checkmark">{verdict_icon}</span> {verdict}</span></div>
  </div>

  <!-- 2. Identity -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Identity</div>
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-value small">{phone_str}</div><div class="stat-label">Phone</div></div>
      <div class="stat-box"><div class="stat-value small">{fmt_date(account_created)}</div><div class="stat-label">Account Created</div></div>
      <div class="stat-box"><div class="stat-value small">{fmt_date(first_demo) if first_demo else EM}</div><div class="stat-label">First Demo</div></div>
      <div class="stat-box"><div class="stat-value small">ambassador</div><div class="stat-label">Role (assigned {fmt_date(role_date)})</div></div>
    </div>
  </div>''']

    sig_rows = [
        ('sig-clear' if max_per_day < 5 else 'sig-watch',
         'Demo volume',
         f'{total_demos} demos \u2014 rank {peer_rank} of {n_peers} peers' + (f' \u2014 max {max_per_day}/day' if max_per_day >= 5 else ''),
         'Clear' if max_per_day < 5 else 'Watch'),
        ('sig-clear' if max_per_day < 5 else 'sig-watch',
         'Burst pattern',
         f'Max {max_per_day}/day, spread across {active_days} different days',
         'Clear' if max_per_day < 5 else 'Watch'),
        ('sig-clear',
         'Peer conversion',
         f'{n_onboarded} of {total_recipients} recipients onboarded as merchants ({pathway_label})',
         'Clear'),
        ('sig-clear',
         'Recipient activity',
         f'{len(set(r["phone_number"] for r in rec_activity))} of {total_recipients} recipients made transactions after demo',
         'Clear'),
        ('sig-watch' if self_spend else 'sig-clear',
         'Card self-spend',
         f'{len(self_spend)} CashExchange/ZCE transactions found as customer' if self_spend else 'Zero CashExchange / ZCE transactions found',
         'Watch' if self_spend else 'Clear'),
        ('sig-watch' if loop else 'sig-clear',
         'Money loop',
         f'{len(loop)} recipient(s) sent back totalling ${loop_total:.2f}' if loop else 'No recipients sent money back to this ambassador',
         'Watch' if loop else 'Clear'),
        ('sig-watch' if unknown_sources else 'sig-clear',
         'Incoming DCNs',
         f'{len(unknown_sources)} non-supervisor source(s) + {len(trusted_sources)} trusted supervisors' if unknown_sources
         else ('From Qasim Fazal &amp; Turab Abbas (trusted supervisors)' if trusted_sources else 'No incoming DCNs found'),
         'Watch' if unknown_sources else 'Clear'),
    ]

    parts.append('''
  <!-- 3. Fraud Signal Summary -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Fraud Signal Summary</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Signal</th><th>Finding</th><th>Verdict</th></tr></thead>
      <tbody>''')
    for cls, sig, finding, v in sig_rows:
        parts.append(f'        <tr class="{cls}"><td>{sig}</td><td>{finding}</td><td>{v}</td></tr>')
    parts.append('      </tbody></table></div>\n  </div>')

    usd_disp = f'${int(total_usd)}' if total_usd == int(total_usd) else f'${total_usd:.1f}'
    max_cls = 'red' if max_per_day >= 5 else ''
    parts.append(f'''
  <!-- 4. Demo Overview -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Demo Overview</div>
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-value">{total_demos}</div><div class="stat-label">Total Demos</div></div>
      <div class="stat-box"><div class="stat-value">{usd_disp}</div><div class="stat-label">Total USD Distributed</div></div>
      <div class="stat-box"><div class="stat-value small">{window_label}</div><div class="stat-label">{window_sub}</div></div>
      <div class="stat-box"><div class="stat-value {max_cls}">{max_per_day}</div><div class="stat-label">Max Demos / Day</div></div>
    </div>
  </div>''')

    parts.append(f'''
  <!-- 5. Merchant Onboardings -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Merchant Onboardings</div>
    <div class="stat-grid" style="grid-template-columns:repeat(2,1fr);max-width:400px;margin-bottom:14px;">
      <div class="stat-box"><div class="stat-value">{n_onboarded} / {total_recipients}</div><div class="stat-label">Recipients Onboarded as Merchants</div></div>
      <div class="stat-box"><div class="stat-value small">{pathway_label if pathway_label != "none" else EM}</div><div class="stat-label">Pathway</div></div>
    </div>''')
    if ob_dedup:
        parts.append('    <div class="table-wrap"><table><thead><tr><th>Recipient Phone</th><th>Pathway</th><th>Onboarded Date</th></tr></thead><tbody>')
        for r in ob_dedup:
            parts.append(f'      <tr><td>{r["phone_number"]}</td><td>{r["pathway"]}</td><td>{fmt_date(r["onboarded_date"])}</td></tr>')
        parts.append('    </tbody></table></div>')
        conv_pct = n_onboarded * 100 // total_recipients if total_recipients else 0
        ic = 'insight-green' if n_onboarded > 0 else 'insight-amber'
        parts.append(f'    <div style="margin-top:12px;"><div class="insight {ic}"><strong>{n_onboarded} of {total_recipients} demo recipients onboarded as merchants</strong> \u2014 {pathway_label} pathway. Conversion rate: {conv_pct}%.</div></div>')
    else:
        parts.append('    <div class="insight insight-amber"><strong>No merchant onboardings</strong> found for this ambassador\'s recipients.</div>')
    parts.append('  </div>')

    parts.append('''
  <!-- 6. Demo Timeline -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Demo Timeline</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Date</th><th>Demos</th></tr></thead>
      <tbody>''')
    for r in timeline:
        parts.append(f'        <tr><td>{fmt_date(r["demo_date"])}</td><td>{r["demo_count"]}</td></tr>')
    parts.append('      </tbody></table></div>\n  </div>')

    parts.append(f'''
  <!-- 7. Peer Comparison -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Peer Comparison \u2014 All {n_peers} Ambassadors by Demo Count</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Rank</th><th>Phone</th><th>Demos</th></tr></thead>
      <tbody>''')
    for r in qc_rows:
        cls = ' class="suspect-row"' if r['id'] == aid else ''
        ph = r['phone_number'] or '(no phone)'
        parts.append(f'        <tr{cls}><td><span class="rank">{r["rank"]}</span></td><td>{ph}</td><td>{r["total_demos"]}</td></tr>')
    parts.append('      </tbody></table></div>\n  </div>')

    parts.append('''
  <!-- 8. Recipient Activity -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Recipient Activity (Post-Demo QA)</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Recipient Phone</th><th>Transaction Type</th><th>Amount</th><th>Direction</th><th>Date</th></tr></thead>
      <tbody>''')
    if rec_activity:
        for r in rec_activity:
            txn_type = r['type'].replace('Transaction::', '')
            parts.append(f'        <tr><td>{r["phone_number"] or EM}</td><td>{txn_type}</td><td>${r["amount_usd"]:.2f}</td><td>{r["direction"]}</td><td>{fmt_date(r["txn_date"])}</td></tr>')
        total_e = len(qe_idx.get(aid, []))
        if total_e > 50:
            parts.append(f'        <tr><td colspan="5" style="text-align:center;color:var(--muted);font-style:italic;">Showing 50 of {total_e} transactions</td></tr>')
    else:
        parts.append('        <tr><td colspan="5" style="color:var(--muted);font-style:italic;">No post-demo transactions found</td></tr>')
    parts.append('      </tbody></table></div>\n  </div>')

    parts.append('''
  <!-- 9. Card Self-Spend -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Card Self-Spend</div>''')
    if self_spend:
        parts.append('    <div class="table-wrap"><table><thead><tr><th>Type</th><th>Amount</th><th>Date</th></tr></thead><tbody>')
        for r in self_spend:
            parts.append(f'      <tr><td>{r["type"].replace("Transaction::","")}</td><td>${r["amount_usd"]:.2f}</td><td>{fmt_date(r["txn_date"])}</td></tr>')
        parts.append('    </tbody></table></div>')
        parts.append('    <div style="margin-top:12px;"><div class="insight insight-amber"><strong>Self-spend detected.</strong> This ambassador has initiated CashExchange or ZCE transactions as a customer. Monitor if volume increases.</div></div>')
    else:
        parts.append('    <div class="insight insight-green"><strong>Zero card-spend transactions found.</strong> No CashExchange or ZCE orders initiated by this ambassador. Self-spend theory disproved.</div>')
    parts.append('  </div>')

    parts.append('''
  <!-- 10. Money Loop -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Money Loop</div>''')
    if loop:
        parts.append('    <div class="table-wrap"><table><thead><tr><th>Recipient</th><th>Sent Back</th><th>Date</th></tr></thead><tbody>')
        for r in loop:
            parts.append(f'      <tr><td>{r["recipient_phone"] or EM}</td><td>${r["amount_usd"]:.2f}</td><td>{fmt_date(r["txn_date"])}</td></tr>')
        parts.append('    </tbody></table></div>')
        parts.append(f'    <div style="margin-top:12px;"><div class="insight insight-amber"><strong>Loop detected \u2014 total ${loop_total:.2f} returned.</strong> {len(loop)} recipient(s) sent funds back to this ambassador. Monitor closely if demo volume increases.</div></div>')
    else:
        parts.append('    <div class="insight insight-green"><strong>No money loop detected.</strong> No recipients have sent funds back to this ambassador.</div>')
    parts.append('  </div>')

    parts.append('''
  <!-- 11. Incoming Demo Budget -->
  <div class="card">
    <div class="card-title"><span class="dot"></span>Incoming Demo Budget (DCN Sources)</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Sender</th><th>Amount</th><th>Transactions</th><th>Note</th></tr></thead>
      <tbody>''')
    if incoming:
        for r in incoming:
            sname = r['sender_name'].strip() or r['sender_phone'] or '(unknown)'
            is_trusted = sname in TRUSTED_SENDERS
            note_color = 'var(--green)' if is_trusted else ('var(--amber)' if r['sender_phone'] else 'var(--muted)')
            note_text = 'Trusted supervisor' if is_trusted else 'Known user'
            parts.append(f'        <tr><td>{sname}</td><td>${r["total_usd"]}</td><td>{r["txn_count"]} \u00d7 $5</td><td style="color:{note_color};">{note_text}</td></tr>')
    else:
        parts.append('        <tr><td colspan="4" style="color:var(--muted);font-style:italic;">No incoming DCNs found</td></tr>')
    parts.append('      </tbody></table></div>')
    if not unknown_sources:
        if incoming:
            parts.append('    <div style="margin-top:12px;"><div class="insight insight-gold"><strong>Budget origin is clean.</strong> All incoming DCNs are from known supervisors. No anomalous source.</div></div>')
    else:
        parts.append(f'    <div style="margin-top:12px;"><div class="insight insight-amber"><strong>Non-supervisor DCN sources detected.</strong> {len(unknown_sources)} sender(s) not identified as trusted supervisors. Verify these sources.</div></div>')
    parts.append('  </div>')

    parts.append(f'''
  <footer>Generated {REPORT_DATE} &nbsp;&bull;&nbsp; ZAR Ground Force Intelligence</footer>
</div>
</body>
</html>''')
    return '\n'.join(parts)


# ── Summary report ────────────────────────────────────────────────────────────
def generate_summary(ambassadors, qa_idx, qb_idx, qc_rows, qd_idx, qf_idx, qg_idx, qh_idx):
    rows = []
    for amb in ambassadors:
        aid = amb['id']
        phone = amb['phone']
        username = amb['username']
        ov = qa_idx.get(aid, {})
        total_demos = ov.get('total_demos', 0)
        total_recipients = ov.get('total_recipients', 0)
        max_per_day = ov.get('max_per_day', 0)

        demos_7d = sum(r['demo_count'] for r in qb_idx.get(aid, [])
                       if Date.fromisoformat(r['demo_date'][:10]) >= PERIOD_START)

        ob_all = qd_idx.get(aid, [])
        ob_by_phone = {}
        for r in ob_all:
            ph = r['phone_number']
            if ph not in ob_by_phone or r['pathway'] == 'PE':
                ob_by_phone[ph] = r
        n_onboarded = len(ob_by_phone)

        loop = qg_idx.get(aid, [])
        loop_total = sum(r['amount_usd'] for r in loop)
        self_spend = qf_idx.get(aid, [])
        incoming = qh_idx.get(aid, [])
        unknown_sources = [r for r in incoming if r['sender_name'].strip() not in TRUSTED_SENDERS
                           and r['sender_name'].strip() != '']

        watch_signals = []
        if max_per_day >= 5: watch_signals.append('Burst')
        if self_spend: watch_signals.append('Self-Spend')
        if loop_total > 1: watch_signals.append('Money Loop')
        if unknown_sources: watch_signals.append('Unknown DCN')

        n_watch = len(watch_signals)
        verdict = 'Elevated Risk' if n_watch >= 3 else 'Low Fraud Risk'
        verdict_color = '#d97706' if n_watch >= 3 else '#16a34a'
        row_bg = 'rgba(217,119,6,0.05)' if n_watch > 0 else 'rgba(22,163,74,0.04)'

        slug = phone_slug(phone) if phone else amb['id'].replace('-', '')
        fname = f"ambassador-fraud-{REPORT_DATE.replace('-','')}-{slug}.html"
        ph_disp = phone or '(no phone)'
        loop_disp = f'${loop_total:.2f}' if loop else '\u2014'
        self_disp = f'{len(self_spend)} txn(s)' if self_spend else '\u2014'
        dcn_total = sum(r['total_usd'] for r in incoming)
        dcn_disp = f'${dcn_total} ({len(incoming)} senders)' if incoming else '\u2014'
        watch_disp = ', '.join(watch_signals) if watch_signals else '\u2014'

        rows.append({'phone': ph_disp, 'username': username, 'demos_7d': demos_7d,
                     'total_demos': total_demos, 'n_onboarded': n_onboarded,
                     'total_recipients': total_recipients, 'loop_disp': loop_disp,
                     'self_disp': self_disp, 'dcn_disp': dcn_disp, 'watch_disp': watch_disp,
                     'n_watch': n_watch, 'verdict': verdict, 'verdict_color': verdict_color,
                     'row_bg': row_bg, 'fname': fname})

    rows.sort(key=lambda x: (-x['n_watch'], -x['total_demos']))

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ambassador Fraud Investigation \u2014 Summary {REPORT_DATE}</title>
{CSS}
<style>
  .summary-table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
  .summary-table th{{background:var(--bg);color:var(--muted);font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em;padding:0.55rem 0.75rem;text-align:left;border-bottom:2px solid var(--border)}}
  .summary-table td{{padding:0.55rem 0.75rem;border-bottom:1px solid var(--border);vertical-align:top}}
  .summary-table tr:last-child td{{border-bottom:none}}
  .verdict-pill{{display:inline-block;padding:3px 10px;border-radius:999px;font-size:0.72rem;font-weight:700;color:#fff;letter-spacing:0.04em;text-transform:uppercase}}
  .watch-count{{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;font-size:0.75rem;font-weight:700}}
  a{{color:var(--zar-gold-dark);text-decoration:none;font-weight:600}}
  a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>Fraud Investigation \u2014 Master Summary</h1>
    <p>{len(ambassadors)} active ambassadors &nbsp;&bull;&nbsp; Period 2026-02-26 to {REPORT_DATE} &nbsp;&bull;&nbsp; Generated {REPORT_DATE}</p>
  </div>
  <div class="card">
    <div class="card-title"><span class="dot"></span>All Ambassadors \u2014 Risk Overview</div>
    <div class="table-wrap">
      <table class="summary-table">
        <thead><tr>
          <th>Ambassador</th><th>Demos (7d / All)</th><th>Merchant Conv.</th>
          <th>Money Loop</th><th>Self-Spend</th><th>Incoming DCNs</th>
          <th>Watch Signals</th><th>Verdict</th><th>Report</th>
        </tr></thead>
        <tbody>
'''
    for r in rows:
        wc_bg = 'var(--amber)' if r['n_watch'] > 0 else 'var(--green)'
        watch_sub = f'<br><span style="font-size:0.72rem;color:var(--amber)">{r["watch_disp"]}</span>' if r['n_watch'] > 0 else ''
        html += f'''          <tr style="background:{r['row_bg']}">
            <td><strong>{r['phone']}</strong><br><span style="color:var(--muted);font-size:0.75rem">{r['username']}</span></td>
            <td>{r['demos_7d']} / {r['total_demos']}</td>
            <td>{r['n_onboarded']} / {r['total_recipients']}</td>
            <td>{r['loop_disp']}</td>
            <td>{r['self_disp']}</td>
            <td>{r['dcn_disp']}</td>
            <td><span class="watch-count" style="background:{wc_bg};color:#fff">{r['n_watch']}</span>{watch_sub}</td>
            <td><span class="verdict-pill" style="background:{r['verdict_color']}">{r['verdict']}</span></td>
            <td><a href="{r['fname']}">View \u2192</a></td>
          </tr>
'''
    html += '        </tbody>\n      </table>\n    </div>\n  </div>\n'

    elevated = [r for r in rows if r['verdict'] == 'Elevated Risk']
    watches = [r for r in rows if r['n_watch'] > 0 and r['verdict'] != 'Elevated Risk']
    clears = [r for r in rows if r['n_watch'] == 0]
    html += '  <div class="card">\n    <div class="card-title"><span class="dot"></span>Key Findings</div>\n    <div style="display:flex;flex-direction:column;gap:10px">\n'
    if elevated:
        html += f'      <div class="insight insight-amber"><strong>{len(elevated)} ambassador(s) show Elevated Risk</strong> (3+ watch signals). Recommend priority review: {", ".join(r["phone"] for r in elevated)}</div>\n'
    if watches:
        html += f'      <div class="insight insight-amber"><strong>{len(watches)} ambassador(s) have watch signals</strong> but remain Low Risk overall. Continue monitoring: {", ".join(r["phone"] for r in watches)}</div>\n'
    html += f'      <div class="insight insight-green"><strong>{len(clears)} ambassador(s) are fully clear</strong> \u2014 no fraud signals detected.</div>\n'
    html += f'    </div>\n  </div>\n\n  <footer>Generated {REPORT_DATE} &nbsp;&bull;&nbsp; ZAR Ground Force Intelligence</footer>\n</div>\n</body>\n</html>'
    return html


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, DATA_FILE)

    print(f"Loading data from {data_path} ...")
    with open(data_path) as f:
        data = json.load(f)

    qa_rows = data['qa']
    qb_rows = data['qb']
    qc_rows = data['qc']
    qd_rows = data['qd']
    qe_rows = data['qe']
    qf_rows = data['qf']
    qg_rows = data['qg']
    qh_rows = data['qh']

    qa_idx = {r['ambassador_id']: r for r in qa_rows}
    qb_idx = defaultdict(list)
    for r in qb_rows: qb_idx[r['ambassador_id']].append(r)
    qd_idx = defaultdict(list)
    for r in qd_rows: qd_idx[r['ambassador_id']].append(r)
    qe_idx = defaultdict(list)
    for r in qe_rows: qe_idx[r['ambassador_id']].append(r)
    qf_idx = defaultdict(list)
    for r in qf_rows: qf_idx[r['ambassador_id']].append(r)
    qg_idx = defaultdict(list)
    for r in qg_rows: qg_idx[r['ambassador_id']].append(r)
    qh_idx = defaultdict(list)
    for r in qh_rows: qh_idx[r['ambassador_id']].append(r)

    out_dir = script_dir
    generated = []

    for amb in AMBASSADORS:
        html = generate_report(amb, qa_idx, qb_idx, qc_rows, qd_idx, qe_idx, qf_idx, qg_idx, qh_idx)
        slug = phone_slug(amb['phone']) if amb['phone'] else amb['id'].replace('-', '')
        fname = f"ambassador-fraud-{REPORT_DATE.replace('-','')}-{slug}.html"
        fpath = os.path.join(out_dir, fname)
        with open(fpath, 'w') as f:
            f.write(html)
        print(f"  {fname}")
        generated.append(fname)

    summary = generate_summary(AMBASSADORS, qa_idx, qb_idx, qc_rows, qd_idx, qf_idx, qg_idx, qh_idx)
    summary_path = os.path.join(out_dir, f'ambassador-fraud-{REPORT_DATE.replace("-","")}-summary.html')
    with open(summary_path, 'w') as f:
        f.write(summary)
    print(f"  ambassador-fraud-{REPORT_DATE.replace('-','')}-summary.html")

    print(f"\nDone. {len(generated) + 1} files written to {out_dir}/")
