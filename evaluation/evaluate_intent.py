import json
from pathlib import Path

from intent import classify_intent
from evaluation.intent_cases import INTENT_CASES


def evaluate_intent():

    results = []
    passed_count = 0

    for index, case in enumerate(INTENT_CASES, start=1):

        user_input = case["input"]
        expected = case["expected"]

        try:
            model_result = classify_intent(user_input)
            actual = model_result.get("intent")
            reason = model_result.get("reason", "")
            error = ""

        except Exception as exception:
            actual = "ERROR"
            reason = ""
            error = str(exception)

        passed = actual == expected

        if passed:
            passed_count += 1

        result = {
            "id": index,
            "input": user_input,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "reason": reason,
            "error": error
        }

        results.append(result)

        status = "通过" if passed else "失败"

        print(
            f"{index}. [{status}] "
            f"预期={expected} 实际={actual} "
            f"输入={user_input}"
        )

    total_count = len(INTENT_CASES)
    accuracy = passed_count / total_count

    summary = {
        "total": total_count,
        "passed": passed_count,
        "failed": total_count - passed_count,
        "accuracy": accuracy,
        "results": results
    }

    results_directory = Path("evaluation/results")
    results_directory.mkdir(parents=True, exist_ok=True)

    results_file = results_directory / "intent_results.json"

    with open(
        results_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            summary,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(f"总案例数：{total_count}")
    print(f"通过数量：{passed_count}")
    print(f"准确率：{accuracy:.1%}")
    print(f"详细结果：{results_file}")


if __name__ == "__main__":
    evaluate_intent()