import json
import os
import re
from threading import Lock


PENDING_FILE = "data/pending_action.json"

DEFAULT_CONTEXT_ID = "default"

_pending_lock = Lock()


def normalize_context_id(context_id):
    """
    保证每个上下文都有可以使用的字符串编号。
    """

    if context_id is None:
        return DEFAULT_CONTEXT_ID

    normalized = str(context_id).strip()

    if not normalized:
        return DEFAULT_CONTEXT_ID

    return normalized


def empty_pending_store():
    """
    创建新版pending文件的基础结构。
    """

    return {
        "version": 2,
        "actions": {}
    }


def load_pending_store():
    """
    读取整个pending状态文件。

    同时兼容旧版单个pending操作的数据结构。
    """

    path = os.fspath(PENDING_FILE)

    if not os.path.exists(path):
        return empty_pending_store()

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):
        return empty_pending_store()

    # 新版结构
    if (
        isinstance(data, dict)
        and isinstance(
            data.get("actions"),
            dict
        )
    ):
        return data

    # 兼容旧版单个pending操作
    if isinstance(data, dict):
        return {
            "version": 2,
            "actions": {
                DEFAULT_CONTEXT_ID: data
            }
        }

    return empty_pending_store()


def save_pending_store(store):
    """
    保存整个pending状态文件。
    使用临时文件，降低写入中断导致文件损坏的风险。
    """

    path = os.fspath(PENDING_FILE)
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    temporary_path = f"{path}.tmp"

    with open(
        temporary_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            store,
            file,
            ensure_ascii=False,
            indent=4
        )

    os.replace(
        temporary_path,
        path
    )


def set_pending_action(
    action,
    context_id=DEFAULT_CONTEXT_ID
):
    """
    为指定用户保存等待确认的操作。
    """

    normalized_context = normalize_context_id(
        context_id
    )

    with _pending_lock:

        store = load_pending_store()

        store["actions"][
            normalized_context
        ] = action

        save_pending_store(store)


def get_pending_action(
    context_id=DEFAULT_CONTEXT_ID
):
    """
    读取指定用户正在等待确认的操作。
    如果没有，返回None。
    """

    normalized_context = normalize_context_id(
        context_id
    )

    with _pending_lock:

        store = load_pending_store()

        return store["actions"].get(
            normalized_context
        )


def clear_pending_action(
    context_id=DEFAULT_CONTEXT_ID
):
    """
    只清除指定用户的pending状态，
    不影响其他家庭成员。
    """

    normalized_context = normalize_context_id(
        context_id
    )

    with _pending_lock:

        store = load_pending_store()

        store["actions"].pop(
            normalized_context,
            None
        )

        path = os.fspath(PENDING_FILE)

        if store["actions"]:
            save_pending_store(store)

        elif os.path.exists(path):
            os.remove(path)


def parse_choice_number(user_input):
    """
    从用户输入中提取候选编号。

    支持：
    第2条
    第二项
    2
    我选第2条
    """

    digit_match = re.search(
        r"第?\s*(\d+)\s*[条项]?",
        user_input
    )

    if digit_match:
        return int(
            digit_match.group(1)
        )

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
        r"第?\s*([一二三四五六七八九十])"
        r"\s*[条项]?",
        user_input
    )

    if chinese_match:

        chinese_number = (
            chinese_match.group(1)
        )

        return chinese_numbers[
            chinese_number
        ]

    return None