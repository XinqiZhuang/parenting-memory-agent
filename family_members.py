import json
import os


MEMBERS_FILE = "data/family_members.json"


def load_family_members():
    """
    读取家庭成员配置。
    """

    path = os.fspath(MEMBERS_FILE)

    if not os.path.exists(path):
        return {}

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
        return {}

    members = data.get(
        "members",
        {}
    )

    if not isinstance(members, dict):
        return {}

    return members


def get_family_member(actor_id):
    """
    根据飞书open_id获取家庭成员信息。
    未配置的成员返回安全的默认名称。
    """

    members = load_family_members()

    member = members.get(
        actor_id,
        {}
    )

    display_name = member.get(
        "display_name",
        "未命名成员"
    )

    role = member.get(
        "role",
        "unknown"
    )

    return {
        "actor_id": actor_id,
        "display_name": display_name,
        "role": role
    }