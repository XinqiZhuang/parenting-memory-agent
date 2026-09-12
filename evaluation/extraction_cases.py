EXTRACTION_CASES = [
    {
        "input": "宝宝今天第一次独立走了。",
        "checks": [
            {
                "type": "not_empty",
                "list": "development_milestones"
            },
            {
                "type": "field_equals",
                "list": "development_milestones",
                "field": "category",
                "expected": "gross_motor"
            }
        ]
    },
    {
        "input": "宝宝今天第一次清楚地叫妈妈。",
        "checks": [
            {
                "type": "field_equals",
                "list": "development_milestones",
                "field": "category",
                "expected": "language"
            }
        ]
    },
    {
        "input": "宝宝会用两个手指捏起小饼干了。",
        "checks": [
            {
                "type": "field_equals",
                "list": "development_milestones",
                "field": "category",
                "expected": "fine_motor"
            }
        ]
    },
    {
        "input": "今天陪宝宝玩了10分钟套杯游戏。",
        "checks": [
            {
                "type": "not_empty",
                "list": "learning_activities"
            },
            {
                "type": "field_equals",
                "list": "learning_activities",
                "field": "duration_minutes",
                "expected": 10
            }
        ]
    },
    {
        "input": "宝宝早上喝了180毫升奶。",
        "checks": [
            {
                "type": "not_empty",
                "list": "feeding_records"
            },
            {
                "type": "field_equals",
                "list": "feeding_records",
                "field": "amount_ml",
                "expected": 180
            }
        ]
    },
    {
        "input": "宝宝中午吃了南瓜泥和半个鸡蛋。",
        "checks": [
            {
                "type": "not_empty",
                "list": "feeding_records"
            }
        ]
    },
    {
        "input": "宝宝今天有点咳嗽。",
        "checks": [
            {
                "type": "not_empty",
                "list": "health_records"
            }
        ]
    },
    {
        "input": "今天是宝宝第一次坐地铁。",
        "checks": [
            {
                "type": "not_empty",
                "list": "memories"
            }
        ]
    },
    {
        "input": "宝宝下午扶着沙发走了两步，还玩了10分钟套杯，喝了180毫升奶。",
        "checks": [
            {
                "type": "not_empty",
                "list": "development_milestones"
            },
            {
                "type": "not_empty",
                "list": "learning_activities"
            },
            {
                "type": "not_empty",
                "list": "feeding_records"
            }
        ]
    },
    {
        "input": "今天天气很好。",
        "checks": [
            {
                "type": "empty",
                "list": "development_milestones"
            },
            {
                "type": "empty",
                "list": "learning_activities"
            },
            {
                "type": "empty",
                "list": "feeding_records"
            },
            {
                "type": "empty",
                "list": "health_records"
            },
            {
                "type": "empty",
                "list": "memories"
            }
        ]
    }
]