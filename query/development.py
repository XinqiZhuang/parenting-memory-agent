from normalize import normalize_development_skill


DEVELOPMENT_CATEGORIES = {

    "大运动": "gross_motor",
    "大运动发展": "gross_motor",
    "运动发展": "gross_motor",

    "精细动作": "fine_motor",
    "精细动作发展": "fine_motor",

    "认知": "cognitive",
    "认知发展": "cognitive",

    "语言": "language",
    "语言发展": "language",

    "社交": "social",
    "社交发展": "social"
}

def remove_duplicate_records(records):
    """
    删除内容相同的重复发育记录。
    """

    unique_records = []
    seen_keys = set()

    for record in records:

        normalized_skill = (
            normalize_development_skill(
                record.get("skill", "")
            )
        )

        record_key = (
            record.get("category", ""),
            normalized_skill,
            record.get("date"),
            record.get("age_months"),
            record.get("description", "")
        )

        if record_key not in seen_keys:
            seen_keys.add(record_key)
            unique_records.append(record)

    return unique_records

def development_sort_key(record):
    """
    为发育记录生成时间排序依据。
    优先使用日期，没有日期时使用月龄。
    """

    date = record.get("date") or ""

    age_months = record.get(
        "age_months"
    )

    if age_months is None:
        age_months = -1

    return (
        bool(date),
        date,
        age_months
    )
    
def query_development(
    baby,
    target="",
    category="",
    latest_only=False
):

    records = baby.get(
        "development_milestones",
        []
    )

    if not records:
        return {
            "status": "EMPTY",
            "record_type": "development",
            "target": target,
            "category": category,
            "records": [],
            "message": "暂时没有成长发育记录。"
        }

    normalized_target = (
        normalize_development_skill(target)
        if target
        else ""
    )

    normalized_category = (
        DEVELOPMENT_CATEGORIES.get(
            category,
            category
        )
    )

    matched_records = []

    for record in records:

        record_skill = (
            normalize_development_skill(
                record.get("skill", "")
            )
        )

        record_category = record.get(
            "category",
            ""
        )

        # 用户查询某个具体技能
        if normalized_target:

            if record_skill == normalized_target:
                matched_records.append(record)

        # 用户查询某个发育类别
        elif normalized_category:

            if record_category == normalized_category:
                matched_records.append(record)

        # 用户没有指定技能或类别
        else:
            matched_records.append(record)

    matched_records = remove_duplicate_records(
        matched_records
    )

    if matched_records and latest_only:

        latest_record = max(
            matched_records,
            key=development_sort_key
        )

        matched_records = [
            latest_record
        ]

    if not matched_records:

        return {
            "status": "NOT_FOUND",
            "record_type": "development",
            "target": normalized_target,
            "category": normalized_category,
            "records": [],
            "message": (
                f"暂时没有找到“"
                f"{normalized_target or normalized_category}"
                f"”的相关记录。"
            )
        }

    return {
        "status": "FOUND",
        "record_type": "development",
        "target": normalized_target,
        "category": normalized_category,
        "records": matched_records,
        "message": ""
    }