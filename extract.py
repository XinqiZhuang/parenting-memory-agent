from dotenv import load_dotenv
from openai import OpenAI
import os
import json
from pydantic import ValidationError
from models import ExtractedData

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

class ExtractionError(Exception):
    """
    DeepSeek输出无法解析或校验时抛出的错误。
    """

    pass

def validate_extracted_data(data):
    """
    使用Pydantic校验DeepSeek提取结果,
    并转换成干净的普通字典。
    """

    try:
        validated_data = (
            ExtractedData.model_validate(data)
        )

    except ValidationError as error:

        print("\n=== Pydantic校验失败 ===")
        print(error)
        print("========================\n")

        raise ExtractionError(
            "DeepSeek提取的数据没有通过校验。"
        ) from error

    return validated_data.model_dump()

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

def parse_extracted_response(result_text):
    """
    将DeepSeek返回的文本解析并校验，
    最终返回干净的普通字典。
    """

    try:
        result = json.loads(result_text)

    except json.JSONDecodeError as error:

        print("\n=== JSON解析失败 ===")
        print(error)
        print("====================\n")

        raise ExtractionError(
            "DeepSeek没有返回合法的JSON。"
        ) from error

    return validate_extracted_data(result)


def extract_data(
    user_input,
    operation="ADD"
):

    normalized_operation = (
        operation.upper().strip()
    )

    if normalized_operation == "UPDATE":

        operation_prompt = """

当前任务类型是UPDATE。

用户描述的可能不是一个新发生的事件，
而是要求修改一条已经存在的记录。

UPDATE提取规则：

1. 不要因为这是修改指令就返回空列表。
2. 必须提取用户明确指定的目标记录。
3. development_milestones中：
   category表示目标记录的类别；
   skill表示用户想修改的能力名称；
   description表示用户要求改成的新描述。
4. “大运动”必须转换成gross_motor。
5. “精细动作”必须转换成fine_motor。
6. 用户没有要求修改的字段使用null，
   不要自行补充。
7. “不要修改日期”表示date应为null，
   不能把这句话写进description。
8. 只提取用户明确要求的新值，
   不要编造日期或月龄。

示例：

用户输入：
请修改宝宝的大运动发展记录：
把独立行走的描述改为多人协同测试，
不要修改日期。

应该返回：

{
    "development_milestones": [
        {
            "category": "gross_motor",
            "skill": "独立行走",
            "description": "多人协同测试",
            "date": null,
            "age_months": null
        }
    ],
    "learning_activities": [],
    "feeding_records": [],
    "health_records": [],
    "memories": []
}
"""

    elif normalized_operation == "ADD":

        operation_prompt = """

当前任务类型是ADD。

请提取用户陈述的新发生的宝宝事件。
不要把修改指令理解为新记录。
"""

    else:
        raise ValueError(
            f"不支持的操作类型：{operation}"
        )

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

""" + operation_prompt

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
    
    return parse_extracted_response(
        result_text
    )


