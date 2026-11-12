"""程序目录下的可携带数据，旧账本使用 SQLite 在线备份读取。"""
from contextlib import closing
from pathlib import Path
import os
import shutil
import sqlite3
import sys
import tempfile


def program_directory():
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def copy_missing(source, target):
    target.mkdir(parents=True, exist_ok=True)
    for name in ("ledger.sqlite3", "table-layout.ini", "custom_rules.json"):
        src, dst = source / name, target / name
        if dst.exists() or not src.is_file():
            continue
        fd, temp = tempfile.mkstemp(dir=target)
        os.close(fd)
        try:
            if name.endswith(".sqlite3"):
                with closing(sqlite3.connect(src.as_uri() + "?mode=ro", uri=True)) as db, closing(sqlite3.connect(temp)) as backup:
                    db.backup(backup)
            else:
                shutil.copyfile(src, temp)
            try:
                os.rename(temp, dst)  # Windows refuses to replace an existing file.
            except FileExistsError:
                pass
        finally:
            Path(temp).unlink(missing_ok=True)


def prepare_data():
    target = program_directory() / "data"
    target.mkdir(parents=True, exist_ok=True)
    return target
