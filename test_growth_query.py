from query.growth import (
    query_weight,
    query_height,
    query_head_circumference
)


def test_growth_query():

    # =========================
    # 测试1：选择日期最新的记录
    # =========================

    sample_baby = {
        "growth_records": [
            {
                "date": "2026-01-15",
                "age_months": 3,
                "height_cm": 62.5,
                "weight_kg": 6.2,
                "head_circumference_cm": 40.1
            },
            {
                "date": "2026-04-15",
                "age_months": 6,
                "height_cm": 68.0,
                "weight_kg": 7.5,
                "head_circumference_cm": 42.5
            }
        ]
    }

    result = query_weight(sample_baby)

    assert result["status"] == "FOUND"
    assert result["metric"] == "weight_kg"
    assert result["unit"] == "kg"
    assert result["record"]["weight_kg"] == 7.5
    assert result["record"]["date"] == "2026-04-15"

    print("PASS 1：正确选择最新体重记录")


    # =========================
    # 测试2：跳过缺少目标指标的记录
    # =========================

    sample_baby = {
        "growth_records": [
            {
                "date": "2026-04-15",
                "age_months": 6,
                "height_cm": 68.0,
                "weight_kg": 7.5
            },
            {
                "date": "2026-05-15",
                "age_months": 7,
                "height_cm": 70.0
            }
        ]
    }

    result = query_weight(sample_baby)

    # 5月记录虽然更新，但没有体重，
    # 所以应该返回4月的7.5kg
    assert result["status"] == "FOUND"
    assert result["record"]["weight_kg"] == 7.5
    assert result["record"]["date"] == "2026-04-15"

    print("PASS 2：正确跳过缺少体重的记录")


    # =========================
    # 测试3：没有日期时按照月龄排序
    # =========================

    sample_baby = {
        "growth_records": [
            {
                "age_months": 3,
                "weight_kg": 6.2
            },
            {
                "age_months": 6,
                "weight_kg": 7.5
            }
        ]
    }

    result = query_weight(sample_baby)

    assert result["status"] == "FOUND"
    assert result["record"]["age_months"] == 6
    assert result["record"]["weight_kg"] == 7.5
    assert result["record"].get("date") is None

    print("PASS 3：无日期时按照月龄选择最新记录")


    # =========================
    # 测试4：完全没有成长记录
    # =========================

    sample_baby = {
        "growth_records": []
    }

    result = query_height(sample_baby)

    assert result["status"] == "EMPTY"
    assert result["record"] is None

    print("PASS 4：空记录正确返回EMPTY")


    # =========================
    # 测试5：有记录但没有所查指标
    # =========================

    sample_baby = {
        "growth_records": [
            {
                "date": "2026-04-15",
                "age_months": 6,
                "height_cm": 68.0
            }
        ]
    }

    result = query_head_circumference(
        sample_baby
    )

    assert result["status"] == "NOT_FOUND"
    assert result["record"] is None
    assert "头围" in result["message"]

    print("PASS 5：缺少目标指标正确返回NOT_FOUND")


    # =========================
    # 测试6：三个查询函数字段正确
    # =========================

    sample_baby = {
        "growth_records": [
            {
                "date": "2026-04-15",
                "age_months": 6,
                "height_cm": 68.0,
                "weight_kg": 7.5,
                "head_circumference_cm": 42.5
            }
        ]
    }

    weight_result = query_weight(sample_baby)
    height_result = query_height(sample_baby)
    head_result = query_head_circumference(
        sample_baby
    )

    assert weight_result["metric"] == "weight_kg"
    assert height_result["metric"] == "height_cm"
    assert (
        head_result["metric"]
        == "head_circumference_cm"
    )

    assert weight_result["unit"] == "kg"
    assert height_result["unit"] == "cm"
    assert head_result["unit"] == "cm"

    print("PASS 6：体重、身高和头围配置正确")

    print(
        "\n全部PASS：成长指标查询测试通过"
    )


if __name__ == "__main__":
    test_growth_query()