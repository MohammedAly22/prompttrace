"""SQLite database layer for PromptTrace."""

import sqlite3
import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DB_PATH: Optional[str] = None

def get_db_path() -> str:
    global _DB_PATH
    if _DB_PATH:
        return _DB_PATH
    return os.environ.get("PROMPTTRACE_DB", str(Path.cwd() / ".prompttrace" / "traces.db"))

def set_db_path(path: str):
    global _DB_PATH
    _DB_PATH = path

def _connect() -> sqlite3.Connection:
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER NOT NULL,
            prompt_hash TEXT NOT NULL,
            prompt_template TEXT NOT NULL,
            input_variables TEXT DEFAULT '{}',
            output TEXT DEFAULT '',
            model TEXT DEFAULT 'unknown',
            generation_params TEXT DEFAULT '{}',
            status TEXT DEFAULT 'success',
            latency_ms REAL DEFAULT 0,
            token_count_input INTEGER DEFAULT 0,
            token_count_output INTEGER DEFAULT 0,
            error_message TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (experiment_id) REFERENCES experiments(id)
        );

        CREATE TABLE IF NOT EXISTS evals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (trace_id) REFERENCES traces(id)
        );

        CREATE INDEX IF NOT EXISTS idx_traces_experiment ON traces(experiment_id);
        CREATE INDEX IF NOT EXISTS idx_traces_prompt_hash ON traces(prompt_hash);
        CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at);
        CREATE INDEX IF NOT EXISTS idx_evals_trace ON evals(trace_id);
    """)
    conn.commit()
    conn.close()

def get_or_create_experiment(name: str, description: str = "") -> int:
    conn = _connect()
    row = conn.execute("SELECT id FROM experiments WHERE name = ?", (name,)).fetchone()
    if row:
        exp_id = row["id"]
    else:
        cur = conn.execute(
            "INSERT INTO experiments (name, description) VALUES (?, ?)",
            (name, description)
        )
        exp_id = cur.lastrowid
        conn.commit()
    conn.close()
    return exp_id

def hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]

def insert_trace(
    experiment_id: int,
    prompt_template: str,
    input_variables: dict,
    output: str,
    model: str = "unknown",
    generation_params: dict = None,
    status: str = "success",
    latency_ms: float = 0,
    token_count_input: int = 0,
    token_count_output: int = 0,
    error_message: str = "",
    tags: list = None,
) -> int:
    conn = _connect()
    cur = conn.execute(
        """INSERT INTO traces
        (experiment_id, prompt_hash, prompt_template, input_variables, output,
         model, generation_params, status, latency_ms, token_count_input,
         token_count_output, error_message, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            experiment_id,
            hash_prompt(prompt_template),
            prompt_template,
            json.dumps(input_variables),
            output,
            model,
            json.dumps(generation_params or {}),
            status,
            latency_ms,
            token_count_input,
            token_count_output,
            error_message,
            json.dumps(tags or []),
        ),
    )
    trace_id = cur.lastrowid
    conn.commit()
    conn.close()
    return trace_id

def insert_eval(trace_id: int, metric_name: str, metric_value: float):
    conn = _connect()
    conn.execute(
        "INSERT INTO evals (trace_id, metric_name, metric_value) VALUES (?, ?, ?)",
        (trace_id, metric_name, metric_value),
    )
    conn.commit()
    conn.close()

def fetch_all_experiments():
    conn = _connect()
    rows = conn.execute("""
        SELECT e.*, COUNT(t.id) as trace_count
        FROM experiments e
        LEFT JOIN traces t ON t.experiment_id = e.id
        GROUP BY e.id
        ORDER BY e.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_traces(experiment_id: Optional[int] = None, limit: int = 200):
    conn = _connect()
    if experiment_id:
        rows = conn.execute(
            """SELECT t.*, e.name as experiment_name
            FROM traces t JOIN experiments e ON t.experiment_id = e.id
            WHERE t.experiment_id = ? ORDER BY t.created_at DESC LIMIT ?""",
            (experiment_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT t.*, e.name as experiment_name
            FROM traces t JOIN experiments e ON t.experiment_id = e.id
            ORDER BY t.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_trace_by_id(trace_id: int):
    conn = _connect()
    row = conn.execute(
        """SELECT t.*, e.name as experiment_name
        FROM traces t JOIN experiments e ON t.experiment_id = e.id
        WHERE t.id = ?""",
        (trace_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def fetch_evals_for_trace(trace_id: int):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM evals WHERE trace_id = ? ORDER BY created_at",
        (trace_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_stats(experiment_id: Optional[int] = None):
    conn = _connect()
    stats = {}
    where = f"WHERE experiment_id = {experiment_id}" if experiment_id else ""

    stats["total_traces"] = conn.execute(f"SELECT COUNT(*) as c FROM traces {where}").fetchone()["c"]
    stats["total_experiments"] = conn.execute("SELECT COUNT(*) as c FROM experiments").fetchone()["c"]
    stats["avg_latency"] = conn.execute(f"SELECT AVG(latency_ms) as a FROM traces {where}").fetchone()["a"] or 0
    stats["success_rate"] = 0
    if stats["total_traces"] > 0:
        success = conn.execute(f"SELECT COUNT(*) as c FROM traces {where} {'AND' if where else 'WHERE'} status='success'").fetchone()["c"]
        stats["success_rate"] = round(success / stats["total_traces"] * 100, 1)

    # latency over time (last 50)
    rows = conn.execute(
        f"SELECT latency_ms, created_at FROM traces {where} ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    stats["latency_timeline"] = [{"latency": r["latency_ms"], "time": r["created_at"]} for r in reversed(rows)]

    # status distribution
    rows = conn.execute(
        f"SELECT status, COUNT(*) as c FROM traces {where} GROUP BY status"
    ).fetchall()
    stats["status_dist"] = {r["status"]: r["c"] for r in rows}

    # model distribution
    rows = conn.execute(
        f"SELECT model, COUNT(*) as c FROM traces {where} GROUP BY model ORDER BY c DESC LIMIT 10"
    ).fetchall()
    stats["model_dist"] = {r["model"]: r["c"] for r in rows}

    # unique prompts
    stats["unique_prompts"] = conn.execute(
        f"SELECT COUNT(DISTINCT prompt_hash) as c FROM traces {where}"
    ).fetchone()["c"]

    conn.close()
    return stats

def fetch_unique_prompts(experiment_id: Optional[int] = None):
    conn = _connect()
    if experiment_id:
        rows = conn.execute("""
            SELECT prompt_hash, prompt_template, COUNT(*) as run_count,
                   AVG(latency_ms) as avg_latency,
                   MIN(created_at) as first_seen, MAX(created_at) as last_seen
            FROM traces WHERE experiment_id = ?
            GROUP BY prompt_hash ORDER BY last_seen DESC
        """, (experiment_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT prompt_hash, prompt_template, COUNT(*) as run_count,
                   AVG(latency_ms) as avg_latency,
                   MIN(created_at) as first_seen, MAX(created_at) as last_seen
            FROM traces GROUP BY prompt_hash ORDER BY last_seen DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_experiment(experiment_id: int):
    conn = _connect()
    conn.execute("DELETE FROM evals WHERE trace_id IN (SELECT id FROM traces WHERE experiment_id = ?)", (experiment_id,))
    conn.execute("DELETE FROM traces WHERE experiment_id = ?", (experiment_id,))
    conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
    conn.commit()
    conn.close()

def delete_trace(trace_id: int):
    conn = _connect()
    conn.execute("DELETE FROM evals WHERE trace_id = ?", (trace_id,))
    conn.execute("DELETE FROM traces WHERE id = ?", (trace_id,))
    conn.commit()
    conn.close()

# Auto-init on import
init_db()