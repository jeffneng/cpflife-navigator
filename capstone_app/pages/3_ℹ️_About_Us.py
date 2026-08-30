import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cpf_life.calculations import escape_dollars, load_assumptions

st.set_page_config(page_title="About Us — CPF LIFE Navigator", page_icon="ℹ️", layout="wide")

cpf = load_assumptions()
rsp = cpf["retirementSumProjection"]
MIN_YEAR, MAX_YEAR = rsp["supportedCohortYears"]["min"], rsp["supportedCohortYears"]["max"]

st.title("ℹ️ About Us")

st.markdown(escape_dollars(
    f"""
## Project

**CPF LIFE Navigator** — a capstone project for the AI Bootcamp (Project Type 2:
Building an Interactive LLM-Powered Solution).

**Author:** Jeffery Neng, individual submission.

## Domain area

**Understanding CPF (Central Provident Fund) Policies** — specifically, CPF LIFE, the
national annuity scheme that pays eligible members a monthly income for life from their
Retirement Account (RA) savings.

## The problem

CPF LIFE is a decision nearly every Singaporean eventually has to make, but it's genuinely
hard to reason about:

- The payout **isn't a published formula** — CPF Board publishes worked examples for a
  handful of balances, not a general calculator.
- There are **three plans** (Standard, Basic, Escalating) with materially different
  payout shapes, and it's hard to picture how they diverge over 20–30 years just from
  reading policy pages.
- Key mechanics — like *why* Basic Plan's payout gradually decreases — are explained in
  prose across multiple official and semi-official sources, not in one place a citizen
  can explore interactively.
- CPF only publishes retirement sum (BRS/FRS/ERS) and payout figures for **one cohort at
  a time** (members turning 55 this year) — anyone further from 55 has no official figure
  to plan against at all.

## Scope & limitations

This simulator only supports members turning age 55 between **{MIN_YEAR} and {MAX_YEAR}**.
CPF Board has published retirement sums and payout figures for the {rsp['baseCohortYear']}
cohort only; for other years in that range, this app **projects** the BRS/FRS/ERS
retirement sums forward at an assumed {rsp['annualGrowthRate']*100:.1f}%/yr (this app's own
modeling assumption, not a CPF projection — see Methodology). Members turning 55 outside
this window aren't supported; the app will say so and ask for a manually-entered RA balance
instead (see the "Your current age" input on the Retirement Simulator).

## Objectives

1. **Consolidate** CPF Board's publicly available payout information (and a widely-cited
   explainer of Basic Plan mechanics) into one interactive tool.
2. **Personalise**: let a user enter generic, non-identifying inputs — current age, which
   retirement sum they're aiming for, gender, plan, and payout start age — and see numbers
   specific to their scenario, without needing to already know their exact RA balance.
3. **Enhance understanding** through an LLM-powered explainer that can answer follow-up
   questions in plain English, grounded in the same data the simulator uses.
4. **Present effectively**: numeric outputs, a payout-by-age snapshot, and a multi-plan
   comparison chart, rather than prose alone.

## Data sources

| Source | Used for |
|---|---|
| [CPF Board — "How much CPF payouts can I get every month"](https://www.cpf.gov.sg/service/article/how-much-cpf-payouts-can-i-get-every-month) | Published payout anchors (6 RA balance points, ages 65 and 70, Standard Plan, male) — and the {rsp['baseCohortYear']} BRS/FRS/ERS figures used as the base for retirement sum projections |
| [CPF Board — "How does the CPF LIFE Basic Plan work"](https://www.cpf.gov.sg/service/article/how-does-the-cpf-life-basic-plan-work) | Basic Plan mechanics: premium fraction, self-funded drawdown, $60,000 threshold, age-90 transition |
| [DBS — "What is CPF LIFE"](https://www.dbs.com.sg/personal/articles/nav/retirement/what-is-cpf-life) | Corroborating explainer for Basic Plan mechanics |
| CPF Board's general guidance that female payouts run "roughly 6% to 8% lower" than male | Female payout approximation (no official female table is published) |

Every number this app models beyond a direct citation is documented — with its
assumption and its source — in `data/cpf-anchors-2026.json` (in this project's
repository) and explained further in **Methodology**.

## Features / use cases

1. **📈 Retirement Simulator** — interactive payout calculator across all three plans,
   with a multi-plan comparison chart.
2. **💬 Policy Explainer** — an LLM-powered Q&A that explains CPF LIFE mechanics in plain
   English, personalized to the user's simulator scenario when available.

## Tech stack

Python, Streamlit (multi-page app), Plotly (charts), OpenAI API (gpt-4o-mini) for the
Policy Explainer. All CPF assumptions live in one JSON file, so the app can be
recalibrated yearly against CPF Board's updated figures without touching code.

## Disclaimer

This tool provides **estimates only**. CPF LIFE payouts are not calculated by a public
formula — actual amounts depend on CPF Board's internal mortality tables, prevailing
interest rates, and your specific cohort. It is not financial advice. Confirm your actual
figures via your **myCPF** account.
"""
))
