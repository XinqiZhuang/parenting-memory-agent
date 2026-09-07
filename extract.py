from dotenv import load_dotenv
from openai import OpenAI
import os
import json

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# user_input = input("请记录宝宝今天发生的事情：")

def extract_data(user_input):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
            "role": "system",
            "content": """ 
你是一个宝宝成长记录助手。

请从用户输入中提取与宝宝成长有关的信息。

请严格按照以下 JSON 结构返回：
{
    "development_milestones": [
        {
            "category": "",
            "skill": "",
            "description": ""
        }
    ],

    "learning_activities": [
        {
            "activity": "",
            "category": "",
            "duration_minutes": null
        }
    ],

    "feeding_records": [
        {
            "date": "",
            "time": "",
            "type": "",
            "foods": [],
            "amount_ml": null,
            "description": ""
        }
    ],

    "health_records": [
        {
            "type": "",
            "description": ""
        }
    ],

    "memories": [
        {
            "event": "",
            "description": ""
        }
    ]
}

规则：
1. 只提取用户明确提供的信息。
2. 不要猜测用户没有提供的信息。
3. 如果某一字段没有信息，使用 null 或空列表。
4. development_milestones 用于记录宝宝发展里程碑。
5. category 使用以下分类：
   gross_motor
   fine_motor
   cognitive
   language
   social
6. learning_activities 用于记录游戏、玩具、早教活动。
7. feeding_records 用于记录奶和辅食。
8. amount_ml 只有用户明确提供毫升数时才填写。
9. health_records 用于记录健康、排便等信息。
10. memories 用于记录第一次坐飞机、第一次坐火车等特殊事件。
11. 不要因为常识而补充用户没有说的信息。
12. 如果用户明确提到日期，请提取日期。
13. 如果用户说“今天”，使用当前日期。
14. 如果无法确定日期，不要猜测，填写空字符串。

"""
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    result_text = response.choices[0].message.content
    print("\n=== DeepSeek 原始返回 ===")
    print(repr(result_text))
    print("========================\n")
    result = json.loads(result_text)
    return result


