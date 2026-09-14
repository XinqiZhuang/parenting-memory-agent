from pathlib import Path

import streamlit as st

from baby import load_baby
from photo_memory import create_photo_memory


PROJECT_DIR = Path(__file__).parent


def render_photo_memory_page():

    st.subheader("📷 宝宝照片回忆")

    st.write(
        "上传照片，并记录照片背后的成长故事。"
    )


    with st.form(
        "photo_memory_form",
        clear_on_submit=True
    ):

        event = st.text_input(
            "回忆标题",
            placeholder="例如：第一次独立走路"
        )

        event_date = st.date_input(
            "发生日期"
        )

        description = st.text_area(
            "回忆描述",
            placeholder=(
                "例如：宝宝在客厅里"
                "第一次独立走了三步。"
            )
        )

        uploaded_files = st.file_uploader(
            "上传照片",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp"
            ],
            accept_multiple_files=True
        )

        submitted = st.form_submit_button(
            "保存回忆"
        )


    if submitted:

        if not event.strip():

            st.error("请填写回忆标题。")

        elif not uploaded_files:

            st.error("请至少上传一张照片。")

        else:

            photos = [
                {
                    "name": uploaded_file.name,
                    "content": (
                        uploaded_file.getvalue()
                    )
                }
                for uploaded_file
                in uploaded_files
            ]

            try:

                create_photo_memory(
                    event=event,
                    description=description,
                    event_date=(
                        event_date.isoformat()
                    ),
                    photos=photos
                )

                st.success("照片回忆保存成功。")

            except ValueError as error:

                st.error(str(error))


    st.divider()

    st.subheader("🌷 成长照片墙")


    baby = load_baby()

    photo_memories = [
        memory
        for memory in baby.get(
            "memories",
            []
        )
        if memory.get("photos")
    ]


    if not photo_memories:

        st.info(
            "还没有照片回忆，"
            "可以先上传第一张照片。"
        )

        return


    for memory in reversed(photo_memories):

        st.markdown(
            f"### {memory['event']}"
        )

        if memory.get("date"):

            st.caption(memory["date"])

        if memory.get("description"):

            st.write(
                memory["description"]
            )


        photo_paths = memory["photos"]

        column_count = min(
            3,
            len(photo_paths)
        )

        columns = st.columns(
            column_count
        )


        for index, photo_path in enumerate(
            photo_paths
        ):

            full_path = (
                PROJECT_DIR
                / photo_path
            )

            column = columns[
                index % column_count
            ]

            if full_path.exists():

                column.image(
                    str(full_path),
                    use_container_width=True
                )

            else:

                column.warning(
                    "照片文件不存在。"
                )