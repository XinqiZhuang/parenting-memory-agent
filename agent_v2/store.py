"""Single-host JSON transactions, serialized across threads/processes using SQLite's lock.

SQLite is only a lock; baby.json remains canonical. A transaction writes domain
data, audit, pending and idempotency receipt together using atomic replacement.
"""
import copy
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_v2.schema import COLLECTIONS


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def file_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path) + ".lock.sqlite3", timeout=15)
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield
        connection.commit()
    finally:
        connection.close()


def read_json(path, example=None):
    path = Path(path)
    if not path.exists():
        if example is None:
            return {"profile": {}}
        path = Path(example)
    with path.open(encoding="utf-8-sig") as file:
        result = json.load(file)
    if not isinstance(result, dict):
        raise ValueError("宝宝数据不是JSON对象；未自动覆盖原文件")
    return result


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare(data):
    seen = set()
    for collection in set(COLLECTIONS.values()):
        records = data.setdefault(collection, [])
        if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
            raise ValueError(f"{collection}格式错误；请先备份并检查")
        for record in records:
            identity = record.get("id")
            if not isinstance(identity, str) or not identity or identity in seen:
                identity = uuid4().hex
                record["id"] = identity
            seen.add(identity)
    state = data.setdefault("_agent_v2", {})
    for key, default in (("events", []), ("contexts", {}), ("receipts", {})):
        state.setdefault(key, default)
    return state


class Repository:
    def __init__(self, path, example=None):
        self.path = Path(path)
        self.example = example

    @contextmanager
    def transaction(self):
        with file_lock(self.path):
            before = read_json(self.path, self.example)
            data = copy.deepcopy(before)
            prepare(data)
            yield data
            if data != before or not self.path.exists():
                # First migration is reversible; do not delete or merge existing records.
                if "_agent_v2" not in before and self.path.exists():
                    backup = self.path.with_name(self.path.stem + ".before_v2." + uuid4().hex[:8] + ".json")
                    atomic_write(backup, before)
                data["_revision"] = before.get("_revision", 0) + 1
                atomic_write(self.path, data)

    def snapshot(self):
        with self.transaction() as data:
            pass
        return copy.deepcopy(data)
