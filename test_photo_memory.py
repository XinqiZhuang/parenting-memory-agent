from pathlib import Path

import pytest

import photo_memory


def test_create_photo_memory(
    tmp_path,
    monkeypatch
):

    fake_baby = {
        "memories": []
    }

    saved_data = {}


    def fake_load_baby():

        return fake_baby


    def fake_save_baby(baby):

        saved_data["baby"] = baby


    monkeypatch.setattr(
        photo_memory,
        "UPLOAD_DIR",
        tmp_path / "uploads"
    )

    monkeypatch.setattr(
        photo_memory,
        "load_baby",
        fake_load_baby
    )

    monkeypatch.setattr(
        photo_memory,
        "save_baby",
        fake_save_baby
    )


    photos = [
        {
            "name": "walking.jpg",
            "content": b"fake image data"
        }
    ]


    result = (
        photo_memory.create_photo_memory(
            event="第一次独立走路",
            description="宝宝在客厅走了三步",
            event_date="2026-09-02",
            photos=photos
        )
    )


    assert result["event"] == (
        "第一次独立走路"
    )

    assert result["date"] == (
        "2026-09-02"
    )

    assert len(result["photos"]) == 1

    assert (
        saved_data["baby"]["memories"][0]
        == result
    )


    saved_photo = Path(
        result["photos"][0]
    )

    assert saved_photo.exists()

    assert saved_photo.read_bytes() == (
        b"fake image data"
    )


def test_reject_unsupported_photo():

    with pytest.raises(ValueError):

        photo_memory.validate_photo_name(
            "baby.exe"
        )

def test_search_photo_memories(
    monkeypatch
):

    fake_baby = {
        "memories": [
            {
                "id": "memory_001",
                "event": "第一次独立走路",
                "description": (
                    "宝宝在客厅独立走了三步"
                ),
                "date": "2026-09-02",
                "photos": [
                    "data/uploads/"
                    "memory_001/photo_1.jpg"
                ]
            },
            {
                "id": "memory_002",
                "event": "第一次坐地铁",
                "description": (
                    "宝宝和爸爸妈妈一起坐地铁"
                ),
                "date": "2026-08-20",
                "photos": [
                    "data/uploads/"
                    "memory_002/photo_1.jpg"
                ]
            }
        ]
    }


    monkeypatch.setattr(
        photo_memory,
        "load_baby",
        lambda: fake_baby
    )


    results = (
        photo_memory.search_photo_memories(
            "宝宝第一次独立走路是什么时候？"
        )
    )

    assert len(results) >= 1

    assert results[0]["event"] == (
        "第一次独立走路"
    )

    assert results[0]["photos"]


def test_photo_search_rejects_unrelated_question(
    monkeypatch
):

    fake_baby = {
        "memories": [
            {
                "event": "第一次独立走路",
                "description": (
                    "宝宝在客厅独立走了三步"
                ),
                "photos": [
                    "data/uploads/photo.jpg"
                ]
            }
        ]
    }


    monkeypatch.setattr(
        photo_memory,
        "load_baby",
        lambda: fake_baby
    )


    results = (
        photo_memory.search_photo_memories(
            "汽车发动机应该怎么维修？"
        )
    )

    assert results == []

def test_unrelated_question_returns_no_photo(
    monkeypatch
):

    fake_baby = {
        "memories": [
            {
                "event": "第一次站立",
                "description": (
                    "宝宝扶着沙发站了起来"
                ),
                "date": "2026-08-01",
                "photos": [
                    "data/uploads/test.jpg"
                ]
            }
        ]
    }

    monkeypatch.setattr(
        photo_memory,
        "load_baby",
        lambda: fake_baby
    )


    results = (
        photo_memory.search_photo_memories(
            "宝宝最近体重是多少？"
        )
    )

    assert results == []