"""Authenticated photo lightbox and native clickable photo surfaces."""
import hashlib

import streamlit as st

from agent_v2.engine import is_live
from agent_v2.schema import COLLECTIONS, NAMES
from agent_v2.service import default_repository
from family_features.access import require_web_access
from family_features.theme import photo_bytes, record_title, text_html


def close_photo_dialog():
    st.session_state.pop("photo_viewer", None)


def close_photo_menus():
    for key in list(st.session_state):
        if key.startswith("photo_menu_"):
            st.session_state[key] = False


def open_photo_dialog(row, index=0):
    require_web_access(show_logout=False)
    close_photo_menus()
    # Keep only a record identity, never a user-provided file path, in viewer state.
    st.session_state["photo_viewer"] = {"entity": row["entity"], "id": row["record"]["id"], "index": index}


def render_photo_surface(row, index=0, *, menu=False, prefix="gallery"):
    from family_features.record_management import render_record_controls
    identity = row["record"]["id"]
    token = hashlib.sha256(f"{prefix}:{row['entity']}:{identity}:{index}".encode()).hexdigest()[:20]
    with st.container(key="photo_visual_" + token):
        try:
            image = photo_bytes(row["record"]["photos"][index])
            st.image(image, use_container_width=True)
        except (OSError, ValueError, IndexError):
            st.caption("照片暂时无法显示，可以通过菜单管理记录。")
        # CSS places this native button across the image, with an accessible label.
        st.button("放大照片", key="photo_open_" + token, use_container_width=True,
                  on_click=open_photo_dialog, args=(row, index))
        if menu:
            with st.popover("照片菜单", icon=":material/more_horiz:", key="photo_menu_" + token, on_change="rerun"):
                render_record_controls(row, prefix, compact=True, menu=True)


def _change_photo(delta):
    st.session_state["photo_viewer"]["index"] += delta


@st.dialog("照片查看", width="large", on_dismiss=close_photo_dialog)
def render_photo_dialog():
    require_web_access(show_logout=False)
    viewer = st.session_state.get("photo_viewer")
    if not viewer:
        return
    entity = viewer.get("entity")
    records = default_repository().snapshot().get(COLLECTIONS.get(entity, ""), [])
    record = next((r for r in records if r.get("id") == viewer.get("id") and is_live(r)), None)
    if not record or not record.get("photos"):
        st.info("这条记录或其照片关联已被移除，请关闭后刷新照片墙。")
    else:
        photos = record["photos"]
        index = min(max(int(viewer.get("index", 0)), 0), len(photos) - 1)
        viewer["index"] = index
        with st.container(key="photo_lightbox"):
            try:
                st.image(photo_bytes(photos[index], width=2400), use_container_width=True)
            except (OSError, ValueError):
                st.info("这张照片暂时无法读取；你仍可切换查看其他照片。")
        text_html(record_title({"entity": entity, "record": record}), "diary-title")
        st.caption(f"{record.get('date') or '日期未记录'} · {NAMES.get(entity, '')} · 第 {index + 1} / {len(photos)} 张")
        if record.get("description"):
            text_html(record["description"])
        if len(photos) > 1:
            a, b = st.columns(2)
            a.button("上一张", key="photo_previous", icon=":material/chevron_left:", disabled=index == 0,
                     use_container_width=True, on_click=_change_photo, args=(-1,))
            b.button("下一张", key="photo_next", icon=":material/chevron_right:", disabled=index == len(photos) - 1,
                     use_container_width=True, on_click=_change_photo, args=(1,))
    if st.button("关闭照片", key="photo_viewer_close", use_container_width=True):
        close_photo_dialog()
        st.rerun()
