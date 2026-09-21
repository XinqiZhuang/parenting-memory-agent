"""One-host durable outbox. Ambiguous deliveries require review, never blind retry."""
import copy
import time
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5
from zoneinfo import ZoneInfo

from agent_v2.service import default_repository
from agent_v2.store import atomic_write, file_lock, read_json
from family_features.records import daily_summary
from family_features.settings import load_settings, allowed_push_chat
from family_features.tips import daily_tip
from family_features.transport import send_text, SendRejected
from storage import data_path


def state_path():
    return data_path("push_state.json")


def read_state():
    path = state_path()
    with file_lock(path):
        return read_json(path) if path.exists() else {"runs": {}, "heartbeat": ""}


def heartbeat():
    path = state_path()
    with file_lock(path):
        state = read_json(path) if path.exists() else {"runs": {}}
        state["heartbeat"] = datetime.now(timezone.utc).isoformat()
        atomic_write(path, state)


def build_body(kind, day, repository=None):
    if kind == "summary":
        return daily_summary((repository or default_repository()).snapshot(), day)
    if kind == "tip":
        return daily_tip(day)
    raise ValueError("未知推送类型")


def due_jobs(settings, now):
    if now.tzinfo is None:
        raise ValueError("调度时间必须包含时区。")
    local = now.astimezone(ZoneInfo(settings.timezone))
    for kind in ("summary", "tip"):
        if not getattr(settings, kind + "_enabled"):
            continue
        hour, minute = map(int, getattr(settings, kind + "_time").split(":"))
        scheduled = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        lag = (local - scheduled).total_seconds()
        if 0 <= lag <= settings.catchup_minutes * 60:
            target_day = local.date() - timedelta(days=1 if kind == "summary" and settings.summary_previous_day else 0)
            yield kind, target_day.isoformat(), local.date().isoformat()


def deliver(kind, day, delivery_day, settings, sender=None, builder=None):
    if not allowed_push_chat(settings.chat_id):
        raise ValueError("接收群必须在FEISHU_ALLOWED_CHAT_IDS中。")
    key = f"{settings.chat_id}:{kind}:{delivery_day}"
    path = state_path()
    now = time.time()
    with file_lock(path):
        state = read_json(path) if path.exists() else {"runs": {}}
        runs = state.setdefault("runs", {})
        old = runs.get(key, {})
        status = old.get("status")
        if status in {"sent", "uncertain", "cancelled"}:
            return status
        if status == "sending":
            if now - old.get("updated", 0) > 300:
                old.update(status="uncertain", error="发送进程中断或超时，请人工核对群消息。", updated=now)
                atomic_write(path, state)
                return "uncertain"
            return "busy"
        if status == "preparing" and now - old.get("updated", 0) < 300:
            return "busy"
        if old.get("attempts", 0) >= 3 or now < old.get("retry_after", 0):
            return "failed"
        run = dict(old, status="preparing", updated=now, attempts=old.get("attempts", 0) + 1,
                   kind=kind, day=day, delivery_day=delivery_day, chat_id=settings.chat_id,
                   owner=uuid4().hex, token=str(uuid5(NAMESPACE_URL, key)))
        runs[key] = run
        atomic_write(path, state)
    try:
        body = run.get("body") or (builder or build_body)(kind, day)
        if not body or len(body.encode("utf-8")) > 24000:
            raise ValueError("推送正文为空或过长。")
    except Exception as exc:
        _update(key, owner=run["owner"], status="failed", error=type(exc).__name__, retry_after=time.time() + 300)
        return "failed"
    # Reload configuration just before sending: a user may have paused the task.
    current = load_settings()
    if current.chat_id != settings.chat_id or not getattr(current, kind + "_enabled"):
        _update(key, owner=run["owner"], status="cancelled", error="发送前配置已暂停或接收群已变化。")
        return "cancelled"
    if not _update(key, owner=run["owner"], status="sending", body=body, error=""):
        return "superseded"
    try:
        message_id = (sender or send_text)(settings.chat_id, body, run["token"])
    except SendRejected as exc:
        _update(key, owner=run["owner"], status="failed", error=str(exc), retry_after=time.time() + 300)
        return "failed"
    except Exception as exc:
        # The server may have accepted the message before our connection failed.
        _update(key, owner=run["owner"], status="uncertain", error=f"{type(exc).__name__}：送达状态不明，请人工核对。")
        return "uncertain"
    _update(key, owner=run["owner"], status="sent", message_id=message_id, error="")
    return "sent"


def _update(key, owner=None, **changes):
    path = state_path()
    with file_lock(path):
        state = read_json(path)
        if owner and state["runs"][key].get("owner") != owner:
            return False
        state["runs"][key].update(changes, updated=time.time())
        atomic_write(path, state)
        return True


def run_due(now=None, sender=None, builder=None):
    heartbeat()
    settings = load_settings()
    now = now or datetime.now(timezone.utc)
    results = []
    for kind, day, delivery_day in due_jobs(settings, now):
        results.append((kind, deliver(kind, day, delivery_day, settings, sender, builder)))
    return results


def resolve_delivery(key, delivered, expected_updated):
    """Only after an authorized user checked the actual group; no message is sent here."""
    path = state_path()
    with file_lock(path):
        state = read_json(path)
        run = state["runs"].get(key)
        if not run or run.get("status") not in {"uncertain", "failed"} or run.get("updated") != expected_updated:
            raise ValueError("该任务状态已改变，或不需要人工处理。请刷新。")
        if delivered:
            run.update(status="sent", manual_resolution="已人工核对送达", updated=time.time(), error="")
        else:
            run.update(status="failed", manual_resolution="已人工核对未送达，允许重试", updated=time.time(),
                       attempts=0, retry_after=0, error="等待下一次到期检查；超出补发窗口时不自动发送。")
        atomic_write(path, state)
