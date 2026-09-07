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


def query_development(
    baby,
    target="",
    category=""
):

    records = baby["development_milestones"]

    if not records:
        return "暂时没有成长发育记录"


    target = normalize_development_skill(target)


    category = DEVELOPMENT_CATEGORIES.get(
        category,
        category
    )


    if target:

        matched_records = []

        for record in records:
            record_skill = normalize_development_skill(
                record["skill"]
            )
            if record_skill == target:
                matched_records.append(record)


        if not matched_records:

            return f"暂时没有找到“{target}”的相关记录"


        return matched_records


    elif category:

        matched_records = []

        for record in records:

            if record["category"] == category:

                matched_records.append(record)


        if not matched_records:

            return f"暂时没有找到“{category}”的相关记录"


        return matched_records


    else:

        return records