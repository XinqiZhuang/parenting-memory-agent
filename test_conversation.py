from conversation import (
    build_contextual_input,
    is_follow_up,
)


def test_detect_follow_up():

    assert is_follow_up(
        "我是问最近一次"
    )


def test_build_contextual_input():

    result = build_contextual_input(
        "我是问最近一次",
        "宝宝有哪些大运动记录？"
    )

    assert "大运动记录" in result
    assert "最近一次" in result


def test_independent_question_unchanged():

    result = build_contextual_input(
        "宝宝最近体重是多少？",
        "宝宝有哪些大运动记录？"
    )

    assert result == (
        "宝宝最近体重是多少？"
    )