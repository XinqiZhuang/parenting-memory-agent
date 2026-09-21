import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, model_validator

from agent_v2.store import atomic_write, file_lock, read_json
from storage import data_path


class PushSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    revision: int = 0
    chat_id: str = ""
    timezone: str = "Asia/Shanghai"
    summary_enabled: bool = False
    summary_time: str = "21:00"
    summary_previous_day: bool = False
    tip_enabled: bool = False
    tip_time: str = "09:00"
    catchup_minutes: int = 120

    @model_validator(mode="after")
    def check(self):
        ZoneInfo(self.timezone)
        for value in (self.summary_time, self.tip_time):
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
                raise ValueError("发送时间必须为HH:MM。")
        if not 1 <= self.catchup_minutes <= 720:
            raise ValueError("补发窗口必须在1到720分钟。")
        if (self.summary_enabled or self.tip_enabled) and not self.chat_id:
            raise ValueError("请先填写接收推送的群chat_id。")
        return self


def load_settings():
    path = data_path("push_settings.json")
    with file_lock(path):
        return PushSettings.model_validate(read_json(path)) if path.exists() else PushSettings(chat_id=os.getenv("FEISHU_PUSH_CHAT_ID", ""))


def family_now():
    return datetime.now(ZoneInfo(load_settings().timezone))


def allowed_push_chat(chat_id):
    allowed = {s.strip() for s in os.getenv("FEISHU_ALLOWED_CHAT_IDS", "").split(",") if s.strip()}
    return bool(chat_id) and chat_id in allowed


def save_settings(settings, expected_revision):
    if settings.chat_id and not allowed_push_chat(settings.chat_id):
        raise ValueError("接收群必须在FEISHU_ALLOWED_CHAT_IDS中。")
    path = data_path("push_settings.json")
    with file_lock(path):
        current = PushSettings.model_validate(read_json(path)) if path.exists() else PushSettings()
        if current.revision != expected_revision:
            raise ValueError("推送配置已被另一页面修改，请刷新后重试。")
        updated = settings.model_copy(update={"revision": current.revision + 1})
        atomic_write(path, updated.model_dump())
    return updated
