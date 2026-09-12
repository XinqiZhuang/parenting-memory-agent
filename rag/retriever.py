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

def split_text(
    text,
    chunk_size=300,
    overlap=50
):

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
    min_score=0.025
):

    if not chunks:
        return []

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4)
    )

    vectors = vectorizer.fit_transform(
        chunks + [question]
    )

    chunk_vectors = vectors[:-1]
    question_vector = vectors[-1]

    similarities = cosine_similarity(
        question_vector,
        chunk_vectors
    )[0]

    ranked_indexes = similarities.argsort()[::-1]

    results = []

    for index in ranked_indexes:

        score = float(similarities[index])

        if score < min_score:
            continue

        results.append({
            "text": chunks[index],
            "score": score
        })

        if len(results) >= top_k:
            break

    return results