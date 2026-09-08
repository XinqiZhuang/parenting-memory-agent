from answer import (
    format_age_months,
    format_development_answer
)


def test_development_answer():

    # =========================
    # 测试1：月龄格式
    # =========================

    assert format_age_months(10) == "10月龄"
    assert format_age_months(12.0) == "12月龄"
    assert format_age_months(12.2) == "12.2月龄"
    assert format_age_months(None) is None

    print("PASS 1：月龄格式化正确")


    # =========================
    # 测试2：日期和月龄都有
    # =========================

    data = {
        "status": "FOUND",
        "record_type": "development",
        "target": "独立行走",
        "category": "gross_motor",
        "records": [
            {
                "category": "gross_motor",
                "skill": "独立走",
                "date": "2026-09-02",
                "age_months": 12,
                "description": (
                    "宝宝第一次独立走发生在前天"
                )
            }
        ],
        "message": ""
    }

    answer = format_development_answer(data)

    print("\n回答1：")
    print(answer)

    assert "独立走" in answer
    assert "2026-09-02" in answer
    assert "12月龄" in answer
    assert "宝宝第一次独立走" in answer

    print("PASS 2：完整时间信息回答正确")


    # =========================
    # 测试3：缺少具体日期
    # =========================

    data = {
        "status": "FOUND",
        "record_type": "development",
        "target": "扶着沙发走",
        "category": "gross_motor",
        "records": [
            {
                "category": "gross_motor",
                "skill": "扶着沙发走",
                "age_months": 10,
                "description": (
                    "下午第一次扶着沙发走了两步。"
                )
            }
        ],
        "message": ""
    }

    answer = format_development_answer(data)

    print("\n回答2：")
    print(answer)

    assert "10月龄" in answer
    assert "没有记录具体日期" in answer

    print("PASS 3：缺少日期时回答正确")


    # =========================
    # 测试4：没有找到记录
    # =========================

    data = {
        "status": "NOT_FOUND",
        "record_type": "development",
        "target": "爬行",
        "category": "gross_motor",
        "records": [],
        "message": "暂时没有找到“爬行”的相关记录。"
    }

    answer = format_development_answer(data)

    assert answer == (
        "暂时没有找到“爬行”的相关记录。"
    )

    print("PASS 4：未找到记录时回答正确")


    # =========================
    # 测试5：多条记录
    # =========================

    data = {
        "status": "FOUND",
        "record_type": "development",
        "target": "",
        "category": "gross_motor",
        "records": [
            {
                "category": "gross_motor",
                "skill": "扶着沙发走",
                "age_months": 10,
                "description": "第一次扶走"
            },
            {
                "category": "gross_motor",
                "skill": "独立行走",
                "date": "2026-09-02",
                "age_months": 12,
                "description": "第一次独立行走"
            }
        ],
        "message": ""
    }

    answer = format_development_answer(data)

    print("\n回答3：")
    print(answer)

    assert "1." in answer
    assert "2." in answer
    assert answer.count("第一次独立行走") == 1

    print("PASS 5：多条记录回答正确")

    print(
        "\n全部PASS：发育查询回答测试通过"
    )


if __name__ == "__main__":
    test_development_answer()