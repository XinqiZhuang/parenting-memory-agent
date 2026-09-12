import json

from json import JSONDecodeError
from pydantic import ValidationError

from extract import (
    ExtractionError,
    parse_extracted_response
)


def test_extract_validation():

    # =========================
    # 测试1：正确数据通过
    # =========================

    valid_data = {
        "development_milestones": [
            {
                "category": "gross_motor",
                "skill": "独立行走",
                "description": "第一次独立走",
                "age_months": "12"
            }
        ],
        "learning_activities": [],
        "feeding_records": [],
        "health_records": [],
        "memories": []
    }

    result_text = json.dumps(
        valid_data,
        ensure_ascii=False
    )

    result = parse_extracted_response(
        result_text
    )

    assert isinstance(result, dict)

    assert (
        result["development_milestones"][0]
        ["age_months"]
        == 12.0
    )

    print("PASS 1：正确数据完成解析和校验")


    # =========================
    # 测试2：非法JSON被拒绝
    # =========================

    invalid_json = """
    {
        "development_milestones": [
    }
    """

    try:
        parse_extracted_response(
            invalid_json
        )

        raise AssertionError(
            "非法JSON本应被拒绝"
        )

    except ExtractionError as error:

        assert isinstance(
            error.__cause__,
            JSONDecodeError
        )

        print("PASS 2：非法JSON被正确拒绝")


    # =========================
    # 测试3：非法category被拒绝
    # =========================

    invalid_category_data = {
        "development_milestones": [
            {
                "category": "错误类别",
                "skill": "独立行走"
            }
        ],
        "learning_activities": [],
        "feeding_records": [],
        "health_records": [],
        "memories": []
    }

    result_text = json.dumps(
        invalid_category_data,
        ensure_ascii=False
    )

    try:
        parse_extracted_response(
            result_text
        )

        raise AssertionError(
            "非法category本应被拒绝"
        )

    except ExtractionError as error:

        assert isinstance(
            error.__cause__,
            ValidationError
        )

        print("PASS 3：非法category被正确拒绝")


    # =========================
    # 测试4：顶层额外字段被拒绝
    # =========================

    extra_field_data = {
        "development_milestones": [],
        "learning_activities": [],
        "feeding_records": [],
        "health_records": [],
        "memories": [],
        "ai_suggestion": "宝宝发展很好"
    }

    result_text = json.dumps(
        extra_field_data,
        ensure_ascii=False
    )

    try:
        parse_extracted_response(
            result_text
        )

        raise AssertionError(
            "额外字段本应被拒绝"
        )

    except ExtractionError as error:

        assert isinstance(
            error.__cause__,
            ValidationError
        )

        print("PASS 4：顶层额外字段被正确拒绝")

    print(
        "\n全部PASS：提取解析和校验测试通过"
    )


if __name__ == "__main__":
    test_extract_validation()