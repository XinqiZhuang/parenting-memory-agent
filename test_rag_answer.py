from rag.generator import answer_with_rag
from types import SimpleNamespace


def test_rag_answer(monkeypatch):

    def fake_completion(**kwargs):
        assert "行走" in kwargs["messages"][-1]["content"]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content="应提供有成人看护的活动空间[资料1]。"
        ))])
    monkeypatch.setattr("rag.generator.client.chat.completions.create", fake_completion)

    result = answer_with_rag(
        question="宝宝刚开始走路，需要注意什么？",
        file_path="knowledge/test_parenting_guide.txt",
        top_k=2,
        chunk_size=80,
        overlap=20,
        min_score=0.1
    )

    print()
    print("RAG回答：")
    print(result["answer"])

    print()
    print("检索来源：")

    for source in result["sources"]:
        print(
            source["source_id"],
            source["score"],
            source["text"]
        )

    assert result["answer"]
    assert 1 <= len(result["sources"]) <= 2
    assert "行走" in result["sources"][0]["text"]
    assert "[资料1]" in result["answer"]
    assert "咨询医生" not in result["answer"]


def test_rag_rejects_irrelevant_question():

    result = answer_with_rag(
        question="汽车发动机应该怎么维修？",
        file_path="knowledge/test_parenting_guide.txt",
        top_k=2,
        chunk_size=80,
        overlap=20,
        min_score=0.1
    )

    assert result["sources"] == []

    assert "没有找到" in result["answer"]

if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
