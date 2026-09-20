from pathlib import Path

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def read_document(file_path):

    path = Path(file_path)

    if path.suffix.lower() == ".pdf":

        reader = PdfReader(path)

        pages = [
            page.extract_text() or ""
            for page in reader.pages
        ]

        return "\n".join(pages)

    return path.read_text(encoding="utf-8")

def read_document_pages(file_path):

    path = Path(file_path)

    if path.suffix.lower() == ".pdf":

        reader = PdfReader(path)

        pages = []

        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            page_text = page.extract_text() or ""

            page_text = clean_document_text(
                page_text
            )

            pages.append({
                "text": page_text,
                "file": path.name,
                "page": page_number
            })

        return pages

    return [
        {
            "text": path.read_text(
                encoding="utf-8"
            ),
            "file": path.name,
            "page": None
        }
    ]


def build_document_chunks(
    file_path,
    chunk_size=300,
    overlap=50
):

    pages = read_document_pages(file_path)

    document_chunks = []

    for page_data in pages:

        page_chunks = split_text(
            page_data["text"],
            chunk_size=chunk_size,
            overlap=overlap
        )

        for chunk in page_chunks:

            document_chunks.append({
                "text": chunk,
                "file": page_data["file"],
                "page": page_data["page"]
            })

    return document_chunks

def split_text(
    text,
    chunk_size=300,
    overlap=50
):

    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("必须满足chunk_size > overlap >= 0")

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    chunks = []

    for paragraph in paragraphs:

        if len(paragraph) <= chunk_size:
            chunks.append(paragraph)
            continue

        start = 0

        while start < len(paragraph):

            end = start + chunk_size

            chunk = paragraph[start:end]

            if chunk:
                chunks.append(chunk)

            start = end - overlap

    return chunks

def retrieve_chunks(
    question,
    chunks,
    top_k=3,
    min_score=0.04
):

    if not chunks:
        return []

    chunk_texts = [
        chunk["text"]
        if isinstance(chunk, dict)
        else chunk
        for chunk in chunks
    ]

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4)
    )

    chunk_vectors = vectorizer.fit_transform(
        chunk_texts
    )

    question_vector = vectorizer.transform(
        [question]
    )

    similarities = cosine_similarity(
        question_vector,
        chunk_vectors
    )[0]

    ranked_indexes = similarities.argsort()[::-1]

    results = []

    for index in ranked_indexes:

        score = float(similarities[index])

        if score <= 0 or score < min_score:
            continue

        original_chunk = chunks[index]

        result = {
            "text": chunk_texts[index],
            "score": score
        }

        if isinstance(original_chunk, dict):

            result["file"] = original_chunk["file"]
            result["page"] = original_chunk["page"]

        results.append(result)

        if len(results) >= top_k:
            break

    return results

def clean_document_text(text):
    replacements = {
        "② 12～17小时，幼儿期为10～14小时。":
        (
            "② 睡眠时间。保证婴幼儿的充足睡眠，"
            "每天总睡眠时间在婴儿期为12～17小时，"
            "幼儿期为10～14小时。"
        )
    }

    cleaned_text = text

    for old_text, new_text in replacements.items():
        cleaned_text = cleaned_text.replace(
            old_text,
            new_text
        )

    return cleaned_text
