"""Small, traceable rotation of excerpts. No invented developmental assessment."""
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "knowledge" / "healthy_parenting_guide_0_3.pdf"
TIPS = [
    ("回应宝宝的信号", "养育人要了解各年龄段婴幼儿身心发展特点，在养育照护中应关注婴幼儿的表情、声音、动作和情绪等表现，理解其所发出的信号和表达的需求，及时给予恰当、积极的回应。"),
    ("留出自由探索的机会", "在保证安全的前提下，养育人要为婴幼儿提供自由玩耍的机会，鼓励儿童自由探索，引导婴幼儿发展解决问题的能力和创造力。"),
    ("在日常互动中陪伴", "养育人应充分参与对婴幼儿的养育照护，提供高质量的亲子陪伴与互动，共同感受成长的快乐，建立融洽的亲子关系。"),
    ("学习发生在日常生活里", "在日常养育过程中，婴幼儿通过模仿、重复、尝试等，发展运动、认知、语言、情感和社会适应等各方面能力。"),
    ("让照护成为学习机会", "养育人要将早期学习融入婴幼儿养育照护的每个环节，充分利用家庭和社会资源，为婴幼儿提供丰富的早期学习机会。"),
    ("准备合适的活动空间", "同时，要为婴幼儿提供整洁、安全、有趣的活动空间，有适合其年龄的玩具、图书和生活用品。"),
    ("理解情绪", "养育人要帮助儿童识别自己和他人的情绪，适时建立合理规则，发展儿童的自我调节能力。"),
]


@lru_cache(maxsize=4)
def source_text(path, mtime):
    from pypdf import PdfReader
    return re.sub(r"\s+", "", PdfReader(path).pages[1].extract_text() or "")


def builtin_tip(day):
    index = date.fromisoformat(day).toordinal() % len(TIPS)
    title, excerpt = TIPS[index]
    if not SOURCE.exists() or re.sub(r"\s+", "", excerpt) not in source_text(str(SOURCE), SOURCE.stat().st_mtime_ns):
        raise ValueError("早教知识来源缺失或摘录与原文不一致，本次未发送。")
    return (f"每日早教小知识 · {day}\n{title}\n\n{excerpt}\n\n"
            f"来源：{SOURCE.name} 第2页。\n通用亲子养育原则，非个体发育评估；当前7条核对过的摘录按日轮换。")


def daily_tip(day):
    from family_features.book_tips import private_book_tip
    body, status = private_book_tip(day)
    if body:
        return body
    fallback = builtin_tip(day)
    if status != "没有私有书籍":
        fallback += "\n本次使用原指南摘录：" + status + "。"
    return fallback
