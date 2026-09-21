"""Shared, local-only index of the bundled guide and private family books.

No network calls, persistent text exports, or modifications to source books.
Only search results are passed to generation by the calling application.
"""
from functools import lru_cache
from pathlib import Path
from threading import RLock

from sklearn.feature_extraction.text import TfidfVectorizer

from rag.retriever import build_document_chunks
from storage import data_path

BUNDLED_GUIDE = Path(__file__).resolve().parents[1] / "knowledge" / "healthy_parenting_guide_0_3.pdf"
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_CHUNKS = 8000
_LOCK = RLock()


def private_knowledge_dir():
    return data_path("knowledge")


def _signature():
    entries = []
    if BUNDLED_GUIDE.is_file():
        entries.append((BUNDLED_GUIDE, BUNDLED_GUIDE.name, "随项目指南"))
    root = private_knowledge_dir()
    # No symlinks or recursion: adding a directory cannot expose other files.
    if root.is_dir() and not root.is_symlink():
        for path in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
            if not path.is_symlink() and path.is_file() and path.suffix.lower() in {".pdf", ".txt"}:
                entries.append((path, "私有/" + path.name, "家庭私有"))
    signature = []
    for path, label, kind in entries:
        try:
            stat = path.stat()
        except OSError:
            signature.append((str(path), label, kind, -1, -1, -1))
        else:
            signature.append((str(path), label, kind, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))
    return tuple(signature)


@lru_cache(maxsize=1)
def _build_index(signature):
    chunks, inventory = [], []
    for filename, label, kind, size, _, _ in signature:
        row = {"资料": label, "范围": kind, "状态": "已收录", "片段数": 0}
        inventory.append(row)
        if size < 0:
            row["状态"] = "无法读取：检查文件和服务账号权限"
            continue
        if size > MAX_FILE_BYTES:
            row["状态"] = "未收录：单文件超过50MB，请拆分"
            continue
        if len(chunks) >= MAX_CHUNKS:
            row["状态"] = "未收录：总片段数达到8000，请减少资料"
            continue
        try:
            document = build_document_chunks(filename, chunk_size=500, overlap=100)
        except Exception:
            # No raw parser exception or book text is logged publicly.
            row["状态"] = "读取失败：检查格式、加密或权限"
            continue
        document = [item for item in document if len("".join(item["text"].split())) >= 2]
        if not document:
            row["状态"] = "未提取到可检索文字：扫描件需先OCR"
            continue
        if len(chunks) + len(document) > MAX_CHUNKS:
            row["状态"] = "未收录：加入后超过8000片段，请拆分或减少资料"
            continue
        chunks.extend(dict(item, file=label) for item in document)
        row["片段数"] = len(document)
    if not chunks:
        return chunks, inventory, None, None
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), max_features=60000)
    vectors = vectorizer.fit_transform([item["text"] for item in chunks])
    return chunks, inventory, vectorizer, vectors


def _index():
    with _LOCK:
        return _build_index(_signature())


def knowledge_inventory():
    """Read-only status; contents never included in diagnostics."""
    return [dict(row) for row in _index()[1]]


def private_knowledge_chunks():
    """Internal use by the daily excerpt selector; no public download route."""
    return [dict(chunk) for chunk in _index()[0] if chunk["file"].startswith("私有/")]


def search_knowledge(question, top_k=3, min_score=0.04):
    if not str(question).strip() or top_k <= 0:
        return []
    chunks, _, vectorizer, vectors = _index()
    if vectorizer is None:
        return []
    # Vectors are L2-normalized, so their dot product is cosine similarity.
    scores = (vectors @ vectorizer.transform([question]).T).toarray().ravel()
    results = []
    for index in scores.argsort()[::-1]:
        score = float(scores[index])
        if score <= 0 or score < min_score:
            continue
        results.append(dict(chunks[index], score=score))
        if len(results) >= top_k:
            break
    return results
