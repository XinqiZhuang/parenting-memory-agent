import json

import baby


def test_initialize_from_example(
    tmp_path,
    monkeypatch
):

    data_file = (
        tmp_path
        / "baby.json"
    )

    example_file = (
        tmp_path
        / "baby.example.json"
    )

    example_data = {
        "profile": {
            "name": "测试宝宝"
        },
        "growth_records": [],
        "development_milestones": [],
        "learning_activities": [],
        "feeding_records": [],
        "health_records": [],
        "memories": []
    }

    example_file.write_text(
        json.dumps(
            example_data,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    monkeypatch.setattr(
        baby,
        "DATA_FILE",
        data_file
    )

    monkeypatch.setattr(
        baby,
        "EXAMPLE_DATA_FILE",
        example_file
    )

    result = baby.load_baby()

    assert result == example_data
    assert data_file.exists()