from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event
from unittest.mock import Mock

import pytest

from family_features.records import browse_records, daily_summary, export_csv
from family_features.settings import PushSettings, save_settings, load_settings
from family_features.scheduler import run_due, read_state, due_jobs
from family_features.transport import SendRejected
from family_features.tips import daily_tip, TIPS


def enable(**changes):
    settings = PushSettings(chat_id="test-group", summary_enabled=True, **changes)
    return save_settings(settings, 0)


def test_summary_counts_only_confirmed_live_day_records():
    data = {"feeding_records": [{"date":"2026-09-20","type":"奶","amount_ml":180},
        {"date":"2026-09-20","type":"奶","amount_ml":200}, {"type":"奶","amount_ml":100},
        {"date":"2026-09-19","type":"奶","amount_ml":200},
        {"date":"2026-09-20","amount_ml":90,"_deleted_at":"x"}],
        "learning_activities": [{"date":"2026-09-20","activity":"套杯","duration_minutes":10},
                                {"date":"2026-09-20","activity":"套杯","duration_minutes":10}]}
    text = daily_summary(data, "2026-09-20")
    assert "380毫升" in text and "20分钟" in text and "可能重复" in text and "1条历史记录" in text
    assert "500" not in text


def test_browser_missing_dates_filters_and_export():
    data = {"memories": [{"event":"散步","date":"2026-09-20"}, {"event":"老照片"},
                          {"event":"已删除","_deleted_at":"x"}, {"event":"错误日期","date":"2026-99-99"}]}
    assert len(browse_records(data)) == 3
    assert len(browse_records(data, start="2026-09-21", include_missing=False)) == 0
    assert len(browse_records(data, missing_only=True)) == 2
    assert len(browse_records(data, keyword="散步")) == 1
    assert export_csv(browse_records(data)).startswith(b"\xef\xbb\xbf")


def test_empty_summary_does_not_assert_no_activity():
    assert "没有已确认的记录" in daily_summary({}, "2026-09-20")


def test_all_tips_match_the_actual_pdf():
    from datetime import date, timedelta
    for offset in range(len(TIPS)):
        assert "第2页" in daily_tip((date(2026,9,20) + timedelta(days=offset)).isoformat())


def test_timezone_due_window_and_previous_day():
    settings = PushSettings(chat_id="test-group", summary_enabled=True, summary_time="00:30", summary_previous_day=True)
    now = datetime(2026,9,20,16,30,tzinfo=timezone.utc)
    assert list(due_jobs(settings, now)) == [("summary","2026-09-20","2026-09-21")]
    assert list(due_jobs(settings, datetime(2026,9,20,16,0,tzinfo=timezone.utc))) == []
    assert list(due_jobs(settings, datetime(2026,9,20,20,0,tzinfo=timezone.utc))) == []


def test_disabled_default_never_sends():
    sender = Mock()
    assert run_due(sender=sender) == []
    sender.assert_not_called()


def test_restart_does_not_resend_success():
    enable()
    sender = Mock(return_value="om_1")
    now = datetime(2026,9,20,13,0,tzinfo=timezone.utc)
    assert run_due(now, sender, lambda *_:"日报") == [("summary","sent")]
    assert run_due(now, sender, lambda *_:"changed") == [("summary","sent")]
    sender.assert_called_once()
    assert list(read_state()["runs"].values())[0]["message_id"] == "om_1"


def test_ambiguous_send_never_retries_automatically():
    enable()
    sender = Mock(side_effect=TimeoutError)
    now = datetime(2026,9,20,13,0,tzinfo=timezone.utc)
    assert run_due(now,sender,lambda *_:"日报")[0][1] == "uncertain"
    run_due(now,sender,lambda *_:"日报")
    sender.assert_called_once()


def test_two_workers_send_once():
    enable()
    now = datetime(2026,9,20,13,0,tzinfo=timezone.utc)
    entered, release = Event(), Event()
    sender = Mock(return_value="message")
    def body(*_):
        entered.set()
        assert release.wait(5)
        return "日报"
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(run_due,now,sender,body)
        assert entered.wait(5)
        second = pool.submit(run_due,now,sender,body).result()
        assert second[0][1] == "busy"
        release.set()
        assert first.result()[0][1] == "sent"
    sender.assert_called_once()


def test_pause_during_generation_stops_delivery():
    enable()
    sender = Mock()
    def body(*_):
        current = load_settings()
        save_settings(current.model_copy(update={"summary_enabled":False}),current.revision)
        return "日报"
    result=run_due(datetime(2026,9,20,13,0,tzinfo=timezone.utc),sender,body)
    assert result[0][1] == "cancelled"
    sender.assert_not_called()


def test_failure_is_visible_and_backoff_applies():
    enable()
    sender=Mock(side_effect=SendRejected("permission"))
    now=datetime(2026,9,20,13,0,tzinfo=timezone.utc)
    assert run_due(now,sender,lambda *_:"日报")[0][1] == "failed"
    run_due(now,sender,lambda *_:"日报")
    sender.assert_called_once()
    assert "permission" in list(read_state()["runs"].values())[0]["error"]


def test_settings_reject_unapproved_group_and_stale_revision():
    with pytest.raises(ValueError):
        save_settings(PushSettings(chat_id="other",summary_enabled=True),0)
    enable()
    with pytest.raises(ValueError):
        save_settings(PushSettings(chat_id="test-group"),0)


@pytest.mark.parametrize("value", ["24:00","9:00","21:60","bad"])
def test_bad_schedule_time(value):
    with pytest.raises(ValueError):
        PushSettings(summary_time=value)


def test_expired_preparation_cannot_later_send_twice():
    from family_features.scheduler import state_path
    from agent_v2.store import atomic_write, read_json, file_lock
    enable()
    now=datetime(2026,9,20,13,0,tzinfo=timezone.utc)
    entered,release=Event(),Event()
    sender=Mock(return_value='om_once')
    def stalled(*_):
        entered.set(); assert release.wait(5)
        return 'old body'
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(run_due,now,sender,stalled)
        assert entered.wait(5)
        path=state_path()
        with file_lock(path):
            state=read_json(path)
            next(iter(state['runs'].values()))['updated']=0
            atomic_write(path,state)
        assert run_due(now,sender,lambda *_:'fresh body')[0][1]=='sent'
        release.set()
        assert first.result()[0][1]=='superseded'
    sender.assert_called_once()
    assert sender.call_args.args[1]=='fresh body'


def test_uncertain_receipt_requires_explicit_resolution():
    from family_features.scheduler import resolve_delivery
    enable()
    now=datetime(2026,9,20,13,0,tzinfo=timezone.utc)
    sender=Mock(side_effect=TimeoutError)
    run_due(now,sender,lambda *_:'日报')
    key,run=next(iter(read_state()['runs'].items()))
    with pytest.raises(ValueError):
        resolve_delivery(key,True,0)
    resolve_delivery(key,True,run['updated'])
    assert run_due(now,sender,lambda *_:'日报')[0][1]=='sent'
    sender.assert_called_once()
