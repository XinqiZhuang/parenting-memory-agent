from query.activity import query_activities


SAMPLE_BABY = {
    "learning_activities": [
        {
            "activity": "套杯游戏",
            "category": "fine_motor",
            "duration_minutes": 10
        },
        {
            "activity": "亲子阅读",
            "category": "language",
            "duration_minutes": 15
        }
    ]
}


def test_query_activity_by_target():

    result = query_activities(
        SAMPLE_BABY,
        target="套杯游戏"
    )

    assert len(result) == 1
    assert result[0]["activity"] == "套杯游戏"


def test_query_activity_by_category():

    result = query_activities(
        SAMPLE_BABY,
        category="fine_motor"
    )

    assert len(result) == 1
    assert result[0]["activity"] == "套杯游戏"


def test_query_activity_with_chinese_category():

    result = query_activities(
        SAMPLE_BABY,
        category="fine_motor",
        target="精细动作"
    )

    assert len(result) == 1
    assert result[0]["activity"] == "套杯游戏"


def test_query_missing_activity():

    result = query_activities(
        SAMPLE_BABY,
        target="积木游戏"
    )

    assert "暂时没有找到" in result