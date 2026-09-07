# from baby import load_baby
from conflict import (
    find_development_candidates,
    rank_development_candidates,
    choose_development_candidate
)


baby = {
    "development_milestones": [
        {
            "category": "gross_motor",
            "skill": "独立走",
            "date": "2026-09-02",
            "description": "宝宝第一次独立走了三步"
        },
        {
            "category": "gross_motor",
            "skill": "独立走",
            "date": "2026-09-03",
            "description": "宝宝第一次独立走了五步"
        }
    ]
}


new_record = {
    "category": "gross_motor",
    "skill": "独立行走",
    "description": "宝宝第一次独立走"
}


candidates = find_development_candidates(
    baby,
    new_record
)

print("候选数量：", len(candidates))


ranked = rank_development_candidates(
    candidates,
    new_record
)

for item in ranked:
    print()
    print("分数：", item["score"])
    print("记录：", item["record"])


choice = choose_development_candidate(
    ranked
)

print()
print("选择结果：", choice)