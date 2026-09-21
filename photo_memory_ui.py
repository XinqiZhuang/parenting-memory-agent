"""Photo uploads and a responsive, naturally sized masonry gallery."""
import hashlib
from html import escape

import streamlit as st
from PIL import Image

from family_features.media import save_web_photos, store_image, resolve_photo
from family_features.settings import family_now
from agent_v2.schema import CATEGORIES, NAMES
from agent_v2.service import default_repository
from family_features.records import browse_records
from family_features.theme import badge, record_title, text_html, show_photo


def _render_upload_form():
    files = st.file_uploader("选择照片（每次最多8张，每张10MB）", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
    contents = [file.getvalue() for file in files]
    signature = hashlib.sha256(b"".join(hashlib.sha256(c).digest() for c in contents)).hexdigest()
    if st.session_state.get("photo_selection") != signature:
        st.session_state["photo_selection"] = signature
        st.session_state["photo_event"] = ""
        st.session_state["photo_description"] = ""
        st.session_state.pop("vision_paths", None)
    consent = st.checkbox("将所选照片的缩小副本发送到我配置的图片模型，用于生成描述草稿")
    if st.button("识别照片，生成草稿", disabled=not contents or not consent):
        try:
            if len(contents) > 4:
                raise ValueError("每次识别最多4张；手动填写保存最多8张。")
            from family_features.vision import describe_photos
            with st.spinner("正在识别照片…"):
                paths = st.session_state.get("vision_paths")
                if paths is None:
                    paths = [store_image(content) for content in contents]
                    st.session_state["vision_paths"] = paths
                result = describe_photos(paths)
            st.session_state["photo_event"] = result["event"]
            st.session_state["photo_description"] = result["description"]
            st.success("草稿已填入下方。请核对，保存前不会加入宝宝档案。")
        except Exception as exc:
            from family_features.vision import VisionUnavailable
            st.error(str(exc) if isinstance(exc, (VisionUnavailable, ValueError)) else "识别服务暂时失败，请手动填写描述。")
    with st.form("photo_memory_form"):
        event = st.text_input("标题", key="photo_event", placeholder="例如：早教活动：认识蔬菜")
        kind = st.selectbox("保存为", ["AUTO", "ACTIVITY", "MEMORY"], format_func=lambda k: {"AUTO":"根据我填写的内容分类", "ACTIVITY":"学习活动", "MEMORY":"生活回忆"}[k])
        category = st.selectbox("活动分类", ["AUTO", ""] + list(CATEGORIES), format_func=lambda k: "根据文字判断" if k == "AUTO" else CATEGORIES.get(k, "未分类"))
        duration = st.text_input("活动时长（分钟，可留空）")
        event_date = st.date_input("实际发生日期", value=family_now().date())
        unknown = st.checkbox("不确定发生日期，留空保存")
        description = st.text_area("描述", key="photo_description")
        st.caption("识别结果可能有误；请核对人物活动，不以照片判断首次发生、年龄或健康状况。")
        submitted = st.form_submit_button("确认信息并保存照片记录")
    if submitted:
        try:
            record, created = save_web_photos(event, description, "" if unknown else event_date.isoformat(), contents,
                                         st.session_state["agent_context_id"], kind=kind, category=category,
                                         duration=float(duration) if duration.strip() else None)
            label = "学习活动" if "activity" in record else "生活回忆"
            st.success(f"已保存到{label}。" if created else "这组照片和信息已经保存，没有重复新增。")
        except (ValueError, RuntimeError, OSError) as exc:
            st.error(str(exc))


def _gallery_columns(rows):
    # Keep photographs at their natural aspect ratios. Greedy placement keeps
    # independent columns balanced without cropping portraits into square tiles.
    columns, heights = [[], [], []], [0, 0, 0]
    for row in rows:
        ratio = 0.8
        try:
            with Image.open(resolve_photo(row["record"]["photos"][0])) as photo:
                ratio = min(photo.height / max(photo.width, 1), 3)
        except (OSError, ValueError):
            pass
        target = min(range(3), key=lambda i: heights[i])
        columns[target].append(row)
        heights[target] += ratio + 0.65
    return columns


def render_photo_memory_page():
    from family_features.record_management import render_management_panel
    from family_features.photo_viewer import render_photo_surface
    a, b = st.columns([5, 1], vertical_alignment="center")
    a.title("照片墙")
    a.caption("那些值得记住的小小瞬间")
    if b.button("上传照片", icon=":material/add:", type="primary", use_container_width=True):
        st.session_state["show_photo_upload"] = not st.session_state.get("show_photo_upload", False)
    if st.session_state.get("show_photo_upload"):
        with st.container(border=True):
            st.subheader("添加照片")
            st.caption("填写真实日期和活动信息，照片会和记录一起保存。")
            _render_upload_form()
            if st.button("收起上传", key="close_photo_upload"):
                st.session_state["show_photo_upload"] = False
                st.rerun()
    render_management_panel()
    with st.container(key="photo_filters"):
        category = st.radio("照片分类", ["全部"] + list(CATEGORIES.values()) + ["生活回忆", "未分类"],
                            horizontal=True, label_visibility="collapsed", key="photo_category")
        keyword = st.text_input("搜索照片", placeholder="搜索照片的标题或描述", key="photo_keyword", label_visibility="collapsed")
    rows = [row for row in browse_records(default_repository().snapshot(), keyword=keyword)
            if row["record"].get("photos")]
    if category != "全部":
        rows = [row for row in rows if (CATEGORIES.get(row["record"].get("category")) or
                 ("生活回忆" if row["entity"] == "MEMORY" else "未分类")) == category]
    if not rows:
        st.info("暂时没有符合条件的照片。可以调整筛选，或上传第一张照片。")
        return
    st.caption(f"共 {len(rows)} 条照片记录 · 点击照片放大 · 悬浮右上角菜单可编辑或删除")
    from family_features.theme import page_slice
    visible = page_slice(rows, "photo", size=18)
    with st.container(key="photo_grid"):
        columns = st.columns(3, gap="medium")
        for col, items in zip(columns, _gallery_columns(visible)):
            with col:
                for row in items:
                    record = row["record"]
                    with st.container(border=True, key="photo_card_" + record["id"]):
                        render_photo_surface(row, menu=True, prefix="photo_wall")
                        text_html(record_title(row), "diary-title")
                        st.markdown('<div class="diary-meta">' + escape(row["date"] or "日期未记录") +
                                    badge(record.get("category"), row["entity"]) + '</div>', unsafe_allow_html=True)
                        if record.get("description"):
                            text_html(record["description"])
                        st.caption(NAMES[row["entity"]] + (f" · {record['duration_minutes']:g} 分钟" if isinstance(record.get("duration_minutes"), (int, float)) else ""))
                        if len(record["photos"]) > 1:
                            with st.expander(f"查看其余 {len(record['photos']) - 1} 张照片"):
                                for index in range(1, len(record["photos"])):
                                    render_photo_surface(row, index, prefix="photo_extra")
