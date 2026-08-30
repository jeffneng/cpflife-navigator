import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cpf_life.calculations import compute, fmt_money, load_assumptions

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

IMPORTANT CAVEATS TO CONVEY WHEN RELEVANT: CPF LIFE payouts are not calculated by a published
public formula. Real payouts depend on CPF Board's internal mortality tables and prevailing
interest rates, and can only be confirmed via a member's own myCPF account. You are not a
licensed financial advisor — do not give personalized investment or financial advice; explain
policy mechanics and let the user draw their own conclusions.

Keep answers concise, plain-English, and specific. Use numbers from the data above where they
help. If the user's current simulator scenario is provided below, use it to personalize your
explanation."""


def build_scenario_context() -> str | None:
    """Pull the user's current scenario from the Retirement Simulator page's
    session state, if they've visited it, so answers can be personalized —
    e.g. 'why is *my* Basic Plan payout dropping?' """
    keys = ["balance", "gender", "plan", "start_age", "life_exp_override"]
    if not all(k in st.session_state for k in keys):
        return None
    result = compute(
        st.session_state["balance"], st.session_state["gender"], st.session_state["plan"],
        st.session_state["start_age"], st.session_state["life_exp_override"] or None, cpf,
    )
    return (
        f"The user's current Retirement Simulator scenario: RA balance "
        f"{fmt_money(st.session_state['balance'])}, {st.session_state['gender'].title()}, "
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
    "How is my payout calculated if I'm female?",
]

st.markdown("**Try an example:**")
cols = st.columns(len(EXAMPLE_QUESTIONS))
example_clicked = None
for col, q in zip(cols, EXAMPLE_QUESTIONS):
    if col.button(q, use_container_width=True):
        example_clicked = q

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask about CPF LIFE…") or example_clicked

if user_input:
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

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
                        temperature=0.3,
                        max_tokens=500,
                    )
                answer = response.choices[0].message.content
                st.markdown(answer)
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
