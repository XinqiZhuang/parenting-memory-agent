import copy
import hashlib
import io
import os
import re
import tempfile
import time
import warnings
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps

from agent_v2.engine import CANCEL, CONFIRM, TTL, set_plan
from agent_v2.schema import validate_values, COLLECTIONS
from agent_v2.service import default_repository, existing_receipt, finish, receipt_key
from storage import data_path
from family_features.classification import photo_record_payload

MAX_BYTES = 10 * 1024 * 1024
MAX_PHOTOS = 8
DRAFT_TTL = 30 * 60
FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def validate_image(content):
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_BYTES:
        raise ValueError("单张照片应为1字节到10MB。")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in FORMATS or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("仅支持静态JPG、PNG、WEBP照片。")
                if image.width * image.height > 24_000_000:
                    raise ValueError("照片不能超过2400万像素，请先缩小。")
                suffix = FORMATS[image.format]
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
        return suffix
    except (OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("图片内容损坏或格式不支持。") from exc


def store_image(content):
    suffix = validate_image(content)
    relative = Path("uploads") / (uuid4().hex + suffix)
    target = data_path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(content)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return relative.as_posix()


def resolve_photo(value):
    """Resolve both new portable paths and old Windows data/uploads paths."""
    if not isinstance(value, str) or not value:
        raise ValueError("照片路径为空。")
    root = data_path("uploads").resolve()
    clean = value.replace("\\", "/")
    parts = clean.split("/")
    if ".." in parts or "uploads" not in parts:
        raise ValueError("照片路径不在上传目录内。")
    suffix = parts[parts.index("uploads") + 1:]
    candidate = root.joinpath(*suffix).resolve()
    if not candidate.is_relative_to(root) or candidate == root:
        raise ValueError("照片路径不在上传目录内。")
    return candidate


def vision_payload(path):
    """Send a resized copy without EXIF/GPS; retain original only in private storage."""
    content = resolve_photo(path).read_bytes()
    validate_image(content)
    with Image.open(io.BytesIO(content)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1400, 1400))
        out = io.BytesIO()
        image.save(out, "JPEG", quality=85)
    return out.getvalue()


def save_web_photos(event, description, event_date, photos, context_id, repository=None, *, kind="AUTO", category="AUTO", duration=None):
    """Explicit form submit confirms this write; repeated submission is idempotent."""
    from agent_v2.engine import add_event
    import json
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise ValueError("每次请选择1到8张照片。")
    entity, values = photo_record_payload(event, description, event_date, kind=kind, category=category, duration=duration)
    hashes = []
    for content in photos:
        validate_image(content)
        hashes.append(hashlib.sha256(content).hexdigest())
    token = hashlib.sha256(json.dumps([entity, values, hashes], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    repository = repository or default_repository()
    with repository.transaction() as data:
        state = data["_agent_v2"]
        ctx = state["contexts"].setdefault(context_id, {})
        if ctx.get("pending"):
            raise ValueError("宝宝档案对话中还有待确认操作，请先确认或取消后再保存照片。")
        previous = next((r for r in data[COLLECTIONS[entity]] if r.get("_photo_submission") == token and not r.get("_deleted_at")), None)
        if previous:
            return previous, False
        record = dict(values, id=uuid4().hex, photos=[store_image(content) for content in photos], _photo_submission=token)
        data[COLLECTIONS[entity]].append(record)
        add_event(state, context_id, "ADD", entity, None, record, "网页用户")
        ctx["last_records"] = [record.copy()]
        ctx["last_command"] = {"action": "QUERY", "entity": entity, "selector": {"id": record["id"]}}
        ctx["generation"] = ctx.get("generation", 0) + 1
        return record, True


def stage_photo(content, context_id, request_id, actor_name="", repository=None):
    repository = repository or default_repository()
    key = receipt_key(context_id, request_id)
    marker = "[图片]" + hashlib.sha256(content).hexdigest()
    with repository.transaction() as data:
        cached = existing_receipt(data, key, marker)
        if cached is not None:
            return cached
        ctx = data["_agent_v2"]["contexts"].setdefault(context_id, {})
        if ctx.get("pending"):
            return "请先确认或取消上一条操作，再重新发送照片。"
        draft = ctx.get("photo_draft", {})
        if time.time() - draft.get("created_at", 0) > DRAFT_TTL:
            draft = {"photos": [], "created_at": time.time(), "values": {}}
        if len(draft["photos"]) >= MAX_PHOTOS:
            return "同一回忆最多8张照片，请先保存或取消当前草稿。"
        draft["photos"].append(store_image(content))
        draft.pop("suggestion", None)
        ctx["photo_draft"] = draft
        text = (f"已收到{len(draft['photos'])}张照片，草稿30分钟内可确认，尚未加入宝宝档案。\n"
                "可以继续发图，然后直接告诉我照片的故事，例如：\n"
                "这是9月15日，我们通过动物模型和认知卡教宝宝认识动物。\n"
                "我会整理日期、标题、分类和描述，给你确认。日期记不清也可以直接说。\n"
                "也可回复“识别照片”查看画面描述，或回复“取消”。")
        return finish(data, context_id, marker, text, key)


def parse_photo_metadata(text):
    text = re.sub(r"^(照片信息|保存照片)[：:\s]*", "", text).strip()
    if not text:
        return {}
    result = {}
    mapping = {"标题": "event", "日期": "date", "描述": "description", "类型": "_kind", "分类": "_category", "时长": "duration_minutes"}
    pattern = r"(?<![^\s；;])(" + "|".join(mapping) + r")\s*[=＝：:]\s*"
    tokens = list(re.finditer(pattern, text))
    seen = set()
    unknown = re.findall(r"(?<![^\s；;])([^\s；;=＝：:]+)\s*[=＝]", text)
    if not tokens or text[:tokens[0].start()].strip(" ;；\n") or any(key not in mapping for key in unknown):
        raise ValueError("请填写：照片信息 标题=认识蔬菜 日期=2026-09-20 分类=认知 描述=通过实物认识蔬菜。")
    for index, match in enumerate(tokens):
        end = tokens[index + 1].start() if index + 1 < len(tokens) else len(text)
        field, value = mapping[match[1]], text[match.end():end].strip(" ;；\n")
        if not value:
            raise ValueError(f"{match[1]}不能为空；日期不清楚可填“未知”。")
        if field in seen:
            raise ValueError("同一字段请只填写一次。")
        seen.add(field)
        if field == "date" and value in {"未知", "不清楚", "未记录"}:
            result["_date_unknown"] = True
        elif field == "date":
            from datetime import date, timedelta
            from family_features.settings import family_now
            offsets = {"今天": 0, "昨天": 1, "前天": 2}
            if value in offsets:
                value = (family_now().date() - timedelta(days=offsets[value])).isoformat()
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError:
                raise ValueError("“日期”请填真实日期，例如日期=2026-09-20，或日期=今天；不清楚可填日期=未知。“实际日期”是说明文字，不能作为日期保存。") from None
            result[field] = value
        elif field == "duration_minutes":
            try:
                result[field] = float(value.removesuffix("分钟").strip())
            except ValueError:
                raise ValueError("时长请填写分钟数，例如时长=10。") from None
        else:
            result[field] = value
    return result


def _draft_from_plan(plan):
    after = plan["after"]
    values = copy.deepcopy(plan.get("photo_note", {}))
    if not values:
        values = {k: after[k] for k in ("date", "description", "duration_minutes") if k in after}
        values["event"] = after.get("activity") or after.get("event", "")
        values["_kind"] = "ACTIVITY" if plan["entity"] == "ACTIVITY" else "MEMORY"
        values["_category"] = after.get("category", "AUTO")
        values["_date_unknown"] = not bool(after.get("date"))
    return {"photos": list(after["photos"]), "created_at": plan["created_at"],
            "suggestion": values, "record_id": after["id"],
            "user_described": plan.get("photo_user_described", plan["entity"] == "ACTIVITY")}


def _merge_note(current, patch):
    values = dict(current)
    values.update(patch)
    if patch.get("date"):
        values["_date_unknown"] = False
        values["_date_note"] = patch.get("_date_note", "")
    if patch.get("_date_unknown"):
        values.pop("date", None)
        values.pop("_date_note", None)
    if patch.get("_kind") == "MEMORY":
        values.pop("duration_minutes", None)
        values["_category"] = "AUTO"
    elif patch.get("_category") not in (None, "AUTO", "", "未知"):
        values["_kind"] = "ACTIVITY"
    return values


def _prepare_photo(ctx, draft):
    values = draft.get("suggestion", {})
    if not values.get("event"):
        return "请告诉我这组照片发生了什么，例如“我们带宝宝认识动物”。照片仍在草稿里，尚未写入。"
    if not values.get("date") and not values.get("_date_unknown"):
        return f"已整理：{values['event']}。请补充事件日期：是哪一天？可以说“昨天”“9月15日”，或者“日期记不清了”。尚未写入。"
    entity, payload = photo_record_payload(values.get("event", ""), values.get("description", ""), values.get("date", ""),
        kind=values.get("_kind", "AUTO"), category=values.get("_category", "AUTO"),
        duration=values.get("duration_minutes"), infer=bool(draft.get("user_described")))
    answer = set_plan(ctx, {"action": "ADD", "entity": entity, "before": None,
        "after": dict(payload, id=draft.get("record_id") or uuid4().hex, photos=list(draft["photos"])),
        "photo_note": copy.deepcopy(values), "photo_user_described": bool(draft.get("user_described"))})
    ctx.pop("photo_draft", None)
    if values.get("_date_note"):
        answer += "\n" + values["_date_note"]
    if values.get("_date_unknown"):
        answer += "\n事件日期：未知（不会用上传日期代替）。"
    return answer + "\n需要调整时直接告诉我，例如“日期改成9月16日”。"


def handle_photo_text(text, context_id, request_id=None, actor_name="", repository=None, recognizer=None, metadata_parser=None, note_parser=None):
    repository = repository or default_repository()
    key = receipt_key(context_id, request_id) if request_id else None
    text = text.strip()
    with repository.transaction() as data:
        cached = existing_receipt(data, key, text)
        if cached is not None:
            return cached
        ctx = data["_agent_v2"]["contexts"].setdefault(context_id, {})
        pending = ctx.get("pending")
        photo_pending = bool(pending and pending.get("action") == "ADD" and pending.get("after", {}).get("photos"))
        if pending and not photo_pending:
            return None
        # Confirmation and cancellation use the common, audited write engine.
        if photo_pending and text in CONFIRM | CANCEL:
            return None
        draft = copy.deepcopy(_draft_from_plan(pending) if photo_pending else ctx.get("photo_draft"))
        if not draft:
            return "请先发送照片；群聊中可先@机器人发送“上传照片”，再单独发图。" if text in {"识别照片", "保存照片"} else None
        if time.time() - draft["created_at"] > (TTL if photo_pending else DRAFT_TTL):
            ctx.pop("photo_draft", None)
            if photo_pending:
                ctx.pop("pending", None)
            return finish(data, context_id, text, "照片草稿已过期，未加入档案。请重新发送照片。", key)
        if text in CANCEL:
            ctx.pop("photo_draft", None)
            return finish(data, context_id, text, "已取消照片草稿，没有新增宝宝记录。", key)
        if text in CONFIRM:
            return "照片还没有生成保存预览。请直接描述照片和日期，再回复“确认”。"
        if text.startswith(("删除", "请删除", "撤销", "查询", "查看", "操作日志")):
            return None
        if not 1 <= len(text) <= 6000:
            return "请用1到6000字描述照片。"
        generation = ctx.get("generation", 0)
        pending_snapshot = copy.deepcopy(pending)
        original_draft = copy.deepcopy(ctx.get("photo_draft"))
        paths = list(draft["photos"])
    error = None
    values = {}
    natural = text != "识别照片"
    try:
        if not natural:
            if recognizer is None:
                from family_features.vision import describe_photos
                recognizer = describe_photos
            suggestion = recognizer(paths)
            values = validate_values("PHOTO", {"event": suggestion["event"], "description": suggestion["description"]}, adding=True)
        elif re.match(r"^(照片信息|保存照片)(?:[：:\s]*$|[：:\s]*(?:标题|日期|描述|类型|分类|时长)\s*[=＝：:])", text):
            values = parse_photo_metadata(text)
        elif metadata_parser is not None:
            # Keep the original parser injection API for existing integrations/tests.
            command = metadata_parser(re.sub(r"^照片描述[：:\s]*", "", text), {})
            if command.action != "ADD" or command.entity not in {"MEMORY", "PHOTO", "ACTIVITY"}:
                raise ValueError("请描述这组照片里的事件。")
            values = dict(command.values)
            if command.entity == "ACTIVITY":
                values["event"] = values.pop("activity")
                values["_kind"] = "ACTIVITY"
                if "category" in values:
                    values["_category"] = values.pop("category")
        else:
            from family_features.photo_language import parse_photo_note
            values = (note_parser or parse_photo_note)(text, draft.get("suggestion", {}))
    except Exception as exc:
        from agent_v2.parser import ParseError
        from family_features.vision import VisionUnavailable
        error = str(exc) if isinstance(exc, (VisionUnavailable, ParseError, ValueError)) else "照片信息整理暂时失败，请稍后重发这句话。照片仍在草稿里，尚未写入。"
    with repository.transaction() as data:
        cached = existing_receipt(data, key, text)
        if cached is not None:
            return cached
        ctx = data["_agent_v2"]["contexts"].setdefault(context_id, {})
        if (ctx.get("generation", 0) != generation or ctx.get("pending") != pending_snapshot
                or ctx.get("photo_draft") != original_draft):
            return "处理期间照片草稿已变化，请重新发送这句话。没有覆盖新草稿。"
        if values.get("_other") and not error:
            return None
        # A correction withdraws the old preview, including when it needs clarification.
        # This prevents a subsequent 'confirm' from saving outdated metadata.
        if photo_pending:
            ctx.pop("pending", None)
        ctx["photo_draft"] = draft
        if error:
            return finish(data, context_id, text, error + ("\n原预览已撤回，请修改后重新确认。" if photo_pending else ""), key)
        if values.get("_question"):
            return finish(data, context_id, text, values["_question"] + "\n照片草稿已保留，尚未写入。", key)
        if not natural:
            # Do not replace already supplied user facts with a new visual guess.
            if not draft.get("user_described"):
                draft["suggestion"] = _merge_note(draft.get("suggestion", {}), values)
            answer = (f"图片识别草稿（需你核对）：\n标题：{values['event']}\n描述：{values['description']}\n"
                      "单张照片不能确认首次发生、年龄或能力水平。\n"
                      "接下来直接告诉我照片的故事，例如：\n"
                      "这是9月15日，我们通过动物模型和认知卡教宝宝认识动物。\n"
                      "我会整理日期、标题和分类，再给你确认；日期记不清也可以直接说。")
            return finish(data, context_id, text, answer, key)
        draft["suggestion"] = _merge_note(draft.get("suggestion", {}), values)
        if values.get("event") or values.get("description") or values.get("_kind") or values.get("_category"):
            draft["user_described"] = True
        try:
            answer = _prepare_photo(ctx, draft)
        except ValueError:
            answer = "这次整理的标题或分类还不完整，请再说一下照片里的活动；草稿已保留，尚未写入。"
        return finish(data, context_id, text, answer, key)
