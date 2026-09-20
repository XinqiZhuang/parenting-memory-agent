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
        temperature=0,
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
UPDATE 必须同时满足：

1. 用户明确要求修改、改成、更正、删除已有记录；
2. 用户提供了希望修改成的新内容。

以下情况不是 UPDATE，而是 QUERY：

- 用户询问某条记录是否存在；
- 用户询问某项活动属于什么能力；
- 用户使用“是不是”“不是……吗”“算不算”“对吗”等确认或反问语气；
- 用户对上一轮回答提出质疑，但没有明确要求修改数据。

示例：

用户：那这个套杯游戏不是精细动作训练吗？
返回：
{
    "intent": "QUERY",
    "reason": "用户在询问活动与发展能力的关系，没有要求修改记录"
}

用户：把套杯游戏的分类改成精细动作
返回：
{
    "intent": "UPDATE",
    "reason": "用户明确要求修改已有记录的分类"
}

如果输入同时包含“上一轮用户问题”“上一轮助手回答”
和“当前用户问题”，应以“当前用户问题”表达的需求为准。

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