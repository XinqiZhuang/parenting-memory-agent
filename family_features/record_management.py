"""Confirmed web edits use the same transactions, conflict checks and audit as Feishu."""
import copy
import re
from uuid import uuid4

import streamlit as st

from agent_v2.engine import execute, is_live, preview_text, summarize_changes
from agent_v2.schema import ALLOWED_FIELDS, CATEGORIES, COLLECTIONS, LABELS, NAME_FIELDS, NAMES, Command
from agent_v2.service import default_repository, finish, handle_request


def preview_change(entity, expected, context_id, *, action="UPDATE", values=None, clear_fields=None,
                   keep_photos=None, repository=None):
    repository = repository or default_repository()
    if entity not in COLLECTIONS or entity == "PHOTO":
        raise ValueError("请从档案中的具体记录打开编辑。")
    command = Command(action=action, entity=entity, selector={"id": expected["id"]},
                      values=values or {}, clear_fields=clear_fields or []) if action != "UPDATE" or values or clear_fields else None
    with repository.transaction() as data:
        ctx = data["_agent_v2"]["contexts"].setdefault(context_id, {})
        if ctx.get("pending"):
            return "还有待确认操作，请先确认或取消。"
        current = next((r for r in data[COLLECTIONS[entity]] if r.get("id") == expected["id"]), None)
        if current != expected or not current or not is_live(current):
            return "记录已经变化或被删除。请关闭编辑，刷新后重新打开；本次未写入。"
        if keep_photos is not None:
            original = current.get("photos", [])
            if not isinstance(keep_photos, list) or any(p not in original for p in keep_photos) or len(set(keep_photos)) != len(keep_photos):
                raise ValueError("保留照片必须选自这条记录现有照片。")
        result = execute(data, command, context_id, "网页用户") if command else "新值与原记录相同，没有修改。"
        if command and not ctx.get("pending") and result != "新值与原记录相同，没有修改。":
            return finish(data, context_id, "网页记录管理", result)
        if action == "UPDATE" and keep_photos is not None and keep_photos != current.get("photos", []):
            # Files are retained for undo; no physical deletion occurs here.
            plan = ctx.get("pending")
            if plan is None:
                from agent_v2.engine import set_plan
                set_plan(ctx, {"action": "UPDATE", "entity": entity, "before": copy.deepcopy(current), "after": copy.deepcopy(current)})
                plan = ctx["pending"]
            plan["after"]["photos"] = list(keep_photos)
            result = preview_text(plan)
        return finish(data, context_id, "网页记录管理", result)


def context_id():
    import streamlit as st
    return st.session_state["agent_context_id"] + ":manage"


def _management_context():
    return default_repository().snapshot()["_agent_v2"]["contexts"].get(context_id(), {})


def close_record_dialog():
    """Dismiss/ESC/cancel never commits a pending operation."""
    from family_features.access import require_web_access
    require_web_access(show_logout=False)
    if _management_context().get("pending"):
        answer = handle_request("取消", context_id(), request_id=uuid4().hex, actor_name="网页用户")
        if _management_context().get("pending"):
            st.session_state["record_notice"] = answer
    st.session_state.pop("record_editor", None)
    st.session_state.pop("record_dialog_notice", None)
    st.session_state["record_dialog_open"] = False


def open_record_editor(row):
    from family_features.access import require_web_access
    require_web_access(show_logout=False)
    from family_features.photo_viewer import close_photo_menus
    close_photo_menus()
    st.session_state.pop("photo_viewer", None)
    st.session_state["record_dialog_open"] = True
    if not _management_context().get("pending"):
        st.session_state["record_editor"] = {"entity": row["entity"], "expected": copy.deepcopy(row["record"]), "token": uuid4().hex}
        st.session_state.pop("record_dialog_notice", None)


def open_record_delete(row):
    from family_features.access import require_web_access
    require_web_access(show_logout=False)
    from family_features.photo_viewer import close_photo_menus
    close_photo_menus()
    st.session_state.pop("photo_viewer", None)
    st.session_state.pop("record_editor", None)
    st.session_state["record_dialog_open"] = True
    try:
        st.session_state["record_dialog_notice"] = preview_change(row["entity"], row["record"], context_id(), action="DELETE")
    except (ValueError, OSError) as exc:
        st.session_state["record_dialog_notice"] = str(exc)


def render_record_controls(row, prefix, compact=False, menu=False):
    identity = row["record"]["id"]
    if not compact:
        st.caption("记录编号：" + identity)
    edit, delete = (st, st) if menu else st.columns(2)
    edit.button("编辑" if compact else "编辑记录", key=f"{prefix}_edit_{identity}",
        icon=":material/edit:" if menu else None, use_container_width=menu,
        on_click=open_record_editor, args=(row,), help="编辑这条记录的文字、日期、分类或关联照片")
    delete.button("删除" if compact else "删除记录", key=f"{prefix}_delete_{identity}",
        icon=":material/delete:" if menu else None, use_container_width=menu,
        on_click=open_record_delete, args=(row,), help="确认后删除整条记录，可撤销")


def _request_undo():
    from family_features.photo_viewer import close_photo_menus
    close_photo_menus()
    st.session_state.pop("photo_viewer", None)
    st.session_state.pop("record_editor", None)
    st.session_state["record_dialog_notice"] = handle_request("撤销上次操作", context_id(), request_id=uuid4().hex,
        actor_name="网页用户", parser=lambda *_: Command(action="UNDO"))
    st.session_state["record_dialog_open"] = True


def render_management_panel():
    if notice := st.session_state.pop("record_notice", ""):
        st.toast(notice)
    with st.expander("操作历史与撤销", expanded=False):
        st.caption("可撤销本次网页会话的编辑或删除。")
        st.button("撤销上一次网页编辑或删除", key="record_manage_undo", on_click=_request_undo)
        if _management_context().get("pending") and not st.session_state.get("record_dialog_open"):
            st.button("继续待确认操作", on_click=lambda: st.session_state.update(record_dialog_open=True))


def render_dialogs():
    # Run after page widgets: a full rerun from a dialog must not discard filters.
    if st.session_state.get("record_dialog_open"):
        _record_dialog()
    elif st.session_state.get("photo_viewer"):
        from family_features.photo_viewer import render_photo_dialog
        render_photo_dialog()


@st.dialog("记录管理", width="medium", on_dismiss=close_record_dialog)
def _record_dialog():
    from family_features.access import require_web_access
    require_web_access(show_logout=False)
    ctx_id = context_id()
    plan = _management_context().get("pending")
    notice = st.session_state.pop("record_dialog_notice", "")
    if plan:
        st.subheader({"DELETE": "删除这条记录？", "UPDATE": "确认修改", "RECLASSIFY": "确认转换分类", "UNDO": "确认撤销"}.get(plan["action"], "确认操作"))
        st.info(preview_text(plan).split("\n尚未写入")[0])
        if plan["action"] == "DELETE":
            st.caption("确认后会从档案和照片墙中移除，可通过操作历史撤销。")
        a, b = st.columns(2)
        confirm = a.button("确认执行", key="record_manage_confirm", type="primary", use_container_width=True)
        cancel = b.button("取消本次操作", key="record_manage_cancel", use_container_width=True)
        if confirm:
            answer = handle_request("确认", ctx_id, request_id=uuid4().hex, actor_name="网页用户")
            st.session_state["record_notice"] = answer
            st.session_state.pop("record_editor", None)
            st.session_state["record_dialog_open"] = False
            st.rerun()
        if cancel:
            close_record_dialog()
            st.rerun()
        return
    if notice:
        st.info(notice)
    if not st.session_state.get("record_editor"):
        if st.button("关闭", key="record_dialog_close"):
            close_record_dialog()
            st.rerun()
        return
    _render_editor_form()


def _render_editor_form():
    ctx_id = context_id()
    editor = st.session_state.get("record_editor")
    if not editor:
        return
    entity, original = editor["entity"], editor["expected"]
    st.subheader("编辑记录 · " + NAMES[entity])
    st.caption("修改后先预览，再确认保存。记录已被他人修改时，会要求刷新。")
    if st.button("关闭编辑", key="record_editor_close"):
        close_record_dialog()
        st.rerun()
    convert = False
    if entity == "MEMORY":
        convert = st.checkbox("把这条回忆转为学习活动（保留日期、描述和照片）", key="record_convert_" + editor["token"])
    with st.form("record_editor_" + editor["token"] + ("_convert" if convert else "_edit")):
        fields = {}
        if convert:
            from family_features.classification import suggested_category
            fields["activity"] = st.text_input("活动名称", value=original.get("event", ""))
            suggestion = suggested_category(original.get("event", "") + original.get("description", ""))
            choices = [""] + list(CATEGORIES)
            fields["category"] = st.selectbox("活动分类", choices, index=choices.index(suggestion), format_func=lambda v: CATEGORIES.get(v, "未分类"))
        else:
            ordered = [key for key in LABELS if key in ALLOWED_FIELDS[entity]]
            for key in ordered:
                value = original.get(key)
                if key == "category":
                    choices = [""] + list(CATEGORIES)
                    fields[key] = st.selectbox("分类", choices, index=choices.index(value) if value in choices else 0,
                                              format_func=lambda v: CATEGORIES.get(v, "未分类"))
                elif key == "description":
                    fields[key] = st.text_area(LABELS[key], value=value or "")
                else:
                    text = "、".join(value) if key == "foods" and isinstance(value, list) else "" if value is None else str(value)
                    label = "日期（YYYY-MM-DD，清空表示未知）" if key == "date" else LABELS[key]
                    fields[key] = st.text_input(label, value=text)
        photos = original.get("photos", [])
        chosen = list(range(len(photos)))
        if photos and not convert:
            chosen = st.multiselect("保留的照片（取消选择可从记录中移除，可撤销）", list(range(len(photos))),
                                    default=list(range(len(photos))), format_func=lambda n: f"第{n + 1}张")
        save = st.form_submit_button("预览修改")
    if save:
        try:
            values, clears = {}, []
            numeric = {"age_months", "height_cm", "weight_kg", "head_circumference_cm", "duration_minutes", "amount_ml", "temperature_c"}
            for key, text in fields.items():
                text = text.strip()
                if not text:
                    if not convert and key in original:
                        clears.append(key)
                    continue
                value = float(text) if key in numeric else [v.strip() for v in re.split(r"[、，,\n]", text) if v.strip()] if key == "foods" else text
                if convert or value != original.get(key):
                    values[key] = value
            result = preview_change(entity, original, ctx_id, action="RECLASSIFY" if convert else "UPDATE",
                                    values=values, clear_fields=clears, keep_photos=None if convert else [photos[i] for i in chosen])
            st.session_state["record_dialog_notice"] = result
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(str(exc))
