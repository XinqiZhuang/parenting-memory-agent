from baby import load_baby, save_baby
from extract import extract_data
from datetime import date
from age import calculate_age_months


def add_data(user_input):

    baby = load_baby()

    extracted_data = extract_data(user_input)

    print("AI提取结果:")
    print(extracted_data)


    # =========================
    # 成长发育里程碑
    # =========================

    for record in extracted_data.get("development_milestones", []):

        birth_date = baby["profile"]["birth_date"]

        record["date"] = date.today().isoformat()
        record["age_months"] = calculate_age_months(birth_date)

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