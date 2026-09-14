from query.development import query_development


def test_development_query():

    sample_baby = {
        "development_milestones": [
            {
                "category": "gross_motor",
                "skill": "扶着沙发走",
                "age_months": 10,
                "description": "下午第一次扶着沙发走了两步。"
            },
            {
                "category": "gross_motor",
                "skill": "独立走",
                "description": "宝宝第一次独立走发生在前天",
                "date": "2026-09-02",
                "age_months": 12
            },

            # 故意加入完全相同的重复记录
            {
                "category": "gross_motor",
                "skill": "独立走",
                "description": "宝宝第一次独立走发生在前天",
                "date": "2026-09-02",
                "age_months": 12
            }
        ]
    }

    # =========================
    # 测试1：查询具体技能
    # =========================

    result = query_development(
        sample_baby,
        target="独立走"
    )

    assert result["status"] == "FOUND"

    assert len(result["records"]) == 1

    assert (
        result["records"][0]["date"]
        == "2026-09-02"
    )

    print("PASS 1：具体技能查询正确")


    # =========================
    # 测试2：记录缺少日期
    # =========================

    result = query_development(
        sample_baby,
        target="扶着沙发走"
    )

    assert result["status"] == "FOUND"

    record = result["records"][0]

    assert record.get("date") is None

    assert record["age_months"] == 10

    print("PASS 2：缺少日期的记录可以正常返回")


    # =========================
    # 测试3：查询不存在的技能
    # =========================

    result = query_development(
        sample_baby,
        target="爬行"
    )

    assert result["status"] == "NOT_FOUND"

    assert result["records"] == []

    print("PASS 3：不存在的技能正确返回NOT_FOUND")


    # =========================
    # 测试4：查询整个类别
    # =========================

    result = query_development(
        sample_baby,
        category="gross_motor"
    )

    assert result["status"] == "FOUND"

    # 三条原始数据中有两条重复，
    # 去重后应该剩下两条
    assert len(result["records"]) == 2

    print("PASS 4：类别查询和去重正确")


    print(
        "\n全部PASS：发育记录查询数据层测试通过"
    )


if __name__ == "__main__":
    test_development_query()

def test_latest_gross_motor_record():

    baby = {
        "development_milestones": [
            {
                "category": "gross_motor",
                "skill": "爬",
                "date": "2026-05-15",
                "age_months": 7
            },
            {
                "category": "gross_motor",
                "skill": "独立行走",
                "date": "2026-09-12",
                "age_months": 12
            },
            {
                "category": "fine_motor",
                "skill": "捏小物品",
                "date": "2026-09-13",
                "age_months": 12
            }
        ]
    }

    result = query_development(
        baby,
        category="gross_motor",
        latest_only=True
    )

    assert result["status"] == "FOUND"

    assert len(result["records"]) == 1

    assert (
        result["records"][0]["skill"]
        == "独立行走"
    )