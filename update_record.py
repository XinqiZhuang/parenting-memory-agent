from baby import load_baby, save_baby
from extract import (
    extract_data,
    ExtractionError
)
from conflict import update_feeding_record, update_development_record
from temporal import parse_event_date, calculate_age_months_at_date
from pending import (
    set_pending_action,
    clear_pending_action
)
from normalize import normalize_development_skill

def update_data(user_input):

    baby = load_baby()

    try:
        extracted_data = extract_data(user_input)

    except ExtractionError as error:
        print(f"提取失败：{error}")

        return "修改失败：AI提取的数据格式不正确，宝宝数据没有被修改。"

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
            
            set_pending_action({
                "type": "UPDATE_DEVELOPMENT",
                "candidates": candidates,
                "new_record": record
            })

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
                    f"{index}. {date}|{skill}|{description}"
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
    

def resolve_pending_update(
    pending_action,
    choice_number
):
    """
    根据用户选择的候选编号，
    完成之前暂停的更新操作。
    """

    action_type = pending_action.get("type")

    if action_type != "UPDATE_DEVELOPMENT":
        return "暂时无法处理这类待确认操作。"

    candidates = pending_action.get(
        "candidates",
        []
    )

    new_record = pending_action.get(
        "new_record",
        {}
    )

    # 检查用户选择的编号是否合法
    if (
        choice_number < 1
        or
        choice_number > len(candidates)
    ):
        return (
            f"请选择1到{len(candidates)}之间的编号。"
        )

    # 用户看到的编号从1开始，
    # Python列表下标从0开始
    selected_candidate = candidates[
        choice_number - 1
    ]

    baby = load_baby()

    target_record = None

    # 在最新的baby.json中重新找到这条记录
    for record in baby.get(
        "development_milestones",
        []
    ):
        if record == selected_candidate:
            target_record = record
            break

    # pending保存之后，原记录可能发生过变化
    if target_record is None:
        clear_pending_action()

        return (
            "原记录已经发生变化，"
            "请重新提出修改请求。"
        )

    # 写入标准化后的技能名称
    normalized_skill = normalize_development_skill(
        new_record.get("skill", "")
    )

    if normalized_skill:
        new_record["skill"] = normalized_skill

    # 真正修改用户选中的记录
    target_record.update(new_record)

    save_baby(baby)

    # 操作完成后清除pending状态
    clear_pending_action()

    return (
        f"已经按照你的选择，"
        f"成功更新第{choice_number}条成长记录。"
    )
