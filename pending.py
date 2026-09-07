import json
import os


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
    如果没有pending操作，返回None。
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
    完成或取消操作后，清除pending状态。
    """

    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)