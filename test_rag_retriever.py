from rag.retriever import (
    read_document,
    split_text,
    retrieve_chunks
)


def test_retrieve_relevant_parenting_text():

    text = read_document(
        "knowledge/test_parenting_guide.txt"
    )

    chunks = split_text(
        text,
        chunk_size=80,
        overlap=20
    )

    results = retrieve_chunks(
        "宝宝刚开始走路，需要注意什么？",
        chunks,
        top_k=2,
        min_score=0.10
    )

    assert len(results) == 1

    assert "行走" in results[0]["text"]

    assert results[0]["score"] > 0.1


if __name__ == "__main__":

    test_retrieve_relevant_parenting_text()

    print("RAG检索测试通过")