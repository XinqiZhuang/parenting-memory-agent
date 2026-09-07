def query_weight(baby):

    records = baby["growth_records"]

    if not records:
        return "暂时没有身高体重记录"

    records = sorted(
        records,
        key=lambda record: record["date"]
    )

    latest = records[-1]

    return latest["weight_kg"]


def query_height(baby):

    records = baby["growth_records"]

    if not records:
        return "暂时没有身高体重记录"

    records = sorted(
        records,
        key=lambda record: record["date"]
    )

    latest = records[-1]

    return latest["height_cm"]


def query_head_circumference(baby):

    records = baby["growth_records"]

    if not records:
        return "暂时没有身高体重记录"

    records = sorted(
        records,
        key=lambda record: record["date"]
    )

    latest = records[-1]

    return latest["head_circumference_cm"]