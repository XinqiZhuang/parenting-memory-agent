import io
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from agent_v2.service import handle_request
from agent_v2.schema import Command, Selector
from family_features.media import (stage_photo, handle_photo_text, resolve_photo, validate_image,
    store_image, vision_payload, save_web_photos)
from family_features.vision import describe_photos, VisionUnavailable


def test_feishu_photo_waits_for_metadata_and_confirmation(repo, image_bytes):
    answer = stage_photo(image_bytes, "mother", "im1", repository=repo)
    assert "尚未加入" in answer
    assert repo.snapshot()["learning_activities"] == []
    assert "预览" in handle_photo_text("确认", "mother", repository=repo)
    answer = handle_photo_text("照片信息 标题=玩套杯；日期=2026-09-20；描述=在客厅", "mother", "m2", repository=repo)
    assert "尚未写入" in answer
    assert repo.snapshot()["learning_activities"] == []
    handle_request("确认", "father", repository=repo)
    assert repo.snapshot()["learning_activities"] == []
    handle_request("确认", "mother", request_id="m3", repository=repo)
    data = repo.snapshot()
    assert len(data["learning_activities"]) == 1
    assert data["learning_activities"][0]["date"] == "2026-09-20"
    assert resolve_photo(data["learning_activities"][0]["photos"][0]).read_bytes() == image_bytes
    handle_request("确认", "mother", request_id="m3", repository=repo)
    assert len(repo.snapshot()["learning_activities"]) == 1


def test_duplicate_image_delivery_does_not_append(repo, image_bytes):
    first = stage_photo(image_bytes, "a", "i", repository=repo)
    assert stage_photo(image_bytes, "a", "i", repository=repo) == first
    assert len(repo.snapshot()["_agent_v2"]["contexts"]["a"]["photo_draft"]["photos"]) == 1


def test_cancel_and_expiry_do_not_create_record(repo, image_bytes):
    stage_photo(image_bytes, "a", "i", repository=repo)
    handle_photo_text("取消", "a", repository=repo)
    assert not repo.snapshot()["memories"]
    stage_photo(image_bytes, "a", "j", repository=repo)
    with repo.transaction() as data:
        data["_agent_v2"]["contexts"]["a"]["photo_draft"]["created_at"] = 0
    assert "过期" in handle_photo_text("照片信息 标题=x；日期=未知", "a", repository=repo)
    assert not repo.snapshot()["memories"]


@pytest.mark.parametrize("metadata", ["标题=套杯", "标题=套杯；日期=2026-02-30", "标题=套杯；日期=2026-09-20；id=evil"])
def test_invalid_metadata_never_creates_pending(repo, image_bytes, metadata):
    stage_photo(image_bytes, "a", "i", repository=repo)
    handle_photo_text("照片信息 " + metadata, "a", repository=repo)
    assert not repo.snapshot()["_agent_v2"]["contexts"]["a"].get("pending")


def test_missing_date_is_explicit(repo, image_bytes):
    stage_photo(image_bytes, "a", "i", repository=repo)
    handle_photo_text("照片信息 标题=套杯；日期=未知", "a", repository=repo)
    handle_request("确认", "a", repository=repo)
    assert "date" not in repo.snapshot()["learning_activities"][0]


def test_vision_draft_requires_user_date_and_confirmation(repo, image_bytes):
    stage_photo(image_bytes, "a", "i", repository=repo)
    answer = handle_photo_text("识别照片", "a", "vision1", repository=repo,
        recognizer=lambda _: {"event": "玩套杯", "description": "孩子手里拿着杯子。"})
    assert "草稿" in answer and not repo.snapshot()["memories"]
    assert "事件日期" in handle_photo_text("保存照片", "a", repository=repo)
    handle_photo_text("保存照片 日期=2026-09-20", "a", repository=repo)
    handle_request("确认", "a", repository=repo)
    assert repo.snapshot()["memories"][0]["event"] == "玩套杯"


def test_vision_never_overwrites_changed_context(repo, image_bytes):
    stage_photo(image_bytes, "a", "i", repository=repo)
    def change(_):
        stage_photo(image_bytes, "a", "j", repository=repo)
        return {"event": "玩套杯", "description": "杯子"}
    assert "已变化" in handle_photo_text("识别照片", "a", repository=repo, recognizer=change)
    assert "suggestion" not in repo.snapshot()["_agent_v2"]["contexts"]["a"]["photo_draft"]


def test_vision_failure_retains_manual_draft(repo, image_bytes):
    stage_photo(image_bytes, "a", "i", repository=repo)
    answer = handle_photo_text("识别照片", "a", repository=repo)
    assert "尚未配置" in answer
    assert repo.snapshot()["_agent_v2"]["contexts"]["a"]["photo_draft"]


@pytest.mark.parametrize(
    "content,repetitions",
    [(b"not an image", 1), (b"<svg></svg>", 1), (b"", 1), (b"x", 10 * 1024 * 1024 + 1)],
    ids=["invalid-bytes", "svg", "empty", "over-10-mib"],
)
def test_bad_images_rejected(content, repetitions):
    # Build large inputs during the test so Windows receives a short pytest ID.
    content = content * repetitions
    with pytest.raises(ValueError):
        validate_image(content)


@pytest.mark.parametrize("path", ["../../secret", "data/uploads/../../.env", "/etc/passwd", "uploads/../x", "uploads"])
def test_path_escape_rejected(path):
    with pytest.raises(ValueError):
        resolve_photo(path)


def test_old_windows_path_resolves_under_current_volume():
    assert resolve_photo("C:\\Users\\Someone\\project\\data\\uploads\\abc\\one.jpg") == resolve_photo("uploads/abc/one.jpg")


def test_vision_removes_metadata(image_bytes):
    with Image.open(io.BytesIO(image_bytes)) as im:
        exif = im.getexif(); exif[0x010E] = "private metadata"
        output = io.BytesIO(); im.save(output, "JPEG", exif=exif)
    path = store_image(output.getvalue())
    with Image.open(io.BytesIO(vision_payload(path))) as im:
        assert not im.getexif()


def test_vision_actual_request_shape_and_extra_fields(image_bytes):
    path = store_image(image_bytes)
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"event":"杯子","description":"孩子拿着杯子"}'))])
    assert describe_photos([path], client)["event"] == "杯子"
    payload = client.chat.completions.create.call_args.kwargs["messages"][1]["content"][1]
    assert payload["image_url"]["url"].startswith("data:image/jpeg;base64,")
    client.chat.completions.create.return_value.choices[0].message.content = '{"event":"杯子","description":"孩子","date":"2020-01-01"}'
    with pytest.raises(ValueError):
        describe_photos([path], client)


def test_web_save_idempotency_audit_and_undo(repo, image_bytes):
    record, created = save_web_photos("套杯", "客厅", "2026-09-20", [image_bytes], "web:a", repo)
    assert created
    duplicate, created = save_web_photos("套杯", "客厅", "2026-09-20", [image_bytes], "web:b", repo)
    assert not created and duplicate["id"] == record["id"]
    assert len(repo.snapshot()["_agent_v2"]["events"]) == 1
    handle_request("撤销上次操作", "web:a", repository=repo, parser=lambda *_: Command(action="UNDO"))
    handle_request("确认", "web:a", repository=repo)
    assert repo.snapshot()["learning_activities"][0]["_deleted_at"]
    assert resolve_photo(record["photos"][0]).exists()


def test_existing_pending_cannot_be_overwritten_by_photos(repo, image_bytes):
    handle_request("new", "a", repository=repo, parser=lambda *_: Command(action="ADD", entity="MEMORY", values={"event":"散步"}))
    assert "先确认" in stage_photo(image_bytes, "a", "i", repository=repo)
    with pytest.raises(ValueError):
        save_web_photos("套杯", "", "", [image_bytes], "a", repo)
    assert repo.snapshot()["_agent_v2"]["contexts"]["a"]["pending"]["after"]["event"] == "散步"


def test_natural_photo_description_produces_confirmable_plan(repo, image_bytes):
    stage_photo(image_bytes, 'a', 'im', repository=repo)
    parser=lambda *_:Command(action='ADD',entity='PHOTO',values={'event':'玩套杯','date':'2026-09-20','description':'在客厅'})
    answer=handle_photo_text('照片描述 今天在客厅玩套杯','a',repository=repo,metadata_parser=parser)
    assert '尚未写入' in answer and not repo.snapshot()['memories']
    handle_request('确认','a',repository=repo)
    assert repo.snapshot()['learning_activities'][0]['activity']=='玩套杯'


def test_natural_photo_description_missing_date_requires_followup(repo,image_bytes):
    stage_photo(image_bytes,'a','im',repository=repo)
    parser=lambda *_:Command(action='ADD',entity='MEMORY',values={'event':'套杯游戏'})
    assert '请补充' in handle_photo_text('照片描述 在家玩套杯','a',repository=repo,metadata_parser=parser)
    assert not repo.snapshot()['_agent_v2']['contexts']['a'].get('pending')
    handle_photo_text('保存照片 日期=未知','a',repository=repo)
    handle_request('确认','a',repository=repo)
    assert 'date' not in repo.snapshot()['learning_activities'][0]
