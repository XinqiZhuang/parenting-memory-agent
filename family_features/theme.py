"""Presentation only: shared warm theme and safe, compact display helpers."""
from html import escape
from io import BytesIO

import streamlit as st
from PIL import Image, ImageOps

from agent_v2.schema import CATEGORIES, NAMES, NAME_FIELDS
from family_features.media import resolve_photo

BABY_ICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-label="宝宝头像" role="img">
<circle cx="32" cy="32" r="31" fill="#f9e5d5"/>
<circle cx="10" cy="35" r="5" fill="#f2cdae"/><circle cx="54" cy="35" r="5" fill="#f2cdae"/>
<circle cx="32" cy="34" r="23" fill="#ffe4c9" stroke="#a7805f" stroke-width="1.5"/>
<path d="M32 14c-10-1-6-12 0-9-6 1-3 8 3 6" fill="#98724f"/>
<circle cx="23" cy="32" r="2" fill="#644e3f"/><circle cx="41" cy="32" r="2" fill="#644e3f"/>
<ellipse cx="18" cy="40" rx="5" ry="3" fill="#efb69a"/><ellipse cx="46" cy="40" rx="5" ry="3" fill="#efb69a"/>
<path d="M27 41q5 6 10 0" fill="none" stroke="#815e46" stroke-width="2" stroke-linecap="round"/></svg>'''

CSS = """
<style>
:root {color-scheme:light; --diary-ink:#343932; --diary-muted:#81857c; --diary-line:#ebe8e1;}
.stApp,[data-testid="stAppViewContainer"] {background:#faf8f3;color:var(--diary-ink);font-family:Inter,"Noto Sans CJK SC","Microsoft YaHei",sans-serif;}
[data-testid="stHeader"] {background:rgba(250,248,243,.95);}
[data-testid="stMainBlockContainer"] {max-width:1600px;padding:2.8rem 2.5rem 4rem;}
[data-testid="stSidebar"] {background:#f7f4ee;border-right:1px solid var(--diary-line);min-width:245px;max-width:245px;}
[data-testid="stSidebarUserContent"] {padding:1.4rem 1.15rem 2rem;}
.diary-brand {display:flex;align-items:center;gap:10px;margin:0 0 30px;}
.diary-brand svg {flex-shrink:0;width:46px;height:46px;}
.diary-brand strong {font-size:17px;white-space:nowrap;letter-spacing:0;}
.diary-brand small {display:block;font-size:11px;color:#8a8c84;margin-top:5px;}
.diary-footer {margin-top:70px;color:#92958c;font-size:12px;}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {gap:8px;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:12px 13px;border-radius:12px;min-height:48px;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {background:#f8e2d1;}
[data-testid="stSidebar"] [data-testid="stRadio"] label>div:first-child {display:none;}
[data-testid="stSidebar"] [data-testid="stRadio"] p {font-size:15px;}
h1,h2,h3,h4,p,label,[data-testid="stWidgetLabel"] {color:var(--diary-ink);}
h1 {font-size:2rem!important;} h2,h3 {letter-spacing:.01em;}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p {color:var(--diary-muted);font-size:13px;}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button {border:1px solid #dfdfd4;background:#fffdfa;border-radius:11px;color:#52634b;box-shadow:none;}
[data-testid="stButton"] button:hover,[data-testid="stFormSubmitButton"] button:hover {border-color:#9ba88e;background:#f1f5ed;color:#405238;}
button[kind="primary"],button[kind="primaryFormSubmit"] {background:#93a182!important;color:white!important;border-color:#93a182!important;}
button[kind="primary"] p,button[kind="primaryFormSubmit"] p {color:white!important;}
button:focus-visible,input:focus-visible {outline:2px solid #758b69!important;outline-offset:3px;}
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div {background:#fffdfa!important;color:#343932!important;border-color:#e6e4db!important;border-radius:10px;}
input,textarea {color:#343932!important;-webkit-text-fill-color:#343932!important;}
[data-baseweb="popover"]>div,[role="listbox"],[role="option"] {background:#fffdfa!important;color:#343932!important;}
[data-testid="stForm"],[data-testid="stExpander"] {border-color:#e6e4db;border-radius:14px;background:#fffdfa;}
[data-testid="stExpander"] summary {color:#53634b;}
[data-testid="stCheckbox"] label p {color:#53604c;}
[data-testid="stChatMessage"] {background:#fffdf9;border:1px solid #eae6dc;border-radius:16px;}
[data-testid="stBottom"],[data-testid="stBottomBlockContainer"] {background:#faf8f3;}
[data-testid="stChatInput"] {background:#fffdfa;border:1px solid #dedfd3;border-radius:16px;}
.diary-badge {display:inline-block;border-radius:20px;padding:3px 11px;font-size:12px;white-space:nowrap;background:#eceee7;color:#67735d;}
.diary-badge.gross_motor {background:#e7eee0;color:#637952;}
.diary-badge.fine_motor {background:#fce6da;color:#a86643;}
.diary-badge.cognitive {background:#fff0c8;color:#8a7443;}
.diary-badge.language {background:#e4edf6;color:#5d7a97;}
.diary-badge.social {background:#eee6f4;color:#89749c;}
.diary-title {font-size:17px;font-weight:600;line-height:1.6;overflow-wrap:anywhere;}
.diary-copy {font-size:14px;line-height:1.7;overflow-wrap:anywhere;white-space:pre-wrap;}
.diary-meta {display:flex;align-items:center;gap:10px;color:#85897f;font-size:12px;margin:6px 0;}
.st-key-photo_grid [class*="st-key-photo_card_"] {background:#fff;border:1px solid #eeebe4;border-radius:17px;box-shadow:0 3px 12px #72684d06;overflow:hidden;}
.st-key-photo_grid [data-testid="stImage"] img {border-radius:11px;width:100%;height:auto;}
.st-key-photo_grid [data-testid="stButton"] button {border:0;background:transparent;padding:0 .4rem;min-height:30px;}
.st-key-photo_grid [data-testid="stButton"] button p {font-size:13px;color:#7f8579;}
.st-key-photo_filters [data-testid="stRadio"] [role="radiogroup"] {gap:8px;}
.st-key-photo_filters [data-testid="stRadio"] label {border:1px solid #e6e2d9;border-radius:25px;padding:6px 14px;background:#fffdfa;}
.st-key-photo_filters [data-testid="stRadio"] label:has(input:checked) {background:#f9e2cf;border-color:#f9e2cf;}
.st-key-photo_filters [data-testid="stRadio"] label>div:first-child {display:none;}
.st-key-archive_table {background:#fff;border:1px solid var(--diary-line);border-radius:16px;padding:0 14px;overflow-x:auto;}
.st-key-archive_table>div {min-width:960px;}
.st-key-archive_table [data-testid="stHorizontalBlock"] {flex-wrap:nowrap!important;align-items:center;gap:14px;}
.st-key-archive_table [data-testid="stColumn"] {min-width:0!important;}
.st-key-archive_table [data-testid="stColumn"]:nth-child(1) {--weight:1.3;}
.st-key-archive_table [data-testid="stColumn"]:nth-child(2) {--weight:1.8;}
.st-key-archive_table [data-testid="stColumn"]:nth-child(3) {--weight:1.15;}
.st-key-archive_table [data-testid="stColumn"]:nth-child(4) {--weight:.9;}
.st-key-archive_table [data-testid="stColumn"]:nth-child(5) {--weight:3;}
.st-key-archive_table [data-testid="stColumn"]:nth-child(6) {--weight:.9;}
.st-key-archive_table [data-testid="stColumn"]:nth-child(7) {--weight:1.3;}
.st-key-archive_table [data-testid="stVerticalBlock"] {gap:0;}
.st-key-archive_table [data-testid="stVerticalBlockBorderWrapper"] {margin:0;}
.diary-table-head {font-size:13px;font-weight:600;padding:17px 0;white-space:nowrap;}
.diary-cell {font-size:13px;line-height:1.65;padding:14px 0;overflow-wrap:anywhere;white-space:pre-wrap;}
.diary-cell.nowrap {white-space:nowrap;font-size:12px;}
.diary-cell small {display:block;color:#94998d;font-size:11px;margin-top:5px;}
.st-key-archive_table [class*="st-key-record_row_"] {border-top:1px solid #eeeae3;}
.st-key-archive_table [data-testid="stButton"] button {font-size:13px;background:transparent;border:0;padding:2px 3px;min-height:30px;}
.st-key-archive_table [data-testid="stButton"] button p {font-size:13px;}
.st-key-archive_table [data-testid="stImage"] img {border-radius:7px;max-height:56px;object-fit:cover;}
.st-key-archive_table [data-testid="stImage"] {margin:8px 0;}
.st-key-archive_table [data-testid="stCaptionContainer"] p {font-size:10px;}
/* Photo hit areas and menus are native Streamlit buttons inside this container. */
[class*="st-key-photo_visual_"] {position:relative;min-height:80px;gap:0!important;}
[class*="st-key-photo_visual_"] [data-testid="stImage"] {margin:0;}
[class*="st-key-photo_visual_"] [data-testid="stImage"] img {display:block;}
[class*="st-key-photo_visual_"] [data-testid="stImage"] button {display:none;}
[class*="st-key-photo_visual_"] [class*="st-key-photo_open_"] {position:absolute!important;inset:0;width:100%!important;height:100%;z-index:1;}
[class*="st-key-photo_visual_"] [data-testid="stButton"] {width:100%;height:100%;}
[class*="st-key-photo_visual_"] [data-testid="stButton"] button {width:100%;height:100%;padding:0!important;background:transparent!important;border:0!important;border-radius:11px;cursor:zoom-in;}
[class*="st-key-photo_visual_"] [data-testid="stButton"] button p {position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;}
[class*="st-key-photo_visual_"] [data-testid="stButton"] button:focus-visible {outline-offset:-3px!important;}
[class*="st-key-photo_visual_"] [class*="st-key-photo_menu_"] {position:absolute!important;top:10px;right:10px;width:auto!important;z-index:3;opacity:0;pointer-events:none;transition:opacity .15s ease;}
[class*="st-key-photo_visual_"]:hover [class*="st-key-photo_menu_"],
[class*="st-key-photo_visual_"]:focus-within [class*="st-key-photo_menu_"],
[class*="st-key-photo_visual_"] [class*="st-key-photo_menu_"]:has(button[aria-expanded="true"]) {opacity:1;pointer-events:auto;}
[class*="st-key-photo_visual_"] [data-testid="stPopoverButton"] {width:36px;height:36px;min-height:36px;padding:0!important;border:1px solid #ffffffba;border-radius:50%;background:#fffdf4ed;color:#4b5545;box-shadow:0 2px 9px #24271a25;}
[class*="st-key-photo_visual_"] [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] {position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);}
[class*="st-key-photo_visual_"] [data-testid="stPopoverButton"] > div > [aria-hidden="true"] {display:none;}
[data-testid="stPopoverBody"] {min-width:140px;border-radius:12px;background:#fffdfa;}
[data-testid="stPopoverBody"] [data-testid="stButton"] button {border:0;justify-content:flex-start;border-radius:8px;}
[data-testid="stDialog"] {align-items:center!important;padding:2vh 0!important;}
[data-testid="stDialog"]>div {background:#fffdf8;max-height:94dvh;overflow-y:auto;}
[data-testid="stDialog"] [role="dialog"] {background:#fffdf8;color:#343932;border-radius:20px;box-shadow:0 20px 80px #33281933;max-height:90dvh;overflow:auto;}
[data-testid="stDialog"] [data-testid="stForm"] {background:transparent;border:0;padding:0;}
.st-key-photo_lightbox [data-testid="stImage"] {width:100%;}
.st-key-photo_lightbox img {display:block;max-height:65dvh;width:100%;object-fit:contain;border-radius:12px;}
.st-key-photo_lightbox [data-testid="stImage"] button {display:none;}
@media(hover:none),(pointer:coarse) {
 [class*="st-key-photo_visual_"] [class*="st-key-photo_menu_"] {opacity:1;pointer-events:auto;}
 [class*="st-key-photo_visual_"] [data-testid="stPopoverButton"] {width:44px;height:44px;}
}
@media(prefers-reduced-motion:reduce) {[class*="st-key-photo_visual_"] * {transition:none!important;}}
@media(max-width:1000px) {[data-testid="stMainBlockContainer"] {padding-left:1.2rem;padding-right:1.2rem;}}
@media(max-width:640px) {
 [data-testid="stMainBlockContainer"] {padding:3.5rem 1rem 3rem;}
 .st-key-photo_grid>[data-testid="stVerticalBlock"]>[data-testid="stHorizontalBlock"] {gap:0;}
 .st-key-archive_table {padding:0 10px;}
 .st-key-archive_table [data-testid="stColumn"] {flex:var(--weight,1) 1 0!important;width:auto!important;}
}
</style>
"""


def apply_theme():
    st.html(CSS)


def render_brand():
    st.sidebar.markdown('<div class="diary-brand">' + BABY_ICON +
        '<div><strong>玖玖的成长日记</strong><small>把日常，慢慢珍藏</small></div></div>', unsafe_allow_html=True)


def badge(category, entity=""):
    label = CATEGORIES.get(category) or ("生活回忆" if entity == "MEMORY" else "未分类")
    css_class = category if category in CATEGORIES else ""
    return f'<span class="diary-badge {css_class}">{escape(label)}</span>'


def record_title(row):
    record = row["record"]
    return str(record.get(NAME_FIELDS.get(row["entity"], "")) or NAMES[row["entity"]])


def text_html(text, css="diary-copy"):
    st.markdown(f'<div class="{css}">{escape(str(text))}</div>', unsafe_allow_html=True)


@st.cache_data(max_entries=80, ttl=300, show_spinner=False)
def _thumbnail(path, modified_ns, width):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((width, width * 3))
        output = BytesIO()
        image.save(output, format="JPEG", quality=85)
        return output.getvalue()


def photo_bytes(value, width=960):
    path = resolve_photo(value)
    return _thumbnail(str(path), path.stat().st_mtime_ns, width)


def show_photo(value, width=960):
    try:
        st.image(photo_bytes(value, width), use_container_width=True)
    except (OSError, ValueError):
        st.caption("照片暂时无法显示，记录仍保留。")


def page_slice(rows, key, size=15):
    """Bound the page after filtering/deletion; avoid loading an entire album."""
    pages = max(1, (len(rows) + size - 1) // size)
    state_key = key + "_page"
    signature = tuple((r["entity"], r["record"]["id"]) for r in rows)
    if st.session_state.get(key + "_results") != signature:
        st.session_state[key + "_results"] = signature
        st.session_state[state_key] = 1
    if pages == 1:
        return rows
    number = st.selectbox("页码", list(range(1, pages + 1)), key=state_key,
                          format_func=lambda n: f"第 {n} 页 / 共 {pages} 页")
    return rows[(number - 1) * size:number * size]
