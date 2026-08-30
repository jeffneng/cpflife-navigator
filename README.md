# CPF LIFE Payout Simulator

Models Singapore's CPF LIFE national annuity scheme: monthly payout, lifetime
total, and bequest decay by RA balance, gender, plan, and payout start age.

## Structure

```
data/
  cpf-anchors-2026.json   CPF payout anchors + all tunable assumptions.
                           Update this file each year when CPF Board revises
                           its payout tables — the app itself never changes.
  scenarios.sqlite         Saved scenarios (created automatically, gitignored)

src/                       Frontend (static, served by the Node server)
  index.html
  styles.css                "Ledger" visual style — navy/gold/teal, serif
                             display type, monospace numbers, ruled rows
  app.js                    Calculation logic + chart rendering + scenario UI

server/
  server.js                 Express app: serves /src, /api/anchors,
                             /api/scenarios (CRUD)
  db.js                     SQLite access (Node's built-in node:sqlite —
                             no native build step)
```

## Run it

```bash
npm install
npm start
```

Then open http://localhost:4600.

Use `npm run dev` instead to auto-restart the server on file changes.

## Updating CPF's figures yearly

Edit [`data/cpf-anchors-2026.json`](data/cpf-anchors-2026.json) — payout
anchors, gender/plan factors, deferral bonus, life expectancy defaults, and
slider ranges all live there. No code changes needed; the frontend fetches
this file fresh from the server on every load.

## Scenarios

Named scenarios (all inputs) are saved to a local SQLite database
(`data/scenarios.sqlite`) via the "Saved scenarios" panel. Saving under an
existing name overwrites it.

## Caveats

Figures are estimates only, calibrated to published 2026 payout illustrations.
CPF LIFE payouts are not produced by a public formula — actual amounts depend
on CPF Board's internal mortality tables and prevailing interest rates.
Confirm real figures via your myCPF account.
