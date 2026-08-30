# CPF LIFE Navigator (Streamlit Capstone App)

AI Bootcamp Capstone (Project Type 2) submission — an interactive, LLM-powered guide to
Singapore's CPF LIFE national annuity scheme.

- **Use case 1 — Retirement Simulator:** enter your RA balance, gender, plan, and payout
  start age; see monthly/annual/lifetime payout figures, a payout-by-age snapshot, and
  all three CPF LIFE plans compared on one chart. Save and reload named scenarios.
- **Use case 2 — Policy Explainer:** ask free-text questions about CPF LIFE and get
  answers from an LLM grounded in the same sourced data as the simulator, personalized
  to your current scenario when available.

See the in-app **About Us** and **Methodology** pages for scope, data sources, and
implementation details.

## Run it locally

```bash
cd capstone_app
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then edit .streamlit/secrets.toml and paste in your own OPENAI_API_KEY
streamlit run streamlit_app.py
```

The app reads `../data/cpf-anchors-2026.json` (the repo-root data file shared with the
original Node/JS prototype) as its single source of truth — no path changes needed.

The Retirement Simulator works without any API key. The Policy Explainer needs
`OPENAI_API_KEY` set (via `.streamlit/secrets.toml` locally, or Streamlit Community
Cloud's Secrets settings when deployed) — without it, it shows a clear setup message
instead of failing silently.

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app pointing at
   this repo, branch `main`, and main file path `capstone_app/streamlit_app.py`.
3. In the app's Settings → Secrets, paste:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
4. Deploy. The `data/` folder at the repo root is included automatically since it's
   part of the same repo.

## Why this app, not the original Node/JS prototype

An earlier version of this simulator was built as a Node/Express + vanilla JS app
(see the repo root `src/`, `server/`). This Streamlit rewrite is the actual capstone
submission — it adds the required second use case (the LLM-powered Policy Explainer)
and the required About Us / Methodology documentation pages, matching the assignment's
Python/Streamlit format. The calculation logic in `cpf_life/calculations.py` is a
verified line-for-line port of the original JS, so both versions agree.
