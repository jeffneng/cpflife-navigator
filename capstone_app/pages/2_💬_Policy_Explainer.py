import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cpf_life.calculations import (
    compute_for_cohort,
    fmt_money,
    load_assumptions,
    project_retirement_readiness,
)

st.set_page_config(page_title="Policy Explainer — CPF LIFE Navigator", page_icon="💬", layout="wide")

cpf = load_assumptions()

st.title("💬 CPF LIFE Policy Explainer")
st.caption("Ask a plain-English question about CPF LIFE. Answers are grounded in the same sourced data used by the simulator — not a generic web search.")


def get_api_key() -> str | None:
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        import os
        return os.environ.get("OPENAI_API_KEY")


def build_system_prompt() -> str:
    """Grounds the LLM in exactly the same facts and sources the simulator
    uses, so its answers stay consistent with the rest of the app (this is
    the 'Consolidate Information' + 'Enhance Understanding' requirement)."""
    anchors_lines = "\n".join(
        f"  - ${a['balance']:,} RA -> ${a['monthlyPayout']:,}/mo at 65, ${a['monthlyPayoutAt70']:,}/mo at 70"
        + (f" ({a['label']})" if a.get("label") else "")
        for a in cpf["payoutAnchors"]
    )
    basic = cpf["basicPlan"]
    return f"""You are a helpful, precise explainer of Singapore's CPF LIFE national annuity
scheme, embedded in an app called "CPF LIFE Navigator". Answer only using the facts below —
do not invent CPF figures or policy details you are not given here. If asked something outside
this scope, say so plainly and suggest the user check their myCPF account or CPF Board directly.

SOURCES: {cpf['source']}

PUBLISHED PAYOUT ANCHORS (male, Standard Plan, from CPF Board):
{anchors_lines}

KEY FACTORS THIS APP APPLIES ON TOP OF THE ANCHORS ABOVE:
- Gender: female payouts are modeled as {(1 - cpf['genderFactor']['female']) * 100:.0f}% lower than
  male for the same balance (CPF states 'roughly 6% to 8% lower'; no official female table is
  published, so this app uses the midpoint as an approximation).
- Plan factor: Basic Plan pays {(1 - cpf['planFactor']['basic']) * 100:.0f}% less than Standard
  initially; Escalating Plan pays {(1 - cpf['planFactor']['escalating']) * 100:.0f}% less than
  Standard initially but grows {cpf['escalatingPlan']['annualEscalationRate'] * 100:.0f}%/year.
- Deferral: delaying payout start from 65 to 70 increases the monthly amount — the exact rate
  is derived per balance from CPF's own age-65 vs age-70 anchor figures above.
- Basic Plan payout DECLINES over time: only ~{basic['premiumFraction']*100:.0f}% of the RA
  balance becomes the CPF LIFE premium; the rest stays in the member's RA, earns ordinary
  interest (plus an extra {basic['extraInterestRate']*100:.0f}% while the RA stays at/above
  ${basic['selfFundedThreshold']:,}) and directly funds the payout until age
  {basic['selfFundedEndAge']}. Once that self-funded RA portion dips below
  ${basic['selfFundedThreshold']:,}, the payout ramps down; from age {basic['selfFundedEndAge']}
  a smaller, stable, lifetime payout is funded from the premium pool. This decline model is
  this app's own approximation of CPF's general description — CPF does not publish the exact
  trajectory.
- Life expectancy assumption: Male {cpf['lifeExpectancy']['male']}, Female {cpf['lifeExpectancy']['female']}.
- Retirement sums (BRS/FRS/ERS) beyond the {cpf['retirementSumProjection']['baseCohortYear']} cohort
  are NOT published by CPF. This app projects them forward at an assumed
  {cpf['retirementSumProjection']['annualGrowthRate']*100:.1f}%/yr from the {cpf['retirementSumProjection']['baseCohortYear']}
  figures (BRS ${cpf['retirementSumProjection']['baseSums']['BRS']:,}, FRS ${cpf['retirementSumProjection']['baseSums']['FRS']:,},
  ERS ${cpf['retirementSumProjection']['baseSums']['ERS']:,}), rounded to the nearest $100 — this app's own
  assumption, not a CPF projection. This app only supports members turning 55 between
  {cpf['retirementSumProjection']['supportedCohortYears']['min']} and {cpf['retirementSumProjection']['supportedCohortYears']['max']}.

TOOL AVAILABLE — project_retirement_readiness: if the user gives you specific numbers (a
birthdate, current OA/SA balances, monthly contributions, and which retirement sum they're
targeting) and asks whether they'll meet a retirement sum by 55 or what the shortfall would
be, CALL THIS TOOL rather than attempting the arithmetic yourself or refusing — you cannot
reliably do multi-month compounding by hand, but this tool does it exactly. If the user
states their own OA/SA interest rates, pass those; otherwise the tool defaults to CPF's
standard 2.5% (OA) / 4% (SA). If they mention wanting to retain an amount in OA rather than
transfer it all to the Retirement Account, pass that as oa_retain_amount. If any required
input (birthdate, current OA, current SA, monthly OA contribution, monthly SA contribution,
target tier) is missing, ask the user for it rather than guessing or refusing outright.

IMPORTANT CAVEATS TO CONVEY WHEN RELEVANT: CPF LIFE payouts are not calculated by a published
public formula. Real payouts depend on CPF Board's internal mortality tables and prevailing
interest rates, and can only be confirmed via a member's own myCPF account. The readiness tool
above is this app's own simplified projection (monthly compounding of the rates given, no
CPF extra-interest tiers unless folded into those rates) — not an official CPF calculation.
You are not a licensed financial advisor — do not give personalized investment or financial
advice beyond reporting the tool's numbers; explain mechanics and let the user draw their own
conclusions.

Keep answers concise, plain-English, and specific. Use numbers from the data above where they
help. If the user's current simulator scenario is provided below, use it to personalize your
explanation."""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "project_retirement_readiness",
            "description": (
                "Projects a member's CPF Ordinary Account (OA) and Special Account (SA) "
                "balances forward month by month from today to their 55th birthday given "
                "monthly contributions and annual interest rates, then checks whether the "
                "combined OA+SA (SA transferred first, then OA) can form the chosen "
                "retirement sum (BRS/FRS/ERS) for their cohort — respecting an optional "
                "amount the member wants to retain in OA rather than transfer to the "
                "Retirement Account. Returns the projected balances, amount used from each "
                "account, the resulting Retirement Account total, and any shortfall."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "birthdate": {"type": "string", "description": "ISO date, YYYY-MM-DD"},
                    "current_oa": {"type": "number", "description": "Current Ordinary Account balance"},
                    "current_sa": {"type": "number", "description": "Current Special Account balance"},
                    "monthly_oa_contribution": {"type": "number"},
                    "monthly_sa_contribution": {"type": "number"},
                    "target_tier": {"type": "string", "enum": ["BRS", "FRS", "ERS"]},
                    "oa_annual_rate": {"type": "number", "description": "Defaults to 0.025 if the user doesn't state one"},
                    "sa_annual_rate": {"type": "number", "description": "Defaults to 0.04 if the user doesn't state one"},
                    "oa_retain_amount": {"type": "number", "description": "Amount to keep in OA instead of transferring to RA; defaults to 0"},
                },
                "required": [
                    "birthdate", "current_oa", "current_sa",
                    "monthly_oa_contribution", "monthly_sa_contribution", "target_tier",
                ],
            },
        },
    }
]


def call_tool(name: str, arguments: dict) -> dict:
    if name == "project_retirement_readiness":
        kwargs = dict(arguments)
        kwargs.setdefault("oa_annual_rate", 0.025)
        kwargs.setdefault("sa_annual_rate", 0.04)
        kwargs.setdefault("oa_retain_amount", 0.0)
        kwargs["cpf"] = cpf
        return project_retirement_readiness(**kwargs)
    return {"error": f"Unknown tool: {name}"}


def build_scenario_context() -> str | None:
    """Pull the user's current scenario from the Retirement Simulator page's
    session state, if they've visited it, so answers can be personalized —
    e.g. 'why is *my* Basic Plan payout dropping?' """
    keys = ["balance", "gender", "plan", "start_age", "life_exp_override", "cohort_year", "current_age"]
    if not all(k in st.session_state for k in keys):
        return None
    result = compute_for_cohort(
        st.session_state["balance"], st.session_state["gender"], st.session_state["plan"],
        st.session_state["start_age"], st.session_state["life_exp_override"] or None, cpf,
        st.session_state["cohort_year"],
    )
    cohort_note = (
        f"turning 55 in {st.session_state['cohort_year']}, aiming for the "
        f"{st.session_state.get('retirement_sum_tier', '?')}"
        if st.session_state["current_age"] <= 55
        else "already past 55 (balance entered manually)"
    )
    return (
        f"The user's current Retirement Simulator scenario: RA balance "
        f"{fmt_money(st.session_state['balance'])} ({cohort_note}), {st.session_state['gender'].title()}, "
        f"{st.session_state['plan'].title()} Plan, payout starting at age "
        f"{st.session_state['start_age']}. This computes to an estimated starting monthly "
        f"payout of {fmt_money(result['monthly'])}, assuming life expectancy "
        f"{result['le']}."
    )


api_key = get_api_key()

scenario_ctx = build_scenario_context()
if scenario_ctx:
    st.info("📎 Using your current Retirement Simulator scenario for context. Visit that page first to personalize answers to your own numbers.")
else:
    st.caption("💡 Tip: visit the Retirement Simulator first, and answers here can reference your own scenario.")

EXAMPLE_QUESTIONS = [
    "What's the difference between Standard, Basic, and Escalating plans?",
    "Why does the Basic Plan's payout decrease over time?",
    "Should I defer my payout from 65 to 70?",
    "Will my OA and SA savings meet the Enhanced Retirement Sum by 55?",
]

st.markdown("**Try an example:**")
cols = st.columns(len(EXAMPLE_QUESTIONS))
example_clicked = None
for col, q in zip(cols, EXAMPLE_QUESTIONS):
    if col.button(q, use_container_width=True):
        example_clicked = q

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

def render_markdown(text: str) -> None:
    # Escape literal $ so st.markdown doesn't treat dollar amounts (e.g.
    # "$350,000 ... $2,761") as LaTeX math delimiters, which mangles
    # everything between them.
    st.markdown(text.replace("$", "\\$"))


for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        render_markdown(msg["content"])

user_input = st.chat_input("Ask about CPF LIFE…") or example_clicked

if user_input:
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        render_markdown(user_input)

    with st.chat_message("assistant"):
        if not api_key:
            answer = (
                "⚠️ No OpenAI API key configured, so I can't call the LLM. "
                "Add `OPENAI_API_KEY` to `.streamlit/secrets.toml` locally, or to this "
                "app's Secrets in Streamlit Community Cloud settings. See the README for details."
            )
            st.warning(answer)
        else:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)

                messages = [{"role": "system", "content": build_system_prompt()}]
                if scenario_ctx:
                    messages.append({"role": "system", "content": scenario_ctx})
                # include recent chat history for follow-up questions
                for m in st.session_state["chat_history"][-8:]:
                    messages.append(m)

                with st.spinner("Thinking…"):
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        tools=TOOLS,
                        temperature=0.2,
                        max_tokens=600,
                    )
                    msg = response.choices[0].message

                    # Tool-calling loop: the model can request the deterministic
                    # readiness calculator instead of doing the arithmetic itself.
                    # We execute the tool, feed the result back, and let it call
                    # again (e.g. a second lookup) up to a small round limit.
                    rounds = 0
                    while msg.tool_calls and rounds < 3:
                        messages.append({
                            "role": "assistant",
                            "content": msg.content,
                            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
                        })
                        for tc in msg.tool_calls:
                            try:
                                args = json.loads(tc.function.arguments)
                                result = call_tool(tc.function.name, args)
                            except Exception as e:
                                result = {"error": str(e)}
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": json.dumps(result),
                            })
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages,
                            tools=TOOLS,
                            temperature=0.2,
                            max_tokens=600,
                        )
                        msg = response.choices[0].message
                        rounds += 1

                answer = msg.content
                render_markdown(answer)
            except Exception as e:
                answer = f"⚠️ Something went wrong calling the LLM: {e}"
                st.error(answer)

    st.session_state["chat_history"].append({"role": "assistant", "content": answer})

if st.session_state["chat_history"]:
    if st.button("Clear conversation"):
        st.session_state["chat_history"] = []
        st.rerun()

st.divider()
st.caption(
    "This explainer is an AI-generated summary grounded in CPF Board's published payout "
    "figures and this app's own modeling assumptions (see Methodology). It is not financial "
    "advice — confirm your own figures via myCPF."
)
