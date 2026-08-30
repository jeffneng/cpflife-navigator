import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cpf_life.calculations import (
    compute_for_cohort,
    escape_dollars,
    fmt_money,
    load_assumptions,
    projected_retirement_sum,
    schedule_for_plan_and_cohort,
)

st.set_page_config(page_title="Retirement Simulator — CPF LIFE Navigator", page_icon="📈", layout="wide")

cpf = load_assumptions()
RSP = cpf["retirementSumProjection"]
BASE_YEAR = RSP["baseCohortYear"]
MIN_YEAR = RSP["supportedCohortYears"]["min"]
MAX_YEAR = RSP["supportedCohortYears"]["max"]

PLAN_LABELS = {"standard": "Standard Plan", "basic": "Basic Plan", "escalating": "Escalating Plan"}
PLAN_LINE_STYLE = {
    "standard": {"dash": "solid", "label": "Standard"},
    "basic": {"dash": "dash", "label": "Basic"},
    "escalating": {"dash": "dot", "label": "Escalating"},
}
SELECTED_COLOR = "#4F9C90"
OTHER_COLOR = "#8FA0AE"
LE_COLOR = "#C7A24A"

st.title("📈 CPF LIFE Retirement Simulator")
st.caption("Model your monthly annuity payout, lifetime total, and how it compares across all three CPF LIFE plans.")
st.caption(f"⚠️ Covers members turning age 55 between {MIN_YEAR} and {MAX_YEAR} only — see Methodology for why.")

# ---- session defaults (also read by the Policy Explainer page for context) ----
defaults = {
    "current_age": 45,
    "retirement_sum_tier": "FRS",
    "manual_balance": RSP["baseSums"]["FRS"],
    "gender": "male",
    "plan": "standard",
    "start_age": 65,
    "life_exp_override": 0,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ---- inputs ----
left, right = st.columns([1, 1.4], gap="large")

with left:
    st.subheader("Your inputs")

    current_age = st.number_input(
        "Your current age", min_value=18, max_value=100,
        value=int(st.session_state["current_age"]), step=1,
    )
    st.session_state["current_age"] = current_age

    if current_age > 55:
        st.info("📋 Check your CPF account for your Retirement Account amount at age 55.")
        manual_balance = st.number_input(
            "Your Retirement Account balance at age 55 ($)",
            min_value=0, step=1000, value=int(st.session_state["manual_balance"]),
        )
        st.session_state["manual_balance"] = manual_balance
        balance = manual_balance
        cohort_year = BASE_YEAR
    else:
        turning_55_year = BASE_YEAR + (55 - current_age)
        if turning_55_year > MAX_YEAR:
            st.warning(
                f"This simulator only models members turning age 55 between {MIN_YEAR} and "
                f"{MAX_YEAR}. At your current age, you'd turn 55 in {turning_55_year} — showing "
                f"figures for the {MAX_YEAR} cohort (the latest supported) as an illustrative "
                f"reference only."
            )
            cohort_year = MAX_YEAR
        else:
            cohort_year = turning_55_year
            st.caption(f"You will turn 55 in **{cohort_year}**.")

        tier = st.radio(
            "Which retirement sum do you wish to meet at 55?",
            options=["BRS", "FRS", "ERS"],
            index=["BRS", "FRS", "ERS"].index(st.session_state["retirement_sum_tier"]),
            horizontal=True,
        )
        st.session_state["retirement_sum_tier"] = tier

        sums = {t: projected_retirement_sum(t, cohort_year, cpf) for t in ["BRS", "FRS", "ERS"]}
        balance = sums[tier]
        st.caption(escape_dollars(
            f"Projected **{tier} {fmt_money(balance)}** for the {cohort_year} cohort "
            f"(BRS {fmt_money(sums['BRS'])} · FRS {fmt_money(sums['FRS'])} · ERS {fmt_money(sums['ERS'])}), "
            f"assuming {RSP['annualGrowthRate']*100:.1f}%/yr growth from CPF's published {BASE_YEAR} figures — "
            f"this app's own projection, not a CPF-published number."
        ))

    st.session_state["balance"] = balance
    st.session_state["cohort_year"] = cohort_year

    gender = st.radio("Gender", options=["male", "female"], format_func=str.title,
                       index=["male", "female"].index(st.session_state["gender"]), horizontal=True)
    st.session_state["gender"] = gender
    m, f = cpf["lifeExpectancy"]["male"], cpf["lifeExpectancy"]["female"]
    active = "Male " + str(m) if gender == "male" else "Female " + str(f)
    st.caption(f"Default life expectancy — Male {m} · Female {f}  (using **{active}**)")

    plan = st.radio("Plan", options=["standard", "basic", "escalating"],
                     format_func=lambda p: PLAN_LABELS[p],
                     index=["standard", "basic", "escalating"].index(st.session_state["plan"]),
                     horizontal=True)
    st.session_state["plan"] = plan

    start_age = st.slider("Payout start age", min_value=65, max_value=70, value=int(st.session_state["start_age"]))
    st.session_state["start_age"] = start_age

    with st.expander("Advanced assumptions"):
        le_override = st.slider(
            "Life expectancy override (0 = auto)",
            min_value=0, max_value=100,
            value=int(st.session_state["life_exp_override"]),
            help="Leave at 0 to use CPF's default life expectancy assumption for the selected gender.",
        )
        st.session_state["life_exp_override"] = le_override

# ---- computation ----
result = compute_for_cohort(
    st.session_state["balance"], st.session_state["gender"], st.session_state["plan"],
    st.session_state["start_age"], st.session_state["life_exp_override"] or None, cpf,
    st.session_state["cohort_year"],
)
sched = schedule_for_plan_and_cohort(
    st.session_state["balance"], st.session_state["gender"], st.session_state["start_age"],
    st.session_state["life_exp_override"] or None, st.session_state["plan"], cpf,
    st.session_state["cohort_year"],
)
le = result["le"]
le_row = next((r for r in sched["rows"] if r["age"] == le), sched["rows"][-1])

with right:
    st.subheader("Simulated payout")
    plan_label = PLAN_LABELS[st.session_state["plan"]]
    defer_note = f" · deferred {result['deferYears']} yr{'s' if result['deferYears'] != 1 else ''}" if result["deferYears"] > 0 else ""
    st.markdown(f"## {fmt_money(result['monthly'])} <span style='font-size:16px;color:#8FA0AE'>per month, starting at age {st.session_state['start_age']}</span>", unsafe_allow_html=True)
    st.caption(f"{plan_label} · assumes life expectancy of **{le}**{defer_note}")

    def ledger_html(rows: list[tuple[str, str]]) -> str:
        # Custom key/value rows instead of st.metric — st.metric ellipsizes
        # long labels/values when columns get narrow, which happened here.
        items = "".join(
            f"<div style='display:flex;justify-content:space-between;gap:12px;"
            f"padding:10px 0;border-bottom:1px solid #2A3F52;'>"
            f"<span style='color:#8FA0AE;'>{k}</span>"
            f"<span style='font-family:\"IBM Plex Mono\",monospace;font-weight:600;'>{v}</span>"
            f"</div>"
            for k, v in rows
        )
        return f"<div style='border-top:1px solid #2A3F52;'>{items}</div>"

    st.markdown(ledger_html([
        ("Annual payout", fmt_money(result["monthly"] * 12)),
        ("Premium at payout start", fmt_money(result["premium"])),
        ("Lifetime total, to life expectancy", fmt_money(le_row["cum"])),
    ]), unsafe_allow_html=True)

    st.markdown("##### Monthly payout by age")
    by_age_rows = []
    for age in [65, 70, 75, 85]:
        if age < st.session_state["start_age"]:
            by_age_rows.append((f"At age {age}", f"starts at {st.session_state['start_age']}"))
        else:
            row = next((r for r in sched["rows"] if r["age"] == age), None)
            by_age_rows.append((f"At age {age}", fmt_money(row["monthly"]) + "/mo" if row else "—"))
    st.markdown(ledger_html(by_age_rows), unsafe_allow_html=True)

    # ---- comparison chart: all 3 plans, selected one highlighted ----
    st.markdown("##### Cumulative payout by plan")
    fig = go.Figure()
    all_series = {}
    for p in ["standard", "basic", "escalating"]:
        s = schedule_for_plan_and_cohort(
            st.session_state["balance"], st.session_state["gender"], st.session_state["start_age"],
            st.session_state["life_exp_override"] or None, p, cpf, st.session_state["cohort_year"],
        )
        all_series[p] = s

    # draw non-selected first, selected last so it renders on top
    plan_order = sorted(all_series.keys(), key=lambda p: p == st.session_state["plan"])
    for p in plan_order:
        s = all_series[p]
        selected = p == st.session_state["plan"]
        style = PLAN_LINE_STYLE[p]
        fig.add_trace(go.Scatter(
            x=[r["age"] for r in s["rows"]],
            y=[r["cum"] for r in s["rows"]],
            mode="lines",
            name=style["label"] + (" (selected)" if selected else ""),
            line=dict(color=SELECTED_COLOR if selected else OTHER_COLOR,
                      width=3 if selected else 1.6,
                      dash=style["dash"]),
        ))

    max_age = max(r["age"] for s in all_series.values() for r in s["rows"])
    fig.add_vline(x=le, line_width=1.3, line_dash="dash", line_color=LE_COLOR,
                  annotation_text=f"age {le}", annotation_font_color=LE_COLOR)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=380,
        xaxis_title="Age",
        yaxis_title="Cumulative payout ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(
    "Figures are approximations derived from CPF Board's published 2026 payout anchors "
    "(BRS/FRS/ERS on the Standard Plan), interpolated for other balances and adjusted for "
    "gender, plan, and deferral. For cohorts turning 55 after 2026, the retirement sum and "
    "resulting payout are both this app's own projection (see Methodology), not CPF-published "
    "figures. CPF LIFE payouts are not calculated by public formula — actual amounts depend on "
    "CPF Board's internal mortality tables, prevailing interest rates, and your specific cohort, "
    "and can only be confirmed via your myCPF account."
)
