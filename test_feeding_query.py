from query.feeding import query_feeding
from answer import format_feeding_answer

BABY = {
    "feeding_records": [
        {
            "date": "2026-05-10",
            "type": "奶",
            "foods": ["奶"],
            "amount_ml": 200
        },
        {
            "date": "2026-09-05",
            "type": "辅食",
            "foods": [
                "南瓜泥",
                "半个鸡蛋"
            ],
            "amount_ml": None
        },
        {
            "date": "2026-09-10",
            "type": "辅食",
            "foods": [
                "猪肉",
                "胡萝卜"
            ],
            "amount_ml": None
        }
    ]
}


def test_query_all_solid_foods():

    result = query_feeding(
        BABY,
        target="辅食"
    )

    assert result["status"] == "FOUND"

    assert len(result["records"]) == 2

    assert (
        result["records"][0]["date"]
        == "2026-09-10"
    )


def test_query_latest_solid_food():

    result = query_feeding(
        BABY,
        target="辅食",
        latest_only=True
    )

    assert len(result["records"]) == 1

    assert result["records"][0]["foods"] == [
        "猪肉",
        "胡萝卜"
    ]


def test_query_specific_food():

    result = query_feeding(
        BABY,
        target="南瓜泥"
    )

    assert len(result["records"]) == 1

    assert (
        "南瓜泥"
        in result["records"][0]["foods"]
    )

def test_format_feeding_answer():

    data = query_feeding(
        BABY,
        target="辅食"
    )

    answer = format_feeding_answer(
        data
    )

    assert "2026-09-10" in answer
    assert "猪肉" in answer
    assert "胡萝卜" in answer
    assert "2026-09-05" in answer
    assert "南瓜泥" in answer
    assert "半个鸡蛋" in answer