import os

from dotenv import load_dotenv
from openai import OpenAI

from rag.retriever import (
    read_document,
    split_text,
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
    min_score=0.025
):

    document_text = read_document(file_path)

    chunks = split_text(document_text, chunk_size=chunk_size, overlap=overlap)

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

        context_parts.append(
            f"[资料{index}]\n{result['text']}"
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
            "file": file_path,
            "text": result["text"],
            "score": result["score"]
        })

    return {
        "answer": answer,
        "sources": sources
    }