from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from family_features import book_tips
from family_features.tips import daily_tip


QUOTE = "在亲子阅读时，家长可以先观察孩子正在关注的画面，再用简短的话回应孩子的指认，让阅读成为相互交流的机会。"
CHUNK = {"file": "私有/亲子互动.pdf", "page": 12, "text": QUOTE}


@pytest.fixture(autouse=True)
def private_sources(monkeypatch):
    book_tips.select_excerpt.cache_clear()
    monkeypatch.setattr(book_tips, "private_knowledge_chunks", lambda: [dict(CHUNK)])
    yield
    book_tips.select_excerpt.cache_clear()


def choose(monkeypatch, value=None):
    call = Mock(return_value=value if value is not None else {"candidate_id": 1, "excerpt": QUOTE})
    monkeypatch.setattr(book_tips, "model_choice", call)
    return call


def test_private_tip_retains_exact_quote_and_pdf_citation(monkeypatch):
    call = choose(monkeypatch)
    body = daily_tip("2026-09-21")
    assert QUOTE in body and "私有/亲子互动.pdf 第12页" in body
    assert "本次使用原指南" not in body
    call.assert_called_once()


@pytest.mark.parametrize("value", [
    {"candidate_id": 99, "excerpt": QUOTE},
    {"candidate_id": 1, "excerpt": QUOTE.replace("可以", "必须")},
    {"candidate_id": 1, "excerpt": QUOTE[:-1]},
    {"candidate_id": "1", "excerpt": QUOTE},
    {"candidate_id": 1, "excerpt": QUOTE, "invented": "not permitted"},
    {"candidate_id": None, "excerpt": ""},
])
def test_unverifiable_model_result_uses_checked_guide(monkeypatch, value):
    choose(monkeypatch, value)
    body = daily_tip("2026-09-21")
    assert "本次使用原指南摘录" in body and "healthy_parenting_guide_0_3.pdf 第2页" in body
    assert "私有/亲子互动.pdf" not in body


def test_no_books_does_not_call_model(monkeypatch):
    monkeypatch.setattr(book_tips, "private_knowledge_chunks", lambda: [])
    call = choose(monkeypatch)
    assert "第2页" in daily_tip("2026-09-21")
    call.assert_not_called()


def test_api_failure_does_not_expose_error_or_invent_tip(monkeypatch):
    call = choose(monkeypatch)
    call.side_effect = TimeoutError("private token must not leak")
    body = daily_tip("2026-09-21")
    assert "本次使用原指南" in body and "private token" not in body


def test_previews_cache_selection_without_marking_anything_sent(monkeypatch):
    from family_features.scheduler import read_state
    call = choose(monkeypatch)
    before = read_state()
    assert daily_tip("2026-09-21") == daily_tip("2026-09-21")
    call.assert_called_once()
    assert read_state() == before


def test_recent_sent_or_uncertain_excerpt_is_excluded(monkeypatch):
    body = f"title\n\n{QUOTE}\n\n来源：book"
    monkeypatch.setattr("family_features.scheduler.read_state", lambda: {"runs": {
        "sent": {"kind": "tip", "status": "sent", "day": "2026-09-20", "body": body},
        "failed": {"kind": "tip", "status": "failed", "day": "2026-09-20", "body": "x\n\n失败项\n\ny"},
        "uncertain": {"kind": "tip", "status": "uncertain", "day": "2026-09-19", "body": "x\n\n未知项\n\ny"},
    }})
    recent = book_tips.recent_quotes("2026-09-21")
    assert book_tips.compact(QUOTE) in recent and "未知项" in recent and "失败项" not in recent
    call = choose(monkeypatch)
    assert "近期未推送" in daily_tip("2026-09-21")
    call.assert_not_called()


def test_expired_quotes_can_return_after_rotation_window(monkeypatch):
    monkeypatch.setattr("family_features.scheduler.read_state", lambda: {"runs": {
        "old": {"kind": "tip", "status": "sent", "day": "2026-07-01", "body": f"title\n\n{QUOTE}\n\nsource"}}})
    assert book_tips.recent_quotes("2026-09-21") == []


def test_book_removal_during_selection_cancels_its_quote(monkeypatch):
    def remove(*args):
        monkeypatch.setattr(book_tips, "private_knowledge_chunks", lambda: [])
        return {"candidate_id": 1, "excerpt": QUOTE}
    monkeypatch.setattr(book_tips, "model_choice", remove)
    assert "本次使用原指南" in daily_tip("2026-09-21")


def test_excerpt_cannot_drop_mid_sentence_conditions():
    source = dict(CHUNK, candidate_id=1, text="如果孩子愿意参与，" + QUOTE)
    with pytest.raises(ValueError, match="中途"):
        book_tips.validate_choice({"candidate_id": 1, "excerpt": QUOTE}, [source])


def test_book_rotation_and_medical_filter():
    chunks = [dict(CHUNK, file=f"私有/{name}.pdf", text=QUOTE + f"示例{name}。") for name in ("A", "B", "C")]
    chunks[1]["text"] = QUOTE + "药物剂量需要核对。"
    first = book_tips.candidates_for_day("2026-09-21", chunks, [])
    second = book_tips.candidates_for_day("2026-09-22", chunks, [])
    assert {c["file"] for c in first} == {"私有/A.pdf", "私有/C.pdf"}
    assert first[0]["file"] != second[0]["file"]


def test_scheduler_uses_private_excerpt_and_does_not_resend(monkeypatch):
    from family_features.scheduler import run_due
    from family_features.settings import PushSettings, save_settings
    save_settings(PushSettings(chat_id="test-group", tip_enabled=True), 0)
    choose(monkeypatch)
    sender = Mock(return_value="fake_message_id")
    now = datetime(2026, 9, 21, 1, 0, tzinfo=timezone.utc)
    assert run_due(now, sender=sender) == [("tip", "sent")]
    assert QUOTE in sender.call_args.args[1]
    assert run_due(now, sender=sender) == [("tip", "sent")]
    sender.assert_called_once()


def test_plain_txt_does_not_get_fake_page_number(monkeypatch):
    monkeypatch.setattr(book_tips, "private_knowledge_chunks", lambda: [dict(CHUNK, file="私有/book.txt", page=None)])
    choose(monkeypatch)
    body = daily_tip("2026-09-21")
    assert "TXT原文" in body and "第None页" not in body


def test_feature_checker_stays_offline_even_with_private_books(monkeypatch, capsys):
    import verify_features
    monkeypatch.setattr("sys.argv", ["verify_features.py"])
    call = choose(monkeypatch)
    verify_features.main()
    call.assert_not_called()
    assert "尚未调用模型" in capsys.readouterr().out


def test_validated_quote_restores_source_word_spacing():
    source_text = QUOTE.replace("亲子阅读", "亲子 阅读")
    selected = book_tips.validate_choice({"candidate_id": 1, "excerpt": QUOTE},
                                        [dict(CHUNK, candidate_id=1, text=source_text)])
    assert selected["excerpt"] == source_text
