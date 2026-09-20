import copy
from unittest.mock import Mock

import pytest

from agent_v2.schema import Command, Selector
from agent_v2.service import handle_request
from agent_v2.store import Repository, atomic_write


def run(repo, cmd=None, text="请求", who="m", message=None, parser=None):
    return handle_request(text, who, repository=repo, parser=parser or (lambda *_: cmd), request_id=message)


@pytest.fixture
def repo(tmp_path):
    repo = Repository(tmp_path / "baby.json")
    atomic_write(repo.path, {"profile": {"birth_date": "2025-09-01"}})
    return repo


def test_failed_commit_does_not_persist_data_audit_or_receipt(repo, monkeypatch):
    run(repo, Command(action="ADD", entity="MEMORY", values={"event": "测试"}))
    before = repo.path.read_bytes()
    with monkeypatch.context() as patch:
        patch.setattr("agent_v2.store.atomic_write", Mock(side_effect=OSError("disk full")))
        answer = run(repo, text="确认", message="confirm1")
    assert "保存失败" in answer
    assert repo.path.read_bytes() == before
    assert repo.snapshot()["_agent_v2"]["events"] == []
    assert "已经记录" in run(repo, text="确认", message="confirm1")
    assert len(repo.snapshot()["_agent_v2"]["events"]) == 1


def test_two_pending_adds_detect_duplicate_on_commit(repo):
    cmd = Command(action="ADD", entity="ACTIVITY", values={"activity": "游戏", "date": "2026-09-20"})
    run(repo, cmd, who="mom")
    run(repo, cmd, who="dad")
    run(repo, text="确认", who="mom")
    assert "没有重复新增" in run(repo, text="确认", who="dad")
    assert len(repo.snapshot()["learning_activities"]) == 1


def test_confirmation_is_not_inferred_from_long_request(repo):
    run(repo, Command(action="ADD", entity="MEMORY", values={"event": "测试"}))
    assert "等待确认" in run(repo, text="我确认你没理解错吗？")
    assert not repo.snapshot()["memories"]


def test_current_context_changes_during_model_call(repo):
    def parser(*_):
        run(repo, Command(action="ADD", entity="MEMORY", values={"event": "另一个请求"}))
        return Command(action="ADD", entity="MEMORY", values={"event": "过时请求"})
    assert "另一条请求" in run(repo, parser=parser)
    run(repo, text="确认")
    assert repo.snapshot()["memories"][0]["event"] == "另一个请求"


def test_date_update_recomputes_month_age_in_preview(repo):
    with repo.transaction() as data:
        data["development_milestones"] = [{"id": "r", "skill": "爬", "date": "2026-05-01", "age_months": 8}]
    result = run(repo, Command(action="UPDATE", entity="DEVELOPMENT", selector=Selector(id="r"), values={"date": "2026-06-01"}))
    assert "月龄：8 → 9" in result
    run(repo, text="确认")
    assert repo.snapshot()["development_milestones"][0]["age_months"] == 9


def test_date_before_birth_and_conflicting_age_rejected(repo):
    assert "早于出生" in run(repo, Command(action="ADD", entity="DEVELOPMENT", values={"skill": "爬", "date": "2024-01-01"}))
    assert "不一致" in run(repo, Command(action="ADD", entity="DEVELOPMENT", values={"skill": "爬", "date": "2026-09-01", "age_months": 1}))
    assert not repo.snapshot()["development_milestones"]


def test_query_and_mutation_context_do_not_cross_users(repo):
    with repo.transaction() as data:
        data["learning_activities"] = [{"id": "a", "activity": "套杯"}]
    run(repo, Command(action="QUERY", entity="ACTIVITY"), who="mother")
    result = run(repo, Command(action="QUERY", selector=Selector(reference="last")), who="father")
    assert "请说明" in result


def test_parser_cannot_set_permissions_or_write_arbitrary_file(repo):
    answer = run(repo, {"action": "ADD", "entity": "MEMORY", "values": {"event": "测试"}, "actor_name": "admin", "path": "../../private"})
    assert "校验" in answer
    assert not repo.snapshot()["memories"]


def test_unsupported_batch_cannot_partially_commit(repo):
    commands = [{"action": "ADD", "entity": "MEMORY", "values": {"event": "A"}},
                {"action": "ADD", "entity": "MEMORY", "values": {"event": "B"}}]
    assert "校验" in run(repo, commands)
    assert not repo.snapshot()["memories"]


def test_no_changes_is_not_logged_as_write(repo):
    with repo.transaction() as data:
        data["learning_activities"] = [{"id": "a", "activity": "套杯", "date": "2026-08-30"}]
    answer = run(repo, Command(action="UPDATE", entity="ACTIVITY", selector=Selector(id="a"), values={"date": "2026-08-30"}))
    assert "没有修改" in answer
    assert not repo.snapshot()["_agent_v2"]["events"]


def test_deleted_record_not_returned_in_statistics(repo):
    with repo.transaction() as data:
        data["feeding_records"] = [{"id": "a", "type": "奶", "amount_ml": 200},
                                   {"id": "b", "type": "奶", "amount_ml": 180, "_deleted_at": "test"}]
    result = run(repo, Command(action="QUERY", entity="FEEDING", selector=Selector(metric="amount_ml", aggregate="sum")))
    assert "为200" in result and "380" not in result


def test_recognizes_development_synonyms_without_merging_records(repo):
    with repo.transaction() as data:
        data["development_milestones"] = [{"id": "a", "skill": "独立走"}, {"id": "b", "skill": "独立行走"}]
    answer = run(repo, Command(action="QUERY", entity="DEVELOPMENT", selector=Selector(name="走路")))
    assert "找到2条" in answer


def test_public_router_uses_new_engine(monkeypatch):
    import router
    monkeypatch.setattr("pending.get_pending_action", lambda *_: None)
    call = Mock(return_value="新版预览")
    monkeypatch.setattr(router, "handle_request", call)
    assert router.route_request("补日期", "web:test", request_id="m1", actor_name="妈妈") == "新版预览"
    call.assert_called_once_with("补日期", "web:test", request_id="m1", actor_name="妈妈")


def test_legacy_invalid_date_cannot_win_latest(repo):
    with repo.transaction() as data:
        data["development_milestones"] = [
            {"id": "a", "skill": "扶站", "date": "2026-08-01"},
            {"id": "b", "skill": "独立走", "date": "未知"}]
    answer = run(repo, Command(action="QUERY", entity="DEVELOPMENT", selector=Selector(latest=True)))
    assert "找到1条" in answer and "2026-08-01" in answer
    assert "不能确定其先后" in answer


def test_feishu_unauthorized_never_calls_router(monkeypatch):
    import feishu_bot
    from types import SimpleNamespace
    monkeypatch.setattr(feishu_bot, "allowed", lambda *_: False)
    call = Mock()
    monkeypatch.setattr(feishu_bot, "route_request", call)
    monkeypatch.setattr(feishu_bot, "reply_text", Mock())
    event = SimpleNamespace(message=SimpleNamespace(chat_id="untrusted", message_id="x"),
                            sender=SimpleNamespace(sender_type="user", sender_id=SimpleNamespace(open_id="stranger")))
    feishu_bot.process_message(SimpleNamespace(event=event))
    call.assert_not_called()
