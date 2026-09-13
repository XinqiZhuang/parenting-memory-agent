from pathlib import Path

import streamlit as st

from router import route_request
from rag.generator import answer_with_rag


PROJECT_DIR = Path(__file__).parent

PDF_PATH = (
    PROJECT_DIR
    / "knowledge"
    / "healthy_parenting_guide_0_3.pdf"
)


st.set_page_config(
    page_title="育儿成长 Agent",
    page_icon="👶",
    layout="centered"
)


st.title("👶 育儿成长 Agent")

st.caption(
    "记录宝宝成长，并基于专业资料回答育儿问题"
)


mode = st.sidebar.radio(
    "请选择功能",
    [
        "宝宝档案",
        "育儿知识库"
    ]
)


if mode == "宝宝档案":

    message_key = "record_messages"

    input_hint = (
        "输入宝宝的成长记录，"
        "或者查询、修改已有记录"
    )

else:

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
                        f"第{source['page']}页｜"
                        f"相关度 {source['score']:.4f}**"
                    )

                    st.write(source["text"])


user_input = st.chat_input(
    input_hint
)


if user_input:

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
                        user_input
                    )

                    answer = str(result)

                    sources = []

                else:

                    result = answer_with_rag(
                        question=user_input,
                        file_path=PDF_PATH,
                        top_k=3,
                        chunk_size=500,
                        overlap=150,
                        min_score=0.04
                    )

                    answer = result["answer"]

                    sources = result["sources"]


                st.write(answer)


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
                                f"第{source['page']}页｜"
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

                st.error(answer)

                print(
                    "Streamlit运行错误：",
                    error
                )


    messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources
    })