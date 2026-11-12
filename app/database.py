"""本地 SQLite 账本。每次操作在同一个事务中保存流水和规则。"""
import json
from .portable import program_directory
import sqlite3
from contextlib import closing
from dataclasses import fields
from datetime import datetime
from pathlib import Path

from .models import Transaction, unique_key

COLUMNS = tuple(field.name for field in fields(Transaction) if field.init)


def default_path():
    return program_directory() / "data" / "ledger.sqlite3"


class LedgerDatabase:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.previous = {}
        self.revision = 0
        schema = ", ".join(f"{col} {'REAL' if col == 'amount' else 'TEXT'}" for col in COLUMNS)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(f"CREATE TABLE IF NOT EXISTS transactions (entry_key TEXT PRIMARY KEY, {schema})")
            columns = {row[1] for row in db.execute("PRAGMA table_info(transactions)")}
            for name in ("merchant_id", "original_order_id", "refund_id", "manual_payment_key"):
                if name not in columns:
                    db.execute(f"ALTER TABLE transactions ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
            db.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, config TEXT NOT NULL, config_path TEXT)")
            db.execute("CREATE INDEX IF NOT EXISTS transaction_time ON transactions(time)")

    def load(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("BEGIN")
            settings = db.execute("SELECT revision, config, config_path FROM settings WHERE id=1").fetchone()
            rows = db.execute(f"SELECT entry_key, {', '.join(COLUMNS)} FROM transactions ORDER BY time, rowid").fetchall()
        previous = {row[0]: row[1:] for row in rows}
        transactions = []
        for values in previous.values():
            data = dict(zip(COLUMNS, values))
            if data["time"]:
                data["time"] = datetime.fromisoformat(data["time"])
            transactions.append(Transaction(**data))
        self.previous = previous
        self.revision = settings[0] if settings else 0
        from .storage import merge_transactions
        from .refunds import reconcile
        transactions = merge_transactions(transactions)
        reconcile(transactions)
        return transactions, (json.loads(settings[1]), settings[2]) if settings else None

    def save(self, transactions, config, config_path):
        current = {}
        for row in transactions:
            values = tuple(getattr(row, col) for col in COLUMNS)
            values = tuple(v.isoformat() if isinstance(v, datetime) else v for v in values)
            current[unique_key(row)] = values
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("SELECT revision FROM settings WHERE id=1").fetchone()
            if (version[0] if version else 0) != self.revision:
                raise RuntimeError("另一个窗口已更新账本。请查看最新数据后重新操作。")
            db.executemany("DELETE FROM transactions WHERE entry_key=?", ((key,) for key in self.previous.keys() - current.keys()))
            placeholders = ", ".join("?" for _ in range(len(COLUMNS) + 1))
            assignments = ", ".join(f"{c}=excluded.{c}" for c in COLUMNS)
            db.executemany(f"INSERT INTO transactions(entry_key, {', '.join(COLUMNS)}) VALUES ({placeholders}) ON CONFLICT(entry_key) DO UPDATE SET {assignments}",
                           ((key, *values) for key, values in current.items() if self.previous.get(key) != values))
            db.execute("INSERT OR REPLACE INTO settings VALUES (1, ?, ?, ?)", (self.revision + 1, json.dumps(config, ensure_ascii=False), config_path))
        self.previous = current
        self.revision += 1
