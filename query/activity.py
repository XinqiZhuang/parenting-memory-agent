def query_activities(baby, category=""):

    records = baby["learning_activities"]

    if not records:
        return "暂时没有早教活动记录"

    if category:

        matched_records = []

        for record in records:

            if record["category"] == category:
                matched_records.append(record)

        if not matched_records:
            return f"暂时没有找到“{category}”相关的活动"

        return matched_records

    return records