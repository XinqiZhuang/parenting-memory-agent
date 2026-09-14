FOLLOW_UP_KEYWORDS = [
    "我是问",
    "我的意思是",
    "最近一次",
    "最新一次",
    "那最近呢",
    "那这个呢",
    "这个呢",
    "它呢"
]


def is_follow_up(user_input):

    short_input = (
        len(user_input.strip()) <= 20
    )

    contains_follow_up_word = any(
        keyword in user_input
        for keyword in FOLLOW_UP_KEYWORDS
    )

    return (
        short_input
        and contains_follow_up_word
    )


def build_contextual_input(
    user_input,
    previous_user_input=""
):

    if (
        previous_user_input
        and is_follow_up(user_input)
    ):

        return (
            f"上一轮问题："
            f"{previous_user_input}\n"
            f"用户补充："
            f"{user_input}"
        )

    return user_input