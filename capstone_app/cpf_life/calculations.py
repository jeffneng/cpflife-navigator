"""CPF LIFE payout calculations.

This is a line-for-line Python port of the calculation logic in
src/app.js (the original Node/JS prototype of this simulator), kept
numerically identical on purpose so the two versions agree. Both read
the same source of truth: data/cpf-anchors-2026.json at the repo root.

See that JSON file's "notes" for citations and the approximations this
model makes — CPF LIFE payouts are not produced by a public formula.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
ANCHORS_PATH = REPO_ROOT / "data" / "cpf-anchors-2026.json"


def load_assumptions() -> dict:
    """Load the CPF anchor tables & assumptions fresh from disk every call,
    so hand-edits to the yearly data file show up without restarting."""
    with open(ANCHORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def interpolated_payout(bal: float, field: str, cpf: dict) -> float:
    """Piecewise-linear interpolation of payout/balance ratio between
    anchors, parametrized by which payout field to read (age-65 or age-70
    figures) — interpolating the ratio (not the raw payout) keeps the curve
    shaped like CPF's (payouts aren't linear in balance)."""
    anchors = cpf["payoutAnchors"]
    pts = [(a["balance"], a[field] / a["balance"]) for a in anchors]

    if bal <= pts[0][0]:
        rate = pts[0][1]
    elif bal >= pts[-1][0]:
        rate = pts[-1][1]
    else:
        rate = pts[-1][1]
        for (b0, r0), (b1, r1) in zip(pts, pts[1:]):
            if b0 <= bal <= b1:
                t = (bal - b0) / (b1 - b0)
                rate = r0 + t * (r1 - r0)
                break
    return bal * rate


def life_expectancy(gender: str, override: Optional[float], cpf: dict) -> float:
    if override and override > 0:
        return override
    return cpf["lifeExpectancy"][gender]


def compute(
    balance: float,
    gender: str,
    plan: str,
    start_age: int,
    life_exp_override: Optional[float],
    cpf: dict,
) -> dict:
    """Starting monthly payout, premium, life expectancy and defer years for
    a given plan. Any plan can be passed to compute a comparison curve."""
    bal = balance

    # 1. base monthly payout at this balance (male, standard), at age 65 and
    #    age 70 — both interpolated directly from CPF's published anchors.
    payout65 = interpolated_payout(bal, "monthlyPayout", cpf)
    payout70 = interpolated_payout(bal, "monthlyPayoutAt70", cpf)

    # 2. deferral adjustment: derive the compound annual rate implied by
    #    *this balance's own* age-65 -> age-70 anchor ratio, so payouts at
    #    65 and 70 land exactly on CPF's published figures.
    defer_years = start_age - 65
    implied_annual_rate = (payout70 / payout65) ** (1 / 5) - 1
    monthly = payout65 * (1 + implied_annual_rate) ** defer_years

    # 3. gender adjustment
    monthly *= cpf["genderFactor"][gender]

    # 4. plan adjustment
    monthly *= cpf["planFactor"][plan]

    # premium at payout start = RA balance grown through any deferral years
    # at CPF's ongoing RA interest rate (same for every plan)
    premium = bal * (1 + cpf["deferral"]["raInterestWhileDeferred"]) ** defer_years

    le = life_expectancy(gender, life_exp_override, cpf)

    return {"monthly": monthly, "premium": premium, "le": le, "deferYears": defer_years}


def build_schedule(monthly_start: float, start_age: int, le: float, plan: str, cpf: dict) -> dict:
    """Flat (Standard/Basic-shape) or escalating (2%/yr) payout schedule."""
    max_age = max(le + 8, start_age + 5, 95)
    rows = []
    cum = 0.0
    cur_monthly = monthly_start
    age = start_age
    while age <= max_age:
        if age > start_age and plan == "escalating":
            cur_monthly *= 1 + cpf["escalatingPlan"]["annualEscalationRate"]
        cum += cur_monthly * 12
        rows.append({"age": age, "cum": cum, "monthly": cur_monthly})
        age += 1
    return {"rows": rows, "maxAge": max_age}


def amortize_monthly(principal: float, annual_rate: float, years: float) -> float:
    """Level monthly payment that fully amortizes `principal` over `years`
    at `annual_rate`, compounded monthly."""
    if principal <= 0:
        return 0.0
    n = max(1, round(years * 12))
    i = annual_rate / 12
    if i == 0:
        return principal / n
    return principal * i / (1 - (1 + i) ** -n)


def build_basic_schedule(balance_at_start: float, start_age: int, initial_monthly: float, le: float, cpf: dict) -> dict:
    """Approximate the Basic Plan's declining payout shape — see
    basicPlan.description in data/cpf-anchors-2026.json for the model and
    its sources: flat while the self-funded RA portion stays above the
    extra-interest threshold, a linear ramp down once it dips below that
    threshold, then a lower flat payout from age 90 funded by the premium
    pool."""
    b = cpf["basicPlan"]
    ord_rate = cpf["deferral"]["raInterestWhileDeferred"]

    self_pool0 = balance_at_start * (1 - b["premiumFraction"])
    premium_pool0 = balance_at_start * b["premiumFraction"]

    # Find the age the self-funded balance first dips below the threshold,
    # simulating it year by year under the flat initial payout.
    self_pool = self_pool0
    crossing_age = b["selfFundedEndAge"]
    age = start_age
    while age < b["selfFundedEndAge"]:
        if self_pool < b["selfFundedThreshold"]:
            crossing_age = age
            break
        rate = ord_rate + b["extraInterestRate"]
        self_pool = self_pool * (1 + rate) - initial_monthly * 12
        age += 1

    premium_pool_at90 = premium_pool0 * (1 + ord_rate) ** (b["selfFundedEndAge"] - start_age)
    post_amort_years = max(b["postSelfFundedAmortizationYears"], le - b["selfFundedEndAge"])
    phase3_monthly = amortize_monthly(premium_pool_at90, ord_rate, post_amort_years)

    max_age = max(le + 8, start_age + 5, 95)
    rows = []
    cum = 0.0
    age = start_age
    while age <= max_age:
        if age < crossing_age:
            monthly = initial_monthly
        elif age < b["selfFundedEndAge"] and crossing_age < b["selfFundedEndAge"]:
            t = (age - crossing_age) / (b["selfFundedEndAge"] - crossing_age)
            monthly = initial_monthly + (phase3_monthly - initial_monthly) * t
        else:
            monthly = phase3_monthly
        cum += monthly * 12
        rows.append({"age": age, "cum": cum, "monthly": monthly})
        age += 1
    return {"rows": rows, "maxAge": max_age}


def schedule_for_plan(
    balance: float,
    gender: str,
    start_age: int,
    life_exp_override: Optional[float],
    plan: str,
    cpf: dict,
) -> dict:
    result = compute(balance, gender, plan, start_age, life_exp_override, cpf)
    if plan == "basic":
        return build_basic_schedule(result["premium"], start_age, result["monthly"], result["le"], cpf)
    return build_schedule(result["monthly"], start_age, result["le"], plan, cpf)


def fmt_money(n: float) -> str:
    return "${:,.0f}".format(round(n))


def escape_dollars(text: str) -> str:
    """Escape literal $ before passing text to st.markdown/st.caption/etc. —
    Streamlit's markdown renderer treats a matched pair of $ anywhere in the
    same call as inline LaTeX math, which mangles everything between two
    dollar amounts (e.g. "$220,400 ... $1,780"). Only needed for text that
    will be markdown-rendered; never apply this to text sent to the LLM."""
    return text.replace("$", "\\$")


# ---- retirement sum projection (used by the Streamlit capstone app only) ----
# See retirementSumProjection.description in data/cpf-anchors-2026.json.

def cohort_growth_factor(cohort_year: int, cpf: dict) -> float:
    p = cpf["retirementSumProjection"]
    return (1 + p["annualGrowthRate"]) ** (cohort_year - p["baseCohortYear"])


def projected_retirement_sum(tier: str, cohort_year: int, cpf: dict) -> float:
    """Projected BRS/FRS/ERS for a member turning 55 in `cohort_year`,
    compounding from the published 2026 figure and rounded to the nearest
    $100 (CPF's own publishing convention)."""
    p = cpf["retirementSumProjection"]
    base = p["baseSums"][tier]
    return round(base * cohort_growth_factor(cohort_year, cpf) / 100) * 100


def compute_for_cohort(
    balance: float,
    gender: str,
    plan: str,
    start_age: int,
    life_exp_override: Optional[float],
    cpf: dict,
    cohort_year: int,
) -> dict:
    """Same as compute(), but for a balance denominated in a later cohort's
    dollars: normalizes to 2026-equivalent dollars, runs the unchanged
    2026-anchored calculation, then re-inflates the dollar outputs by the
    same growth factor. cohort_year = 2026 (the base year) is a no-op."""
    growth_factor = cohort_growth_factor(cohort_year, cpf)
    result = compute(balance / growth_factor, gender, plan, start_age, life_exp_override, cpf)
    return {
        "monthly": result["monthly"] * growth_factor,
        "premium": result["premium"] * growth_factor,
        "le": result["le"],
        "deferYears": result["deferYears"],
    }


def schedule_for_plan_and_cohort(
    balance: float,
    gender: str,
    start_age: int,
    life_exp_override: Optional[float],
    plan: str,
    cpf: dict,
    cohort_year: int,
) -> dict:
    growth_factor = cohort_growth_factor(cohort_year, cpf)
    sched = schedule_for_plan(balance / growth_factor, gender, start_age, life_exp_override, plan, cpf)
    return {
        "rows": [
            {"age": r["age"], "cum": r["cum"] * growth_factor, "monthly": r["monthly"] * growth_factor}
            for r in sched["rows"]
        ],
        "maxAge": sched["maxAge"],
    }


# ---- OA/SA -> Retirement Sum readiness projection ----
# A pre-55 "will I make it" calculator: projects OA and SA forward month by
# month to age 55, then applies CPF's actual RA-formation waterfall (SA
# first, then OA, down to an optional retained OA floor) against a chosen
# retirement sum tier. This is the tool the Policy Explainer's LLM calls
# for questions involving specific balances/contributions/rates — the LLM
# never does this arithmetic itself; this function does, deterministically.

def _months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def project_retirement_readiness(
    birthdate: str,
    current_oa: float,
    current_sa: float,
    monthly_oa_contribution: float,
    monthly_sa_contribution: float,
    target_tier: str,
    cpf: dict,
    oa_annual_rate: float = 0.025,
    sa_annual_rate: float = 0.04,
    oa_retain_amount: float = 0.0,
    as_of: Optional[date] = None,
) -> dict:
    """Project OA/SA to age 55 and check readiness against a retirement sum.

    birthdate: "YYYY-MM-DD". target_tier: "BRS" | "FRS" | "ERS".
    Assumptions (approximations, not CPF's exact mechanics):
    - Monthly compounding of the given annual rates (contribution added,
      then interest applied, each month) — not CPF's actual interest
      crediting schedule (monthly computation, annual crediting, based on
      lowest monthly balance).
    - Does not add CPF's extra interest tiers (e.g. +1%/+2% on the first
      $60,000/$30,000 of combined balances) unless already folded into the
      rates you supply — pass blended rates if you want that reflected.
    - At 55, SA is used to form the Retirement Account before OA (matching
      CPF's real order), and OA is drawn no lower than oa_retain_amount.
    - The retirement sum target is this app's own projection for the
      member's cohort year (see retirementSumProjection), not a published
      CPF figure, for any cohort after the base year.
    """
    as_of = as_of or date.today()
    bdate = date.fromisoformat(birthdate)
    turn_55_date = bdate.replace(year=bdate.year + 55)
    months = max(0, _months_between(as_of, turn_55_date))

    rsp = cpf["retirementSumProjection"]
    min_year, max_year = rsp["supportedCohortYears"]["min"], rsp["supportedCohortYears"]["max"]
    cohort_year = turn_55_date.year
    out_of_range = not (min_year <= cohort_year <= max_year)
    cohort_year_used = min(max(cohort_year, min_year), max_year)
    target_sum = projected_retirement_sum(target_tier, cohort_year_used, cpf)

    oa, sa = float(current_oa), float(current_sa)
    for _ in range(months):
        oa = oa * (1 + oa_annual_rate / 12) + monthly_oa_contribution
        sa = sa * (1 + sa_annual_rate / 12) + monthly_sa_contribution

    sa_used = min(sa, target_sum)
    remaining = target_sum - sa_used
    available_oa = max(0.0, oa - oa_retain_amount)
    oa_used = min(remaining, available_oa)
    ra_formed = sa_used + oa_used
    shortfall = max(0.0, target_sum - ra_formed)

    return {
        "turn_55_date": turn_55_date.isoformat(),
        "months_projected": months,
        "cohort_year": cohort_year,
        "cohort_outside_supported_range": out_of_range,
        "oa_at_55": round(oa, 2),
        "sa_at_55": round(sa, 2),
        "target_tier": target_tier,
        "target_sum": target_sum,
        "sa_used_for_ra": round(sa_used, 2),
        "oa_used_for_ra": round(oa_used, 2),
        "ra_formed": round(ra_formed, 2),
        "shortfall": round(shortfall, 2),
        "meets_target": shortfall <= 0.5,
        "oa_remaining_after_transfer": round(oa - oa_used, 2),
    }
