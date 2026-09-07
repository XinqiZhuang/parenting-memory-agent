DEVELOPMENT_SKILL_SYNONYMS = {
    "爬行": "爬",
    "会爬": "爬",
    "开始爬": "爬",

    "走路": "独立走",
    "行走": "独立走",
    "独立行走": "独立走",
    "独立走路": "独立走",
    "会走": "独立走",

    "独立站立": "独立站",
    "独立站": "独立站",
    "自己站": "独立站",
    "自己站立": "独立站",

    "扶着站": "扶站",
    "扶站起来": "扶站",
    "开始扶站": "扶站"
}


def normalize_development_skill(skill):

    if not skill:
        return ""

    return DEVELOPMENT_SKILL_SYNONYMS.get(
        skill,
        skill
    )