from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_streamlit_all_three_pages_open_offline():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    first_context = app.session_state["agent_context_id"]
    app.sidebar.radio[0].set_value("照片回忆").run(timeout=15)
    assert not app.exception
    app.sidebar.radio[0].set_value("育儿知识库").run(timeout=15)
    assert not app.exception
    assert app.session_state["agent_context_id"] == first_context


def test_streamlit_chat_uses_isolated_context(monkeypatch):
    route = Mock(return_value="准备补日期，尚未写入。")
    monkeypatch.setattr("router.route_request", route)
    app = AppTest.from_file(str(APP)).run(timeout=15)
    app.sidebar.radio[0].set_value("宝宝档案").run(timeout=15)
    app.chat_input[0].set_value("另外一条补日期").run(timeout=15)
    assert not app.exception
    assert route.call_args.args == ("另外一条补日期",)
    assert route.call_args.kwargs["context_id"].startswith("web:")
    assert route.call_args.kwargs["request_id"]
    assert app.session_state["record_messages"][-1]["content"] == "准备补日期，尚未写入。"
    second = AppTest.from_file(str(APP)).run(timeout=15)
    assert second.session_state["agent_context_id"] != app.session_state["agent_context_id"]
