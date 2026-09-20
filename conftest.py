"""Offline regression isolation: never read private runtime data or call paid APIs."""
import os
import tempfile
from types import SimpleNamespace

import pytest
import openai

_test_dir = tempfile.TemporaryDirectory(prefix="parenting-tests-")
os.environ["PARENTING_DATA_DIR"] = _test_dir.name
os.environ["DEEPSEEK_API_KEY"] = "offline-test-not-a-real-key"


def _blocked_api(*args, **kwargs):
    raise AssertionError("离线回归禁止真实API调用")


class OfflineClient:
    def __init__(self, *args, **kwargs):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=_blocked_api))


_real_client = openai.OpenAI
openai.OpenAI = OfflineClient

# These original files are interactive/manual demos with no test functions.
collect_ignore = ["test_query.py", "test_activity_analysis.py", "test_modules.py", "test_data.py",
                  "test_age.py", "test_activity.py", "test_conflict.py"]


@pytest.fixture(autouse=True)
def isolate_every_test(tmp_path, monkeypatch):
    import baby
    import pending
    import audit
    import httpx
    monkeypatch.setattr(baby, "DATA_FILE", tmp_path / "baby.json")
    monkeypatch.setattr(pending, "PENDING_FILE", tmp_path / "pending.json")
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "audit.jsonl")
    def blocked(*args, **kwargs):
        raise AssertionError("离线测试禁止访问真实API；请使用显式live评估脚本")
    monkeypatch.setattr(httpx.Client, "send", blocked)


def pytest_sessionfinish(session, exitstatus):
    openai.OpenAI = _real_client
    _test_dir.cleanup()
