import os

from dotenv import load_dotenv
from openai import OpenAI

from rag.retriever import (
    build_document_chunks,
    retrieve_chunks
)


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def answer_with_rag(
    question,
    file_path,
    top_k=3,
    chunk_size=300,
    overlap=50,
    min_score=0.04
):

    chunks = build_document_chunks(
        file_path,
        chunk_size=chunk_size,
        overlap=overlap
    )

    retrieved_chunks = retrieve_chunks(
        question,
        chunks,
        top_k=top_k,
        min_score=min_score
    )

    if not retrieved_chunks:

        return {
            "answer": "没有找到可以用于回答的育儿资料。",
            "sources": []
        }

    context_parts = []

    for index, result in enumerate(
        retrieved_chunks,
        start=1
    ):

        file_name = result.get(
            "file",
            file_path
        )

        page_number = result.get("page")

        if page_number:

            source_location = (
                f"{file_name}，第{page_number}页"
            )

        else:

            source_location = file_name

        context_parts.append(
            f"[资料{index}]\n"
            f"来源：{source_location}\n"
            f"内容：{result['text']}"
        )

    context = "\n\n".join(context_parts)

    response = client.chat.completions.create(
        model="deepseek-chat",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """
你是一个谨慎的育儿知识助手。

请只根据提供的资料回答用户问题。

规则：
1. 不要使用资料之外的知识进行补充。
2. 如果资料不足，请明确说明资料不足。
3. 回答中的重要结论必须使用[资料1]、[资料2]这样的格式标注来源。
4. 不要进行医学诊断。
5. 只有资料明确建议咨询医生，或者用户明确描述紧急健康症状时，才可以提出就医建议。
6. 不要添加资料中没有出现的风险、症状、判断或建议。
7. 回答中的每一个具体数字、年龄范围和结论，都必须能够在资料原文中直接找到。
8. 不要根据常识或模型自身知识补充资料中没有明确写出的内容。
9. 如果资料文字残缺，不要猜测残缺部分。
10. 为了匹配资料中的年龄术语，可以使用以下年龄阶段规则：

- 未满1周岁，归入婴儿期。
- 满1周岁但未满3周岁，归入幼儿期。

这些规则只能用于年龄阶段的术语匹配，
不能用于补充资料中不存在的其他育儿知识。

例如：
用户询问“一岁宝宝”，可以使用资料中“幼儿期”的内容回答。
用户询问“八个月宝宝”，可以使用资料中“婴儿期”的内容回答。
"""
            },
            {
                "role": "user",
                "content": f"""
用户问题：
{question}

可参考的资料：
{context}
"""
            }
        ]
    )

    answer = response.choices[0].message.content

    sources = []

    for index, result in enumerate(
        retrieved_chunks,
        start=1
    ):

        sources.append({
            "source_id": index,
            "file": result.get("file", file_path),
            "page": result.get("page"),
            "text": result["text"],
            "score": result["score"]
        })

    return {
        "answer": answer,
        "sources": sources
    }