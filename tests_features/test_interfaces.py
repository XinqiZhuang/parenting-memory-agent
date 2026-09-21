import json
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from family_features.transport import download_photo, send_text

APP = Path(__file__).resolve().parents[1] / 'streamlit_app.py'


def test_all_web_pages_open_and_dashboard_reads_shared_data(repo):
    with repo.transaction() as data:
        data['learning_activities'].append({'activity':'套杯游戏','date':'2026-09-20'})
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    for page in ['档案总览','每日推送','照片回忆','育儿知识库','宝宝档案']:
        app.sidebar.radio[0].set_value(page).run(timeout=15)
        assert not app.exception, page
        if page == '档案总览':
            assert any('套杯游戏' in element.value for element in app.markdown)


def test_public_web_requires_password(monkeypatch):
    monkeypatch.setenv('APP_ENV','production')
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert app.error and not app.chat_input and not app.sidebar.radio
    monkeypatch.setenv('WEB_PASSWORD','test-passphrase-12345')
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert len(app.text_input)==1 and not app.sidebar.radio
    app.text_input[0].set_value('wrong')
    app.button[0].click().run(timeout=15)
    assert not app.sidebar.radio
    app.session_state['_login_after']=0
    app.text_input[0].set_value('test-passphrase-12345')
    app.button[0].click().run(timeout=15)
    assert not app.exception and app.sidebar.radio


def test_push_form_saves_and_preview_does_not_send(monkeypatch):
    from family_features.settings import load_settings
    sender=Mock()
    monkeypatch.setattr('family_features.transport.send_text',sender)
    app=AppTest.from_file(str(APP)).run(timeout=15)
    app.sidebar.radio[0].set_value('每日推送').run(timeout=15)
    app.text_input(key='push_cfg_chat').set_value('test-group')
    app.checkbox(key='push_cfg_summary').check()
    next(b for b in app.button if b.label=='保存推送设置').click().run(timeout=15)
    assert not app.exception and load_settings().summary_enabled
    next(b for b in app.button if b.label=='仅预览，不发送').click().run(timeout=15)
    assert not app.exception
    sender.assert_not_called()


def test_sdk_download_and_send_request_shapes(image_bytes):
    import io
    client=Mock()
    response=Obj(success=lambda:True,file=io.BytesIO(image_bytes),code=0)
    client.im.v1.message_resource.get.return_value=response
    assert download_photo(client,'om_x','img_x')==image_bytes
    request=client.im.v1.message_resource.get.call_args.args[0]
    assert request.paths == {'message_id':'om_x','file_key':'img_x'}
    client.im.v1.message.create.return_value=Obj(success=lambda:True,data=Obj(message_id='om_y'))
    assert send_text('test-group','日报','token',client)=='om_y'
    request=client.im.v1.message.create.call_args.args[0]
    assert request.request_body.uuid=='token'
    assert json.loads(request.request_body.content)['text']=='日报'


def test_rich_post_extracts_mentions_text_and_photos():
    from feishu_bot import extract_post
    payload={'zh_cn':{'title':'','content':[[{'tag':'at','user_id':'bot'}, {'tag':'text','text':'上传照片'}, {'tag':'img','image_key':'img_1'}]]}}
    assert extract_post(Obj(content=json.dumps(payload)))==('上传照片',['img_1'])


def test_group_messages_not_addressed_to_bot_are_ignored(monkeypatch):
    import feishu_bot
    monkeypatch.setattr(feishu_bot,'allowed',lambda *_:True)
    route=Mock()
    monkeypatch.setattr(feishu_bot,'route_request',route)
    reply=Mock(); monkeypatch.setattr(feishu_bot,'reply_text',reply)
    msg=Obj(chat_id='test-group',chat_type='group',message_id='om',message_type='text',mentions=[],content='{"text":"普通聊天"}')
    sender=Obj(sender_type='user',sender_id=Obj(open_id='mother'))
    feishu_bot.process_message(Obj(event=Obj(message=msg,sender=sender)))
    route.assert_not_called(); reply.assert_not_called()


def test_private_photo_then_confirm_visible_to_dashboard(monkeypatch,repo,image_bytes):
    import feishu_bot
    monkeypatch.setattr(feishu_bot,'allowed',lambda *_:True)
    monkeypatch.setattr('family_features.transport.download_photo',lambda *_:image_bytes)
    reply=Mock(return_value=True)
    monkeypatch.setattr(feishu_bot,'reply_text',reply)
    def send(kind, content, identity):
        message=Obj(chat_id='test-group',chat_type='p2p',message_id=identity,message_type=kind,mentions=[],content=json.dumps(content))
        sender=Obj(sender_type='user',sender_id=Obj(open_id='mother'))
        feishu_bot.process_message(Obj(event=Obj(message=message,sender=sender)))
    repo.snapshot()  # Initialize an empty family instead of the example profile.
    send('image',{'image_key':'i'},'p1')
    assert not repo.snapshot()['memories']
    send('text',{'text':'照片信息 标题=玩套杯；日期=2026-09-20'},'p2')
    assert '尚未写入' in reply.call_args.args[1]
    send('text',{'text':'确认'},'p3')
    from family_features.records import browse_records
    assert browse_records(repo.snapshot())[0]['record']['activity']=='玩套杯'
    assert browse_records(repo.snapshot())[0]['entity']=='ACTIVITY'
