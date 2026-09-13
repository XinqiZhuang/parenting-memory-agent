RAG_CASES = [
    {
        "question": "一岁宝宝每天应该睡多长时间？",
        "expected_keywords": [
            "幼儿期为10～14小时",
            "夜间睡眠时间应达到8小时以上"
        ],
        "should_find": True
    },
    {
        "question": "怎样和一岁宝宝交流和玩耍？",
        "expected_keywords": [
            "交流和玩耍"
        ],
        "should_find": True
    },
    {
        "question": "宝宝为什么要定期做健康检查？",
        "expected_keywords": [
            "定期健康检查"
        ],
        "should_find": True
    },
    {
        "question": "宝宝添加辅食需要注意什么？",
        "expected_keywords": [
            "辅食"
        ],
        "should_find": True
    },
    {
        "question": "汽车发动机应该怎么维修？",
        "expected_keywords": [],
        "should_find": False
    },
    {
        "question": "现在应该购买哪一只股票？",
        "expected_keywords": [],
        "should_find": False
    }
]