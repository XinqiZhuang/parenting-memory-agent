from answer import (
    format_measurement_value,
    format_growth_answer
)


def test_growth_answer():

    # 测试1：测量数值格式
    assert format_measurement_value(68.0) == "68"
    assert format_measurement_value(7.5) == "7.5"
    assert format_measurement_value(42) == "42"
    assert format_measurement_value(None) is None

    print("PASS 1：测量数值格式正确")


    # 测试2：完整体重记录
    data = {
        "status": "FOUND",
        "record_type": "growth",
        "metric": "weight_kg",
        "metric_name": "体重",
        "unit": "kg",
        "record": {
            "date": "2026-04-15",
            "age_months": 6,
            "weight_kg": 7.5
        },
        "message": ""
    }

    answer = format_growth_answer(data)

    print("\n回答1：")
    print(answer)

    assert "体重" in answer
    assert "7.5kg" in answer
    assert "2026-04-15" in answer
    assert "6月龄" in answer

    print("PASS 2：完整体重回答正确")


    # 测试3：没有具体日期
    data = {
        "status": "FOUND",
        "record_type": "growth",
        "metric": "height_cm",
        "metric_name": "身高",
        "unit": "cm",
        "record": {
            "age_months": 6,
            "height_cm": 68.0
        },
        "message": ""
    }

    answer = format_growth_answer(data)

    print("\n回答2：")
    print(answer)

    assert "身高" in answer
    assert "68cm" in answer
    assert "6月龄" in answer
    assert "没有记录具体测量日期" in answer

    print("PASS 3：缺少日期时回答正确")


    # 测试4：没有任何成长记录
    data = {
        "status": "EMPTY",
        "record_type": "growth",
        "metric": "weight_kg",
        "metric_name": "体重",
        "unit": "kg",
        "record": None,
        "message": "暂时没有成长测量记录。"
    }

    answer = format_growth_answer(data)

    assert answer == "暂时没有成长测量记录。"

    print("PASS 4：EMPTY回答正确")


    # 测试5：有记录但没有头围
    data = {
        "status": "NOT_FOUND",
        "record_type": "growth",
        "metric": "head_circumference_cm",
        "metric_name": "头围",
        "unit": "cm",
        "record": None,
        "message": "目前没有记录宝宝的头围。"
    }

    answer = format_growth_answer(data)

    assert answer == "目前没有记录宝宝的头围。"

    print("PASS 5：NOT_FOUND回答正确")

    print(
        "\n全部PASS：成长指标回答测试通过"
    )


if __name__ == "__main__":
    test_growth_answer()