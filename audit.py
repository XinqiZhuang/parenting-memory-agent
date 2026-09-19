import json
import os
from datetime import datetime, timezone
from threading import Lock


AUDIT_FILE = "data/audit_log.jsonl"

_audit_lock = Lock()


def record_audit_event(
    *,
    message_id,
    chat_id,
    actor_id,
    request_text,
    actor_name="",
    actor_role="",
    response_text="",
    status="SUCCESS",
    error_message=""
):
    """
    保存一条飞书Agent操作记录。
    """

    event = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": "feishu",
        "message_id": message_id,
        "chat_id": chat_id,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "actor_role": actor_role,
        "request_text": request_text,
        "response_text": response_text,
        "status": status,
        "error_message": error_message
    }

    path = os.fspath(AUDIT_FILE)
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    try:
        with _audit_lock:
            with open(
                path,
                "a",
                encoding="utf-8"
            ) as file:
                file.write(
                    json.dumps(
                        event,
                        ensure_ascii=False
                    )
                )
                file.write("\n")

    except OSError as error:
        print(
            "审计日志写入失败：",
            error
        )
        return False

    return True


def read_audit_events(limit=None):
    """
    读取审计事件。
    limit用于读取最后几条。
    """

    path = os.fspath(AUDIT_FILE)

    if not os.path.exists(path):
        return []

    events = []

    with _audit_lock:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                stripped_line = line.strip()

                if not stripped_line:
                    continue

                try:
                    event = json.loads(
                        stripped_line
                    )

                except json.JSONDecodeError:
                    continue

                events.append(event)

    if limit is None:
        return events

    return events[-limit:]

def has_audit_event(message_id):
    """
    判断一条飞书消息是否已经进入过处理流程。
    """

    if not message_id:
        return False

    events = read_audit_events()

    return any(
        event.get("message_id")
        == message_id
        for event in events
    )