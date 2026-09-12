import json
from pathlib import Path

from extract import extract_data
from evaluation.extraction_cases import EXTRACTION_CASES


def run_check(extracted_data, check):

    records = extracted_data.get(check["list"], [])
    check_type = check["type"]

    if check_type == "not_empty":
        return len(records) > 0

    if check_type == "empty":
        return len(records) == 0

    if check_type == "field_equals":

        field = check["field"]
        expected = check["expected"]

        return any(
            record.get(field) == expected
            for record in records
        )

    return False


def evaluate_extraction():

    results = []
    passed_count = 0

    for index, case in enumerate(
        EXTRACTION_CASES,
        start=1
    ):

        try:
            extracted_data = extract_data(case["input"])

            check_results = [
                run_check(extracted_data, check)
                for check in case["checks"]
            ]

            passed = all(check_results)
            error = ""

        except Exception as exception:
            extracted_data = {}
            check_results = []
            passed = False
            error = str(exception)

        if passed:
            passed_count += 1

        results.append({
            "id": index,
            "input": case["input"],
            "passed": passed,
            "checks": case["checks"],
            "check_results": check_results,
            "extracted_data": extracted_data,
            "error": error
        })

        status = "通过" if passed else "失败"

        print(
            f"{index}. [{status}] "
            f"输入={case['input']}"
        )

    total_count = len(EXTRACTION_CASES)
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

    results_file = (
        results_directory /
        "extraction_results.json"
    )

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
    evaluate_extraction()