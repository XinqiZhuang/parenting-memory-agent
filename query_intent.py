import json
from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def classify_query(user_input):

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": """
你是一个育儿数据查询助手。

请判断用户想查询哪一种宝宝数据。

只能返回以下类型：

QUERY_WEIGHT
QUERY_HEIGHT
QUERY_HEAD_CIRCUMFERENCE
QUERY_DEVELOPMENT
QUERY_FEEDING
QUERY_HEALTH
QUERY_LEARNING
QUERY_MEMORY
QUERY_ACTIVITY
ANALYZE_ACTIVITY
ANALYZE_DEVELOPMENT
ANALYZE_FEEDING
UNKNOWN

含义：

QUERY_WEIGHT:
查询体重。

QUERY_HEIGHT:
查询身高。

QUERY_HEAD_CIRCUMFERENCE:
查询头围。

QUERY_DEVELOPMENT:
查询成长发育里程碑。

QUERY_FEEDING:
查询饮食、奶量、辅食。

QUERY_HEALTH:
查询健康、排便、生病等信息。

QUERY_LEARNING:
查询早教、游戏、玩具、训练等。

QUERY_MEMORY:
查询特殊事件或家庭记录。

QUERY_ACTIVITY:
用户询问宝宝玩过什么活动、早教活动、游戏、玩具等记录。

ANALYZE_ACTIVITY:
分析宝宝近期参与的活动是否适合当前月龄，以及可能涉及哪些发展能力

ANALYZE_DEVELOPMENT:
分析宝宝当前的成长发展情况，并结合历史记录进行评价

ANALYZE_FEEDING:
分析宝宝近期的饮食/辅食记录，并根据相关信息提供建议

判断规则：

QUERY:
用户只是想知道已经记录的事实信息，例如：
“宝宝什么时候开始爬？”
“宝宝最近玩了什么？”
“宝宝有哪些大运动发展记录？”

ANALYZE:
用户希望 AI 对已有数据进行评价、判断、比较或提供建议，例如：
“宝宝最近玩的游戏适合他吗？”
“宝宝现在的大运动发展怎么样？”
“宝宝最近的辅食安排合理吗？”

UNKNOWN:
无法判断。



target:
表示用户具体想查询的某一个对象。

如果用户查询的是整个类别，而不是某一个具体对象，则 target 必须为空字符串。

category:
表示用户想查询的数据类别。

对于成长发育：

gross_motor = 大运动
fine_motor = 精细动作
cognitive = 认知
language = 语言
social = 社交

示例：

用户：
宝宝什么时候开始爬？

返回：
{
    "query_type": "QUERY_DEVELOPMENT",
    "target": "爬",
    "category": "gross_motor",
    "reason": "用户询问具体的爬行发展里程碑"
}

用户：
宝宝什么时候开始扶站？

返回：
{
    "query_type": "QUERY_DEVELOPMENT",
    "target": "扶站",
    "category": "gross_motor",
    "reason": "用户询问具体的扶站发展里程碑"
}

用户：
宝宝有哪些大运动发展记录？

返回：
{
    "query_type": "QUERY_DEVELOPMENT",
    "target": "",
    "category": "gross_motor",
    "reason": "用户希望查看全部大运动发展记录"
}

用户：
宝宝有哪些精细动作发展？

返回：
{
    "query_type": "QUERY_DEVELOPMENT",
    "target": "",
    "category": "fine_motor",
    "reason": "用户希望查看全部精细动作发展记录"
}

用户：宝宝最近玩了什么游戏？
返回：
{
    "query_type": "QUERY_ACTIVITY",
    "target": "",
    "category": "",
    "reason": "用户询问宝宝近期参与过的活动"
}

用户：宝宝最近玩的游戏适合他吗？
返回：
{
    "query_type": "ANALYZE_ACTIVITY",
    "target": "",
    "category": "",
    "reason": "用户希望分析宝宝活动与当前月龄的匹配情况"
}

请严格返回 JSON:

{
    "query_type": "",
    "target": "",
    "category": "",
    "reason": ""
}

不要输出其他内容。
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

