from rag.retriever import (
    build_document_chunks,
    retrieve_chunks
)


FILE_PATH = (
    "knowledge/"
    "healthy_parenting_guide_0_3.pdf"
)


QUESTIONS = [
    "怎样和一岁宝宝交流和玩耍？",
    "一岁宝宝每天应该睡多长时间？",
    "一岁宝宝应该多久做一次健康检查？",
    "怎么预防宝宝烧伤和烫伤？",
    "汽车发动机应该怎么维修？",
    "现在应该购买哪一只股票？"
]


def evaluate_real_retrieval():

    chunks = build_document_chunks(
        FILE_PATH,
        chunk_size=300,
        overlap=50
    )

    print("知识片段数量：", len(chunks))

    for question in QUESTIONS:

        print()
        print("=" * 60)
        print("问题：", question)

        results = retrieve_chunks(
            question,
            chunks,
            top_k=3,
            min_score=0
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            print()
            print(
                f"结果{index}｜"
                f"分数={result['score']:.4f}｜"
                f"第{result['page']}页"
            )

            print(result["text"][:200])


if __name__ == "__main__":

    evaluate_real_retrieval()