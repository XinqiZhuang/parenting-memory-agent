from baby import load_baby, save_baby
from extract import (
    extract_data,
    ExtractionError
)
from datetime import date
from temporal import parse_event_date, calculate_age_months_at_date


def add_data(user_input):

    baby = load_baby()

    try:
        extracted_data = extract_data(user_input)

    except ExtractionError as error:
        print(f"提取失败：{error}")

        return "记录失败：AI提取的数据格式不正确，宝宝数据没有被保存。"


    # =========================
    # 成长发育里程碑
    # =========================

    parsed_event_date = parse_event_date(user_input)

    for record in extracted_data.get("development_milestones", []):

        birth_date = baby["profile"]["birth_date"]

        event_date = (
            parsed_event_date
            or record.get("date")
            or date.today().isoformat()
        )

        record["date"] = event_date

        record["age_months"] = calculate_age_months_at_date(
            birth_date,
            event_date
        )

        baby["development_milestones"].append(record)


    # =========================
    # 早教活动
    # =========================

    for record in extracted_data.get("learning_activities", []):
        baby["learning_activities"].append(record)


    # =========================
    # 饮食记录
    # =========================

    for record in extracted_data.get("feeding_records", []):
        baby["feeding_records"].append(record)


    # =========================
    # 健康记录
    # =========================

    for record in extracted_data.get("health_records", []):
        baby["health_records"].append(record)


    # =========================
    # 特殊记忆
    # =========================

    for record in extracted_data.get("memories", []):
        baby["memories"].append(record)


    save_baby(baby)

    print("数据已经保存到 baby.json")

    return "已经记录宝宝的新信息。"