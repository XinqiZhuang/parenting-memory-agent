import json

from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def format_age_months(age_months):
    """
    将月龄格式化成容易阅读的文字。
    """

    if age_months is None:
        return None

    if isinstance(age_months, float):
        age_text = f"{age_months:g}"
    else:
        age_text = str(age_months)

    return f"{age_text}月龄"


def format_development_answer(data):
    """
    根据真实发育记录生成确定性回答。
    不调用大模型，不补充数据中不存在的信息。
    """

    status = data.get("status")

    if status in ["EMPTY", "NOT_FOUND"]:
        return data.get(
            "message",
            "目前没有找到相关成长发育记录。"
        )

    records = data.get("records", [])

    if not records:
        return "目前没有找到相关成长发育记录。"

    answer_lines = []

    for index, record in enumerate(
        records,
        start=1
    ):

        skill = record.get(
            "skill",
            "未命名的发育能力"
        )

        date = record.get("date")

        age_months = record.get(
            "age_months"
        )

        description = record.get(
            "description",
            ""
        )

        age_text = format_age_months(
            age_months
        )

        time_parts = []

        if date:
            time_parts.append(
                f"日期是{date}"
            )

        if age_text:
            time_parts.append(
                f"当时约{age_text}"
            )

        if time_parts:
            time_text = "，".join(
                time_parts
            )
        else:
            time_text = "没有记录具体时间"

        if len(records) == 1:
            line = (
                f"宝宝有一条“{skill}”记录："
                f"{time_text}。"
            )
        else:
            line = (
                f"{index}. “{skill}”："
                f"{time_text}。"
            )

        if not date and age_text:
            line += "没有记录具体日期。"

        if description:
            line += (
                f"原始描述：{description}"
            )

        answer_lines.append(line)

    return "\n".join(answer_lines)


def generate_answer(user_input, data):

    # 发育事实查询使用确定性代码回答
    if (
        isinstance(data, dict)
        and
        data.get("record_type")
        == "development"
    ):
        return format_development_answer(
            data
        )

    data_text = json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": """
你是一个育儿数据助手。

请严格根据提供的宝宝真实数据回答用户问题。

不要编造数据。

如果数据中没有相关信息，请明确告诉用户目前没有记录。

回答应该自然、简洁、容易理解。
"""
            },
            {
                "role": "user",
                "content": f"""
用户的问题：

{user_input}

宝宝的相关数据：

{data_text}

请根据这些数据回答用户。
"""
            }
        ]
    )

    return response.choices[0].message.content