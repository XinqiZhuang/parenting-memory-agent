"""Regression checks for the real authenticated pages and shared record actions."""
import csv
import io
from pathlib import Path

from streamlit.testing.v1 import AppTest

from family_features.media import save_web_photos
from family_features.records import browse_records, export_csv

APP = Path(__file__).resolve().parents[1] / 'streamlit_app.py'


def start():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    return app


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_archive_is_home_and_add_opens_existing_chat(repo):
    repo.snapshot()
    app = start()
    assert app.title[0].value == '档案总览'
    assert not app.chat_input
    button(app, '新增记录').click().run(timeout=15)
    assert not app.exception and app.chat_input
    assert app.sidebar.radio[0].value == '宝宝档案'


def test_table_columns_keep_measurements_and_export_separate_fields(repo):
    with repo.transaction() as data:
        data['feeding_records'].append({'type':'奶','date':'2026-09-20','amount_ml':180,'foods':['南瓜']})
        data['growth_records'].append({'date':'2026-09-20','height_cm':76,'weight_kg':10.6})
        data['learning_activities'].append({'activity':'画画','duration_minutes':0,'description':'=2+2'})
    app = start()
    text = '\n'.join(e.value for e in app.markdown)
    for label in ['活动 / 事件','时长','描述','操作','0 分钟']:
        assert label in text
    assert any('180' in e.value for e in app.caption)
    assert any('10.6' in e.value for e in app.caption)
    exported = list(csv.DictReader(io.StringIO(export_csv(browse_records(repo.snapshot())).decode('utf-8-sig'))))
    feeding = next(r for r in exported if r['类型']=='喂养')
    assert feeding['奶量(ml)']=='180' and feeding['食物']=='南瓜'
    assert next(r for r in exported if r['活动 / 事件']=='画画')['描述']=="'=2+2"


def test_category_filter_delete_targets_exact_row_and_keeps_other_records(repo):
    with repo.transaction() as data:
        data['learning_activities'] = [{'id':'cognitive-record','activity':'认动物','category':'cognitive'},
                                      {'id':'motor-record','activity':'练习独走','category':'gross_motor'}]
    app = start()
    app.selectbox(key='archive_category').set_value('cognitive').run(timeout=15)
    assert len([b for b in app.button if b.label=='删除'])==1
    button(app,'删除').click().run(timeout=15)
    assert all(not r.get('_deleted_at') for r in repo.snapshot()['learning_activities'])
    button(app,'确认执行').click().run(timeout=15)
    records = repo.snapshot()['learning_activities']
    assert records[0].get('_deleted_at') and not records[1].get('_deleted_at')
    assert not app.exception


def test_pagination_and_filter_reset_do_not_edit_wrong_record(repo):
    with repo.transaction() as data:
        data['learning_activities'] = [{'id':f'activity-{i}','activity':f'练习项目{i:02}','date':'2026-09-20'} for i in range(22)]
    app=start()
    assert len([b for b in app.button if b.label=='编辑']) == 15
    app.selectbox(key='archive_page').set_value(2).run(timeout=15)
    button(app,'编辑').click().run(timeout=15)
    assert app.session_state['record_editor']['expected']['id']=='activity-15'
    button(app,'关闭编辑').click().run(timeout=15)
    app.text_input(key='archive_keyword').set_value('练习项目03').run(timeout=15)
    assert not app.exception
    button(app,'编辑').click().run(timeout=15)
    assert app.session_state['record_editor']['expected']['id']=='activity-3'


def test_photo_wall_filter_keeps_title_description_and_existing_upload_form(repo,image_bytes):
    save_web_photos('认识蔬菜','通过实物认知','2026-09-15',[image_bytes],'u',repo)
    save_web_photos('散步回忆','一家人在公园','2026-09-20',[image_bytes],'u',repo,kind='MEMORY')
    app=start()
    app.sidebar.radio[0].set_value('照片回忆').run(timeout=15)
    assert not app.text_area
    app.radio(key='photo_category').set_value('认知').run(timeout=15)
    assert len([b for b in app.button if b.label=='编辑'])==1
    assert any('认识蔬菜' in e.value for e in app.markdown)
    button(app,'上传照片').click().run(timeout=15)
    assert not app.exception and app.text_area
    button(app,'收起上传').click().run(timeout=15)
    assert not app.exception and not app.text_area


def test_user_text_cannot_inject_markup_into_gallery(repo,image_bytes):
    save_web_photos('<img src=x onerror=alert(1)>','<script>unsafe</script>','2026-09-20',[image_bytes],'u',repo,kind='MEMORY')
    app=start()
    app.sidebar.radio[0].set_value('照片回忆').run(timeout=15)
    text='\n'.join(e.value for e in app.markdown)
    assert '&lt;script&gt;unsafe&lt;/script&gt;' in text
    assert '<script>unsafe</script>' not in text and '<img src=x' not in text


def test_daily_view_uses_event_date_and_allows_edit(repo,image_bytes):
    save_web_photos('认识蔬菜','实物认知','2026-09-15',[image_bytes],'u',repo)
    app=start()
    app.sidebar.radio[0].set_value('每日记录').run(timeout=15)
    from datetime import date
    app.date_input(key='diary_day').set_value(date(2026,9,15)).run(timeout=15)
    assert len([b for b in app.button if b.label=='编辑'])==1
    app.date_input(key='diary_day').set_value(date(2026,9,16)).run(timeout=15)
    assert not [b for b in app.button if b.label=='编辑']
    assert not app.exception
