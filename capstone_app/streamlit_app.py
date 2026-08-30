import streamlit as st

st.set_page_config(
    page_title="CPF LIFE Navigator",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ CPF LIFE Navigator")
st.caption("An interactive guide to Singapore's CPF LIFE national annuity scheme, built for the AI Bootcamp Capstone project.")

st.markdown(
    """
CPF LIFE is one of the most consequential — and most confusing — decisions a Singaporean
retiree makes. The rules span multiple official pages, the payout math isn't published as a
formula, and the difference between Standard, Basic, and Escalating plans is hard to picture
without seeing real numbers.

**This app consolidates CPF Board's publicly available payout information into two
interactive tools:**
"""
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Retirement Simulator")
    st.markdown(
        """
        Enter your Retirement Account balance, gender, and payout start age to see:
        - Your estimated monthly payout, starting age 65–70
        - Lifetime total received, to life expectancy
        - **All three plans (Standard / Basic / Escalating) compared on one chart**
        - How Basic Plan's payout declines over time
        - Save and reload named scenarios to compare choices later
        """
    )
    st.page_link("pages/1_📈_Retirement_Simulator.py", label="Open the Retirement Simulator →", icon="📈")

with col2:
    st.subheader("💬 Policy Explainer")
    st.markdown(
        """
        Ask a plain-English question about CPF LIFE — plan differences, deferral,
        how Basic Plan's drawdown works, bequest, or anything about your own scenario
        from the simulator — and get an answer grounded in the same sourced data used
        by the simulator, not a generic web answer.
        """
    )
    st.page_link("pages/2_💬_Policy_Explainer.py", label="Open the Policy Explainer →", icon="💬")

st.divider()

st.markdown(
    """
Use the sidebar to navigate between the two tools, or read **About Us** and
**Methodology** for the project's scope, data sources, and how it's built.
"""
)

with st.expander("⚠️ Estimate only — please read"):
    st.markdown(
        """
        Figures are approximations derived from CPF Board's published payout anchors,
        interpolated for other balances and adjusted for gender, plan, and deferral.
        CPF LIFE payouts are not calculated by a public formula — actual amounts depend
        on CPF Board's internal mortality tables, prevailing interest rates, and your
        specific cohort, and can only be confirmed via your **myCPF** account. See the
        **Methodology** page for exactly which figures are official and which are
        modeled approximations.
        """
    )
