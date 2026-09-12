QUERY_CASES = [
    {
        "input": "宝宝最近一次体重是多少？",
        "expected": "QUERY_WEIGHT"
    },
    {
        "input": "宝宝现在多高？",
        "expected": "QUERY_HEIGHT"
    },
    {
        "input": "宝宝最近一次头围是多少？",
        "expected": "QUERY_HEAD_CIRCUMFERENCE"
    },
    {
        "input": "宝宝什么时候开始爬？",
        "expected": "QUERY_DEVELOPMENT",
        "expected_target": "爬",
        "expected_category": "gross_motor"
    },
    {
        "input": "宝宝有哪些大运动发展记录？",
        "expected": "QUERY_DEVELOPMENT",
        "expected_target": "",
        "expected_category": "gross_motor"
    },
    {
        "input": "宝宝有哪些精细动作记录？",
        "expected": "QUERY_DEVELOPMENT",
        "expected_target": "",
        "expected_category": "fine_motor"
    },
    {
        "input": "宝宝最近喝了多少奶？",
        "expected": "QUERY_FEEDING"
    },
    {
        "input": "宝宝最近吃过哪些辅食？",
        "expected": "QUERY_FEEDING"
    },
    {
        "input": "宝宝最近有没有生病？",
        "expected": "QUERY_HEALTH"
    },
    {
        "input": "宝宝上次排便是什么时候？",
        "expected": "QUERY_HEALTH"
    },
    {
        "input": "宝宝最近玩过什么游戏？",
        "expected": "QUERY_ACTIVITY"
    },
    {
        "input": "宝宝有哪些早教训练记录？",
        "expected": "QUERY_LEARNING"
    },
    {
        "input": "宝宝第一次坐地铁是什么时候？",
        "expected": "QUERY_MEMORY"
    },
    {
        "input": "宝宝最近玩的游戏适合他的月龄吗？",
        "expected": "ANALYZE_ACTIVITY"
    },
    {
        "input": "宝宝现在的大运动发展怎么样？",
        "expected": "ANALYZE_DEVELOPMENT"
    },
    {
        "input": "宝宝最近的辅食安排合理吗？",
        "expected": "ANALYZE_FEEDING"
    },
    {
        "input": "今天天气怎么样？",
        "expected": "UNKNOWN"
    }
]