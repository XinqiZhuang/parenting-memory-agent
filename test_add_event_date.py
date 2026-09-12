from unittest.mock import patch

from add_record import add_data


def test_add_uses_event_date():

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

    extracted_data = {
        "development_milestones": [
            {
                "category": "gross_motor",
                "skill": "独立走",
                "description": "宝宝前天第一次独立走。"
            }
        ],
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
            return_value=extracted_data
        ):
            with patch(
                "add_record.parse_event_date",
                return_value="2026-09-10"
            ):
                with patch(
                    "add_record.save_baby"
                ) as mock_save:

                    result = add_data(
                        "宝宝前天第一次独立走了"
                    )

                    saved_baby = mock_save.call_args.args[0]
                    saved_record = saved_baby[
                        "development_milestones"
                    ][0]

                    assert saved_record["date"] == "2026-09-10"
                    assert "age_months" in saved_record
                    assert "已经记录" in result


if __name__ == "__main__":

    test_add_uses_event_date()

    print("ADD事件日期测试通过")