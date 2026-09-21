from pathlib import Path
from uuid import uuid4

import streamlit as st

from router import route_request
from rag.generator import answer_with_rag

from photo_memory_ui import (
    render_photo_memory_page,
)
from photo_memory import (
    search_photo_memories,
)
from family_features.access import require_web_access
from family_features.theme import apply_theme, render_brand
from family_features.record_management import render_dialogs
from family_features.media import resolve_photo
from conversation import (
    build_contextual_input,
)

PROJECT_DIR = Path(__file__).parent

def show_related_memories(
    photo_memories
):

    if not photo_memories:

        return


    st.markdown("#### 📷 相关照片回忆")


    for memory in photo_memories:

        st.markdown(
            f"**{memory['event']}**"
        )

        if memory.get("date"):

            st.caption(
                memory["date"]
            )

        if memory.get("description"):

            st.write(
                memory["description"]
            )


        photo_paths = memory.get(
            "photos",
            []
        )

        column_count = min(
            3,
            len(photo_paths)
        )

        if column_count == 0:

            continue


        columns = st.columns(
            column_count
        )


        for index, photo_path in enumerate(
            photo_paths
        ):

            try:
                full_path = resolve_photo(photo_path)
            except ValueError:
                continue

            if full_path.exists():

                columns[
                    index % column_count
                ].image(
                    str(full_path),
                    use_container_width=True
                )


st.set_page_config(
    page_title="玖玖的成长日记",
    page_icon="👶",
    layout="wide"
)

apply_theme()
require_web_access(show_logout=False)
render_brand()

if "agent_context_id" not in st.session_state:
    st.session_state["agent_context_id"] = "web:" + uuid4().hex
page_labels = {"档案总览": "档案总览", "照片回忆": "照片墙", "宝宝档案": "对话记录",
               "每日记录": "每日记录", "育儿知识库": "育儿知识库", "每日推送": "推送设置"}
mode = st.sidebar.radio(
    "请选择功能",
    list(page_labels), format_func=page_labels.get, key="diary_page", label_visibility="collapsed"
)
st.sidebar.markdown('<div class="diary-footer">一家人的成长记录<br>飞书与网页共用同一份档案</div>', unsafe_allow_html=True)
if st.session_state.get("_web_auth") and st.sidebar.button("退出登录"):
    st.session_state.clear()
    st.rerun()

if mode == "档案总览":
    from family_features.dashboard import render_dashboard
    render_dashboard()
    render_dialogs()
    st.stop()

if mode == "每日推送":
    from family_features.dashboard import render_push_settings
    render_push_settings()
    st.stop()

if mode == "每日记录":
    from family_features.dashboard import render_daily_records
    render_daily_records()
    render_dialogs()
    st.stop()


if mode == "照片回忆":

    render_photo_memory_page()
    render_dialogs()

    st.stop()

if mode == "宝宝档案":

    st.title("对话记录")
    st.caption("记录今天的小事，也可以查询、修改已经保存的成长记录。")

    message_key = "record_messages"

    input_hint = (
        "输入宝宝的成长记录，"
        "或者查询、修改已有记录"
    )

else:

    st.title("育儿知识库")
    st.caption("从已收录的育儿资料中寻找答案，并查看出处。")
    from rag.knowledge_base import knowledge_inventory
    with st.expander("已收录资料与读取状态"):
        st.dataframe(knowledge_inventory(), hide_index=True, use_container_width=True)
        st.caption("私有书籍用于家庭问答；回答时选中的少量片段会发送到配置的语言模型接口。")

    message_key = "rag_messages"

    input_hint = (
        "请输入需要查询的育儿问题"
    )


if message_key not in st.session_state:

    st.session_state[message_key] = []


messages = st.session_state[message_key]


for message in messages:

    with st.chat_message(message["role"]):

        st.write(message["content"])

        if message.get("sources"):

            with st.expander("查看引用资料"):

                for index, source in enumerate(
                    message["sources"],
                    start=1
                ):

                    st.markdown(
                        f"**资料{index}｜"
                        f"{source['file']}｜"
                        f"{('第' + str(source['page']) + '页｜') if source.get('page') else ''}"
                        f"相关度 {source['score']:.4f}**"
                    )

                    st.write(source["text"])

        show_related_memories(
            message.get(
                "photo_memories",
                []
            )
        )


user_input = st.chat_input(
    input_hint
)


if user_input:

    previous_user_input = ""

    for previous_message in reversed(
        messages
    ):

        if (
            previous_message["role"]
            == "user"
        ):

            previous_user_input = (
                previous_message[
                    "content"
                ]
            )

            break

    messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):

        st.write(user_input)


    with st.chat_message("assistant"):

        with st.spinner("正在处理..."):

            try:

                if mode == "宝宝档案":

                    result = route_request(
                        user_input,
                        context_id=st.session_state["agent_context_id"],
                        request_id=uuid4().hex,
                        actor_name="网页用户"
                    )

                    answer = str(result)

                    sources = []

                    photo_memories = (
                        search_photo_memories(
                            user_input
                        )
                    )

                else:

                    result = answer_with_rag(
                        question=user_input,
                        top_k=3,
                        chunk_size=500,
                        overlap=150,
                        min_score=0.04
                    )

                    answer = result["answer"]

                    sources = result["sources"]

                    photo_memories = []


                st.write(answer)

                show_related_memories(
                    photo_memories
                )


                if sources:

                    with st.expander(
                        "查看引用资料"
                    ):

                        for index, source in enumerate(
                            sources,
                            start=1
                        ):

                            st.markdown(
                                f"**资料{index}｜"
                                f"{source['file']}｜"
                                f"{('第' + str(source['page']) + '页｜') if source.get('page') else ''}"
                                f"相关度 "
                                f"{source['score']:.4f}**"
                            )

                            st.write(
                                source["text"]
                            )


            except Exception as error:

                answer = (
                    "处理失败，请稍后重试。"
                )

                sources = []

                photo_memories = []

                st.error(answer)

                print(
                    "Streamlit运行错误：",
                    error
                )


    messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "photo_memories": photo_memories
    })
