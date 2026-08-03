import pytest

from backend.app.rag_context import RAGContextError, build_rag_context


def _result(filename, page_number, chunk_index, content, score):
    return {
        "document_id": "document-id",
        "filename": filename,
        "page_number": page_number,
        "chunk_index": chunk_index,
        "content": content,
        "similarity_score": score,
    }


def test_search_results_generate_context_and_citations():
    result = build_rag_context(
        [_result("resume.pdf", 2, 3, "Python project experience", 0.9)]
    )

    assert "只能依据以下给定资料" in result["context"]
    assert "文件：resume.pdf" in result["context"]
    assert "页码：第 2 页" in result["context"]
    assert "片段：第 3 段" in result["context"]
    assert result["citations"] == [
        {"filename": "resume.pdf", "page_number": 2, "chunk_index": 3}
    ]


def test_results_are_sorted_by_similarity_score():
    result = build_rag_context(
        [
            _result("low.pdf", 1, 0, "low", 0.2),
            _result("high.pdf", 1, 0, "high", 0.9),
        ]
    )

    context = result["context"]
    assert context.index("high") < context.index("low")


def test_max_chunks_limits_context_results():
    result = build_rag_context(
        [_result("file.pdf", index + 1, index, f"content {index}", 1 - index / 10) for index in range(3)],
        max_chunks=2,
    )

    assert "content 0" in result["context"]
    assert "content 1" in result["context"]
    assert "content 2" not in result["context"]


def test_max_chars_limits_total_context_length():
    result = build_rag_context(
        [_result("file.pdf", 1, 0, "x" * 500, 0.9)],
        max_chars=180,
    )

    assert len(result["context"]) <= 180


def test_filename_and_page_number_are_preserved_without_fabrication():
    result = build_rag_context(
        [_result("真实简历.pdf", 7, 2, "真实内容", 0.8)]
    )

    assert "真实简历.pdf" in result["context"]
    assert "第 7 页" in result["context"]
    assert "第 2 段" in result["context"]
    assert "伪造" not in result["context"]


def test_empty_results_return_no_evidence_message():
    result = build_rag_context([])

    assert result == {"context": "没有找到足够依据", "citations": []}


def test_duplicate_file_and_page_citations_are_deduplicated():
    result = build_rag_context(
        [
            _result("resume.pdf", 2, 0, "first chunk", 0.9),
            _result("resume.pdf", 2, 1, "second chunk", 0.8),
        ]
    )

    assert result["context"].count("文件：resume.pdf") == 2
    assert result["citations"] == [
        {"filename": "resume.pdf", "page_number": 2, "chunk_index": 0}
    ]


@pytest.mark.parametrize(
    "results",
    [
        "not a list",
        [{"filename": "resume.pdf"}],
        [{"filename": "resume.pdf", "page_number": 0, "chunk_index": 0, "content": "text", "similarity_score": 0.5}],
    ],
)
def test_invalid_input_format_raises_clear_error(results):
    with pytest.raises(RAGContextError):
        build_rag_context(results)


def test_invalid_limits_raise_clear_error():
    result = [_result("resume.pdf", 1, 0, "text", 0.5)]

    with pytest.raises(RAGContextError):
        build_rag_context(result, max_chunks=0)
    with pytest.raises(RAGContextError):
        build_rag_context(result, max_chars=0)
