import os
import tempfile

import baby
import pending

from baby import load_baby, save_baby
from pending import set_pending_action
from router import route_request


def test_pending_update_flow():

    with tempfile.TemporaryDirectory() as temp_dir:

        # 使用临时数据文件，不碰真实baby.json
        baby.DATA_FILE = os.path.join(
            temp_dir,
            "baby.json"
        )

        pending.PENDING_FILE = os.path.join(
            temp_dir,
            "pending_action.json"
        )

        sample_baby = {
            "profile": {
                "name": "测试宝宝",
                "birth_date": "2025-09-01"
            },
            "feeding_records": [],
            "development_milestones": [
                {
                    "category": "gross_motor",
                    "skill": "独立行走",
                    "date": "2026-08-30",
                    "age_months": 11.9,
                    "description": "第一次尝试独立走"
                },
                {
                    "category": "gross_motor",
                    "skill": "独立行走",
                    "date": "2026-09-01",
                    "age_months": 12.0,
                    "description": "能够独立走几步"
                }
            ]
        }

        save_baby(sample_baby)

        # 模拟上一轮出现多个候选
        set_pending_action(
            {
                "type": "UPDATE_DEVELOPMENT",
                "candidates": [
                    record.copy()
                    for record
                    in sample_baby[
                        "development_milestones"
                    ]
                ],
                "new_record": {
                    "category": "gross_motor",
                    "skill": "独立行走",
                    "date": "2026-09-06",
                    "age_months": 12.2,
                    "description": "更正为这一天第一次独立行走"
                }
            }
        )

        # 模拟用户下一轮回答
        result = route_request("第2条")

        updated_baby = load_baby()

        first_record = updated_baby[
            "development_milestones"
        ][0]

        second_record = updated_baby[
            "development_milestones"
        ][1]

        print("Agent返回：", result)
        print("第一条记录：", first_record)
        print("第二条记录：", second_record)

        # 第一条不能被修改
        assert (
            first_record["date"]
            == "2026-08-30"
        )

        # 升级安全边界：旧版待确认请求不得直接执行，需重新预览。
        assert (
            second_record["date"]
            == "2026-09-01"
        )
        assert "旧版待确认请求" in result

        # 完成后pending文件应被清除
        assert not os.path.exists(
            pending.PENDING_FILE
        )

        print(
            "\nPASS：pending多轮更新闭环测试通过"
        )


if __name__ == "__main__":
    test_pending_update_flow()
