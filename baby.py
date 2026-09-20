import hashlib
import json
from pathlib import Path

from storage import data_path
from agent_v2.store import atomic_write, file_lock, read_json

PROJECT_DIR = Path(__file__).parent
DATA_FILE = data_path("baby.json")
EXAMPLE_DATA_FILE = PROJECT_DIR / "data" / "baby.example.json"


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Snapshot(dict):
    """Legacy read/modify/save callers retain an optimistic version token."""
    pass


def load_baby():
    with file_lock(DATA_FILE):
        data = read_json(DATA_FILE, EXAMPLE_DATA_FILE)
        if not Path(DATA_FILE).exists():
            atomic_write(DATA_FILE, data)
        result = Snapshot(data)
        result.original_fingerprint = fingerprint(data)
        return result


def save_baby(baby):
    with file_lock(DATA_FILE):
        if Path(DATA_FILE).exists():
            current = read_json(DATA_FILE)
            expected = getattr(baby, "original_fingerprint", None)
            if expected and fingerprint(current) != expected:
                raise RuntimeError("数据已被其他人修改，请刷新后重试；本次未覆盖。")
            if "_agent_v2" in current and expected is None:
                raise RuntimeError("新版数据拒绝无版本号的整体覆盖，请重新读取再保存。")
        atomic_write(DATA_FILE, baby)
        if isinstance(baby, Snapshot):
            baby.original_fingerprint = fingerprint(baby)
