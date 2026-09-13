from rag.retriever import build_document_chunks


def test_pdf_chunks_keep_source_information():

    chunks = build_document_chunks(
        "knowledge/healthy_parenting_guide_0_3.pdf",
        chunk_size=300,
        overlap=50
    )

    assert len(chunks) > 0

    first_chunk = chunks[0]

    assert (
        first_chunk["file"]
        == "healthy_parenting_guide_0_3.pdf"
    )

    assert first_chunk["page"] == 1

    assert first_chunk["text"]


def test_pdf_contains_development_content():

    chunks = build_document_chunks(
        "knowledge/healthy_parenting_guide_0_3.pdf"
    )

    matching_chunks = [
        chunk
        for chunk in chunks
        if "生长发育" in chunk["text"]
    ]

    assert len(matching_chunks) > 0


if __name__ == "__main__":

    test_pdf_chunks_keep_source_information()
    test_pdf_contains_development_content()

    print("PDF来源和页码测试通过")