import copy
import re
import time
from datetime import date
from uuid import uuid4

from agent_v2.schema import Command, Selector, COLLECTIONS, NAME_FIELDS, NAMES, LABELS, CATEGORIES, ALLOWED_FIELDS
from agent_v2.store import utc_now
from normalize import normalize_development_skill


TTL = 20 * 60
CONFIRM = {"确认", "确认修改", "确认新增", "确认删除", "确认撤销", "确定"}
CANCEL = {"取消", "算了", "不改了", "不用了", "不用改了", "不修改了"}


def normalized(value):
    return re.sub(r"[\s，。！？、,.!?：:；;\"'“”‘’]", "", str(value or "")).lower()


def display(value):
    if value is None or value == "":
        return "未记录"
    if isinstance(value, list):
        return "、".join(map(str, value)) or "空"
    return CATEGORIES.get(str(value), str(value))


def describe(record):
    parts = []
    for field in ("date", "time", "skill", "activity", "event", "type", "category",
                  "height_cm", "weight_kg", "head_circumference_cm", "foods", "amount_ml",
                  "duration_minutes", "temperature_c", "age_months", "description"):
        if record.get(field) is not None and record.get(field) != "":
            parts.append(f"{LABELS[field]}：{display(record[field])}")
    if not record.get("date"):
        parts.append("日期未记录")
    if record.get("photos"):
        parts.append(f"关联照片：{len(record['photos'])}张")
    return "；".join(parts) or "空记录"


def is_live(record):
    return not record.get("_deleted_at")


def known_date(record):
    value = record.get("date")
    if not isinstance(value, str):
        return ""
    try:
        return value if date.fromisoformat(value).isoformat() == value else ""
    except ValueError:
        return ""


def match_records(data, entity, selector):
    records = [r for r in data.get(COLLECTIONS.get(entity, ""), []) if is_live(r)]
    if entity == "PHOTO":
        records = [r for r in records if r.get("photos")]
    matches = []
    for record in records:
        if selector.id and record.get("id") != selector.id:
            continue
        if selector.name:
            target = normalized(selector.name)
            if entity == "DEVELOPMENT":
                valid = normalized(normalize_development_skill(record.get("skill", ""))) == normalized(normalize_development_skill(selector.name))
            else:
                searchable = str(record.get(NAME_FIELDS.get(entity, ""), ""))
                if entity == "FEEDING":
                    searchable += " " + " ".join(record.get("foods") or [])
                valid = target in normalized(searchable)
            if not valid:
                continue
        if any(getattr(selector, key) and record.get(key) != getattr(selector, key)
               for key in ("category", "date", "type", "time")):
            continue
        event_date = known_date(record)
        if selector.start_date and (not event_date or event_date < selector.start_date):
            continue
        if selector.end_date and (not event_date or event_date > selector.end_date):
            continue
        if selector.missing_field and record.get(selector.missing_field) not in (None, ""):
            continue
        if selector.metric and record.get(selector.metric) is None:
            continue
        matches.append(record)
    return matches


def select_time(records, selector):
    if not (selector.latest or selector.earliest):
        return records, ""
    dated = [r for r in records if known_date(r)]
    if not dated:
        return [], "记录缺少日期，无法确定最近/最早一次。"
    boundary = (max if selector.latest else min)(r["date"] for r in dated)
    selected = [r for r in dated if r["date"] == boundary]
    note = "仅比较已记录日期；另有未注明日期的记录，不能确定其先后。" if len(dated) < len(records) else ""
    if len(selected) > 1:
        note += "同一天有多条记录，无法仅凭日期进一步判断先后。"
    return selected, note


def parse_choice(text):
    match = re.fullmatch(r"(?:我选|选择|选)?\s*第?\s*(\d{1,3}|[一二三四五六七八九十两])\s*(?:条|项|个)?[。！!]?", text.strip())
    if not match:
        return None
    value = match.group(1)
    return int(value) if value.isdigit() else {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}[value]


def resolve_reference(command, context):
    command = command.model_copy(deep=True)
    sel = command.selector
    if sel.reference:
        previous = context.get("last_command", {})
        if command.entity == "UNKNOWN":
            command.entity = previous.get("entity", "UNKNOWN")
        old = previous.get("selector", {})
        if not sel.name:
            sel.name = old.get("name", "")
        snapshots = context.get("last_records", [])
        # If there was a single last record, referring to 'that one' is unambiguous.
        if sel.reference == "last" and len(snapshots) == 1:
            sel.id = snapshots[0].get("id", "")
        if sel.reference == "another" and not sel.missing_field:
            # Never infer 'missing date' just because a new date is provided.
            if len(snapshots) == 1:
                return command, "“另外一条”指哪条？请给出活动名称、原日期或分类。"
    return command, ""


def summarize_changes(before, after):
    return "；".join(f"{LABELS.get(k, k)}：{display(before.get(k))} → {display(v)}"
                    for k, v in after.items() if not k.startswith("_") and k != "id" and before.get(k) != v)


def add_event(state, context_id, action, entity, before, after, actor_name="", undo_of=None):
    event = {"id": uuid4().hex, "timestamp": utc_now(), "context_id": context_id,
             "actor_name": actor_name or context_id, "action": action, "entity": entity,
             "before": copy.deepcopy(before), "after": copy.deepcopy(after), "undo_of": undo_of}
    state["events"].append(event)
    return event


def preview_text(plan):
    action = plan["action"]
    before, after = plan.get("before"), plan.get("after")
    if action == "ADD":
        detail = "准备新增：" + describe(after)
    elif action == "DELETE":
        detail = "准备删除（可撤销；照片文件保留）：" + describe(before)
    elif action == "UNDO":
        detail = "准备撤销你最近一次写入，仅还原这一条记录。"
    else:
        detail = "准备修改“" + display(before.get(NAME_FIELDS.get(plan["entity"], ""), NAMES[plan["entity"]])) + "”：\n" + summarize_changes(before, after)
    return detail + "\n尚未写入。请回复“确认”或“取消”（20分钟内有效）。"


def set_plan(context, plan):
    plan["created_at"] = time.time()
    context["pending"] = plan
    return preview_text(plan)


def plan_write(data, state, context, command):
    entity = command.entity
    if entity not in COLLECTIONS:
        return "无法确定要操作哪类记录，未写入。请提供活动/能力/食物名称。"
    if "date" in command.values and entity in {"DEVELOPMENT", "GROWTH"}:
        birth = data.get("profile", {}).get("birth_date")
        if birth:
            try:
                birthday, event_date = date.fromisoformat(birth), date.fromisoformat(command.values["date"])
                if event_date < birthday:
                    return "事件日期早于出生日期，请核对；本次没有写入。"
                months = (event_date.year - birthday.year) * 12 + event_date.month - birthday.month - (event_date.day < birthday.day)
                if "age_months" in command.values and abs(command.values["age_months"] - months) >= 1:
                    return "填写的月龄和出生日期、事件日期不一致，请核对；本次没有写入。"
                command.values["age_months"] = months
            except ValueError:
                return "档案出生日期格式不正确，请先核对；本次没有写入。"
    if command.action == "ADD":
        if entity == "PHOTO":
            return "请在网页的“照片回忆”页上传图片；文字消息不能新增照片文件。"
        after = dict(command.values)
        after["id"] = uuid4().hex
        comparable = {k: v for k, v in after.items() if k != "id"}
        for record in data[COLLECTIONS[entity]]:
            if is_live(record) and all(record.get(k) == v for k, v in comparable.items()):
                return "已有相同内容的记录，本次没有重复新增。若是另一次活动，请补充日期或描述。"
        return set_plan(context, {"action": "ADD", "entity": entity, "before": None, "after": after})

    selector = command.selector
    if not any((selector.id, selector.name, selector.category, selector.date, selector.type,
                selector.start_date, selector.end_date, selector.missing_field, selector.latest, selector.earliest)):
        return "请说明要修改/删除的记录名称或原日期。本次未写入。"
    candidates = match_records(data, entity, selector)
    candidates, note = select_time(candidates, selector)
    if not candidates:
        return "没有找到对应记录，未新增或修改任何数据。" + note
    if len(candidates) > 30:
        return "匹配记录过多，请补充原日期、名称或分类；本次未写入。"
    if len(candidates) > 1:
        context["pending"] = {"action": "CHOOSE", "command": command.model_dump(),
                              "candidates": copy.deepcopy(candidates), "created_at": time.time()}
        return "找到多条记录，请选编号（如“第二条”），然后确认修改；也可回复“取消”：\n" + "\n".join(f"{i}. {describe(r)}" for i, r in enumerate(candidates, 1))
    return plan_for_record(context, command, candidates[0])


def plan_for_record(context, command, record):
    before = copy.deepcopy(record)
    after = copy.deepcopy(record)
    if command.action == "UPDATE":
        after.update(command.values)
        if before == after:
            return "新值与原记录相同，没有修改。"
    else:
        after["_deleted_at"] = utc_now()
    return set_plan(context, {"action": command.action, "entity": command.entity, "before": before, "after": after})


def handle_pending(data, state, context, context_id, text, actor_name=""):
    if text.strip() in CANCEL:
        existed = context.pop("pending", None)
        return "已经取消这次修改。" if existed else "当前没有待确认操作。"
    plan = context.get("pending")
    if not plan:
        if text.strip() in CONFIRM or parse_choice(text) is not None:
            return "当前没有等待确认的操作，请先提出要修改的记录。"
        return None
    if time.time() - plan.get("created_at", 0) > TTL:
        context.pop("pending", None)
        return "待确认操作已过期，没有写入。请重新提出请求。"
    if plan["action"] == "CHOOSE":
        choice = parse_choice(text)
        candidates = plan["candidates"]
        if choice is None or not 1 <= choice <= len(candidates):
            return f"请回复1到{len(candidates)}之间的编号，或回复“取消”。日期不会被当成编号。"
        selected = candidates[choice - 1]
        command = Command.model_validate(plan["command"])
        current = next((r for r in data[COLLECTIONS[command.entity]] if r.get("id") == selected["id"]), None)
        if current != selected:
            context.pop("pending", None)
            return "原记录已被其他操作修改，请重新查询后操作；本次未写入。"
        return plan_for_record(context, command, current)
    if text.strip() not in CONFIRM:
        return "有操作等待确认，尚未写入。请回复“确认”或“取消”，再提出新问题。"
    collection = data[COLLECTIONS[plan["entity"]]]
    before, after = plan.get("before"), plan.get("after")
    identity = (before or after)["id"]
    current = next((r for r in collection if r.get("id") == identity), None)
    if current != before:
        context.pop("pending", None)
        return "原记录已发生变化，为防止覆盖他人修改，本次未写入。请重新提出请求。"
    if before is None:
        comparable = {k: v for k, v in after.items() if k != "id"}
        if any(is_live(r) and all(r.get(k) == v for k, v in comparable.items()) for r in collection):
            context.pop("pending", None)
            return "已存在相同记录，本次没有重复新增。"
        collection.append(copy.deepcopy(after))
    else:
        current.clear()
        current.update(copy.deepcopy(after))
    event = add_event(state, context_id, plan["action"], plan["entity"], before, after,
                      actor_name, plan.get("undo_of"))
    context.pop("pending", None)
    context["last_records"] = [copy.deepcopy(after)]
    context["last_command"] = {"action": "QUERY", "entity": plan["entity"], "selector": {"id": identity}}
    if plan["action"] == "UPDATE":
        result = "修改成功：" + summarize_changes(before, after)
    elif plan["action"] == "DELETE":
        result = "已删除该记录，可回复“撤销上次操作”恢复。照片文件未删除。"
    elif plan["action"] == "UNDO":
        result = "已撤销该次写入，其余记录未改变。"
    else:
        result = "已经记录：" + describe(after)
    return result + "\n操作编号：" + event["id"][:8]


def plan_undo(data, state, context, context_id):
    undone = {e.get("undo_of") for e in state["events"] if e.get("undo_of")}
    event = next((e for e in reversed(state["events"]) if e["context_id"] == context_id
                  and e["action"] in {"ADD", "UPDATE", "DELETE"} and e["id"] not in undone), None)
    if not event:
        return "没有可撤销的本人操作（旧版日志不支持自动撤销）。"
    before = event["after"]
    after = copy.deepcopy(event["before"])
    if after is None:
        after = dict(before, _deleted_at=utc_now())
    current = next((r for r in data[COLLECTIONS[event["entity"]]] if r.get("id") == before["id"]), None)
    if current != before:
        return "记录已被后续操作改变，不能直接撤销，以免覆盖他人修改。"
    return set_plan(context, {"action": "UNDO", "entity": event["entity"], "before": before,
                              "after": after, "undo_of": event["id"]})


def audit_answer(state, context_id, scope="self"):
    prefix = context_id.rsplit(":", 1)[0] + ":" if scope == "family" and context_id.startswith("feishu:") else None
    events = [e for e in state["events"] if (e["context_id"].startswith(prefix) if prefix else e["context_id"] == context_id)][-10:]
    if not events:
        return "这个会话尚无新版数据写入日志。旧版飞书通信日志仍保留在audit_log.jsonl；其中的SUCCESS不代表数据正确写入。"
    lines = ["当前群/本人最近的数据操作（仅实际写入，不含查询）："]
    for e in reversed(events):
        details = summarize_changes(e["before"] or {}, e["after"] or {})
        if e["action"] == "DELETE":
            details = "删除：" + describe(e["before"])
        lines.append(f"{e['timestamp']} | {e['actor_name']} | {e['action']} | {details}")
    return "\n".join(lines)


def execute(data, command, context_id="default", actor_name=""):
    state = data["_agent_v2"]
    context = state["contexts"].setdefault(context_id, {})
    command, problem = resolve_reference(command, context)
    if problem:
        return problem
    if command.action == "AUDIT":
        return audit_answer(state, context_id, command.selector.audit_scope)
    if command.action == "UNDO":
        return plan_undo(data, state, context, context_id)
    if command.action in {"ADD", "UPDATE", "DELETE"}:
        return plan_write(data, state, context, command)
    if command.entity not in COLLECTIONS:
        return "请说明要查询的宝宝记录；通用育儿问题请说明具体主题。"
    if command.selector.metric and command.selector.metric not in ALLOWED_FIELDS[command.entity]:
        return "此类记录没有该数值字段，请核对查询条件。"
    matches = match_records(data, command.entity, command.selector)
    matches, note = select_time(matches, command.selector)
    context["last_command"] = command.model_dump()
    context["last_records"] = copy.deepcopy(matches[:command.selector.limit])
    if not matches:
        return "目前没有找到相关记录。" + note
    aggregate = command.selector.aggregate
    if command.action == "QUERY" and aggregate == "count":
        return f"找到{len(matches)}条符合条件的记录。记录条数不一定等于实际活动次数。" + note
    if command.action == "QUERY" and aggregate in {"sum", "average"}:
        metric = command.selector.metric
        values = [r.get(metric) for r in matches if isinstance(r.get(metric), (int, float)) and not isinstance(r.get(metric), bool)]
        if not values:
            return "这些记录没有可统计的数值。"
        total = sum(values) if aggregate == "sum" else sum(values) / len(values)
        label = "合计" if aggregate == "sum" else "平均"
        return f"根据{len(values)}条含有效数值的记录，{LABELS[metric]}{label}为{total:g}。只统计已有记录，不代表实际全天总量。" + note
    if command.action == "ANALYZE":
        return {"records": copy.deepcopy(matches[:20]), "entity": command.entity}
    limited = matches[:command.selector.limit]
    answer = f"找到{len(matches)}条{NAMES[command.entity]}记录：\n" + "\n".join(f"{i}. {describe(r)}" for i, r in enumerate(limited, 1))
    if len(matches) > len(limited):
        answer += f"\n本次显示前{len(limited)}条，请用日期范围进一步筛选。"
    return answer + ("\n" + note if note else "")
