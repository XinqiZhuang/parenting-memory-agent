from baby import load_baby
from query_intent import classify_query
from query.activity import query_activities
from activity_analysis import analyze_activities


baby = load_baby()

user_input = input("请输入你的问题：")


# 第一步：让 DeepSeek 判断用户想做什么
intent_result = classify_query(user_input)

print("\nAI 意图判断：")
print(intent_result)


query_type = intent_result["query_type"]
category = intent_result.get("category", "")


# 第二步：根据意图决定下一步
if query_type == "QUERY_ACTIVITY":

    activities = query_activities(
        baby,
        category
    )

    print("\n检索到的活动记录：")
    print(activities)


elif query_type == "ANALYZE_ACTIVITY":

    activities = query_activities(
        baby,
        category
    )

    print("\n用于分析的活动记录：")
    print(activities)

    result = analyze_activities(
        baby,
        activities
    )

    print("\nAI 活动分析：")
    print(result)


else:

    print("\n这个测试程序目前只处理 QUERY_ACTIVITY 和 ANALYZE_ACTIVITY")