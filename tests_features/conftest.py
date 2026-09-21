import io
import sys

import pytest
from PIL import Image

from agent_v2.store import Repository


@pytest.fixture(autouse=True)
def isolate_features(tmp_path, monkeypatch):
    original_main = sys.modules.get("__main__")
    import storage
    import requests
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("WEB_PASSWORD", raising=False)
    for key in ("VISION_API_KEY", "VISION_BASE_URL", "VISION_MODEL", "FEISHU_PUSH_CHAT_ID"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("FEISHU_ALLOWED_CHAT_IDS", "test-group")
    def deny(*args, **kwargs):
        raise AssertionError("禁止测试发送真实请求")
    monkeypatch.setattr(requests.sessions.Session, "request", deny)
    try:
        yield
    finally:
        # Streamlit AppTest installs a script module as __main__; do not let it
        # become the entry point of later multiprocessing spawn tests.
        if original_main is not None:
            sys.modules["__main__"] = original_main


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path / "baby.json")


@pytest.fixture
def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (64, 48), "orange").save(output, "JPEG")
    return output.getvalue()
