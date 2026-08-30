"""Local SQLite persistence for named simulator scenarios."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parents[1] / "scenarios.sqlite"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            inputs_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


def list_scenarios() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, updated_at FROM scenarios ORDER BY updated_at DESC"
        ).fetchall()
    return [{"id": r[0], "name": r[1], "updated_at": r[2]} for r in rows]


def get_scenario(scenario_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, inputs_json FROM scenarios WHERE id = ?", (scenario_id,)
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "inputs": json.loads(row[2])}


def save_scenario(name: str, inputs: dict) -> None:
    inputs_json = json.dumps(inputs)
    with _connect() as conn:
        existing = conn.execute("SELECT id FROM scenarios WHERE name = ?", (name,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE scenarios SET inputs_json = ?, updated_at = datetime('now') WHERE id = ?",
                (inputs_json, existing[0]),
            )
        else:
            conn.execute(
                "INSERT INTO scenarios (name, inputs_json) VALUES (?, ?)", (name, inputs_json)
            )
        conn.commit()


def delete_scenario(scenario_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
        conn.commit()
