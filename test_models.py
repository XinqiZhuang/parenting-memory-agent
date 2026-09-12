from pydantic import ValidationError

from models import (
    DevelopmentMilestone,
    GrowthRecord,
    ExtractedData
)


def test_models():

    # =========================
    # 测试1：正确发育记录
    # =========================

    record = DevelopmentMilestone(
        category="gross_motor",
        skill="独立行走",
        description="第一次独立走",
        date="2026-09-02",
        age_months=12
    )

    assert record.skill == "独立行走"
    assert record.age_months == 12

    print("PASS 1：正确发育记录通过校验")


    # =========================
    # 测试2：字符串数字自动转换
    # =========================

    record = DevelopmentMilestone(
        category="gross_motor",
        skill="爬行",
        age_months="8"
    )

    assert record.age_months == 8.0
    assert isinstance(record.age_months, float)

    print("PASS 2：字符串数字成功转换为小数")


    # =========================
    # 测试3：没有日期也允许通过
    # =========================

    record = DevelopmentMilestone(
        category="gross_motor",
        skill="扶着沙发走",
        age_months=10
    )

    assert record.date is None

    print("PASS 3：缺少日期的记录可以通过")


    # =========================
    # 测试4：负月龄必须被拒绝
    # =========================

    try:
        DevelopmentMilestone(
            category="gross_motor",
            skill="独立行走",
            age_months=-2
        )

        raise AssertionError(
            "负月龄本应校验失败，但却通过了"
        )

    except ValidationError:
        print("PASS 4：负月龄被正确拒绝")


    # =========================
    # 测试5：非法category必须被拒绝
    # =========================

    try:
        DevelopmentMilestone(
            category="运动能力",
            skill="独立行走"
        )

        raise AssertionError(
            "非法category本应校验失败，但却通过了"
        )

    except ValidationError:
        print("PASS 5：非法category被正确拒绝")


    # =========================
    # 测试6：空skill必须被拒绝
    # =========================

    try:
        DevelopmentMilestone(
            category="gross_motor",
            skill=""
        )

        raise AssertionError(
            "空skill本应校验失败，但却通过了"
        )

    except ValidationError:
        print("PASS 6：空skill被正确拒绝")


    # =========================
    # 测试7：未知字段必须被拒绝
    # =========================

    try:
        DevelopmentMilestone(
            category="gross_motor",
            skill="爬行",
            invented_field="模型编造的字段"
        )

        raise AssertionError(
            "未知字段本应校验失败，但却通过了"
        )

    except ValidationError:
        print("PASS 7：未知字段被正确拒绝")


    # =========================
    # 测试8：正确成长测量记录
    # =========================

    growth = GrowthRecord(
        date="2026-04-15",
        age_months=6,
        height_cm=68.0,
        weight_kg=7.5,
        head_circumference_cm=42.5
    )

    assert growth.height_cm == 68.0
    assert growth.weight_kg == 7.5
    assert growth.head_circumference_cm == 42.5

    print("PASS 8：正确成长测量记录通过校验")


    # =========================
    # 测试9：负测量值必须被拒绝
    # =========================

    try:
        GrowthRecord(
            age_months=6,
            weight_kg=-7.5
        )

        raise AssertionError(
            "负体重本应校验失败，但却通过了"
        )

    except ValidationError:
        print("PASS 9：负测量值被正确拒绝")


    # =========================
    # 展示模型怎样转回字典
    # =========================

    record_dict = growth.model_dump()

    print("\nPydantic模型转换成字典：")
    print(record_dict)

    assert isinstance(record_dict, dict)

    print("PASS 10：模型可以转换成普通字典")


    # =========================
    # 测试11：完整提取结果
    # =========================


    extracted = ExtractedData(
        development_milestones=[
            {
                "category": "gross_motor",
                "skill": "独立行走",
                "age_months": "12"
            }
        ]
    )

    assert len(
        extracted.development_milestones
    ) == 1

    assert (
        extracted
        .development_milestones[0]
        .age_months
        == 12.0
    )

    assert extracted.feeding_records == []
    assert extracted.memories == []

    print("PASS 11：完整提取结果校验正确")


    # =========================
    # 测试12：顶层未知字段被拒绝
    # =========================

    try:
        ExtractedData(
            development_milestones=[],
            ai_suggestion="宝宝发展很好"
        )

        raise AssertionError(
            "顶层未知字段本应被拒绝"
        )

    except ValidationError:
        print("PASS 12：顶层未知字段被正确拒绝")


    # =========================
    # 测试13：嵌套错误记录被拒绝
    # =========================

    try:
        ExtractedData(
            development_milestones=[
                {
                    "category": "错误类别",
                    "skill": "独立行走",
                    "age_months": -2
                }
            ]
        )

        raise AssertionError(
            "错误的发育记录本应被拒绝"
        )

    except ValidationError:
        print("PASS 13：嵌套错误记录被正确拒绝")

    print(
        "\n全部PASS：Pydantic数据模型测试通过"
    )


if __name__ == "__main__":
    test_models()