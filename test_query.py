from query_intent import classify_query


test_inputs = [
    "宝宝最近玩了什么游戏？",
    "宝宝最近玩的游戏适合他吗？",
    "宝宝有哪些大运动发展记录？",
    "宝宝现在的大运动发展怎么样？"
]


for user_input in test_inputs:
    print("\n用户：", user_input)

    result = classify_query(user_input)

    print("AI 查询判断：", result)