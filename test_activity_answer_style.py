from activity_analysis import (
    choose_response_style,
    extract_current_question
)


def test_confirmation_question_is_concise():

    result = choose_response_style(
        "这个套杯游戏是精细动作训练吗？"
    )

    assert result == "concise"


def test_detailed_request_is_detailed():

    result = choose_response_style(
        "请全面分析宝宝最近的活动"
    )

    assert result == "detailed"


def test_normal_question_is_standard():

    result = choose_response_style(
        "宝宝最近进行了哪些活动"
    )

    assert result == "standard"


def test_extract_current_follow_up_question():

    contextual_input = (
        "上一轮用户问题：宝宝有套杯游戏吗\n"
        "上一轮助手回答：有两条记录\n"
        "当前用户问题：这个游戏是精细动作训练吗？"
    )

    result = extract_current_question(
        contextual_input
    )

    assert result == (
        "这个游戏是精细动作训练吗？"
    )