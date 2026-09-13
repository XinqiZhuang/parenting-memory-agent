import pytest

from evaluation.rag_cases import RAG_CASES
from evaluation.evaluate_rag_retrieval import (
    contains_expected_keywords,
)
from rag.retriever import (
    build_document_chunks,
    retrieve_chunks,
)


PDF_PATH = "knowledge/healthy_parenting_guide_0_3.pdf"


@pytest.fixture(scope="module")
def document_chunks():

    return build_document_chunks(
        PDF_PATH,
        chunk_size=500,
        overlap=150
    )


@pytest.mark.parametrize(
    "case",
    RAG_CASES
)
def test_rag_retrieval(
    case,
    document_chunks
):

    results = retrieve_chunks(
        case["question"],
        document_chunks,
        top_k=3,
        min_score=0.04
    )

    if case["should_find"]:

        assert contains_expected_keywords(
            results,
            case["expected_keywords"]
        )

    else:

        assert results == []