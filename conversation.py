FOLLOW_UP_KEYWORDS = [
    "我是问",
    "我的意思是",
    "最近一次",
    "最新一次",
    "那最近呢",
    "那这个呢",
    "这个呢",
    "它呢",
    "刚才说的",
    "上一条",
    "前面那条"
]

FOLLOW_UP_PREFIXES = [
    "那",
    "这个",
    "这条",
    "它",
    "刚才",
    "上一条",
    "前面"
]


def is_follow_up(user_input):

    text = user_input.strip()

    if not text:
        return False

    short_input = len(text) <= 40

    contains_follow_up_word = any(
        keyword in text
        for keyword in FOLLOW_UP_KEYWORDS
    )

    starts_with_follow_up_word = any(
        text.startswith(prefix)
        for prefix in FOLLOW_UP_PREFIXES
    )

    confirmation_question = (
        "不是" in text
        and (
            text.endswith("吗")
            or text.endswith("吗？")
            or text.endswith("吗?")
        )
    )

    return (
        short_input
        and (
            contains_follow_up_word
            or starts_with_follow_up_word
            or confirmation_question
        )
    )


def build_contextual_input(
    user_input,
    previous_user_input="",
    previous_assistant_answer=""
):

    if (
        previous_user_input
        and is_follow_up(user_input)
    ):

        context_parts = [
            f"上一轮用户问题：{previous_user_input}"
        ]

        if previous_assistant_answer:
            context_parts.append(
                "上一轮助手回答："
                f"{previous_assistant_answer}"
            )

        context_parts.append(
            f"当前用户问题：{user_input}"
        )

        return "\n".join(context_parts)

    return user_input