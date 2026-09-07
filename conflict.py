from baby import load_baby, save_baby
from normalize import normalize_development_skill

def update_feeding_record(baby, new_record):
    for record in baby["feeding_records"]:
        if (
            record.get("date") == new_record.get("date") and
            record.get("time") == new_record.get("time") and
            record.get("type") == new_record.get("type")
        ):
            record.update(new_record)
            return True
    return False

def find_development_candidates(baby, new_record):

    target_skill = normalize_development_skill(
        new_record.get("skill", "")
    )

    target_category = new_record.get(
        "category",
        ""
    )

    candidates = []

    for record in baby["development_milestones"]:

        old_skill = normalize_development_skill(
            record.get("skill", "")
        )

        old_category = record.get(
            "category",
            ""
        )

        if (
            old_skill == target_skill
            and
            old_category == target_category
        ):
            candidates.append(record)

    return candidates

def rank_development_candidates(
    candidates,
    new_record
):

    ranked = []

    new_date = new_record.get("date", "")
    new_description = new_record.get(
        "description",
        ""
    )

    for record in candidates:

        score = 0

        old_date = record.get("date", "")
        old_description = record.get(
            "description",
            ""
        )

        # 日期完全一致，优先级最高
        if (
            new_date
            and old_date
            and new_date == old_date
        ):
            score += 3

        # 描述中有相同关键词时，加分
        if (
            new_description
            and old_description
        ):

            for keyword in [
                "第一次",
                "开始",
                "独立",
                "扶着",
                "走",
                "站",
                "爬"
            ]:

                if (
                    keyword in new_description
                    and
                    keyword in old_description
                ):
                    score += 1

        ranked.append(
            {
                "record": record,
                "score": score
            }
        )

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return ranked

def choose_development_candidate(ranked_candidates):

    if not ranked_candidates:
        return {
            "status": "NOT_FOUND",
            "record": None
        }

    if len(ranked_candidates) == 1:
        return {
            "status": "MATCHED",
            "record": ranked_candidates[0]["record"]
        }

    first = ranked_candidates[0]
    second = ranked_candidates[1]

    if first["score"] > second["score"]:
        return {
            "status": "MATCHED",
            "record": first["record"]
        }

    return {
        "status": "AMBIGUOUS",
        "record": None
    }


def update_development_record(baby, new_record):

    candidates = find_development_candidates(
        baby,
        new_record
    )

    ranked = rank_development_candidates(
        candidates,
        new_record
    )

    choice = choose_development_candidate(
        ranked
    )

    status = choice["status"]

    if status == "NOT_FOUND":
        return {
            "status": "NOT_FOUND",
            "record": None
        }

    elif status == "AMBIGUOUS":
        return {
            "status": "AMBIGUOUS",
            "record": None,
            "candidates": [
                item["record"]
                for item in ranked
            ]
        }

    elif status == "MATCHED":

        target_record = choice["record"]

        # 把new_record的skill标准化，并把标准值写给new_record
        normalized_skill = normalize_development_skill(
            new_record.get("skill", "")
        )
        new_record["skill"] = normalized_skill

        target_record.update(new_record)

        return {
            "status": "UPDATED",
            "record": target_record
        }

    else:
        return {
            "status": "ERROR",
            "record": None
        }


