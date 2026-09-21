from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


COLLECTIONS = {
    "GROWTH": "growth_records", "DEVELOPMENT": "development_milestones",
    "ACTIVITY": "learning_activities", "FEEDING": "feeding_records",
    "HEALTH": "health_records", "MEMORY": "memories", "PHOTO": "memories",
}
NAMES = {"GROWTH": "生长测量", "DEVELOPMENT": "发育里程碑", "ACTIVITY": "学习活动",
         "FEEDING": "喂养", "HEALTH": "健康", "MEMORY": "回忆", "PHOTO": "照片回忆"}
NAME_FIELDS = {"DEVELOPMENT": "skill", "ACTIVITY": "activity", "MEMORY": "event",
               "PHOTO": "event", "HEALTH": "type", "FEEDING": "type"}
CATEGORIES = {"gross_motor": "大运动", "fine_motor": "精细动作", "cognitive": "认知",
              "language": "语言", "social": "社交"}
ALLOWED_FIELDS = {
    "GROWTH": {"date", "age_months", "height_cm", "weight_kg", "head_circumference_cm"},
    "DEVELOPMENT": {"date", "age_months", "skill", "category", "description"},
    "ACTIVITY": {"date", "activity", "category", "duration_minutes", "description"},
    "FEEDING": {"date", "time", "type", "foods", "amount_ml", "description"},
    "HEALTH": {"date", "time", "type", "description", "temperature_c"},
    "MEMORY": {"date", "event", "description"}, "PHOTO": {"date", "event", "description"},
}
LABELS = {"date": "日期", "age_months": "月龄", "skill": "能力", "activity": "活动",
          "category": "分类", "duration_minutes": "时长(分钟)", "description": "描述",
          "weight_kg": "体重(kg)", "height_cm": "身高(cm)", "head_circumference_cm": "头围(cm)",
          "type": "类型", "foods": "食物", "amount_ml": "奶量(ml)", "event": "事件",
          "time": "时间", "temperature_c": "体温(℃)"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)


class Selector(StrictModel):
    scope: Literal["entity", "development_and_activity"] = "entity"
    id: str = ""
    name: str = ""
    category: str = ""
    date: str = ""
    start_date: str = ""
    end_date: str = ""
    type: str = ""
    time: str = ""
    missing_field: str = ""
    latest: bool = False
    earliest: bool = False
    reference: Literal["", "last", "another"] = ""
    metric: str = ""
    aggregate: Literal["list", "count", "sum", "average"] = "list"
    audit_scope: Literal["self", "family"] = "self"
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def valid_filters(self):
        for field in ("date", "start_date", "end_date"):
            value = getattr(self, field)
            if value:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError("日期必须是YYYY-MM-DD")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("日期范围起止颠倒")
        if self.latest and self.earliest:
            raise ValueError("不能同时查最新和最早")
        if self.category and self.category not in CATEGORIES:
            raise ValueError("分类无效")
        if self.metric and self.metric not in {"height_cm", "weight_kg", "head_circumference_cm", "amount_ml", "duration_minutes", "temperature_c", "age_months"}:
            raise ValueError("测量指标无效")
        if self.aggregate in {"sum", "average"} and not self.metric:
            raise ValueError("求和或平均必须指定metric")
        if self.missing_field and self.missing_field not in LABELS:
            raise ValueError("缺失字段无效")
        return self


class Command(StrictModel):
    action: Literal["ADD", "QUERY", "UPDATE", "DELETE", "RECLASSIFY", "ANALYZE", "KNOWLEDGE", "AUDIT", "UNDO", "UNKNOWN"]
    entity: Literal["GROWTH", "DEVELOPMENT", "ACTIVITY", "FEEDING", "HEALTH", "MEMORY", "PHOTO", "UNKNOWN"] = "UNKNOWN"
    selector: Selector = Field(default_factory=Selector)
    values: dict = Field(default_factory=dict)
    clear_fields: list[str] = Field(default_factory=list)
    reason: str = ""

    @model_validator(mode="after")
    def validate_payload(self):
        if self.clear_fields:
            allowed_clear = ALLOWED_FIELDS.get(self.entity, set()) - {NAME_FIELDS.get(self.entity)}
            if self.action != "UPDATE" or set(self.clear_fields) - allowed_clear or set(self.clear_fields) & set(self.values):
                raise ValueError("只可明确清空可选字段，不能与修改值重复")
        if self.selector.scope != "entity" and (self.action not in {"QUERY", "ANALYZE"} or self.entity not in {"DEVELOPMENT", "ACTIVITY"}):
            raise ValueError("跨类型检索只用于发展与活动的查询或分析")
        if self.action in {"ADD", "UPDATE"}:
            if self.values or not self.clear_fields:
                self.values = validate_values(self.entity, self.values, adding=self.action == "ADD")
        elif self.action == "RECLASSIFY":
            if self.entity not in {"MEMORY", "PHOTO"}:
                raise ValueError("目前只支持把回忆转为学习活动")
            self.values = validate_values("ACTIVITY", self.values)
            if set(self.values) - {"activity", "category"}:
                raise ValueError("转换类型时只修改活动名称和分类，保留原日期与描述")
        elif self.values:
            raise ValueError("查询等只读操作不接受写入字段")
        return self


def validate_values(entity, values, adding=False):
    if entity not in ALLOWED_FIELDS or not values:
        raise ValueError("请提供明确的记录类型和内容")
    unknown = set(values) - ALLOWED_FIELDS[entity]
    if unknown:
        raise ValueError("不支持的字段：" + ",".join(sorted(unknown)))
    numeric = {"age_months", "height_cm", "weight_kg", "head_circumference_cm",
               "amount_ml", "duration_minutes", "temperature_c"}
    cleaned = {}
    for key, value in values.items():
        if value is None:
            raise ValueError("缺失字段请省略；不允许null覆盖已有信息")
        if key in numeric:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key}必须是数字")
            import math
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{key}必须是非负有限数字")
        elif key == "foods":
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                raise ValueError("食物必须是非空文本列表")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key}必须是非空文本")
        if key == "date":
            try:
                valid_date = date.fromisoformat(value).isoformat() == value
            except ValueError:
                valid_date = False
            if not valid_date:
                raise ValueError("日期无效，请填写真实日期，例如2026-09-20；照片日期不清楚可填“未知”")
        if key == "category" and value not in CATEGORIES:
            raise ValueError("分类无效")
        cleaned[key] = value.strip() if isinstance(value, str) else value
    if adding:
        name_field = NAME_FIELDS.get(entity)
        if name_field and not cleaned.get(name_field):
            raise ValueError(f"新增记录需要{LABELS[name_field]}")
        if entity == "GROWTH" and not (set(cleaned) & {"height_cm", "weight_kg", "head_circumference_cm"}):
            raise ValueError("生长记录至少需要一个测量值")
    return cleaned
