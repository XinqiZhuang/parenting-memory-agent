from pathlib import Path
from unittest.mock import Mock

from dotenv import dotenv_values


def test_setup_preserves_existing_secrets_and_does_not_echo_them(tmp_path, monkeypatch, capsys):
    import configure_features
    original=tmp_path/'.env'
    original.write_text('DEEPSEEK_API_KEY=private-test-value\nCUSTOM_OPTION=keep\n',encoding='utf-8')
    monkeypatch.setattr(configure_features,'__file__',str(tmp_path/'configure_features.py'))
    answers=iter(['育儿助手Agent','','',''])
    passwords=iter(['family-password-for-test','family-password-for-test'])
    monkeypatch.setattr('builtins.input',lambda *_:next(answers))
    monkeypatch.setattr(configure_features.getpass,'getpass',lambda *_:next(passwords))
    configure_features.main()
    config=dotenv_values(original)
    assert config['DEEPSEEK_API_KEY']=='private-test-value'
    assert config['CUSTOM_OPTION']=='keep'
    assert config['WEB_PASSWORD']=='family-password-for-test'
    assert 'private-test-value' not in capsys.readouterr().out
    assert len(list((tmp_path/'config-backups').iterdir()))==1


def test_short_password_never_modifies_env(tmp_path, monkeypatch):
    import configure_features
    import pytest
    original=tmp_path/'.env'; original.write_bytes(b'DEEPSEEK_API_KEY=keep\n')
    monkeypatch.setattr(configure_features,'__file__',str(tmp_path/'configure_features.py'))
    monkeypatch.setattr('builtins.input',lambda *_:'')
    monkeypatch.setattr(configure_features.getpass,'getpass',lambda *_:'short')
    with pytest.raises(SystemExit):
        configure_features.main()
    assert original.read_bytes()==b'DEEPSEEK_API_KEY=keep\n'
