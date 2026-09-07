import os
from openai import OpenAI
from dotenv import load_dotenv
from age import calculate_age_months


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def analyze_activities(baby, activities):

    birth_date = baby["profile"]["birth_date"]
    age_months = calculate_age_months(birth_date)

    prompt = f"""
你是一名儿童早期发展分析助手。

请根据下面宝宝的信息和活动记录进行分析。

宝宝当前月龄：
{age_months}个月

活动记录：
{activities}

请分析：

1. 这些活动主要涉及哪些发展能力？
2. 是否与宝宝当前月龄阶段的需求匹配？
3. 可以继续保持哪些活动？
4. 还可以增加哪些类型的活动？

请用简单、清晰的中文回答。
不要虚构宝宝没有提供的信息。
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content