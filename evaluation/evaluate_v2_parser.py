"""Explicit opt-in, live API evaluation on synthetic cases; no baby data mutations."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from agent_v2.parser import parse_command


BASE_CASES = [
    ("宝宝最近一次大运动是什么", "QUERY", "DEVELOPMENT", {"category": "gross_motor", "latest": True, "scope": "development_and_activity"}),
    ("记录宝宝今天第一次自己用勺子吃饭", "ADD", "DEVELOPMENT", {}),
    ("宝宝有哪些学习活动记录", "QUERY", "ACTIVITY", {}),
    ("宝宝有哪些精细动作训练", "QUERY", "ACTIVITY", {"category": "fine_motor"}),
    ("宝宝有套杯游戏的记录吗", "QUERY", "ACTIVITY", {"name": "套杯游戏"}),
    ("这个套杯游戏是精细动作训练吗", "ANALYZE", "ACTIVITY", {}),
    ("给没有日期的那条套杯游戏补上日期2026-08-30", "UPDATE", "ACTIVITY", {"missing_field": "date"}),
    ("把2026-08-27套杯游戏的日期改成2026-08-30", "UPDATE", "ACTIVITY", {"date": "2026-08-27"}),
    ("把套杯游戏的分类改成精细动作", "UPDATE", "ACTIVITY", {"name": "套杯游戏"}),
    ("记录宝宝今天体重10.6公斤", "ADD", "GROWTH", {}),
    ("宝宝最新体重是多少", "QUERY", "GROWTH", {"metric": "weight_kg", "latest": True}),
    ("宝宝2026-09-01到2026-09-20之间吃过哪些辅食", "QUERY", "FEEDING", {"start_date": "2026-09-01", "end_date": "2026-09-20"}),
    ("宝宝今天喝奶总共多少毫升", "QUERY", "FEEDING", {"aggregate": "sum", "metric": "amount_ml"}),
    ("记录宝宝今天早上喝了180毫升奶", "ADD", "FEEDING", {}),
    ("记录宝宝今天大便一次", "ADD", "HEALTH", {}),
    ("宝宝最近的排便记录", "QUERY", "HEALTH", {}),
    ("记录宝宝今天第一次坐飞机", "ADD", "MEMORY", {}),
    ("宝宝第一次站立的照片", "QUERY", "PHOTO", {}),
    ("删除2026-08-30那条套杯游戏记录", "DELETE", "ACTIVITY", {"date": "2026-08-30"}),
    ("操作日志", "AUDIT", "UNKNOWN", {}),
    ("撤销上次操作", "UNDO", "UNKNOWN", {}),
    ("一岁宝宝怎样安全地练习走路", "KNOWLEDGE", None, {}),
]


MEMORY_BOUNDARY_CASES = [
    ("记录宝宝昨天第一次去动物园", "ADD", "MEMORY", {}),
    ("宝宝第一次坐火车是哪天", "QUERY", "MEMORY", {}),
    ("记录宝宝今天第一次扶着栏杆站起来", "ADD", "DEVELOPMENT", {}),
    ("记录宝宝今天第一次叫妈妈", "ADD", "DEVELOPMENT", {}),
    ("记录宝宝今天第一次玩了10分钟套杯游戏", "ADD", "ACTIVITY", {}),
    ("把第一次坐飞机的日期改成2026-09-18", "UPDATE", "MEMORY", {}),
]
CASES = BASE_CASES + MEMORY_BOUNDARY_CASES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="使用.env里的DeepSeek密钥，会消耗少量API额度")
    args = parser.parse_args()
    if not args.live:
        print("默认不调用API。真实评估请运行：python -m evaluation.evaluate_v2_parser --live")
        return
    results = []
    for text, action, entity, selector in CASES:
        try:
            command = parse_command(text)
            passed = command.action == action and (entity is None or command.entity == entity)
            passed = passed and all(getattr(command.selector, k) == v for k, v in selector.items())
            if text.startswith("给没有日期") or text.startswith("把2026-08-27"):
                passed = passed and command.values.get("date") == "2026-08-30"
            if text == "把第一次坐飞机的日期改成2026-09-18":
                passed = passed and command.values.get("date") == "2026-09-18"
            item = {"input": text, "passed": bool(passed), "actual": command.model_dump()}
        except Exception as exc:
            item = {"input": text, "passed": False, "error": type(exc).__name__}
        results.append(item)
        print(("PASS " if item["passed"] else "FAIL ") + text, flush=True)
        if not item["passed"]:
            print("  期望：" + json.dumps({"action": action, "entity": entity, "selector": selector}, ensure_ascii=False), flush=True)
            print("  实际：" + json.dumps(item.get("actual", {"error": item.get("error")}), ensure_ascii=False), flush=True)
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "passed": sum(r["passed"] for r in results),
              "total": len(results), "scope": "synthetic live command parsing, not medical or whole-system accuracy", "cases": results}
    destination = Path(__file__).parent / "results" / "v2_live_parser_results.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    base_passed = sum(r["passed"] for r in results[:len(BASE_CASES)])
    boundary_passed = sum(r["passed"] for r in results[len(BASE_CASES):])
    print(f"原有用例：{base_passed}/{len(BASE_CASES)}；新增分类用例：{boundary_passed}/{len(MEMORY_BOUNDARY_CASES)}")
    print(f"通过：{report['passed']}/{report['total']}；报告：{destination}")
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
