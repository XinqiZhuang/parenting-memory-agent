from rag.generator import answer_with_rag


question = "一岁宝宝每天应该睡多长时间？"

result = answer_with_rag(
    question=question,
    file_path=(
        "knowledge/"
        "healthy_parenting_guide_0_3.pdf"
    ),
    top_k=3,
    chunk_size=500,
    overlap=150,
    min_score=0.04
)

print()
print("问题：")
print(question)

print()
print("回答：")
print(result["answer"])

print()
print("引用来源：")

for source in result["sources"]:

    print(
        f"[资料{source['source_id']}] "
        f"{source['file']} "
        f"第{source['page']}页 "
        f"相关度={source['score']:.4f}"
    )

    print(source["text"])
    print()