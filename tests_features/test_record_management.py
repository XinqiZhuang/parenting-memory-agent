import copy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from agent_v2.engine import is_live
from agent_v2.parser import parse_command
from agent_v2.schema import Command, Selector
from agent_v2.service import handle_request
from family_features.classification import photo_record_payload
from family_features.media import stage_photo, handle_photo_text, parse_photo_metadata, resolve_photo, save_web_photos
from family_features.record_management import preview_change
from family_features.records import browse_records, daily_summary

APP = Path(__file__).resolve().parents[1] / 'streamlit_app.py'


def seeded(repo):
    with repo.transaction() as data:
        data['development_milestones'] = [
            {'id':'milestone-walk', 'skill':'独立行走','category':'gross_motor','date':'2026-09-12'},
            {'id':'milestone-spoon','skill':'自己用勺子吃饭','category':'fine_motor','date':'2026-09-19'}]
        data['learning_activities'] = [
            {'id':'activity-walk','activity':'练习独走','category':'gross_motor','date':'2026-09-20','duration_minutes':10},
            {'id':'activity-draw','activity':'画画','category':'fine_motor','date':'2026-09-20','duration_minutes':5}]


@pytest.mark.parametrize('history', ['DEVELOPMENT', 'ACTIVITY', 'PHOTO'])
@pytest.mark.parametrize('category,expected', [('大运动','练习独走'), ('精细动作','画画')])
def test_latest_request_does_not_change_with_history(repo, history, category, expected):
    seeded(repo)
    with repo.transaction() as data:
        data['_agent_v2']['contexts']['mother'] = {'last_command': {'entity':history, 'selector':{'name':'不相关内容'}}}
    answer = handle_request(f'宝宝最近一次{category}是什么时候', 'mother', repository=repo)
    assert '2026-09-20' in answer and expected in answer
    assert '2026-09-12' not in answer and '2026-09-19' not in answer


def test_practice_walk_and_explicit_milestone_have_different_scopes(repo):
    seeded(repo)
    answer = handle_request('宝宝最近一次练习走是什么时候', repository=repo)
    assert '2026-09-20' in answer and '练习独走' in answer
    milestone = Command(action='QUERY', entity='DEVELOPMENT', selector={'latest':True,'category':'gross_motor'})
    answer = handle_request('最近一次大运动里程碑',repository=repo,parser=lambda *_:milestone)
    assert '2026-09-12' in answer and '2026-09-20' not in answer


def test_cross_scope_returns_newest_milestone_when_it_really_is_newest(repo):
    seeded(repo)
    with repo.transaction() as data:
        data['development_milestones'][0]['date']='2026-09-21'
    assert '2026-09-21' in handle_request('宝宝最近一次大运动是什么时候',repository=repo)


@pytest.mark.parametrize('delimiter', [' ', '； ', ';', '\n'])
def test_metadata_accepts_normal_separators(delimiter):
    text = '保存照片 ' + delimiter.join(['日期=2026-09-20', '标题=早教活动：认动物', '描述=利用动物模型和认知卡带宝宝认识动物'])
    fields = parse_photo_metadata(text)
    assert fields['date'] == '2026-09-20' and fields['event']=='早教活动：认动物'


@pytest.mark.parametrize('bad', ['实际日期','2026-02-30','YYYY-MM-DD'])
def test_invalid_date_is_friendly_and_preserves_draft(repo,image_bytes,bad):
    stage_photo(image_bytes,'a','photo',repository=repo)
    result = handle_photo_text('保存照片 日期='+bad+' 标题=认识动物','a',repository=repo)
    assert '日期' in result and 'isoformat' not in result
    state = repo.snapshot()['_agent_v2']['contexts']['a']
    assert state.get('photo_draft') and not state.get('pending')


def test_duplicate_unknown_date_field_rejected():
    with pytest.raises(ValueError):
        parse_photo_metadata('照片信息 日期=未知 日期=2026-09-20 标题=相册')


@pytest.mark.parametrize('title,description,day', [
    ('早教活动：认动物','利用动物模型和认知卡带宝宝认识动物','2026-09-20'),
    ('早教活动：认识蔬菜','通过认知卡和蔬菜实体认识蔬菜','2026-09-15')])
def test_user_photo_examples_saved_as_cognitive_activities(repo,image_bytes,title,description,day):
    stage_photo(image_bytes,'a','image',repository=repo)
    handle_photo_text(f'照片信息 日期={day} 标题={title} 描述={description}','a',repository=repo)
    assert not repo.snapshot()['learning_activities']
    handle_request('确认','a',repository=repo)
    data=repo.snapshot()
    assert not data['memories']
    record=data['learning_activities'][0]
    assert record['activity']==title and record['category']=='cognitive'
    assert record['date']==day and resolve_photo(record['photos'][0]).exists()
    assert '学习活动：1条' in daily_summary(data, day)
    other = '2026-09-20' if day != '2026-09-20' else '2026-09-15'
    assert title not in daily_summary(data, other)


def test_explicit_memory_is_respected():
    entity, values=photo_record_payload('画画的珍贵回忆','', '2026-09-20',kind='MEMORY')
    assert entity=='MEMORY' and 'category' not in values


def test_vision_objects_do_not_establish_an_activity(repo,image_bytes):
    stage_photo(image_bytes,'a','image',repository=repo)
    handle_photo_text('识别照片','a',repository=repo,recognizer=lambda _: {'event':'认知卡片','description':'一张动物认知卡放在桌上'})
    handle_photo_text('保存照片 日期=2026-09-20','a',repository=repo)
    handle_request('确认','a',repository=repo)
    assert len(repo.snapshot()['memories'])==1 and not repo.snapshot()['learning_activities']


def memory(repo,image_bytes):
    record,_=save_web_photos('早教活动：认识蔬菜','通过卡片认识蔬菜','2026-09-15',[image_bytes],'web:upload',repo,kind='MEMORY')
    return record


def test_convert_preserves_identity_and_photos_and_can_undo(repo,image_bytes):
    original=memory(repo,image_bytes)
    answer=preview_change('MEMORY',original,'manager',action='RECLASSIFY',values={'category':'cognitive'},repository=repo)
    assert '转为学习活动' in answer and len(repo.snapshot()['memories'])==1
    handle_request('确认','manager',repository=repo)
    data=repo.snapshot()
    assert not data['memories']
    result=data['learning_activities'][0]
    assert result['id']==original['id'] and result['photos']==original['photos'] and result['date']==original['date']
    assert result['category']=='cognitive' and result['activity']==original['event'] and 'event' not in result
    assert '学习活动：1条' in daily_summary(data,'2026-09-15')
    handle_request('撤销上次操作','manager',repository=repo)
    handle_request('确认','manager',repository=repo)
    assert repo.snapshot()['memories']==[original] and not repo.snapshot()['learning_activities']


def test_conversion_confirmation_rejects_concurrent_edit(repo,image_bytes):
    original=memory(repo,image_bytes)
    preview_change('MEMORY',original,'manager',action='RECLASSIFY',values={'category':'cognitive'},repository=repo)
    with repo.transaction() as data:
        data['memories'][0]['description']='爸爸修改的描述'
    assert '发生变化' in handle_request('确认','manager',repository=repo)
    assert repo.snapshot()['memories'][0]['description']=='爸爸修改的描述'
    assert not repo.snapshot()['learning_activities']


def test_edit_date_description_category_duration_and_undo(repo,image_bytes):
    record,_=save_web_photos('认动物','旧描述','2026-09-20',[image_bytes],'u',repo)
    answer=preview_change('ACTIVITY',record,'m',values={'date':'2026-09-19','description':'新描述','category':'language','duration_minutes':8},repository=repo)
    assert '尚未写入' in answer and repo.snapshot()['learning_activities'][0]==record
    handle_request('确认','m',repository=repo)
    result=repo.snapshot()['learning_activities'][0]
    assert result['duration_minutes']==8 and result['category']=='language' and result['date']=='2026-09-19'
    assert result['id']==record['id'] and result['photos']==record['photos']
    handle_request('撤销上次操作','m',repository=repo);handle_request('确认','m',repository=repo)
    assert repo.snapshot()['learning_activities'][0]==record


def test_clear_optional_fields_and_detach_photo_is_reversible(repo,image_bytes):
    record=memory(repo,image_bytes)
    preview_change('MEMORY',record,'m',clear_fields=['date','description'],keep_photos=[],repository=repo)
    handle_request('确认','m',repository=repo)
    result=repo.snapshot()['memories'][0]
    assert 'date' not in result and 'description' not in result and not result['photos']
    assert resolve_photo(record['photos'][0]).exists()
    handle_request('撤销上次操作','m',repository=repo);handle_request('确认','m',repository=repo)
    assert repo.snapshot()['memories'][0]==record


def test_stale_editor_cannot_overwrite_newer_record(repo,image_bytes):
    record=memory(repo,image_bytes)
    with repo.transaction() as data:
        data['memories'][0]['event']='新标题'
    assert '已经变化' in preview_change('MEMORY',record,'m',values={'event':'旧页面标题'},repository=repo)
    assert repo.snapshot()['memories'][0]['event']=='新标题'


def test_feishu_can_delete_activity_photo_by_name_then_undo(repo,image_bytes):
    record,_=save_web_photos('早教活动：认动物','利用模型认动物','2026-09-20',[image_bytes],'u',repo)
    answer=handle_request('删除认动物的照片','feishu:family:mother',repository=repo)
    assert '准备删除' in answer and is_live(repo.snapshot()['learning_activities'][0])
    handle_request('确认','feishu:family:mother',repository=repo)
    assert not browse_records(repo.snapshot()) and resolve_photo(record['photos'][0]).exists()
    handle_request('撤销上次操作','feishu:family:mother',repository=repo)
    handle_request('确认','feishu:family:mother',repository=repo)
    assert browse_records(repo.snapshot())[0]['record']==record


def test_feishu_delete_by_short_record_id_without_model(repo,image_bytes):
    record=memory(repo,image_bytes)
    assert '准备删除' in handle_request('删除记录 '+record['id'][:8],'f',repository=repo)
    handle_request('确认','f',repository=repo)
    assert not is_live(repo.snapshot()['memories'][0])


def test_duplicate_photo_titles_require_selection_across_collections(repo,image_bytes):
    original=memory(repo,image_bytes)
    activity,_=save_web_photos(original['event'],original['description'],original['date'],[image_bytes],'u',repo)
    assert '多条' in handle_request('删除认识蔬菜的照片','a',repository=repo)
    data=repo.snapshot()
    candidates=data['_agent_v2']['contexts']['a']['pending']['candidates']
    index=next(i for i,r in enumerate(candidates,1) if r['id']==activity['id'])
    handle_request(f'第{index}项','a',repository=repo);handle_request('确认','a',repository=repo)
    assert is_live(repo.snapshot()['memories'][0]) and not is_live(repo.snapshot()['learning_activities'][0])


def button(app,label):
    return next(b for b in app.button if b.label==label)


def test_web_editor_preview_confirm_and_delete_ui(repo,image_bytes):
    original=memory(repo,image_bytes)
    app=AppTest.from_file(str(APP)).run(timeout=15)
    app.sidebar.radio[0].set_value('档案总览').run(timeout=15)
    button(app,'编辑').click().run(timeout=15)
    next(t for t in app.text_input if t.label=='事件').set_value('蔬菜认知活动')
    button(app,'预览修改').click().run(timeout=15)
    assert not app.exception and repo.snapshot()['memories'][0]['event']==original['event']
    button(app,'确认执行').click().run(timeout=15)
    assert not app.exception and repo.snapshot()['memories'][0]['event']=='蔬菜认知活动'
    button(app,'删除').click().run(timeout=15)
    assert is_live(repo.snapshot()['memories'][0])
    button(app,'确认执行').click().run(timeout=15)
    assert not app.exception and not is_live(repo.snapshot()['memories'][0])
    button(app,'撤销上一次网页编辑或删除').click().run(timeout=15)
    button(app,'确认执行').click().run(timeout=15)
    assert is_live(repo.snapshot()['memories'][0])


def test_photo_wall_converts_memory_and_still_displays_photo(repo,image_bytes):
    original=memory(repo,image_bytes)
    app=AppTest.from_file(str(APP)).run(timeout=15)
    app.sidebar.radio[0].set_value('照片回忆').run(timeout=15)
    button(app,'编辑').click().run(timeout=15)
    next(c for c in app.checkbox if c.label.startswith('把这条回忆转为')).check().run(timeout=15)
    button(app,'预览修改').click().run(timeout=15)
    assert not app.exception
    button(app,'确认执行').click().run(timeout=15)
    assert not app.exception
    record=repo.snapshot()['learning_activities'][0]
    assert record['id']==original['id'] and record['category']=='cognitive'
    assert any('学习活动' in e.value for e in app.caption)
    assert any('蔬菜' in e.value for e in app.markdown)
    button(app,'删除').click().run(timeout=15)
    button(app,'确认执行').click().run(timeout=15)
    assert not app.exception and not is_live(repo.snapshot()['learning_activities'][0])
