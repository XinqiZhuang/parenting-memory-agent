import json
import os
import re


PENDING_FILE = "data/pending_action.json"


def set_pending_action(action):
    """
    保存等待用户确认的操作。
    """

    os.makedirs(
        os.path.dirname(PENDING_FILE),
        exist_ok=True
    )

    with open(
        PENDING_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            action,
            file,
            ensure_ascii=False,
            indent=4
        )


def get_pending_action():
    """
    读取正在等待用户确认的操作。
    如果没有pending操作,返回None。
    """

    if not os.path.exists(PENDING_FILE):
        return None

    try:
        with open(
            PENDING_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):
        return None


def clear_pending_action():
    """
    完成或取消操作后,清除pending状态。
    """

    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)

def parse_choice_number(user_input):
    """
    从用户输入中提取候选编号。

    支持：
    第2条
    2
    我选第2条
    第二条

    返回从1开始的编号。
    无法识别时返回None。
    """

    # 处理阿拉伯数字
    digit_match = re.search(
        r"第?\s*(\d+)\s*条?",
        user_input
    )

    if digit_match:
        return int(digit_match.group(1))

    # 处理简单中文数字
    chinese_numbers = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10
    }

    chinese_match = re.search(
        r"第?\s*([一二三四五六七八九十])\s*条?",
        user_input
    )

    if chinese_match:
        chinese_number = chinese_match.group(1)
        return chinese_numbers[chinese_number]

    return None