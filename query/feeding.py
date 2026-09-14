def feeding_sort_key(record):

    return record.get("date") or ""


def query_feeding(
    baby,
    target="",
    latest_only=False
):

    records = baby.get(
        "feeding_records",
        []
    )

    if not records:

        return {
            "status": "EMPTY",
            "record_type": "feeding",
            "target": target,
            "records": [],
            "message": "暂时没有饮食记录。"
        }


    normalized_target = (
        target.strip()
        if target
        else ""
    )


    if normalized_target == "辅食":

        matched_records = [
            record
            for record in records
            if record.get("type") == "辅食"
        ]

    elif normalized_target in [
        "奶",
        "奶量",
        "喝奶"
    ]:

        matched_records = [
            record
            for record in records
            if record.get("type") == "奶"
        ]

    elif normalized_target:

        matched_records = [
            record
            for record in records
            if normalized_target
            in record.get("foods", [])
        ]

    else:

        matched_records = list(records)


    matched_records.sort(
        key=feeding_sort_key,
        reverse=True
    )


    if latest_only and matched_records:

        matched_records = [
            matched_records[0]
        ]


    if not matched_records:

        return {
            "status": "NOT_FOUND",
            "record_type": "feeding",
            "target": normalized_target,
            "records": [],
            "message": (
                f"暂时没有找到“"
                f"{normalized_target}"
                f"”的饮食记录。"
            )
        }


    return {
        "status": "FOUND",
        "record_type": "feeding",
        "target": normalized_target,
        "records": matched_records,
        "message": ""
    }