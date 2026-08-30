import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cpf_life.calculations import escape_dollars

st.set_page_config(page_title="Methodology — CPF LIFE Navigator", page_icon="📋", layout="wide")

st.title("📋 Methodology")

st.markdown(escape_dollars(
    """
## Data flow (shared by both use cases)

Both the Retirement Simulator and the Policy Explainer read from **one file**,
`data/cpf-anchors-2026.json`, which holds every CPF LIFE figure and assumption this app
uses: published payout anchors (6 RA balances × ages 65/70), gender and plan factors,
the escalating-plan rate, the Basic Plan drawdown model's parameters, default life
expectancy, and the retirement sum projection assumptions (see below). Every non-cited
figure in that file carries a dated note explaining the assumption and its source. This
means the app can be recalibrated every year against CPF Board's updated tables by
editing that one JSON file — no code changes needed.

`cpf_life/calculations.py` is the single implementation of the payout math (interpolation,
gender/plan/deferral adjustment, and the Basic Plan decline model) that both use cases call
into, so the numbers a user sees in the simulator and the numbers the Policy Explainer talks
about are guaranteed to agree — they're the same function calls.

### Projecting the retirement sum for a future cohort

CPF Board publishes BRS/FRS/ERS and payout figures for **one cohort at a time** — members
turning 55 in the current year (2026: BRS $110,200 / FRS $220,400 / ERS $440,800). To let a
user younger than 55 plan ahead, this app projects those three sums forward for cohorts
turning 55 up to 2046, compounding at an assumed **3.5%/yr** (this app's own assumption —
not published by CPF) and rounding to the nearest $100, matching CPF's own publishing
convention:

```
projected_sum = round(base_sum × (1.035)^(cohort_year − 2026) / 100) × 100
```

Because the interpolation curve (`payoutAnchors`) is only calibrated in 2026 dollars, a
future cohort's larger nominal balance is first divided by that same growth factor
("normalized" back to 2026-equivalent dollars) before interpolation, and the resulting
payout is multiplied back up by the growth factor afterward. This assumes a future
cohort's whole payout schedule — including the Basic Plan's $60,000 self-funded
threshold — scales up in step with the retirement sums, since CPF hasn't published future
payout tables either. Members turning 55 outside 2026–2046, or already past 55, fall back
to a manually-entered RA balance instead (no projection applied).
"""
))

st.divider()
st.markdown("## Use Case 1 — Retirement Simulator")
st.caption("Interactive payout calculator across Standard, Basic, and Escalating plans.")

FLOWCHART_1 = """
<svg viewBox="0 0 990 260" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;font-family:'IBM Plex Sans',sans-serif;">
  <defs>
    <marker id="arrow1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#4F9C90"/>
    </marker>
  </defs>
  <style>
    .box{fill:#17293B;stroke:#C7A24A;stroke-width:1.5;rx:6;}
    .lbl{fill:#E9E7DE;font-size:12.5px;text-anchor:middle;}
    .arrow{stroke:#4F9C90;stroke-width:2;marker-end:url(#arrow1);fill:none;}
  </style>

  <rect class="box" x="10" y="150" width="160" height="70"/>
  <text class="lbl" x="90" y="176">User inputs</text>
  <text class="lbl" x="90" y="194" font-size="10.5" fill="#8FA0AE">Age, RS tier, Gender,</text>
  <text class="lbl" x="90" y="208" font-size="10.5" fill="#8FA0AE">Plan, Start Age</text>

  <rect class="box" x="200" y="150" width="160" height="70"/>
  <text class="lbl" x="280" y="174">Project retirement</text>
  <text class="lbl" x="280" y="190">sum for cohort year</text>
  <text class="lbl" x="280" y="206" font-size="10.5" fill="#8FA0AE">age + tier -&gt; balance</text>

  <rect class="box" x="390" y="20" width="160" height="70"/>
  <text class="lbl" x="470" y="50">data/cpf-anchors-</text>
  <text class="lbl" x="470" y="66">2026.json</text>
  <text class="lbl" x="470" y="82" font-size="10.5" fill="#8FA0AE">payout anchors + factors</text>

  <rect class="box" x="390" y="150" width="160" height="70"/>
  <text class="lbl" x="470" y="170">Normalize to base year,</text>
  <text class="lbl" x="470" y="186">interpolate payout &amp;</text>
  <text class="lbl" x="470" y="202" font-size="10.5" fill="#8FA0AE">apply gender/plan/deferral</text>

  <rect class="box" x="580" y="150" width="160" height="70"/>
  <text class="lbl" x="660" y="180">Build payout schedule</text>
  <text class="lbl" x="660" y="196" font-size="10.5" fill="#8FA0AE">flat / escalating / declining</text>

  <rect class="box" x="800" y="150" width="180" height="70"/>
  <text class="lbl" x="890" y="174">Render outputs</text>
  <text class="lbl" x="890" y="190" font-size="10.5" fill="#8FA0AE">metrics, payout-by-age,</text>
  <text class="lbl" x="890" y="204" font-size="10.5" fill="#8FA0AE">3-plan comparison chart</text>

  <path class="arrow" d="M170,185 L200,185"/>
  <path class="arrow" d="M360,185 L390,185"/>
  <path class="arrow" d="M470,90 L470,150"/>
  <path class="arrow" d="M550,185 L580,185"/>
  <path class="arrow" d="M740,185 L800,185"/>
</svg>
"""
components.html(FLOWCHART_1, height=280)

st.divider()
st.markdown("## Use Case 2 — Policy Explainer")
st.caption("LLM-powered Q&A grounded in the same data as the simulator.")

FLOWCHART_2 = """
<svg viewBox="0 0 820 260" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;font-family:'IBM Plex Sans',sans-serif;">
  <defs>
    <marker id="arrow2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#4F9C90"/>
    </marker>
  </defs>
  <style>
    .box{fill:#17293B;stroke:#C7A24A;stroke-width:1.5;rx:6;}
    .lbl{fill:#E9E7DE;font-size:13px;text-anchor:middle;}
    .arrow{stroke:#4F9C90;stroke-width:2;marker-end:url(#arrow2);fill:none;}
  </style>

  <rect class="box" x="20" y="150" width="160" height="70"/>
  <text class="lbl" x="100" y="180">User question</text>
  <text class="lbl" x="100" y="198" font-size="11" fill="#8FA0AE">free text or example</text>

  <rect class="box" x="220" y="20" width="160" height="70"/>
  <text class="lbl" x="300" y="50">Current simulator</text>
  <text class="lbl" x="300" y="66">scenario (optional)</text>
  <text class="lbl" x="300" y="82" font-size="11" fill="#8FA0AE">from session state</text>

  <rect class="box" x="220" y="150" width="160" height="70"/>
  <text class="lbl" x="300" y="174">Build grounded</text>
  <text class="lbl" x="300" y="190">system prompt</text>
  <text class="lbl" x="300" y="206" font-size="11" fill="#8FA0AE">CPF facts + sources</text>

  <rect class="box" x="420" y="150" width="160" height="70"/>
  <text class="lbl" x="500" y="180">OpenAI Chat</text>
  <text class="lbl" x="500" y="196">Completions API</text>
  <text class="lbl" x="500" y="212" font-size="11" fill="#8FA0AE">gpt-4o-mini</text>

  <rect class="box" x="620" y="150" width="160" height="70"/>
  <text class="lbl" x="700" y="174">Display answer</text>
  <text class="lbl" x="700" y="190" font-size="11" fill="#8FA0AE">chat UI +</text>
  <text class="lbl" x="700" y="204" font-size="11" fill="#8FA0AE">disclaimer</text>

  <path class="arrow" d="M180,185 L220,185"/>
  <path class="arrow" d="M300,90 L300,150"/>
  <path class="arrow" d="M380,185 L420,185"/>
  <path class="arrow" d="M580,185 L620,185"/>
</svg>
"""
components.html(FLOWCHART_2, height=280)

st.divider()

st.markdown(
    """
## Implementation details

- **Language / framework:** Python + Streamlit (multi-page app).
- **Calculation engine:** `cpf_life/calculations.py` — pure functions, no UI dependency,
  ported line-for-line from an earlier JS prototype and verified to produce identical
  results, so behavior didn't drift across the rewrite.
- **Charting:** Plotly, styled to match the app's navy/gold/teal palette; the selected
  plan is drawn solid and on top, the other two in muted grey with distinct dash
  patterns (solid / dashed / dotted) so each plan is identifiable by shape as well as
  color regardless of which is selected.
- **LLM integration:** OpenAI's `gpt-4o-mini` via the Chat Completions API. The system
  prompt is built fresh from `data/cpf-anchors-2026.json` on every call (see the
  Explainer's `build_system_prompt()`), so the model can't drift from the app's own
  numbers, and the user's current simulator scenario (if any) is appended as
  additional context for personalization.
- **No personally identifiable information** is collected or required, and nothing is
  persisted between sessions — all inputs (age, retirement sum tier, gender, plan,
  start age) are generic scenario parameters, not identity data, and live only in the
  current browser session's state.
"""
)
