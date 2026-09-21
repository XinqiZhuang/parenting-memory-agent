"""Family archive, daily reading and push configuration."""
from datetime import date, datetime, timezone
from html import escape

import streamlit as st

from agent_v2.schema import NAMES, CATEGORIES, LABELS
from agent_v2.service import default_repository
from family_features.records import browse_records, table_rows, export_csv, daily_summary, ENTITIES
from family_features.settings import family_now
from family_features.theme import badge, record_title, text_html, show_photo, page_slice


def _details(record):
    """Retain measurements/feeding facts in mixed tables without inventing prose."""
    parts = []
    for key in ("time", "age_months", "foods", "amount_ml", "height_cm", "weight_kg", "head_circumference_cm", "temperature_c"):
        value = record.get(key)
        if value is not None and value != "" and value != []:
            text = "、".join(map(str, value)) if isinstance(value, list) else str(value)
            parts.append(LABELS[key] + "：" + text)
    return "；".join(parts)


def render_archive_table(rows):
    from family_features.record_management import render_record_controls
    # Native buttons keep all actions in the authenticated Streamlit session.
    # The scrollable table uses actual Python callbacks, never writable URL links.
    weights = [1.3, 1.8, 1.15, .9, 3, .9, 1.3]
    with st.container(key="archive_table"):
        columns = st.columns(weights)
        for col, label in zip(columns, ["日期", "活动 / 事件", "分类", "时长", "描述", "照片", "操作"]):
            with col:
                text_html(label, "diary-table-head")
        for row in rows:
            r = row["record"]
            with st.container(key="record_row_" + r["id"]):
                cells = st.columns(weights, vertical_alignment="center")
                with cells[0]:
                    text_html(row["date"] or "日期未记录", "diary-cell nowrap")
                with cells[1]:
                    st.markdown('<div class="diary-cell"><strong>' + escape(record_title(row)) +
                                '</strong><small>' + escape(NAMES[row["entity"]]) + '</small></div>', unsafe_allow_html=True)
                with cells[2]:
                    st.markdown(badge(r.get("category"), row["entity"]), unsafe_allow_html=True)
                with cells[3]:
                    duration = r.get("duration_minutes")
                    text_html(f"{duration:g} 分钟" if isinstance(duration, (float, int)) else "—", "diary-cell nowrap")
                with cells[4]:
                    text_html(r.get("description") or "—", "diary-cell")
                    if details := _details(r):
                        st.caption(details)
                with cells[5]:
                    photos = r.get("photos", [])
                    if photos:
                        show_photo(photos[0], 160)
                        if len(photos) > 1:
                            st.caption(f"共 {len(photos)} 张")
                    else:
                        text_html("—", "diary-cell")
                with cells[6]:
                    render_record_controls(row, "table", compact=True)
    st.caption("缺少的字段显示为「—」。窄屏可左右滑动表格；完整照片可在照片墙查看。")


def render_timeline(rows, prefix="timeline"):
    from family_features.record_management import render_record_controls
    for row in rows:
        with st.container(border=True):
            st.caption(f"{row['date'] or '日期未记录'} · {NAMES[row['entity']]}")
            text_html(record_title(row), "diary-title")
            text_html(row["text"])
            photos = row["record"].get("photos", [])
            if photos:
                with st.expander(f"查看 {len(photos)} 张照片"):
                    for path in photos:
                        show_photo(path)
            render_record_controls(row, prefix, compact=True)


def render_dashboard():
    a, b, c = st.columns([5, 1.2, 1], vertical_alignment="center")
    a.title("档案总览")
    a.caption("每一次成长，都有迹可循")
    def open_record_chat():
        st.session_state["diary_page"] = "宝宝档案"
    b.button("新增记录", icon=":material/add:", type="primary", use_container_width=True, on_click=open_record_chat)
    if c.button("刷新档案", icon=":material/refresh:", use_container_width=True):
        st.session_state.pop("record_editor", None)
        st.rerun()
    from family_features.record_management import render_management_panel
    render_management_panel()
    data = default_repository().snapshot()
    rows = browse_records(data)
    with st.container(border=True):
        first, second, third = st.columns([1, 1, 2])
        entity = first.selectbox("记录类型", ["ALL"] + ENTITIES, format_func=lambda k: "全部类型" if k == "ALL" else NAMES[k], key="archive_entity", label_visibility="collapsed")
        category = second.selectbox("活动分类", ["ALL"] + list(CATEGORIES) + ["uncategorized"], format_func=lambda k: "全部分类" if k == "ALL" else CATEGORIES.get(k, "未分类"), key="archive_category", label_visibility="collapsed")
        keyword = third.text_input("关键词", placeholder="搜索活动、食物或描述", label_visibility="collapsed", key="archive_keyword")
        start, end = "", ""
        with st.expander("日期筛选"):
            use_range = st.checkbox("按日期范围筛选")
            if use_range:
                dated = [r["date"] for r in rows if r["date"]]
                earliest = date.fromisoformat(min(dated)) if dated else family_now().date()
                latest = date.fromisoformat(max(dated)) if dated else family_now().date()
                a, b = st.columns(2)
                start = a.date_input("开始日期", value=earliest).isoformat()
                end = b.date_input("结束日期", value=latest).isoformat()
                if start > end:
                    st.error("开始日期不能晚于结束日期。")
                    return
            missing_only = st.checkbox("只看缺日期/日期无效的记录")
            include_missing = st.checkbox("包含缺日期记录", value=not use_range, disabled=missing_only)
    selected = browse_records(data, entity, start, end, keyword, missing_only, include_missing or missing_only)
    if category != "ALL":
        selected = [r for r in selected if (r["record"].get("category") or "uncategorized") == category]
    st.caption(f"共 {len(selected)} 条记录 · 飞书与网页同步 · 读取于 {family_now():%H:%M}")
    display = st.radio("展示方式", ["表格", "时间线"], horizontal=True, label_visibility="collapsed", key="archive_view")
    if selected:
        visible = page_slice(selected, "archive")
        if display == "表格":
            render_archive_table(visible)
        else:
            render_timeline(visible)
    else:
        st.info("没有符合筛选条件的记录。试试调整日期或分类。")
    with st.expander("导出与操作记录"):
        st.download_button("导出筛选结果 CSV", data=export_csv(selected), file_name="baby-records.csv", mime="text/csv")
        st.caption("最近100次实际写入。完整历史保存在数据文件内。")
        events = data.get("_agent_v2", {}).get("events", [])
        st.dataframe([{"时间": e.get("timestamp", ""), "操作者": e.get("actor_name", ""),
                       "操作": e.get("action", ""), "类型": NAMES.get(e.get("entity"), e.get("entity", "")),
                       "操作编号": e.get("id", "")} for e in reversed(events[-100:])], use_container_width=True, hide_index=True)


def render_daily_records():
    st.title("每日记录")
    st.caption("按发生日期，重温这一天的小小进步")
    from family_features.record_management import render_management_panel
    render_management_panel()
    day = st.date_input("查看哪一天", value=family_now().date(), key="diary_day").isoformat()
    data = default_repository().snapshot()
    rows = browse_records(data, start=day, end=day, include_missing=False)
    st.caption(f"这一天有 {len(rows)} 条已确认记录")
    if rows:
        render_timeline(page_slice(rows, "daily"), "daily")
    else:
        st.info("这一天还没有已确认的记录。未记录不等于没有发生。")
    with st.expander("查看当日日报文字"):
        st.text(daily_summary(data, day))


def render_push_settings():
    from family_features.settings import load_settings, save_settings, PushSettings
    from family_features.scheduler import read_state, build_body
    st.title("推送设置")
    st.caption("开启后由独立的定时服务发送。仅打开网页不会启动定时任务。")
    settings = load_settings()
    expected_revision = st.session_state.setdefault("push_form_revision", settings.revision)
    if expected_revision != settings.revision:
        st.warning("设置已有变化。请点击下方按钮重新加载，再编辑。")
    if st.button("重新加载推送设置"):
        for key in list(st.session_state):
            if key.startswith("push_cfg_") or key == "push_form_revision":
                del st.session_state[key]
        st.rerun()
    state = read_state()
    beat = state.get("heartbeat", "")
    if beat:
        try:
            seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(beat)).total_seconds()
            st.info("定时服务在线。" if seconds < 120 else "定时服务超过2分钟未更新，请检查scheduler进程。")
        except ValueError:
            st.warning("定时服务心跳时间异常。")
    else:
        st.info("尚未检测到定时服务。配置后请启动 python run_scheduler.py。")
    with st.form("push_configuration"):
        chat = st.text_input("接收群 chat_id", value=settings.chat_id, key="push_cfg_chat")
        zone = st.text_input("时区", value=settings.timezone, key="push_cfg_zone")
        summary_enabled = st.checkbox("每天发送活动总结", value=settings.summary_enabled, key="push_cfg_summary")
        summary_time = st.text_input("总结发送时间 HH:MM", value=settings.summary_time, key="push_cfg_summary_time")
        previous = st.checkbox("总结前一天（适合凌晨发送）", value=settings.summary_previous_day, key="push_cfg_previous")
        tip_enabled = st.checkbox("每天发送一条早教知识", value=settings.tip_enabled, key="push_cfg_tip")
        tip_time = st.text_input("早教知识发送时间 HH:MM", value=settings.tip_time, key="push_cfg_tip_time")
        window = st.number_input("程序错过发送时间后，允许补发多少分钟", min_value=1, max_value=720, value=settings.catchup_minutes, key="push_cfg_window")
        if st.form_submit_button("保存推送设置"):
            try:
                updated = PushSettings(chat_id=chat.strip(), timezone=zone.strip(), summary_enabled=summary_enabled,
                    summary_time=summary_time.strip(), summary_previous_day=previous, tip_enabled=tip_enabled,
                    tip_time=tip_time.strip(), catchup_minutes=int(window))
                saved = save_settings(updated, expected_revision)
                st.session_state["push_form_revision"] = saved.revision
                st.success("设置已保存；定时服务会在下一轮检查时读取。")
            except Exception as exc:
                st.error(str(exc))
    st.caption("早教优先摘取私有书籍中的亲子互动、阅读和游戏内容，附书名与PDF页码；近期已发摘录会避开。没有合适内容或核对失败时，使用原指南摘录。")
    st.caption("预览早教内容也可能调用DeepSeek筛选少量候选片段；不发送飞书消息。原有发送时间和开关继续有效。")
    day = st.date_input("预览内容日期", value=family_now().date(), key="push_preview_day").isoformat()
    kind = st.selectbox("预览类型", ["summary", "tip"], format_func=lambda k: "活动总结" if k == "summary" else "早教知识")
    if st.button("仅预览，不发送"):
        try:
            st.text(build_body(kind, day))
        except Exception as exc:
            st.error(str(exc))
    st.caption("发送不确定表示网络超时或发送进程中断：请先核对群消息。系统不会盲目重发。")
    runs = sorted(state.get("runs", {}).values(), key=lambda r: r.get("updated", 0), reverse=True)[:30]
    st.dataframe([{ "日期": r["day"], "任务": r["kind"], "状态": r["status"], "尝试次数": r.get("attempts", 0),
                   "说明": r.get("error", ""), "消息编号": r.get("message_id", "")}
                  for r in runs], use_container_width=True, hide_index=True)
    unresolved = {key: run for key, run in state.get("runs", {}).items() if run.get("status") in {"uncertain", "failed"}}
    if unresolved:
        with st.expander("人工处理失败或送达不确定的任务"):
            selected = st.selectbox("选择任务", list(unresolved), format_func=lambda key: f"{unresolved[key]['day']} · {unresolved[key]['kind']} · {unresolved[key]['status']}")
            checked = st.checkbox("我已经在飞书群中核对过是否收到该条消息")
            delivered = st.radio("核对结果", ["已收到", "未收到"])
            if st.button("保存核对结果", disabled=not checked):
                from family_features.scheduler import resolve_delivery
                try:
                    resolve_delivery(selected, delivered == "已收到", unresolved[selected]["updated"])
                    st.success("已保存。未收到的任务仅在其原补发时间窗口内重试。")
                except ValueError as exc:
                    st.error(str(exc))
