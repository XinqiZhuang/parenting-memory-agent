import csv
import io
from datetime import date

from agent_v2.engine import describe, is_live, known_date
from agent_v2.schema import COLLECTIONS, NAMES, CATEGORIES

ENTITIES = [key for key in COLLECTIONS if key != "PHOTO"]


def browse_records(data, entity="ALL", start="", end="", keyword="", missing_only=False, include_missing=True):
    result = []
    for kind in ENTITIES:
        if entity not in {"ALL", kind}:
            continue
        for record in data.get(COLLECTIONS[kind], []):
            if not is_live(record):
                continue
            day = known_date(record)
            if missing_only and day:
                continue
            if not day and not include_missing:
                continue
            if day and ((start and day < start) or (end and day > end)):
                continue
            text = describe(record)
            if keyword.casefold() not in text.casefold():
                continue
            result.append({"entity": kind, "date": day, "text": text, "record": record})
    return sorted(result, key=lambda row: (bool(row["date"]), row["date"], str(row["record"].get("time", ""))), reverse=True)


def table_rows(rows):
    from agent_v2.schema import NAME_FIELDS
    result = []
    for row in rows:
        r, entity = row["record"], row["entity"]
        result.append({"日期": row["date"] or "未记录/无效日期", "类型": NAMES[entity],
            "活动 / 事件": r.get(NAME_FIELDS.get(entity, "")) or NAMES[entity],
            "分类": CATEGORIES.get(r.get("category"), "生活回忆" if entity == "MEMORY" else ""),
            "时长(分钟)": r.get("duration_minutes", ""), "描述": r.get("description", ""),
            "时间": r.get("time", ""), "食物": "、".join(r.get("foods") or []),
            "奶量(ml)": r.get("amount_ml", ""), "体重(kg)": r.get("weight_kg", ""),
            "身高(cm)": r.get("height_cm", ""), "头围(cm)": r.get("head_circumference_cm", ""),
            "月龄": r.get("age_months", ""), "体温(℃)": r.get("temperature_c", ""),
            "照片": len(r.get("photos", [])), "编号": r.get("id", ""), "内容": row["text"]})
    return result


def export_csv(rows):
    stream = io.StringIO()
    fields = ["日期", "类型", "活动 / 事件", "分类", "时长(分钟)", "描述", "时间", "食物", "奶量(ml)",
              "体重(kg)", "身高(cm)", "头围(cm)", "月龄", "体温(℃)", "照片", "编号", "内容"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in table_rows(rows):
        # Neutralize spreadsheet formula injection in user supplied strings.
        writer.writerow({k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
                         for k, v in row.items()})
    return stream.getvalue().encode("utf-8-sig")


def daily_summary(data, day):
    date.fromisoformat(day)
    rows = browse_records(data, start=day, end=day, include_missing=False)
    lines = [f"宝宝每日记录 · {day}", "仅汇总截至发送时已确认、事件日期为当天的记录；未记录不等于未发生。"]
    if not rows:
        lines.append("这一天暂时没有已确认的记录。")
    for kind in ENTITIES:
        selected = [r["record"] for r in rows if r["entity"] == kind]
        if not selected:
            continue
        lines.append(f"\n{NAMES[kind]}：{len(selected)}条")
        if kind == "FEEDING":
            amounts = [r["amount_ml"] for r in selected if isinstance(r.get("amount_ml"), (int, float)) and not isinstance(r.get("amount_ml"), bool)]
            if amounts:
                lines.append(f"已记录奶量合计：{sum(amounts):g}毫升（{len(amounts)}条含奶量记录）")
        if kind == "ACTIVITY":
            durations = [r["duration_minutes"] for r in selected if isinstance(r.get("duration_minutes"), (int, float)) and not isinstance(r.get("duration_minutes"), bool)]
            if durations:
                lines.append(f"记录时长合计：{sum(durations):g}分钟；同名/不同分类记录可能重复，不等于实际活动总时长。")
        for record in selected[:3]:
            text = describe(record)
            lines.append("• " + (text[:180] + "…" if len(text) > 180 else text))
        if len(selected) > 3:
            lines.append(f"其余{len(selected)-3}条请在档案总览按日期查看。")
    missing = len(browse_records(data, missing_only=True))
    if missing:
        lines.append(f"\n另有{missing}条历史记录缺少有效日期，未计入本日报。")
    return "\n".join(lines)
