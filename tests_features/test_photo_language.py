import json
from datetime import date
from types import SimpleNamespace as Obj
from unittest.mock import Mock

import pytest

from agent_v2.parser import ParseError
from agent_v2.service import handle_request
from family_features.media import handle_photo_text, stage_photo
from family_features.photo_language import parse_photo_note, resolve_date

TODAY = date(2026, 9, 20)
NOTE = '这是9月15日，我们通过动物模型和认知卡教宝宝认识动物'
RESULT = dict(event='认识动物', description='通过动物模型和认知卡教宝宝认识动物',
              kind='ACTIVITY', category='cognitive', date_text='9月15日')


def parser(raw=RESULT):
    return lambda text, current: parse_photo_note(text, current, caller=lambda _: raw, today=TODAY)


def context(repo, actor='mother'):
    return repo.snapshot()['_agent_v2']['contexts'][actor]


def preview(repo, image_bytes):
    stage_photo(image_bytes, 'mother', 'image', repository=repo)
    return handle_photo_text(NOTE, 'mother', 'note', repository=repo, note_parser=parser())


def test_user_exact_sentence_activity_photo_and_confirmation(repo, image_bytes):
    answer = preview(repo, image_bytes)
    assert '2026-09-15' in answer and '认知' in answer and '尚未写入' in answer
    assert '没有写年份' in answer
    assert not repo.snapshot()['learning_activities'] and not repo.snapshot()['memories']
    assert handle_photo_text('确认', 'mother', repository=repo) is None
    handle_request('确认', 'mother', request_id='confirm', repository=repo)
    record = repo.snapshot()['learning_activities'][0]
    assert record['activity'] == '认识动物' and record['category'] == 'cognitive'
    assert record['date'] == '2026-09-15' and len(record['photos']) == 1
    assert len(repo.snapshot()['_agent_v2']['events']) == 1


@pytest.mark.parametrize('expression,expected', [
    ('9月15日', '2026-09-15'), ('九月十五日', '2026-09-15'),
    ('2025年9月15日', '2025-09-15'), ('去年9月15日', '2025-09-15'),
    ('2026/9/15', '2026-09-15'), ('昨天', '2026-09-19'), ('大前天', '2026-09-17'),
    ('上周五', '2026-09-11'), ('本周三', '2026-09-16')])
def test_explicit_dates(expression, expected):
    assert resolve_date(expression, today=TODAY)[0] == expected


def test_relative_date_uses_family_timezone(monkeypatch):
    monkeypatch.setattr('family_features.photo_language.family_now', lambda: Obj(date=lambda: date(2026, 9, 21)))
    assert resolve_date('昨天')[0] == '2026-09-20'


def test_date_omitted_by_model_still_preserved():
    result = dict(RESULT); result.pop('date_text')
    assert parse_photo_note(NOTE, caller=lambda _: result, today=TODAY)['date'] == '2026-09-15'


def test_model_cannot_fabricate_date_or_paths():
    with pytest.raises(ValueError):
        parse_photo_note(NOTE, caller=lambda _: dict(RESULT, date_text='2020-01-01'))
    with pytest.raises(ParseError):
        parse_photo_note(NOTE, caller=lambda _: dict(RESULT, photos=['/etc/passwd']))
    with pytest.raises(ValueError):
        parse_photo_note('宝宝玩套杯', caller=lambda _: dict(event='套杯', date_unknown=True))


@pytest.mark.parametrize('reply', ['日期记不清了', '记不清了', '不知道', '未知'])
def test_missing_date_plain_reply_retains_metadata(repo, image_bytes, reply):
    stage_photo(image_bytes, 'mother', 'image', repository=repo)
    raw = dict(RESULT); raw.pop('date_text')
    answer = handle_photo_text('我们通过模型教宝宝认识动物', 'mother', repository=repo, note_parser=parser(raw))
    assert '事件日期' in answer and not context(repo).get('pending')
    answer = handle_photo_text(reply, 'mother', repository=repo)
    assert '未知' in answer and '尚未写入' in answer
    handle_request('确认', 'mother', repository=repo)
    record = repo.snapshot()['learning_activities'][0]
    assert record['activity'] == '认识动物' and 'date' not in record


def test_date_correction_replaces_preview_same_photo_no_extra_record(repo, image_bytes):
    preview(repo, image_bytes)
    original = context(repo)['pending']['after']
    answer = handle_photo_text('日期改成9月16日', 'mother', 'fix', repository=repo)
    after = context(repo)['pending']['after']
    assert '2026-09-16' in answer
    assert original['id'] == after['id'] and original['photos'] == after['photos']
    assert handle_photo_text('日期改成9月16日', 'mother', 'fix', repository=repo) == answer
    handle_request('确认', 'mother', repository=repo)
    assert [r['date'] for r in repo.snapshot()['learning_activities']] == ['2026-09-16']


def test_partial_day_preserves_explicit_previous_year_month(repo, image_bytes):
    preview(repo, image_bytes)
    handle_photo_text('2025年9月15日', 'mother', repository=repo)
    answer = handle_photo_text('改成16号', 'mother', repository=repo)
    assert '2025-09-16' in answer and '月份沿用' in answer


def test_invalid_correction_withdraws_old_preview_and_retains_photo(repo, image_bytes):
    preview(repo, image_bytes)
    answer = handle_photo_text('日期改成2月30日', 'mother', repository=repo)
    assert '不存在' in answer and '原预览已撤回' in answer
    assert not context(repo).get('pending') and context(repo)['photo_draft']['photos']
    assert '还没有生成' in handle_photo_text('确认', 'mother', repository=repo)
    assert not repo.snapshot()['learning_activities']
    handle_photo_text('9月16日', 'mother', repository=repo)
    assert context(repo)['pending']['after']['date'] == '2026-09-16'


def test_api_failure_keeps_draft_and_does_not_confirm_old_preview(repo, image_bytes):
    preview(repo, image_bytes)
    def fail(*_):
        raise ParseError('暂时没能整理这句话')
    answer = handle_photo_text('改成认识蔬菜', 'mother', repository=repo, note_parser=fail)
    assert '原预览已撤回' in answer and not context(repo).get('pending')
    assert context(repo)['photo_draft']['photos']


def test_revision_of_category_and_title_keeps_date_and_photo(repo, image_bytes):
    preview(repo, image_bytes)
    answer = handle_photo_text('其实是玩套杯，改成精细动作', 'mother', repository=repo,
                              note_parser=parser(dict(event='玩套杯', kind='ACTIVITY', category='fine_motor')))
    assert '精细动作' in answer and '2026-09-15' in answer
    assert context(repo)['pending']['after']['activity'] == '玩套杯'


def test_unrelated_request_not_treated_as_photo_note(repo, image_bytes):
    preview(repo, image_bytes)
    old = context(repo)['pending']
    assert handle_photo_text('宝宝吃了什么', 'mother', repository=repo,
                             note_parser=parser(dict(intent='other'))) is None
    assert context(repo)['pending'] == old


def test_ambiguous_description_does_not_write_or_keep_old_preview(repo, image_bytes):
    preview(repo, image_bytes)
    answer = handle_photo_text('两张照片分别是不同天', 'mother', repository=repo,
                              note_parser=parser(dict(intent='clarify', question='这组照片是哪一天？')))
    assert '哪一天' in answer and not context(repo).get('pending')
    assert context(repo)['photo_draft']['photos']


def test_other_actor_cannot_change_or_confirm_photo(repo, image_bytes):
    preview(repo, image_bytes)
    assert handle_photo_text('日期改成9月16日', 'father', repository=repo) is None
    assert handle_photo_text('确认', 'father', repository=repo) is None
    assert context(repo)['pending']['after']['date'] == '2026-09-15'


def test_stale_completion_cannot_overwrite_confirmed_record(repo, image_bytes):
    preview(repo, image_bytes)
    def concurrent(*_):
        handle_request('确认', 'mother', repository=repo)
        return dict(date='2026-09-16')
    answer = handle_photo_text('日期改成9月16日', 'mother', repository=repo, note_parser=concurrent)
    assert '已变化' in answer and not context(repo).get('pending')
    assert repo.snapshot()['learning_activities'][0]['date'] == '2026-09-15'
    assert not context(repo).get('photo_draft')


def test_expired_preview_cannot_be_revived_by_correction(repo, image_bytes):
    preview(repo, image_bytes)
    with repo.transaction() as data:
        data['_agent_v2']['contexts']['mother']['pending']['created_at'] = 0
    assert '过期' in handle_photo_text('日期改成9月16日', 'mother', repository=repo)
    assert not context(repo).get('pending') and not repo.snapshot()['learning_activities']


def test_model_gets_only_this_draft_metadata_not_other_people_or_photo_paths():
    caller = Mock(return_value=RESULT)
    parse_photo_note(NOTE, {'event':'动物', 'photos':['secret-path'], 'other_actor':'secret-name'}, caller=caller, today=TODAY)
    payload = json.loads(caller.call_args.args[0][1]['content'])
    assert payload['当前草稿'] == {'event':'动物'}


def test_vision_then_raw_sentence_replaces_visual_list_with_user_story(repo, image_bytes):
    stage_photo(image_bytes, 'mother', 'image', repository=repo)
    handle_photo_text('识别照片', 'mother', repository=repo,
                      recognizer=lambda _: dict(event='木托盘和卡片', description='画面有老虎和狮子。'))
    answer = handle_photo_text(NOTE, 'mother', repository=repo, note_parser=parser())
    assert '认知' in answer and '木托盘' not in answer
    assert context(repo)['pending']['after']['description'] == RESULT['description']


def test_rich_post_caption_preview_and_duplicate_delivery(monkeypatch, repo, image_bytes):
    import feishu_bot
    monkeypatch.setattr(feishu_bot, 'allowed', lambda *_: True)
    monkeypatch.setattr('agent_v2.service.default_repository', lambda: repo)
    monkeypatch.setattr('family_features.media.default_repository', lambda: repo)
    monkeypatch.setattr('family_features.transport.download_photo', lambda *_: image_bytes)
    monkeypatch.setattr('family_features.photo_language.parse_photo_note', parser())
    reply = Mock(return_value=True)
    monkeypatch.setattr(feishu_bot, 'reply_text', reply)
    content = {'zh_cn':{'content': [[{'tag':'img','image_key':'image'}, {'tag':'text','text':NOTE}]]}}
    msg = Obj(chat_id='test-group', chat_type='p2p', message_id='post1', message_type='post', mentions=[], content=json.dumps(content))
    event = Obj(event=Obj(message=msg, sender=Obj(sender_type='user', sender_id=Obj(open_id='mother'))))
    feishu_bot.process_message(event)
    actor = 'feishu:test-group:mother'
    assert '尚未写入' in reply.call_args.args[1]
    assert len(context(repo, actor)['pending']['after']['photos']) == 1
    feishu_bot.process_message(event)
    assert len(context(repo, actor)['pending']['after']['photos']) == 1
    assert not repo.snapshot()['learning_activities']
    handle_request('确认', actor, repository=repo)
    feishu_bot.process_message(event)
    assert len(repo.snapshot()['learning_activities']) == 1
    assert not context(repo, actor).get('pending')
    # A fresh photo must not rewrite a previous unconfirmed record with its caption.
    stage_photo(image_bytes, actor, 'newphoto', repository=repo)
    handle_photo_text(NOTE, actor, repository=repo)
    before = context(repo, actor)['pending']
    msg.message_id = 'post2'
    feishu_bot.process_message(event)
    assert '先确认' in reply.call_args.args[1]
    assert context(repo, actor)['pending'] == before
