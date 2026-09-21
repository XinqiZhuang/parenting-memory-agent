"""Photo is an attachment; the user's activity description determines its record type."""
import re

from agent_v2.schema import CATEGORIES, validate_values


def suggested_category(text):
    rules = [
        ("cognitive", r"认知|认识?(?:动物|蔬菜|水果|颜色|形状|数字)|配对|分类游戏|拼图"),
        ("fine_motor", r"精细动作|画画|涂鸦|套杯|积木|串珠|手指|用勺"),
        ("gross_motor", r"大运动|走路|独走|行走|爬行|攀爬|踢球|跑步|跳跃"),
        ("language", r"语言|阅读|读绘本|讲故事|学说|儿歌"),
        ("social", r"社交|轮流|分享游戏|角色扮演"),
    ]
    return next((category for category, pattern in rules if re.search(pattern, text)), "")


def photo_record_payload(title, description="", event_date="", *, kind="AUTO", category="AUTO", duration=None, infer=True):
    aliases = {"自动": "AUTO", "学习活动": "ACTIVITY", "活动": "ACTIVITY", "早教": "ACTIVITY",
               "回忆": "MEMORY", "照片回忆": "MEMORY", "PHOTO": "MEMORY"}
    kind = aliases.get(kind, kind)
    category = {v: k for k, v in CATEGORIES.items()}.get(category, category)
    if kind not in {"AUTO", "ACTIVITY", "MEMORY"}:
        raise ValueError("类型请填“学习活动”或“回忆”。")
    if category not in {"AUTO", "", "未知", *CATEGORIES}:
        raise ValueError("分类请填大运动、精细动作、认知、语言或社交。")
    if kind == "MEMORY" and category in CATEGORIES:
        raise ValueError("活动分类需要类型=学习活动；如果要保存生活回忆，请把分类设为自动或未知。")
    text = title + " " + description
    activity_hint = bool(re.search(r"早教|练习|训练|游戏|画画|涂鸦|套杯|阅读|读绘本|认识?(?:动物|蔬菜|水果|颜色|形状|数字)", text))
    if kind == "AUTO":
        kind = "ACTIVITY" if category in CATEGORIES or duration is not None or infer and activity_hint else "MEMORY"
    if category == "AUTO":
        category = suggested_category(text) if infer else ""
    if kind == "MEMORY" and (duration is not None or category in CATEGORIES and not activity_hint):
        # An explicit memory choice is respected; activity-specific metadata cannot be discarded silently.
        if duration is not None:
            raise ValueError("时长属于学习活动，请填写类型=学习活动，或去掉时长。")
    values = {"activity" if kind == "ACTIVITY" else "event": title.strip()}
    if description.strip():
        values["description"] = description.strip()
    if event_date:
        values["date"] = event_date
    if kind == "ACTIVITY":
        if category in CATEGORIES:
            values["category"] = category
        if duration is not None:
            values["duration_minutes"] = duration
    return kind, validate_values(kind, values, adding=True)
