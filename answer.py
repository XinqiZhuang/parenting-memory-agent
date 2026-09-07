import json

from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def generate_answer(user_input, data):

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