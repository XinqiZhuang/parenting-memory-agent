from baby import load_baby
from intent import classify_intent
from add_record import add_data
from update_record import update_data

from query_intent import classify_query
from query_router import query_data

from query.activity import query_activities
from activity_analysis import analyze_activities

from answer import generate_answer


def route_request(user_input):

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

        target = query_result.get("target", "")
        category = query_result.get("category", "")


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
                category
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