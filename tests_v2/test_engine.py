import copy
import json
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import get_context

import pytest

from agent_v2.engine import match_records, parse_choice
from agent_v2.schema import Command, Selector, COLLECTIONS
from agent_v2.service import handle_request
from agent_v2.store import Repository, atomic_write


PAYLOADS = {
    "GROWTH": {"weight_kg": 10.5, "date": "2026-09-20"},
    "DEVELOPMENT": {"skill": "独立行走", "category": "gross_motor", "date": "2026-09-20"},
    "ACTIVITY": {"activity": "套杯游戏", "category": "cognitive", "duration_minutes": 10},
    "FEEDING": {"type": "奶", "amount_ml": 180, "time": "早上", "date": "2026-09-20"},
    "HEALTH": {"type": "排便", "description": "一次", "date": "2026-09-20"},
    "MEMORY": {"event": "第一次坐飞机", "date": "2026-09-20"},
}


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "domain.json"
    atomic_write(path, {"profile": {"birth_date": "2025-09-01"}})
    return Repository(path)


def request(repo, command=None, text="请求", who="mother", message=None):
    parser = lambda *_: command
    return handle_request(text, who, repository=repo, parser=parser, request_id=message, actor_name=who)


def live(repo, entity):
    return [r for r in repo.snapshot()[COLLECTIONS[entity]] if not r.get("_deleted_at")]


@pytest.mark.parametrize("entity", PAYLOADS)
def test_crud_undo_and_audit_all_entities(repo, entity):
    command = Command(action="ADD", entity=entity, values=PAYLOADS[entity])
    assert "尚未写入" in request(repo, command)
    assert live(repo, entity) == []
    assert "已经记录" in request(repo, text="确认", message="add-confirm")
    record = live(repo, entity)[0]
    result = request(repo, Command(action="QUERY", entity=entity))
    assert "找到1条" in result
    update = Command(action="UPDATE", entity=entity, selector=Selector(id=record["id"]), values={"date": "2026-09-19"})
    assert "尚未写入" in request(repo, update)
    assert "修改成功" in request(repo, text="确认")
    assert live(repo, entity)[0]["date"] == "2026-09-19"
    assert "尚未写入" in request(repo, Command(action="DELETE", entity=entity, selector=Selector(id=record["id"])))
    assert "已删除" in request(repo, text="确认删除")
    assert live(repo, entity) == []
    assert "尚未写入" in request(repo, Command(action="UNDO"))
    assert "已撤销" in request(repo, text="确认")
    assert live(repo, entity)[0]["date"] == "2026-09-19"
    logs = request(repo, Command(action="AUDIT"))
    assert "UPDATE" in logs and "DELETE" in logs and "UNDO" in logs
    # Check the event-date diff, not the wall-clock audit timestamp.
    original_date = PAYLOADS[entity].get("date", "未记录")
    update_log = next(line for line in logs.splitlines() if " | UPDATE | " in line)
    assert f"日期：{original_date} → 2026-09-19" in update_log


def seed_activities(repo, extra=False):
    with repo.transaction() as data:
        data["learning_activities"] = [
            {"id": "a", "activity": "套杯游戏", "category": "fine_motor", "date": "2026-08-27", "duration_minutes": 10},
            {"id": "b", "activity": "套杯游戏", "category": "cognitive", "duration_minutes": 10},
        ]
        if extra:
            data["learning_activities"].append({"id": "c", "activity": "套杯游戏", "category": ""})


def test_complete_user_repro_no_duplicate(repo):
    seed_activities(repo)
    request(repo, Command(action="QUERY", entity="ACTIVITY", selector=Selector(name="套杯游戏")))
    command = Command(action="UPDATE", entity="ACTIVITY", selector=Selector(name="套杯游戏", missing_field="date", reference="another"), values={"date": "2026-08-30"})
    assert "日期：未记录 → 2026-08-30" in request(repo, command, text="另外一条套杯游戏的日期是2026-08-30")
    assert "修改成功" in request(repo, text="确认")
    records = live(repo, "ACTIVITY")
    assert len(records) == 2
    assert [r["date"] for r in records] == ["2026-08-27", "2026-08-30"]
    assert repo.snapshot()["memories"] == []


def test_two_missing_dates_ask_number_then_confirm(repo):
    seed_activities(repo, extra=True)
    command = Command(action="UPDATE", entity="ACTIVITY", selector=Selector(name="套杯游戏", missing_field="date"), values={"date": "2026-08-30"})
    assert "找到多条" in request(repo, command)
    assert "日期不会被当成编号" in request(repo, text="2026-08-30")
    assert "尚未写入" in request(repo, text="第一项")
    assert "date" not in live(repo, "ACTIVITY")[1]
    request(repo, text="确认")
    assert live(repo, "ACTIVITY")[1]["date"] == "2026-08-30"
    assert "date" not in live(repo, "ACTIVITY")[2]


def test_new_date_not_used_as_selector_and_no_implicit_preference(repo):
    seed_activities(repo)
    cmd = Command(action="UPDATE", entity="ACTIVITY", selector=Selector(name="套杯游戏"), values={"date": "2026-08-30"})
    assert "找到多条" in request(repo, cmd)
    assert "date" not in live(repo, "ACTIVITY")[1]


def test_context_isolation_and_stale_write_rejection(repo):
    seed_activities(repo)
    def cmd(day):
        return Command(action="UPDATE", entity="ACTIVITY", selector=Selector(id="b"), values={"date": day})
    request(repo, cmd("2026-08-30"), who="mother")
    request(repo, cmd("2026-08-31"), who="father")
    request(repo, text="确认", who="father")
    assert "本次未写入" in request(repo, text="确认", who="mother")
    assert live(repo, "ACTIVITY")[1]["date"] == "2026-08-31"
    assert "尚无" in request(repo, Command(action="AUDIT"), who="mother")
    assert "2026-08-31" in request(repo, Command(action="AUDIT"), who="father")


def test_duplicate_message_receipts_survive_restart(repo):
    command = Command(action="ADD", entity="ACTIVITY", values=PAYLOADS["ACTIVITY"])
    preview = request(repo, command, message="m1")
    assert request(Repository(repo.path), command, message="m1") == preview
    answer = request(repo, text="确认", message="m2")
    assert request(Repository(repo.path), text="确认", message="m2") == answer
    assert len(live(repo, "ACTIVITY")) == 1
    assert len(repo.snapshot()["_agent_v2"]["events"]) == 1
    assert "内容不同" in request(repo, text="删除全部", message="m2")


@pytest.mark.parametrize("text", ["取消", "算了", "不用改了"])
def test_cancel_never_writes(repo, text):
    request(repo, Command(action="ADD", entity="MEMORY", values=PAYLOADS["MEMORY"]))
    assert "取消" in request(repo, text=text)
    assert not live(repo, "MEMORY")


def test_expired_confirmation(repo):
    request(repo, Command(action="ADD", entity="MEMORY", values=PAYLOADS["MEMORY"]))
    with repo.transaction() as data:
        data["_agent_v2"]["contexts"]["mother"]["pending"]["created_at"] = 0
    assert "已过期" in request(repo, text="确认")
    assert not live(repo, "MEMORY")


@pytest.mark.parametrize("entity", PAYLOADS)
def test_not_found_update_never_adds(repo, entity):
    cmd = Command(action="UPDATE", entity=entity, selector=Selector(id="missing"), values={"date": "2026-08-30"})
    assert "没有找到" in request(repo, cmd)
    assert live(repo, entity) == []


def test_no_broad_update(repo):
    seed_activities(repo)
    cmd = Command(action="UPDATE", entity="ACTIVITY", values={"date": "2026-08-30"})
    assert "请说明" in request(repo, cmd)
    assert "date" not in live(repo, "ACTIVITY")[1]


def test_no_confirmation_from_model(repo):
    data = {"action": "ADD", "entity": "ACTIVITY", "values": PAYLOADS["ACTIVITY"], "confirmed": True}
    assert "安全校验" in request(repo, data)
    assert not live(repo, "ACTIVITY")


def test_pending_blocks_unrelated_write(repo):
    request(repo, Command(action="ADD", entity="MEMORY", values=PAYLOADS["MEMORY"]))
    assert "等待确认" in request(repo, Command(action="ADD", entity="ACTIVITY", values=PAYLOADS["ACTIVITY"]), text="新增套杯游戏")
    assert not live(repo, "ACTIVITY")


def test_missing_date_does_not_disappear_from_all_query(repo):
    seed_activities(repo)
    result = request(repo, Command(action="QUERY", entity="ACTIVITY"))
    assert "找到2条" in result and "日期未记录" in result
    result = request(repo, Command(action="QUERY", entity="ACTIVITY", selector=Selector(latest=True)))
    assert "2026-08-27" in result and "不能确定其先后" in result


def test_same_date_tie_not_arbitrary(repo):
    seed_activities(repo)
    with repo.transaction() as data:
        data["learning_activities"][1]["date"] = "2026-08-27"
    answer = request(repo, Command(action="QUERY", entity="ACTIVITY", selector=Selector(latest=True)))
    assert "找到2条" in answer and "同一天" in answer


def test_id_preservation_no_automatic_dedup_and_backup(repo):
    seed_activities(repo)
    first = repo.snapshot()
    second = Repository(repo.path).snapshot()
    assert first == second
    assert list(repo.path.parent.glob("*.before_v2.*.json"))


def test_transaction_rolls_back_on_error(repo):
    before = repo.snapshot()
    with pytest.raises(RuntimeError):
        with repo.transaction() as data:
            data["memories"].append({"event": "should not persist"})
            raise RuntimeError("disk/network failure simulation")
    assert repo.snapshot() == before


def test_thread_confirm_idempotency(repo):
    request(repo, Command(action="ADD", entity="MEMORY", values=PAYLOADS["MEMORY"]))
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: request(repo, text="确认", message="same"), range(6)))
    assert len(set(results)) == 1
    assert len(live(repo, "MEMORY")) == 1


def _increment(path):
    repo = Repository(path)
    for _ in range(4):
        with repo.transaction() as data:
            data["test_counter"] = data.get("test_counter", 0) + 1


def test_cross_process_no_lost_updates(repo):
    ctx = get_context("spawn")
    processes = [ctx.Process(target=_increment, args=(str(repo.path),)) for _ in range(3)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(25)
        assert process.exitcode == 0
    assert repo.snapshot()["test_counter"] == 12


def test_undo_cannot_overwrite_another_actor(repo):
    seed_activities(repo)
    for who, day in (("mother", "2026-08-30"), ("father", "2026-08-31")):
        request(repo, Command(action="UPDATE", entity="ACTIVITY", selector=Selector(id="b"), values={"date": day}), who=who)
        request(repo, text="确认", who=who)
    assert "不能直接撤销" in request(repo, Command(action="UNDO"))


@pytest.mark.parametrize("text,number", [("第2条", 2), ("第二项", 2), ("2", 2), ("我选第二条", 2),
                                         ("2026-08-30", None), ("确认第2条日期2026-08-30", None), ("修改第一次", None)])
def test_choice_only_complete_short_replies(text, number):
    assert parse_choice(text) == number
