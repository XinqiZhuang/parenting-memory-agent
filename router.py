from baby import load_baby
from intent import classify_intent
from add_record import add_data
from update_record import (
    update_data,
    resolve_pending_update
)

from query_intent import classify_query
from query_router import query_data
from query.activity import query_activities
from activity_analysis import analyze_activities

from answer import generate_answer

from pending import (
    get_pending_action,
    parse_choice_number,
    clear_pending_action
)


def route_request(user_input):


    # =========================
    # 优先处理上一轮待确认操作
    # =========================

    pending_action = get_pending_action()

    if pending_action:

        # 用户可以主动取消上一次操作
        cancel_keywords = [
            "取消",
            "算了",
            "不用改了",
            "不修改了"
        ]

        if any(
            keyword in user_input
            for keyword in cancel_keywords
        ):
            clear_pending_action()

            return "已经取消这次修改。"

        choice_number = parse_choice_number(
            user_input
        )

        if choice_number is None:
            candidates = pending_action.get(
                "candidates",
                []
            )

            return (
                "目前有一项修改正在等待确认，"
                f"请回复1到{len(candidates)}之间的编号，"
                "例如“第2条”;"
                "也可以回复“取消”。"
            )

        return resolve_pending_update(
            pending_action,
            choice_number
        )

    # 第一层：判断用户总体想做什么
    intent_result = classify_intent(user_input)

    intent = intent_result["intent"]

    print("\n顶层意图：", intent)


    # =========================
    # ADD
    # =========================

    if intent == "ADD":

        print("→ 进入数据添加流程")

        result = add_data(user_input)

        return result


    # =========================
    # UPDATE
    # =========================

    elif intent == "UPDATE":

        print("→ 进入数据修改流程")

        result = update_data(user_input)

        return result


    # =========================
    # QUERY / ANALYZE
    # =========================

    elif intent == "QUERY":

        baby = load_baby()

        # 第二层：判断具体查询 / 分析类型
        query_result = classify_query(user_input)

        print("具体意图：", query_result)

        query_type = query_result["query_type"]

        target = (
            query_result.get("target")
            or ""
        )

        category = (
            query_result.get("category")
            or ""
        )

        latest_keywords = [
            "最近一次",
            "最新一次",
            "最后一次",
            "最近的",
            "最新的"
        ]

        latest_only = any(
            keyword in user_input
            for keyword in latest_keywords
        )


        if latest_only and any(
            keyword in target
            for keyword in latest_keywords
        ):

            target = ""


        if (
            query_type == "QUERY_FEEDING"
            and not target
        ):

            if "辅食" in user_input:

                target = "辅食"

            elif any(
                keyword in user_input
                for keyword in [
                    "喝奶",
                    "奶量",
                    "多少奶"
                ]
            ):

                target = "奶"

        # -------------------------
        # Activity Analysis
        # -------------------------

        if query_type == "ANALYZE_ACTIVITY":

            activities = query_activities(
                baby,
                category
            )

            result = analyze_activities(
                baby,
                activities
            )

            return result


        # -------------------------
        # 普通 Query
        # -------------------------

        elif query_type.startswith("QUERY_"):

            data = query_data(
                baby,
                query_type,
                target,
                category,
                latest_only=latest_only
            )

            result = generate_answer(
                user_input,
                data
            )

            return result


        # -------------------------
        # 尚未实现的分析
        # -------------------------

        elif query_type == "ANALYZE_DEVELOPMENT":

            return "成长发展分析功能正在开发中。"


        elif query_type == "ANALYZE_FEEDING":

            return "辅食分析功能正在开发中。"


        else:

            return "暂时无法识别这个问题。"


    else:

        return "暂时无法识别你的需求。"