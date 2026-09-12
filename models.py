from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)


class DevelopmentMilestone(BaseModel):
    """
    一条成长发育里程碑记录。
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    category: Literal[
        "gross_motor",
        "fine_motor",
        "cognitive",
        "language",
        "social"
    ]

    skill: str = Field(
        min_length=1
    )

    description: Optional[str] = None

    date: Optional[str] = None

    age_months: Optional[float] = Field(
        default=None,
        ge=0,
        le=216
    )


class GrowthRecord(BaseModel):
    """
    一条身高、体重、头围测量记录。
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    date: Optional[str] = None

    age_months: Optional[float] = Field(
        default=None,
        ge=0,
        le=216
    )

    height_cm: Optional[float] = Field(
        default=None,
        ge=0
    )

    weight_kg: Optional[float] = Field(
        default=None,
        ge=0
    )

    head_circumference_cm: Optional[float] = Field(
        default=None,
        ge=0
    )

class ExtractedData(BaseModel):
    """
    DeepSeek一次信息提取的完整结果。
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    development_milestones: list[
        DevelopmentMilestone
    ] = Field(
        default_factory=list
    )

    learning_activities: list[
        dict
    ] = Field(
        default_factory=list
    )

    feeding_records: list[
        dict
    ] = Field(
        default_factory=list
    )

    health_records: list[
        dict
    ] = Field(
        default_factory=list
    )

    memories: list[
        dict
    ] = Field(
        default_factory=list
    )