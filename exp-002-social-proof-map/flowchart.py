"""Generate the full experiment HTML report — 4-card one-pager."""

import os
from typing import List, Tuple, Optional
from config import FUNNEL_STEPS, EXPERIMENT_NAME, MAP_AMBASSADORS
from funnel import FunnelMetrics, PeriodInfo, FlowchartNodes

CSS = """\
  :root {
    --zar-gold: #B8992E;
    --zar-gold-light: #CBAF4A;
    --zar-gold-dark: #9A7E24;
    --zar-sky-blue: #7BC4E8;
    --background: #F5F0E8;
    --card: #FFFFFF;
    --border: #E8E3DB;
    --text: #1A1A1A;
    --text-secondary: #6B6B6B;
    --success: #16a34a;
    --danger: #dc2626;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--background);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px;
    color: var(--text);
  }
  h1 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 6px;
  }
  .subtitle {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 30px;
    text-align: center;
    max-width: 700px;
  }
  .data-card {
    margin-top: 30px;
    background: var(--card);
    border-radius: 20px;
    padding: 1.5rem 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid var(--border);
    width: 960px;
  }
  .data-card h2 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .data-card h2 .num {
    background: linear-gradient(135deg, var(--zar-gold), var(--zar-gold-light));
    color: white;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 600;
  }
  .data-card .period-info {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-bottom: 16px;
  }
  .data-card table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .data-card th {
    padding: 0.6rem 0.75rem;
    text-align: left;
    color: var(--text-secondary);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid var(--border);
  }
  .data-card th.num-col { text-align: right; }
  .data-card td {
    padding: 0.6rem 0.75rem;
    color: var(--text);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  .data-card td.num-col {
    text-align: right;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
  }
  .data-card tr:last-child td { border-bottom: none; }
  .data-card tr.total-row td {
    font-weight: 700;
    background: rgba(184,153,46,0.08);
    border-bottom: none;
  }
  .data-card tr.total-row td:first-child {
    color: var(--zar-gold-dark);
  }
  .delta-pos { color: var(--success); font-weight: 600; }
  .delta-neg { color: var(--danger); font-weight: 600; }
  .delta-zero { color: var(--text-secondary); }
  .badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 600;
  }
  .badge-success { background: rgba(22,163,74,0.15); color: #16a34a; }
  .badge-warning { background: rgba(184,153,46,0.15); color: var(--zar-gold-dark); }
  .badge-danger  { background: rgba(220,38,38,0.15); color: #dc2626; }

  /* Stat grid */
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  .stat-box {
    background: var(--background);
    padding: 1rem;
    border-radius: 12px;
    text-align: center;
  }
  .stat-value {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--zar-gold-dark);
  }
  .stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
  }

  /* Insight box */
  .insight {
    background: linear-gradient(135deg, rgba(184,153,46,0.08), rgba(184,153,46,0.02));
    border-left: 3px solid var(--zar-gold);
    padding: 1rem;
    margin-top: 1rem;
    font-size: 0.85rem;
    border-radius: 0 12px 12px 0;
  }
  .insight strong { color: var(--zar-gold-dark); }
  .section-heading {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text);
    margin: 1.25rem 0 0.75rem;
  }

  /* Executive summary */
  .exec-summary {
    background: linear-gradient(135deg, rgba(184,153,46,0.06), rgba(184,153,46,0.02));
    border: 1.5px solid var(--zar-gold);
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1rem;
  }
  .exec-summary h3 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: var(--zar-gold-dark);
    margin-bottom: 0.75rem;
  }
  .exec-summary ul {
    padding-left: 1.25rem;
    font-size: 0.85rem;
    line-height: 1.7;
  }
  .exec-summary li { margin-bottom: 0.25rem; }
  .verdict-box {
    margin-top: 1.25rem;
    padding: 1rem 1.25rem;
    border-radius: 12px;
    font-size: 0.9rem;
    font-weight: 600;
  }
  .verdict-positive {
    background: rgba(22,163,74,0.1);
    border: 1.5px solid var(--success);
    color: var(--success);
  }
  .verdict-negative {
    background: rgba(220,38,38,0.1);
    border: 1.5px solid var(--danger);
    color: var(--danger);
  }
  .verdict-neutral {
    background: rgba(184,153,46,0.1);
    border: 1.5px solid var(--zar-gold);
    color: var(--zar-gold-dark);
  }"""


def _sig2(val: float) -> str:
    """Format a number to 2 significant digits."""
    s = f"{val:.2g}"
    return s if 'e' not in s else f"{val:.0f}"


def _conv_rate(count: int, total: int) -> Optional[float]:
    return count / total * 100 if total else None


def _fmt_conv(rate: Optional[float]) -> str:
    return f"{_sig2(rate)}%" if rate is not None else "\u2014"


def _fmt_delta_html(base_rate: Optional[float], expt_rate: Optional[float]) -> str:
    if base_rate is None or expt_rate is None:
        return '<span class="delta-zero">\u2014</span>'
    d = expt_rate - base_rate
    if abs(d) < 0.05:
        return '<span class="delta-zero">0.0</span>'
    sign = "+" if d >= 0 else ""
    cls = "delta-pos" if d > 0 else "delta-neg"
    return f'<span class="{cls}">{sign}{_sig2(d)}</span>'


def _e2e_badge(rate: Optional[float]) -> str:
    if rate is None:
        return ""
    if rate >= 20:
        cls = "badge-success"
    elif rate >= 10:
        cls = "badge-warning"
    else:
        cls = "badge-danger"
    return f' <span class="badge {cls}">{_sig2(rate)}%</span>'


def _delta_badge(base_rate: Optional[float], expt_rate: Optional[float]) -> str:
    """Colored badge showing delta between two rates."""
    if base_rate is None or expt_rate is None:
        return '<span class="badge" style="background:#eee;color:#999;">&mdash;</span>'
    d = expt_rate - base_rate
    sign = "+" if d >= 0 else ""
    if d > 2:
        cls = "badge-success"
    elif d < -2:
        cls = "badge-danger"
    else:
        cls = "badge-warning"
    return f'<span class="badge {cls}">{sign}{_sig2(d)}pp</span>'


# --- Card 1: Map Group vs Control Funnel ---

def _map_ambassador_subtitle() -> str:
    """Build subtitle listing map ambassadors and their start dates."""
    parts = []
    for name, start in sorted(MAP_AMBASSADORS.items(), key=lambda x: x[1]):
        parts.append(f"{name} (from {start.strftime('%b %d')})")
    return ", ".join(parts)


def _build_comparison_card(control_m: FunnelMetrics, treatment_m: FunnelMetrics,
                           period_info: PeriodInfo) -> str:
    ctrl_d, treat_d = control_m.as_dict(), treatment_m.as_dict()
    ctrl_conv, treat_conv = control_m.step_conversions(), treatment_m.step_conversions()

    rows_html = []
    for step in FUNNEL_STEPS:
        c_count = ctrl_d[step]
        t_count = treat_d[step]
        c_conv = _fmt_conv(ctrl_conv[step])
        t_conv = _fmt_conv(treat_conv[step])
        delta = _fmt_delta_html(ctrl_conv[step], treat_conv[step])
        rows_html.append(
            f'      <tr>'
            f'<td>{step}</td>'
            f'<td class="num-col">{c_count}</td>'
            f'<td class="num-col">{c_conv}</td>'
            f'<td class="num-col">{t_count}</td>'
            f'<td class="num-col">{t_conv}</td>'
            f'<td class="num-col">{delta}</td>'
            f'</tr>'
        )

    amb_list = _map_ambassador_subtitle()

    return f"""\
<div class="data-card">
  <h2><span class="num">1</span> Map Group vs Control (No Map)</h2>
  <div class="period-info">
    Window: {period_info.range_str} ({period_info.num_days} day{"s" if period_info.num_days != 1 else ""})
    &nbsp;&middot;&nbsp; Map group: {amb_list}
  </div>
  <table>
    <thead>
      <tr>
        <th>Step</th>
        <th class="num-col">Control #</th>
        <th class="num-col">Ctrl Conv</th>
        <th class="num-col">Map #</th>
        <th class="num-col">Map Conv</th>
        <th class="num-col">&Delta;</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


# --- Card 2/3: Per-Ambassador Breakdown (generic — used for both groups) ---

def _build_ambassador_card(amb_data: List[Tuple[str, FunnelMetrics]],
                           total_m: FunnelMetrics,
                           period_info: PeriodInfo,
                           card_num: int = 2,
                           group_label: str = "Control",
                           subtitle: str = "") -> str:
    rows_html = []
    for name, m in amb_data:
        if m.visits == 0:
            continue
        opener_pct = _fmt_conv(_conv_rate(m.opener_passed, m.visits))
        demo_pct = _fmt_conv(_conv_rate(m.demos, m.opener_passed))
        e2e = _conv_rate(m.onboardings, m.visits)
        e2e_pct = _fmt_conv(e2e)
        rows_html.append(
            f'      <tr>'
            f'<td>{name}</td>'
            f'<td class="num-col">{m.visits}</td>'
            f'<td class="num-col">{opener_pct}</td>'
            f'<td class="num-col">{m.demos}</td>'
            f'<td class="num-col">{demo_pct}</td>'
            f'<td class="num-col">{m.onboardings}</td>'
            f'<td class="num-col">{e2e_pct}{_e2e_badge(e2e)}</td>'
            f'</tr>'
        )

    # Total row
    t_opener = _fmt_conv(_conv_rate(total_m.opener_passed, total_m.visits))
    t_demo = _fmt_conv(_conv_rate(total_m.demos, total_m.opener_passed))
    t_e2e = _conv_rate(total_m.onboardings, total_m.visits)
    t_e2e_pct = _fmt_conv(t_e2e)
    rows_html.append(
        f'      <tr class="total-row">'
        f'<td>TOTAL</td>'
        f'<td class="num-col">{total_m.visits}</td>'
        f'<td class="num-col">{t_opener}</td>'
        f'<td class="num-col">{total_m.demos}</td>'
        f'<td class="num-col">{t_demo}</td>'
        f'<td class="num-col">{total_m.onboardings}</td>'
        f'<td class="num-col">{t_e2e_pct}{_e2e_badge(t_e2e)}</td>'
        f'</tr>'
    )

    sub = subtitle or f"{period_info.range_str} &middot; Shows variance within the {group_label.lower()} group"

    return f"""\
<div class="data-card">
  <h2><span class="num">{card_num}</span> Per-Ambassador Breakdown ({group_label})</h2>
  <div class="period-info">
    {sub}
  </div>
  <table>
    <thead>
      <tr>
        <th>Ambassador</th>
        <th class="num-col">Visits</th>
        <th class="num-col">Opener Conv</th>
        <th class="num-col">Demos</th>
        <th class="num-col">Demo Conv</th>
        <th class="num-col">Onboard</th>
        <th class="num-col">E2E %</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


# --- Card 4: Friction vs Credibility Analysis ---

def _build_friction_card(control_m: FunnelMetrics, treatment_m: FunnelMetrics,
                         control_nodes: FlowchartNodes, treatment_nodes: FlowchartNodes) -> str:
    # Metric 1: Opener pass rate
    c_opener_rate = _conv_rate(control_m.opener_passed, control_m.visits)
    t_opener_rate = _conv_rate(treatment_m.opener_passed, treatment_m.visits)

    # Metric 2: Questions asked rate (among those who passed opener)
    c_q_rate = _conv_rate(control_nodes.asked_questions, control_m.opener_passed) if control_m.opener_passed else None
    t_q_rate = _conv_rate(treatment_nodes.asked_questions, treatment_m.opener_passed) if treatment_m.opener_passed else None

    # Metric 3: Demo -> Onboard rate
    c_demo_onboard = _conv_rate(control_m.onboardings, control_m.demos)
    t_demo_onboard = _conv_rate(treatment_m.onboardings, treatment_m.demos)

    metrics = [
        ("Opener Pass Rate", "Did the map reduce rejections at the door?",
         c_opener_rate, t_opener_rate,
         control_m.opener_passed, control_m.visits,
         treatment_m.opener_passed, treatment_m.visits),
        ("Questions Asked Rate", "Did the map create new conversation friction?",
         c_q_rate, t_q_rate,
         control_nodes.asked_questions, control_m.opener_passed,
         treatment_nodes.asked_questions, treatment_m.opener_passed),
        ("Demo &rarr; Onboard Rate", "Did map-sourced demos convert better?",
         c_demo_onboard, t_demo_onboard,
         control_m.onboardings, control_m.demos,
         treatment_m.onboardings, treatment_m.demos),
    ]

    metric_rows = []
    for label, question, c_rate, t_rate, c_num, c_den, t_num, t_den in metrics:
        c_str = _fmt_conv(c_rate)
        t_str = _fmt_conv(t_rate)
        delta = _delta_badge(c_rate, t_rate)

        # Insight interpretation
        if c_rate is not None and t_rate is not None:
            d = t_rate - c_rate
            if label == "Opener Pass Rate":
                if d > 5:
                    insight = "Map appears to reduce rejections"
                elif d < -5:
                    insight = "Map may increase rejection friction"
                else:
                    insight = "No meaningful difference at opener"
            elif label == "Questions Asked Rate":
                if d > 10:
                    insight = "Map generates more questions (friction risk)"
                elif d < -10:
                    insight = "Map reduces questions (smoother path to demo)"
                else:
                    insight = "Similar question rates"
            else:
                if d > 5:
                    insight = "Map-sourced demos convert better"
                elif d < -5:
                    insight = "Map-sourced demos convert worse"
                else:
                    insight = "Similar conversion after demo"
        else:
            insight = "Insufficient data"

        metric_rows.append(
            f'      <tr>'
            f'<td><strong>{label}</strong><br><span style="font-size:0.75rem;color:var(--text-secondary);">{question}</span></td>'
            f'<td class="num-col">{c_str}<br><span style="font-size:0.7rem;color:var(--text-secondary);">{c_num}/{c_den}</span></td>'
            f'<td class="num-col">{t_str}<br><span style="font-size:0.7rem;color:var(--text-secondary);">{t_num}/{t_den}</span></td>'
            f'<td class="num-col">{delta}</td>'
            f'<td style="font-size:0.8rem;">{insight}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">4</span> Friction vs Credibility Analysis</h2>
  <div class="period-info">
    Three diagnostic sub-metrics: where exactly does the map help (or hurt)?
  </div>
  <table>
    <thead>
      <tr>
        <th>Metric</th>
        <th class="num-col">Control</th>
        <th class="num-col">Map Group</th>
        <th class="num-col">&Delta;</th>
        <th>Interpretation</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(metric_rows)}
    </tbody>
  </table>
</div>"""


# --- Card 5: Executive Summary ---

def _build_executive_card(control_m: FunnelMetrics, treatment_m: FunnelMetrics) -> str:
    c_opener = _conv_rate(control_m.opener_passed, control_m.visits)
    t_opener = _conv_rate(treatment_m.opener_passed, treatment_m.visits)
    c_e2e = control_m.e2e_rate()
    t_e2e = treatment_m.e2e_rate()

    # Determine verdict
    opener_delta = (t_opener - c_opener) if (t_opener is not None and c_opener is not None) else 0
    e2e_delta = (t_e2e - c_e2e) if (t_e2e is not None and c_e2e is not None) else 0

    if opener_delta > 10 and e2e_delta > 5:
        verdict_cls = "verdict-positive"
        verdict_text = "Social proof map shows strong positive signal across multiple ambassadors. Recommend teaching verbal social proof to all ambassadors immediately, and building a merchant map feature in the app."
        confidence = "High"
    elif opener_delta > 5 or e2e_delta > 3:
        verdict_cls = "verdict-positive"
        verdict_text = "Social proof map shows moderate positive signal. Phase 2 expansion (3 ambassadors) will clarify whether this is method-driven or ambassador-driven. Teach verbal social proof as a low-cost interim measure."
        confidence = "Medium"
    elif opener_delta < -5 or e2e_delta < -3:
        verdict_cls = "verdict-negative"
        verdict_text = "Social proof map shows negative signal. The map may add friction without building enough credibility. Consider verbal social proof (\"your neighbor uses ZAR\") as a lighter-weight alternative."
        confidence = "Medium"
    else:
        verdict_cls = "verdict-neutral"
        verdict_text = "Results are inconclusive. Phase 2 data (Afsar + Arslan from Feb 16) will increase sample size. Revisit after 3+ days of Phase 2 data."
        confidence = "Low"

    c_opener_str = _fmt_conv(c_opener)
    t_opener_str = _fmt_conv(t_opener)
    c_e2e_str = _fmt_conv(c_e2e)
    t_e2e_str = _fmt_conv(t_e2e)

    n_map = len(MAP_AMBASSADORS)
    amb_names = ", ".join(sorted(MAP_AMBASSADORS.keys()))

    return f"""\
<div class="data-card">
  <h2><span class="num">5</span> Executive Summary &amp; Recommendations</h2>
  <div class="period-info">
    Data-driven verdict on the social proof map intervention &middot; {n_map} map ambassadors: {amb_names}
  </div>

  <div class="stat-grid">
    <div class="stat-box">
      <div class="stat-value">{t_opener_str}</div>
      <div class="stat-label">Map Group Opener Pass</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{c_opener_str}</div>
      <div class="stat-label">Control Opener Pass</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{_delta_badge(c_opener, t_opener)}</div>
      <div class="stat-label">Opener Delta</div>
    </div>
  </div>

  <div class="exec-summary">
    <h3>Why This Matters</h3>
    <ul>
      <li><strong>54% of rejections are addressable by social proof.</strong> "Not interested in dollars" (43%) and "Doesn't trust" (11%) both stem from the same root: the merchant doesn't believe this is real.</li>
      <li><strong>This tests credibility vs product objection.</strong> If showing nearby merchants increases conversion, the objection was never about the product &mdash; it was about trust.</li>
      <li><strong>Phase 2 expansion:</strong> Afsar and Arslan join Sharoon from Feb 16, testing whether the map effect is <em>method-driven</em> (transfers across ambassadors) or <em>person-driven</em> (Sharoon-specific).</li>
      <li><strong>Clear scaling paths:</strong> verbal social proof (short-term) &rarr; merchant map feature (medium-term) &rarr; self-reinforcing growth loop (long-term).</li>
    </ul>
  </div>

  <div style="margin-top:1.25rem;">
    <div class="section-heading">Outcome</div>
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th class="num-col">Control</th>
          <th class="num-col">Map Group</th>
          <th class="num-col">&Delta;</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Opener Pass Rate</td>
          <td class="num-col">{c_opener_str}</td>
          <td class="num-col">{t_opener_str}</td>
          <td class="num-col">{_delta_badge(c_opener, t_opener)}</td>
        </tr>
        <tr>
          <td>End-to-End Rate</td>
          <td class="num-col">{c_e2e_str}</td>
          <td class="num-col">{t_e2e_str}</td>
          <td class="num-col">{_delta_badge(c_e2e, t_e2e)}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="{verdict_cls} verdict-box">
    Confidence: {confidence} &mdash; {verdict_text}
  </div>
</div>"""


# --- HTML Assembly ---

def generate_html(control_m: FunnelMetrics, treatment_m: FunnelMetrics,
                  period_info: PeriodInfo,
                  control_amb_data: List[Tuple[str, FunnelMetrics]],
                  control_total: FunnelMetrics,
                  treatment_amb_data: List[Tuple[str, FunnelMetrics]],
                  treatment_total: FunnelMetrics,
                  control_nodes: FlowchartNodes,
                  treatment_nodes: FlowchartNodes) -> str:
    days_word = f"{period_info.num_days} day{'s' if period_info.num_days != 1 else ''}"

    card1 = _build_comparison_card(control_m, treatment_m, period_info)
    card2 = _build_ambassador_card(treatment_amb_data, treatment_total, period_info,
                                   card_num=2, group_label="Map Group",
                                   subtitle=_map_ambassador_subtitle())
    card3 = _build_ambassador_card(control_amb_data, control_total, period_info,
                                   card_num=3, group_label="Control")
    card4 = _build_friction_card(control_m, treatment_m, control_nodes, treatment_nodes)
    card5 = _build_executive_card(control_m, treatment_m)

    total_visits = control_m.visits + treatment_m.visits
    n_map = len(MAP_AMBASSADORS)
    amb_names = ", ".join(sorted(MAP_AMBASSADORS.keys()))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{EXPERIMENT_NAME} &mdash; EXP-002</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>

<h1>{EXPERIMENT_NAME} &mdash; EXP-002</h1>
<div class="subtitle">
  Does showing a map of nearby ZAR merchants bypass objections?<br>
  {n_map} map ambassadors ({amb_names}) vs control &middot;
  {total_visits} onboarding visits &middot; {days_word} &middot; {period_info.range_str}
</div>

{card1}

{card2}

{card3}

{card4}

{card5}

<div style="margin-top:20px; font-size:0.75rem; color:var(--text-secondary);">
  Generated from visit form data &middot; {period_info.range_str} &middot; Window: {days_word}
</div>

</body>
</html>
"""


def write_html(control_m: FunnelMetrics, treatment_m: FunnelMetrics,
               period_info: PeriodInfo,
               control_amb_data: List[Tuple[str, FunnelMetrics]],
               control_total: FunnelMetrics,
               treatment_amb_data: List[Tuple[str, FunnelMetrics]],
               treatment_total: FunnelMetrics,
               control_nodes: FlowchartNodes,
               treatment_nodes: FlowchartNodes) -> None:
    html_path = os.path.join(os.path.dirname(__file__), "social_proof_map.html")
    html = generate_html(control_m, treatment_m, period_info,
                         control_amb_data, control_total,
                         treatment_amb_data, treatment_total,
                         control_nodes, treatment_nodes)
    with open(html_path, "w") as f:
        f.write(html)
    import sys
    print(f"  Updated report: {html_path}", file=sys.stderr)
