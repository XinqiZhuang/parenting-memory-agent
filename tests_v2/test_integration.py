import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent_v2.schema import Command, Selector
from agent_v2.store import Repository, atomic_write
from agent_v2.service import handle_request


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path / "data.json")


def run(repo, command=None, text="请求", who="feishu:group:mother", parser=None):
    return handle_request(text, who, repository=repo, parser=parser or (lambda *_: command))


def test_migration_preserves_all_existing_fields_and_duplicate_records(repo):
    sample = {"profile": {"name": "测试"}, "custom": {"preserve": True},
              "learning_activities": [{"activity": "套杯"}, {"activity": "套杯"}],
              "memories": [{"id": "original-photo-id", "event": "站立", "photos": ["data/uploads/photo.jpg"]}]}
    atomic_write(repo.path, sample)
    data = repo.snapshot()
    assert data["custom"] == sample["custom"]
    assert len(data["learning_activities"]) == 2
    assert data["learning_activities"][0]["id"] != data["learning_activities"][1]["id"]
    assert data["memories"] == sample["memories"]
    backup = list(repo.path.parent.glob("*.before_v2.*.json"))[0]
    assert json.loads(backup.read_text(encoding="utf-8")) == sample


def test_corrupted_file_is_not_replaced(repo):
    repo.path.write_text('{"broken":', encoding="utf-8")
    result = run(repo, Command(action="QUERY", entity="MEMORY"))
    assert "失败" in result
    assert repo.path.read_text(encoding="utf-8") == '{"broken":'


def test_legacy_read_modify_save_rejects_stale_snapshot(tmp_path, monkeypatch):
    import baby
    path = tmp_path / "versioned.json"
    monkeypatch.setattr(baby, "DATA_FILE", path)
    atomic_write(path, {"profile": {}, "memories": []})
    first = baby.load_baby()
    second = baby.load_baby()
    first["memories"].append({"event": "A"})
    baby.save_baby(first)
    second["memories"].append({"event": "B"})
    with pytest.raises(RuntimeError, match="其他人"):
        baby.save_baby(second)
    assert baby.load_baby()["memories"] == [{"event": "A"}]


def test_raw_dict_cannot_replace_v2_document(repo, monkeypatch):
    import baby
    repo.snapshot()
    monkeypatch.setattr(baby, "DATA_FILE", repo.path)
    with pytest.raises(RuntimeError, match="无版本号"):
        baby.save_baby({"profile": {}})


@pytest.mark.parametrize("action", ["ANALYZE", "KNOWLEDGE"])
def test_knowledge_routes_readonly(repo, monkeypatch, action):
    with repo.transaction() as data:
        data["learning_activities"].append({"id": "a", "activity": "套杯", "category": "fine_motor"})
    mock = Mock(return_value="根据记录，该活动的分类为精细动作。")
    monkeypatch.setattr("agent_v2.knowledge.evidence_answer", mock)
    result = run(repo, Command(action=action, entity="ACTIVITY"), text="这个活动是精细动作训练吗")
    assert "精细动作" in result
    assert mock.call_count == 1
    assert not repo.snapshot()["_agent_v2"]["events"]


def test_analysis_failure_never_writes(repo, monkeypatch):
    monkeypatch.setattr("agent_v2.knowledge.evidence_answer", Mock(side_effect=TimeoutError))
    result = run(repo, Command(action="KNOWLEDGE"), text="如何安全玩耍")
    assert "暂时不可用" in result
    assert repo.snapshot()["_agent_v2"]["events"] == []


def test_family_audit_only_same_group(repo):
    for who in ("feishu:group:mother", "feishu:group:father", "feishu:other:outsider"):
        run(repo, Command(action="ADD", entity="MEMORY", values={"event": who}), who=who)
        run(repo, text="确认", who=who)
    response = run(repo, Command(action="AUDIT", selector=Selector(audit_scope="family")))
    assert "father" in response and "mother" in response
    assert "outsider" not in response


def test_another_query_inherits_entity_with_missing_date(repo):
    with repo.transaction() as data:
        data["learning_activities"] = [
            {"id": "a", "activity": "套杯", "date": "2026-08-27"},
            {"id": "b", "activity": "套杯"}]
    run(repo, Command(action="QUERY", entity="ACTIVITY", selector=Selector(name="套杯")))
    # Inherit context without letting a model manufacture an ID.
    cmd = Command(action="QUERY", selector=Selector(reference="another", missing_field="date"))
    response = run(repo, cmd, text="另外一条呢")
    assert "找到1条" in response and "日期未记录" in response


@pytest.mark.parametrize("aggregate,expected", [("sum", "380"), ("average", "190"), ("count", "3条")])
def test_statistics_use_records_only(repo, aggregate, expected):
    with repo.transaction() as data:
        data["feeding_records"] = [{"id": "a", "type": "奶", "amount_ml": 180},
                                   {"id": "b", "type": "奶", "amount_ml": 200},
                                   {"id": "c", "type": "奶"}]
    sel = Selector(aggregate=aggregate, metric="amount_ml" if aggregate != "count" else "")
    assert expected in run(repo, Command(action="QUERY", entity="FEEDING", selector=sel))


def test_missing_all_dates_not_fake_latest(repo):
    with repo.transaction() as data:
        data["development_milestones"] = [{"id": "x", "skill": "爬", "age_months": 7}]
    result = run(repo, Command(action="QUERY", entity="DEVELOPMENT", selector=Selector(latest=True)))
    assert "无法确定" in result


def test_query_date_range_and_category_intersection(repo):
    with repo.transaction() as data:
        data["learning_activities"] = [
            {"id": "a", "activity": "套杯", "category": "fine_motor", "date": "2026-08-27"},
            {"id": "b", "activity": "套杯", "category": "cognitive", "date": "2026-08-30"},
            {"id": "c", "activity": "套杯", "category": "fine_motor", "date": "2026-08-31"}]
    selector = Selector(name="套杯", category="fine_motor", start_date="2026-08-28", end_date="2026-09-01")
    answer = run(repo, Command(action="QUERY", entity="ACTIVITY", selector=selector))
    assert "找到1条" in answer and "2026-08-31" in answer


def test_photo_soft_delete_retains_file(repo, tmp_path):
    photo = tmp_path / "picture.jpg"
    photo.write_bytes(b"fake test image")
    with repo.transaction() as data:
        data["memories"] = [{"id": "p", "event": "站立", "photos": [str(photo)]}]
    run(repo, Command(action="DELETE", entity="PHOTO", selector=Selector(id="p")))
    run(repo, text="确认")
    assert photo.read_bytes() == b"fake test image"
    assert "没有找到" in run(repo, Command(action="QUERY", entity="PHOTO"))
    run(repo, Command(action="UNDO"))
    run(repo, text="确认")
    assert "找到1条" in run(repo, Command(action="QUERY", entity="PHOTO"))


def test_feishu_deny_unknown_member(monkeypatch):
    import feishu_bot
    monkeypatch.delenv("FEISHU_ALLOWED_CHAT_IDS", raising=False)
    monkeypatch.delenv("FEISHU_ALLOWED_USER_IDS", raising=False)
    monkeypatch.setattr(feishu_bot, "load_family_members", lambda: {"mother": {}})
    assert feishu_bot.allowed("group", "mother")
    assert not feishu_bot.allowed("group", "stranger")
    monkeypatch.setenv("FEISHU_ALLOWED_CHAT_IDS", "group")
    assert feishu_bot.allowed("group", "father")
    assert not feishu_bot.allowed("other", "mother")


def test_feishu_passes_raw_text_identity_and_message_id(monkeypatch):
    import feishu_bot
    monkeypatch.setattr(feishu_bot, "allowed", lambda *_: True)
    monkeypatch.setattr(feishu_bot, "get_family_member", lambda _: {"display_name": "妈妈"})
    route = Mock(return_value="预览")
    monkeypatch.setattr(feishu_bot, "route_request", route)
    monkeypatch.setattr(feishu_bot, "reply_text", Mock(return_value=True))
    data = SimpleNamespace(event=SimpleNamespace(
        message=SimpleNamespace(chat_id="g", message_id="m", message_type="text", mentions=[SimpleNamespace(key="@_u")],
                                content=json.dumps({"text": "@_u 补日期"})),
        sender=SimpleNamespace(sender_type="user", sender_id=SimpleNamespace(open_id="mother"))))
    feishu_bot.process_message(data)
    route.assert_called_once_with("补日期", context_id="feishu:g:mother", request_id="m", actor_name="妈妈")


def test_new_parser_error_cannot_pollute_data(repo):
    def broken(*_):
        raise ValueError("bad extraction")
    answer = run(repo, text="另外一条补日期", parser=broken)
    assert "没有新增或修改" in answer
    data = repo.snapshot()
    assert data["learning_activities"] == [] and data["memories"] == []
