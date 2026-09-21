from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pypdf import PdfWriter

from rag import knowledge_base as kb


@pytest.fixture
def books(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path / "private")
    guide = tmp_path / "guide.txt"
    guide.write_text("这是公开指南，介绍亲子阅读和讲故事。", encoding="utf-8")
    monkeypatch.setattr(kb, "BUNDLED_GUIDE", guide)
    kb.private_knowledge_dir().mkdir(parents=True)
    kb._build_index.cache_clear()
    yield kb.private_knowledge_dir()
    kb._build_index.cache_clear()


def put(books, name, content):
    path = books / name
    path.write_text(content, encoding="utf-8")
    return path


def test_private_and_bundled_search_share_corpus(books):
    put(books, "book.txt", "拼图实验：先拿起三角形，再放进同形状的框架。")
    assert kb.search_knowledge("三角形拼图")[0]["file"] == "私有/book.txt"
    assert kb.search_knowledge("亲子阅读和讲故事")[0]["file"] == "guide.txt"
    assert all(row["状态"] == "已收录" for row in kb.knowledge_inventory())


def test_cache_refreshes_when_books_change_or_are_removed(books):
    path = put(books, "book.txt", "三角形拼图训练")
    assert kb.search_knowledge("三角形拼图")
    path.write_text("积木搭建活动，排列积木。", encoding="utf-8")
    assert not kb.search_knowledge("三角形拼图")
    assert kb.search_knowledge("积木搭建")
    path.unlink()
    assert not kb.search_knowledge("积木搭建")


def test_bad_and_scanned_files_do_not_disable_other_books(books):
    put(books, "bad.pdf", "not a PDF")
    put(books, "empty.txt", "   \n ")
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(books / "scan.pdf")
    put(books, "good.txt", "形状分类教学实验")
    status = {row["资料"]: row["状态"] for row in kb.knowledge_inventory()}
    assert status["私有/bad.pdf"].startswith("读取失败")
    assert status["私有/scan.pdf"].startswith("未提取到")
    assert status["私有/empty.txt"].startswith("未提取到")
    assert kb.search_knowledge("形状分类")[0]["file"] == "私有/good.txt"


def test_only_private_top_level_supported_files_are_read(books, tmp_path):
    put(books, "ignored.docx", "不应读取这里的词句")
    (books / "nested").mkdir()
    put(books / "nested", "hidden.txt", "不应读取这里的词句")
    target = tmp_path / "secret.txt"
    target.write_text("私人资料不应通过链接收录", encoding="utf-8")
    try:
        (books / "linked.txt").symlink_to(target)
    except OSError:
        pass  # Windows may require privileges for symlinks.
    assert [row["资料"] for row in kb.knowledge_inventory()] == ["guide.txt"]


def test_same_basename_is_unambiguous(books):
    put(books, "guide.txt", "拼图训练与积木堆叠")
    names = {row["资料"] for row in kb.knowledge_inventory()}
    assert names == {"guide.txt", "私有/guide.txt"}


def test_private_pdf_keeps_original_text_and_page(books, monkeypatch):
    import rag.retriever as retriever
    text = "② 12～17小时，幼儿期为10～14小时。"
    monkeypatch.setattr(retriever, "PdfReader", lambda _: SimpleNamespace(
        pages=[SimpleNamespace(extract_text=lambda: text)]))
    put(books, "private.pdf", "fake test input")
    result = kb.search_knowledge("幼儿期")[0]
    assert result["text"] == text
    assert result["page"] == 1


@pytest.mark.parametrize("question,top_k", [("", 3), ("汽车发动机维修", 3), ("亲子阅读", 0)])
def test_empty_or_irrelevant_search(books, question, top_k):
    assert kb.search_knowledge(question, top_k=top_k) == []


def test_capacity_limits_are_visible_and_skip_whole_document(books, monkeypatch):
    monkeypatch.setattr(kb, "MAX_CHUNKS", 1)
    put(books, "extra.txt", "形状分类教学实验")
    row = next(row for row in kb.knowledge_inventory() if row["资料"] == "私有/extra.txt")
    assert row["状态"].startswith("未收录") and row["片段数"] == 0


def test_feishu_and_web_generation_both_retrieve_private_books(books, monkeypatch):
    from rag.generator import answer_with_rag
    from agent_v2.knowledge import evidence_answer
    put(books, "private.txt", "积木堆叠活动：将大积木放在下方，小积木放在上方。")
    reply = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="测试回答[资料1]"))])
    call = Mock(return_value=reply)
    monkeypatch.setattr("rag.generator.client.chat.completions.create", call)
    web = answer_with_rag("积木堆叠")
    assert web["sources"][0]["file"] == "私有/private.txt"
    assert "积木放在下方" in call.call_args.kwargs["messages"][-1]["content"]
    monkeypatch.setattr("openai.OpenAI", lambda **kw: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=call))))
    bot = evidence_answer("积木堆叠")
    assert "私有/private.txt" in bot and "第None页" not in bot
    assert "积木放在下方" in call.call_args.kwargs["messages"][-1]["content"]


def test_checker_does_not_print_book_content(books, monkeypatch, capsys):
    import check_knowledge
    put(books, "private.txt", "这一段私人图书正文不应出现在检查日志中")
    monkeypatch.setattr("sys.argv", ["check_knowledge.py", "--question", "私人图书"])
    check_knowledge.main()
    output = capsys.readouterr().out
    assert "私有/private.txt" in output
    assert "这一段私人图书正文" not in output


def test_new_private_books_are_gitignored():
    import subprocess
    project = Path(__file__).resolve().parents[1]
    if not (project / ".git").exists():
        pytest.skip("Source archive has no git metadata")
    result = subprocess.run(["git", "check-ignore", "data/knowledge/example.pdf", "data/knowledge/nested/a.txt"],
                            cwd=project, capture_output=True, text=True)
    assert result.returncode == 0
    assert len(result.stdout.splitlines()) == 2
