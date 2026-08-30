const express = require('express');
const path = require('node:path');
const fs = require('node:fs');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 4600;

app.use(express.json());

// ---- CPF assumptions data (read fresh each request so /data edits show up
//      without a server restart — this file is meant to be hand-updated yearly) ----
const ANCHORS_PATH = path.join(__dirname, '..', 'data', 'cpf-anchors-2026.json');
app.get('/api/anchors', (req, res) => {
  try {
    const raw = fs.readFileSync(ANCHORS_PATH, 'utf-8');
    res.type('application/json').send(raw);
  } catch (err) {
    res.status(500).json({ error: 'Could not read CPF anchors file', detail: err.message });
  }
});

// ---- scenario persistence ----
app.get('/api/scenarios', (req, res) => {
  res.json(db.listScenarios());
});

app.get('/api/scenarios/:id', (req, res) => {
  const scenario = db.getScenario(Number(req.params.id));
  if (!scenario) return res.status(404).json({ error: 'Scenario not found' });
  res.json(scenario);
});

app.post('/api/scenarios', (req, res) => {
  const { name, inputs } = req.body || {};
  if (!name || typeof name !== 'string' || !name.trim()) {
    return res.status(400).json({ error: 'A scenario name is required' });
  }
  if (!inputs || typeof inputs !== 'object') {
    return res.status(400).json({ error: 'Scenario inputs are required' });
  }
  const saved = db.saveScenario(name.trim(), inputs);
  res.status(201).json(saved);
});

app.delete('/api/scenarios/:id', (req, res) => {
  const ok = db.deleteScenario(Number(req.params.id));
  if (!ok) return res.status(404).json({ error: 'Scenario not found' });
  res.status(204).end();
});

// ---- static frontend ----
app.use(express.static(path.join(__dirname, '..', 'src')));

app.listen(PORT, () => {
  console.log(`CPF LIFE simulator running at http://localhost:${PORT}`);
});
