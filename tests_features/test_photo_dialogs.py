"""Real Streamlit page actions must stay in modal blocks and target exact records."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from agent_v2.engine import is_live
from family_features.media import save_web_photos

APP = Path(__file__).resolve().parents[1] / 'streamlit_app.py'


def start(repo, image_bytes, photos=1):
    record, _ = save_web_photos('认识动物', '模型和认知卡', '2026-09-15', [image_bytes] * photos, 'u', repo)
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    return app, record


def button(app, label):
    return next(b for b in app.button if b.label == label)


def active_dialog(app):
    dialogs = [d for d in app.get('dialog') if d.proto.dialog.is_open]
    assert len(dialogs) == 1
    return dialogs[0]


def test_archive_edit_form_and_confirmation_are_inside_modal(repo, image_bytes):
    app, record = start(repo, image_bytes)
    button(app, '编辑').click().run(timeout=15)
    dialog = active_dialog(app)
    assert dialog.text_input and not app.main.text_input(key='archive_keyword').value
    next(t for t in dialog.text_area if t.label == '描述').set_value('修改后的内容')
    button(dialog, '预览修改').click().run(timeout=15)
    dialog = active_dialog(app)
    assert repo.snapshot()['learning_activities'][0]['description'] == '模型和认知卡'
    button(dialog, '确认执行').click().run(timeout=15)
    assert repo.snapshot()['learning_activities'][0]['description'] == '修改后的内容'
    assert not app.session_state['record_dialog_open'] and not app.exception


def test_gallery_buttons_only_inside_popover_and_delete_in_modal(repo, image_bytes):
    app, record = start(repo, image_bytes)
    app.sidebar.radio[0].set_value('照片回忆').run(timeout=15)
    popovers = app.get('popover')
    assert len(popovers) == 1
    assert [b.label for b in popovers[0].button] == ['编辑', '删除']
    button(popovers[0], '删除').click().run(timeout=15)
    dialog = active_dialog(app)
    assert '删除' in dialog.subheader[0].value
    assert is_live(repo.snapshot()['learning_activities'][0])
    button(dialog, '取消本次操作').click().run(timeout=15)
    assert is_live(repo.snapshot()['learning_activities'][0])
    assert not app.session_state['record_dialog_open']
    assert not repo.snapshot()['_agent_v2']['contexts'][app.session_state['agent_context_id'] + ':manage'].get('pending')


def test_photo_click_opens_modal_and_switches_only_attached_images(repo, image_bytes):
    app, record = start(repo, image_bytes, photos=2)
    app.sidebar.radio[0].set_value('照片回忆').run(timeout=15)
    button(app, '放大照片').click().run(timeout=15)
    dialog = active_dialog(app)
    assert dialog.proto.dialog.title == '照片查看'
    assert '第 1 / 2 张' in dialog.caption[0].value
    assert button(dialog, '上一张').disabled
    button(dialog, '下一张').click().run(timeout=15)
    dialog = active_dialog(app)
    assert '第 2 / 2 张' in dialog.caption[0].value
    assert button(dialog, '下一张').disabled
    button(dialog, '关闭照片').click().run(timeout=15)
    assert 'photo_viewer' not in app.session_state
    assert repo.snapshot()['learning_activities'][0] == record


def test_closing_unsubmitted_edit_leaves_data_and_filter(repo, image_bytes):
    app, record = start(repo, image_bytes)
    app.text_input(key='archive_keyword').set_value('动物').run(timeout=15)
    button(app, '编辑').click().run(timeout=15)
    next(t for t in app.text_area if t.label == '描述').set_value('不应保存')
    button(app, '关闭编辑').click().run(timeout=15)
    assert app.text_input(key='archive_keyword').value == '动物'
    assert repo.snapshot()['learning_activities'][0] == record
    assert not app.session_state['record_dialog_open']


def test_modal_rechecks_concurrent_change_before_confirm(repo, image_bytes):
    app, record = start(repo, image_bytes)
    button(app, '删除').click().run(timeout=15)
    with repo.transaction() as data:
        data['learning_activities'][0]['description'] = '其他家长已修改'
    button(active_dialog(app), '确认执行').click().run(timeout=15)
    result = repo.snapshot()['learning_activities'][0]
    assert is_live(result) and result['description'] == '其他家长已修改'
    assert not app.exception


def test_viewer_detects_removed_record_and_exits_without_mutation(repo, image_bytes):
    app, record = start(repo, image_bytes)
    app.sidebar.radio[0].set_value('照片回忆').run(timeout=15)
    button(app, '放大照片').click().run(timeout=15)
    with repo.transaction() as data:
        data['learning_activities'][0]['_deleted_at'] = '2026-09-21'
    app.run(timeout=15)
    assert '已被移除' in active_dialog(app).info[0].value
    button(app, '关闭照片').click().run(timeout=15)
    assert not app.exception


def test_dismiss_callback_cancels_pending_delete_without_writing(monkeypatch, repo, image_bytes):
    import streamlit as st
    from family_features.record_management import close_record_dialog, preview_change
    record, _ = save_web_photos('认识动物', '认知卡', '2026-09-15', [image_bytes], 'u', repo)
    preview_change('ACTIVITY', record, 'web:test:manage', action='DELETE', repository=repo)
    state = {'agent_context_id':'web:test', 'record_dialog_open':True, 'record_editor':{'expected':record}}
    monkeypatch.setattr(st, 'session_state', state)
    close_record_dialog()
    assert not state['record_dialog_open'] and 'record_editor' not in state
    assert not repo.snapshot()['_agent_v2']['contexts']['web:test:manage'].get('pending')
    assert repo.snapshot()['learning_activities'][0] == record


def test_open_menu_then_edit_closes_dropdown_before_showing_dialog(repo, image_bytes):
    app, _ = start(repo, image_bytes)
    app.sidebar.radio[0].set_value('照片回忆').run(timeout=15)
    menu_key = next(k for k in app.session_state.filtered_state if k.startswith('photo_menu_'))
    app.session_state[menu_key] = True
    app.run(timeout=15)
    button(app, '编辑').click().run(timeout=15)
    assert active_dialog(app).text_input
    assert app.session_state[menu_key] is False
    assert not app.exception
