import re


CATEGORY_ALIASES = {
    "gross_motor": {
        "gross_motor",
        "大运动"
    },
    "fine_motor": {
        "fine_motor",
        "精细动作"
    },
    "cognitive": {
        "cognitive",
        "认知"
    },
    "language": {
        "language",
        "语言"
    },
    "social": {
        "social",
        "社交"
    }
}


def normalize_search_text(value):

    return re.sub(
        r"[\s，。！？、,.!?：:；;\"'“”‘’]",
        "",
        str(value or "").lower()
    )


def flatten_record_text(value):

    if isinstance(value, dict):
        return " ".join(
            flatten_record_text(item)
            for item in value.values()
        )

    if isinstance(value, list):
        return " ".join(
            flatten_record_text(item)
            for item in value
        )

    return str(value or "")


def category_matches(
    record_category,
    category
):

    requested = normalize_search_text(
        category
    )

    actual = normalize_search_text(
        record_category
    )

    aliases = CATEGORY_ALIASES.get(
        requested,
        {requested}
    )

    normalized_aliases = {
        normalize_search_text(alias)
        for alias in aliases
    }

    return actual in normalized_aliases


def target_is_category_name(
    target,
    category
):

    if not target or not category:
        return False

    requested = normalize_search_text(
        category
    )

    normalized_target = normalize_search_text(
        target
    )

    aliases = CATEGORY_ALIASES.get(
        requested,
        {requested}
    )

    return normalized_target in {
        normalize_search_text(alias)
        for alias in aliases
    }


def query_activities(
    baby,
    category="",
    target=""
):

    records = baby.get(
        "learning_activities",
        []
    )

    if not records:
        return "暂时没有早教活动记录"

    if target_is_category_name(
        target,
        category
    ):
        target = ""

    matched_records = []

    for record in records:

        if category and not category_matches(
            record.get("category", ""),
            category
        ):
            continue

        if target:
            normalized_target = (
                normalize_search_text(target)
            )

            normalized_record = (
                normalize_search_text(
                    flatten_record_text(record)
                )
            )

            if (
                normalized_target
                not in normalized_record
            ):
                continue

        matched_records.append(record)

    if not matched_records:
        search_name = target or category

        return (
            f"暂时没有找到“{search_name}”"
            "相关的活动记录"
        )

    return matched_records