from baby import load_baby, save_baby
from extract import extract_data
from conflict import update_feeding_record, update_development_record
from temporal import parse_event_date, calculate_age_months_at_date
from pending import set_pending_action

def update_data(user_input):

    baby = load_baby()

    extracted_data = extract_data(user_input)

    print("AI提取结果:")
    print(extracted_data)

    updated_anything = False


    # =========================
    # 成长发育记录
    # =========================

    for record in extracted_data.get("development_milestones") or []:

        event_date = parse_event_date(user_input)

        if event_date:

            record["date"] = event_date
            birth_date = baby["profile"]["birth_date"]
            record["age_months"] = calculate_age_months_at_date(
                birth_date,
                event_date
            )

        update_result = update_development_record(baby,record)

        status = update_result["status"]

        if status == "UPDATED":
            print("成功更新成长发育记录")
            updated_anything = True

        elif status == "AMBIGUOUS":

            candidates = update_result["candidates"]

            message_lines = [
                "我找到多条可能需要修改的成长记录，请确认你指的是哪一条："
            ]

            for index, candidate in enumerate(
                candidates,
                start=1
            ):

                date = candidate.get("date", "日期未知")
                skill = candidate.get("skill", "未知能力")
                description = candidate.get(
                    "description",
                    ""
                )

                message_lines.append(
                    f"{index}. {date}｜{skill}｜{description}"
                )

            return "\n".join(message_lines)

        elif status == "NOT_FOUND":
            print("没有找到对应的成长发育记录")


    # =========================
    # 饮食记录
    # =========================

    for record in extracted_data.get("feeding_records") or []:

        updated = update_feeding_record(
            baby,
            record
        )

        if updated:
            print("成功更新饮食记录")
            updated_anything = True


    # =========================
    # 保存
    # =========================

    if updated_anything:

        save_baby(baby)

        print("数据已经保存到 baby.json")

        return "已经成功更新宝宝的记录。"

    else:

        return "没有找到对应的记录，暂时无法更新。"
    


