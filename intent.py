import json
from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def classify_intent(user_input):

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": """
你是一个育儿数据管理助手。

你的任务不是回答用户问题，
而是判断用户想对宝宝数据进行什么操作。

只能返回以下三种 intent:

ADD
UPDATE
QUERY

定义：

ADD:
用户提供了新的宝宝信息，希望加入宝宝档案。

UPDATE:
用户明确表示要修改、更正、纠正之前已经记录的信息。

QUERY:
用户正在提出关于宝宝的问题，希望查询、分析或了解宝宝相关信息。

注意：

如果用户希望分析宝宝已有的数据，例如：
“宝宝最近玩的游戏适合他吗？”
“宝宝现在的大运动发展怎么样？”
“宝宝最近的辅食安排合理吗？”

顶层 intent 仍然返回 QUERY。

后续系统会进一步判断这是普通查询还是分析任务。

请严格按照以下 JSON 格式返回：

{
    "intent": "",
    "reason": ""
}

不要输出 JSON 以外的任何内容。
"""
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    result_text = response.choices[0].message.content

    result = json.loads(result_text)

    return result