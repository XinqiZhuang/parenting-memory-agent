import json

import pytest
from pydantic import ValidationError

from agent_v2.parser import parse_command, ParseError
from agent_v2.schema import Command, Selector


@pytest.mark.parametrize("values", [{"date": "2026-02-30"}, {"date": "2026-9-1"}, {"date": None},
                                   {"duration_minutes": -1}, {"duration_minutes": True}, {"duration_minutes": "10"},
                                   {"id": "fake"}, {"photos": ["../../private"]}, {"_deleted_at": "today"},
                                   {"category": "wrong"}, {"description": ""}, {}, {"duration_minutes": float("nan")}])
def test_update_payload_rejected(values):
    with pytest.raises(ValidationError):
        Command(action="UPDATE", entity="ACTIVITY", values=values)


@pytest.mark.parametrize("selector", [{"latest": "false"}, {"latest": True, "earliest": True},
                                    {"start_date": "2026-09-30", "end_date": "2026-09-01"},
                                    {"date": "2026-99-99"}, {"limit": 0}, {"limit": 999},
                                    {"category": "大运动"}, {"missing_field": "password"}, {"metric": "secret"}])
def test_selector_rejected(selector):
    with pytest.raises(ValidationError):
        Selector(**selector)


@pytest.mark.parametrize("action", ["QUERY", "DELETE", "ANALYZE", "AUDIT", "UNKNOWN", "UNDO"])
def test_read_delete_actions_do_not_accept_arbitrary_values(action):
    with pytest.raises(ValidationError):
        Command(action=action, values={"description": "unexpected"})


def test_parser_valid_unicode_json_and_context():
    calls = []
    def caller(messages):
        calls.append(messages)
        return json.dumps({"action": "UPDATE", "entity": "ACTIVITY", "selector": {"name": "套杯游戏", "missing_field": "date"}, "values": {"date": "2026-08-30"}}, ensure_ascii=False)
    result = parse_command("另外一条日期是2026-08-30", {"history": [{"role": "assistant", "content": "套杯游戏缺日期"}]}, caller=caller)
    assert result.action == "UPDATE"
    assert result.values["date"] == "2026-08-30"
    assert "套杯游戏缺日期" in calls[0][-1]["content"]
    assert "补日期是UPDATE" in calls[0][0]["content"]


def test_parser_retry_invalid_then_valid():
    responses = iter(["not JSON", '{"action":"QUERY","entity":"ACTIVITY"}'])
    result = parse_command("宝宝玩过什么", caller=lambda _: next(responses))
    assert result.action == "QUERY"


def test_parser_fails_closed_after_two_invalid_responses():
    calls = []
    def caller(_):
        calls.append(1)
        return '{"action":"UPDATE","entity":"ACTIVITY","values":{"date":"wrong"}}'
    with pytest.raises(ParseError):
        parse_command("改日期", caller=caller)
    assert len(calls) == 2


def test_timeout_does_not_turn_into_add():
    def caller(_):
        raise TimeoutError("test")
    with pytest.raises(ParseError, match="没有执行写入"):
        parse_command("套杯日期改为昨天", caller=caller)


@pytest.mark.parametrize("text,action", [("操作日志", "AUDIT"), ("刚才记录了什么", "AUDIT"), ("撤销上次操作", "UNDO")])
def test_control_commands_no_llm(text, action):
    def forbidden(_):
        raise AssertionError("should not call API")
    assert parse_command(text, caller=forbidden).action == action
