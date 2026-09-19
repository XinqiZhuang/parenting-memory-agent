import os
import tempfile

import audit


def test_record_and_read_audit_events():

    original_file = audit.AUDIT_FILE

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            audit.AUDIT_FILE = os.path.join(
                temp_dir,
                "audit_log.jsonl"
            )

            first_result = (
                audit.record_audit_event(
                    message_id="message-1",
                    chat_id="family-group",
                    actor_id="mother",
                    actor_name="妈妈",
                    actor_role="mother",
                    request_text="记录宝宝第一次走路",
                    response_text="记录成功",
                    status="SUCCESS"
                )
            )

            second_result = (
                audit.record_audit_event(
                    message_id="message-2",
                    chat_id="family-group",
                    actor_id="father",
                    request_text="查询最近一次大运动",
                    response_text="最近一次是独立行走",
                    status="SUCCESS"
                )
            )

            assert first_result is True
            assert second_result is True

            events = audit.read_audit_events()

            assert audit.has_audit_event(
                "message-1"
            ) is True

            assert audit.has_audit_event(
                "message-2"
            ) is True

            assert audit.has_audit_event(
                "message-not-found"
            ) is False

            assert len(events) == 2

            assert (
                events[0]["actor_id"]
                == "mother"
            )

            assert (
                events[1]["actor_id"]
                == "father"
            )

            latest_event = (
                audit.read_audit_events(
                    limit=1
                )
            )

            assert len(latest_event) == 1

            assert (
                latest_event[0]["message_id"]
                == "message-2"
            )

            assert (
                events[0]["actor_name"]
                == "妈妈"
            )

            assert (
                events[0]["actor_role"]
                == "mother"
            )

    finally:
        audit.AUDIT_FILE = original_file