from unittest.mock import patch

from extract import ExtractionError
from add_record import add_data
from update_record import update_data


def test_add_does_not_save_on_extraction_error():

    sample_baby = {
        "profile": {
            "birth_date": "2025-09-01"
        },
        "development_milestones": [],
        "learning_activities": [],
        "feeding_records": [],
        "health_records": [],
        "memories": []
    }

    with patch(
        "add_record.load_baby",
        return_value=sample_baby
    ):
        with patch(
            "add_record.extract_data",
            side_effect=ExtractionError("测试校验错误")
        ):
            with patch(
                "add_record.save_baby"
            ) as mock_save:

                result = add_data("记录一条错误数据")

                mock_save.assert_not_called()

                assert "没有被保存" in result


def test_update_does_not_save_on_extraction_error():

    sample_baby = {
        "profile": {
            "birth_date": "2025-09-01"
        },
        "development_milestones": [],
        "feeding_records": []
    }

    with patch(
        "update_record.load_baby",
        return_value=sample_baby
    ):
        with patch(
            "update_record.extract_data",
            side_effect=ExtractionError("测试校验错误")
        ):
            with patch(
                "update_record.save_baby"
            ) as mock_save:

                result = update_data("修改一条错误数据")

                mock_save.assert_not_called()

                assert "没有被修改" in result


if __name__ == "__main__":

    test_add_does_not_save_on_extraction_error()
    test_update_does_not_save_on_extraction_error()

    print("写入安全测试全部通过")