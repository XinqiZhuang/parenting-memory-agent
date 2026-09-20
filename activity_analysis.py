import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from age import calculate_age_months


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def extract_current_question(question):

    marker = "当前用户问题："

    if marker in question:
        return question.rsplit(
            marker,
            1
        )[-1].strip()

    return question.strip()


def choose_response_style(question):

    current_question = extract_current_question(
        question
    )

    detailed_keywords = [
        "全面分析",
        "详细分析",
        "系统分析",
        "综合分析"
    ]

    if any(
        keyword in current_question
        for keyword in detailed_keywords
    ):
        return "detailed"

    if current_question.endswith(
        ("吗", "吗？", "吗?")
    ):
        return "concise"

    return "standard"


def analyze_activities(
    baby,
    activities,
    question=""
):

    birth_date = baby["profile"]["birth_date"]

    age_months = calculate_age_months(
        birth_date
    )

    current_question = extract_current_question(
        question
    )

    response_style = choose_response_style(
        question
    )

    activities_text = json.dumps(
        activities,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
用户当前问题：
{current_question}

宝宝当前月龄：
{age_months}个月

检索到的活动记录：
{activities_text}

回答模式：
{response_style}

回答规则：

1. 只回答用户当前提出的问题，不要自动扩展成完整育儿报告。
2. concise 模式：先直接回答“是”“不是”“部分是”或“资料不足”，随后用1至3句话解释，最多150个汉字，不要补充用户没有询问的活动建议。
3. standard 模式：用简短、清晰的中文回答，通常不超过3个短段落。
4. detailed 模式：只有用户明确要求全面或详细分析时，才分析发展能力、月龄匹配和活动建议。
5. 同一个活动可以同时涉及多种发展能力，不要强行把它限制为单一分类。
6. 区分“档案中记录的分类”和“根据儿童发展知识作出的分析判断”。
7. 不要虚构宝宝没有提供的信息。
8. 使用适合飞书纯文本消息的格式，不要使用Markdown标题、星号或分隔线。
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一名儿童早期发展分析助手。"
                    "你的回答应准确、克制，"
                    "并根据用户问题控制详细程度。"
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content