"""SQLite storage layer for strategies, trades, alerts, and backtests."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_db: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    global _db
    if _db is None:
        db_path = DATA_DIR / "hyperliquid.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db = sqlite3.connect(str(db_path))
        _db.row_factory = sqlite3.Row
        _db.execute("PRAGMA journal_mode=WAL")
        _init_tables(_db)
    return _db


def _init_tables(db: sqlite3.Connection):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS strategies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            rules TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            order_id TEXT,
            coin TEXT NOT NULL,
            side TEXT NOT NULL,
            size REAL NOT NULL,
            price REAL,
            total REAL,
            market_type TEXT DEFAULT 'perp',
            strategy_id TEXT,
            status TEXT NOT NULL,
            filled_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS alert_rules (
            id TEXT PRIMARY KEY,
            coin TEXT NOT NULL,
            condition TEXT NOT NULL,
            action TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_triggered_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS alert_history (
            id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL,
            coin TEXT NOT NULL,
            message TEXT NOT NULL,
            data TEXT,
            acknowledged INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS position_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot TEXT NOT NULL,
            total_equity REAL NOT NULL,
            total_pnl REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS backtests (
            id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            config TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)


def get_config(key: str) -> Optional[str]:
    row = get_db().execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_config(key: str, value: str):
    get_db().execute(
        "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value),
    )
    get_db().commit()
