def growth_record_sort_key(record):
    """
    生成成长记录的排序依据。

    优先按照日期判断先后；
    没有日期时，再参考月龄。
    """

    date = record.get("date")

    if date:
        return (2, date)

    age_months = record.get("age_months")

    if isinstance(
        age_months,
        (int, float)
    ):
        return (1, age_months)

    return (0, 0)


def query_latest_growth_metric(
    baby,
    metric_key,
    metric_name,
    unit
):
    """
    查询某个成长指标的最新记录。

    metric_key:
    数据中的字段名称。

    metric_name:
    向用户展示的中文名称。

    unit:
    指标单位。
    """

    records = baby.get(
        "growth_records",
        []
    )

    if not records:
        return {
            "status": "EMPTY",
            "record_type": "growth",
            "metric": metric_key,
            "metric_name": metric_name,
            "unit": unit,
            "record": None,
            "message": "暂时没有成长测量记录。"
        }

    valid_records = []

    for record in records:

        value = record.get(metric_key)

        if value is not None:
            valid_records.append(record)

    if not valid_records:
        return {
            "status": "NOT_FOUND",
            "record_type": "growth",
            "metric": metric_key,
            "metric_name": metric_name,
            "unit": unit,
            "record": None,
            "message": (
                f"目前没有记录宝宝的"
                f"{metric_name}。"
            )
        }

    sorted_records = sorted(
        valid_records,
        key=growth_record_sort_key
    )

    latest_record = sorted_records[-1]

    return {
        "status": "FOUND",
        "record_type": "growth",
        "metric": metric_key,
        "metric_name": metric_name,
        "unit": unit,
        "record": latest_record,
        "message": ""
    }


def query_weight(baby):

    return query_latest_growth_metric(
        baby=baby,
        metric_key="weight_kg",
        metric_name="体重",
        unit="kg"
    )


def query_height(baby):

    return query_latest_growth_metric(
        baby=baby,
        metric_key="height_cm",
        metric_name="身高",
        unit="cm"
    )


def query_head_circumference(baby):

    return query_latest_growth_metric(
        baby=baby,
        metric_key="head_circumference_cm",
        metric_name="头围",
        unit="cm"
    )