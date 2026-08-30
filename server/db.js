// SQLite persistence for named scenarios, via Node's built-in node:sqlite
// (no native build step — requires Node 22.5+).
const { DatabaseSync } = require('node:sqlite');
const path = require('node:path');
const fs = require('node:fs');

const DATA_DIR = path.join(__dirname, '..', 'data');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

const DB_PATH = path.join(DATA_DIR, 'scenarios.sqlite');
const db = new DatabaseSync(DB_PATH);

db.exec(`
  CREATE TABLE IF NOT EXISTS scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    inputs_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
`);

function listScenarios() {
  const stmt = db.prepare(
    'SELECT id, name, created_at, updated_at FROM scenarios ORDER BY updated_at DESC'
  );
  return stmt.all();
}

function getScenario(id) {
  const stmt = db.prepare('SELECT * FROM scenarios WHERE id = ?');
  const row = stmt.get(id);
  if (!row) return null;
  return { ...row, inputs: JSON.parse(row.inputs_json) };
}

function saveScenario(name, inputs) {
  const inputsJson = JSON.stringify(inputs);
  const existing = db.prepare('SELECT id FROM scenarios WHERE name = ?').get(name);
  if (existing) {
    db.prepare(
      "UPDATE scenarios SET inputs_json = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(inputsJson, existing.id);
    return getScenario(existing.id);
  }
  const info = db
    .prepare('INSERT INTO scenarios (name, inputs_json) VALUES (?, ?)')
    .run(name, inputsJson);
  return getScenario(info.lastInsertRowid);
}

function deleteScenario(id) {
  const info = db.prepare('DELETE FROM scenarios WHERE id = ?').run(id);
  return info.changes > 0;
}

module.exports = { listScenarios, getScenario, saveScenario, deleteScenario };
