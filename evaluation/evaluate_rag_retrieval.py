from evaluation.rag_cases import RAG_CASES
from rag.retriever import (
    build_document_chunks,
    retrieve_chunks,
)


FILE_PATH = (
    "knowledge/"
    "healthy_parenting_guide_0_3.pdf"
)


def contains_expected_keywords(
    results,
    expected_keywords
):
    for result in results:

        text = result["text"]

        if all(
            keyword in text
            for keyword in expected_keywords
        ):
            return True

    return False


def evaluate_case(case, chunks):

    results = retrieve_chunks(
        case["question"],
        chunks,
        top_k=3,
        min_score=0.04
    )

    if case["should_find"]:
        passed = contains_expected_keywords(
            results,
            case["expected_keywords"]
        )
    else:
        passed = len(results) == 0

    return passed, results


def main():

    chunks = build_document_chunks(
        FILE_PATH,
        chunk_size=500,
        overlap=150
    )

    passed_count = 0

    for index, case in enumerate(
        RAG_CASES,
        start=1
    ):

        passed, results = evaluate_case(
            case,
            chunks
        )

        if passed:
            passed_count += 1

        status = "通过" if passed else "失败"

        print(
            f"{index}. {status}｜"
            f"{case['question']}"
        )

        for rank, result in enumerate(
            results,
            start=1
        ):
            print(
                f"   Top {rank}："
                f"{result['score']:.4f}｜"
                f"第{result['page']}页"
            )

    total = len(RAG_CASES)

    accuracy = (
        passed_count / total * 100
        if total
        else 0
    )

    print("\n评估结果")
    print("总案例数：", total)
    print("通过数量：", passed_count)
    print(f"通过率：{accuracy:.1f}%")


if __name__ == "__main__":
    main()