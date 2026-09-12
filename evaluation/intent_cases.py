INTENT_CASES = [
    {
        "input": "宝宝今天第一次独立走了。",
        "expected": "ADD"
    },
    {
        "input": "下午宝宝喝了180毫升奶。",
        "expected": "ADD"
    },
    {
        "input": "宝宝昨天有点咳嗽。",
        "expected": "ADD"
    },
    {
        "input": "今天陪宝宝玩了十分钟套杯。",
        "expected": "ADD"
    },
    {
        "input": "宝宝会爬了。",
        "expected": "ADD"
    },

    {
        "input": "更正一下，宝宝是前天第一次独立走。",
        "expected": "UPDATE"
    },
    {
        "input": "刚才体重写错了，应该是10.6公斤。",
        "expected": "UPDATE"
    },
    {
        "input": "不是今天开始走，是昨天。",
        "expected": "UPDATE"
    },
    {
        "input": "把刚才记录的奶量从180毫升改为150毫升。",
        "expected": "UPDATE"
    },

    {
        "input": "宝宝什么时候第一次独立走？",
        "expected": "QUERY"
    },
    {
        "input": "宝宝最近一次体重是多少？",
        "expected": "QUERY"
    },
    {
        "input": "宝宝最近玩过什么游戏？",
        "expected": "QUERY"
    },
    {
        "input": "宝宝最近的辅食安排合理吗？",
        "expected": "QUERY"
    },
    {
        "input": "宝宝会爬了吗？",
        "expected": "QUERY"
    }
]