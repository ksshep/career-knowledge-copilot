from collections.abc import Mapping


RAG_INSTRUCTION = (
    "回答时只能依据以下给定资料作答；如果资料不足，请明确说明无法确定。"
)


class RAGContextError(ValueError):
    """Raised when search results or context limits are invalid."""


def build_rag_context(
    search_results: list[Mapping[str, object]],
    max_chunks: int = 5,
    max_chars: int = 6000,
) -> dict[str, str | list[dict[str, str | int]]]:
    """Format ranked search results into bounded model context and citations."""
    _validate_limits(max_chunks, max_chars)
    if not isinstance(search_results, list):
        raise RAGContextError("search_results must be a list")

    if not search_results:
        return {"context": "没有找到足够依据", "citations": []}

    validated_results = [_validate_result(result) for result in search_results]
    ranked_results = sorted(
        validated_results,
        key=lambda result: result["similarity_score"],
        reverse=True,
    )[:max_chunks]

    context = RAG_INSTRUCTION
    citations: list[dict[str, str | int]] = []
    seen_citations: set[tuple[str, int]] = set()

    for result in ranked_results:
        prefix = (
            f"\n\n文件：{result['filename']}"
            f"\n页码：第 {result['page_number']} 页"
            f"\n片段：第 {result['chunk_index']} 段"
            "\n内容："
        )
        remaining = max_chars - len(context) - len(prefix)
        if remaining <= 0:
            break

        content = result["content"][:remaining]
        context += prefix + content

        citation_key = (result["filename"], result["page_number"])
        if citation_key not in seen_citations:
            citations.append(
                {
                    "filename": result["filename"],
                    "page_number": result["page_number"],
                    "chunk_index": result["chunk_index"],
                }
            )
            seen_citations.add(citation_key)

        if len(context) >= max_chars:
            break

    return {"context": context, "citations": citations}


def _validate_limits(max_chunks: int, max_chars: int) -> None:
    if not isinstance(max_chunks, int) or isinstance(max_chunks, bool) or max_chunks <= 0:
        raise RAGContextError("max_chunks must be greater than 0")
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars <= 0:
        raise RAGContextError("max_chars must be greater than 0")
    if max_chars < len(RAG_INSTRUCTION):
        raise RAGContextError("max_chars is too small for the required instruction")


def _validate_result(result: Mapping[str, object]) -> dict[str, str | int | float]:
    if not isinstance(result, Mapping):
        raise RAGContextError("each search result must be a mapping")

    filename = result.get("filename")
    page_number = result.get("page_number")
    chunk_index = result.get("chunk_index")
    content = result.get("content")
    score = result.get("similarity_score")

    if not isinstance(filename, str) or not filename.strip():
        raise RAGContextError("search result filename must be a non-empty string")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number <= 0:
        raise RAGContextError("search result page_number must be greater than 0")
    if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index < 0:
        raise RAGContextError("search result chunk_index must be non-negative")
    if not isinstance(content, str) or not content.strip():
        raise RAGContextError("search result content must be a non-empty string")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise RAGContextError("search result similarity_score must be numeric")

    return {
        "filename": filename,
        "page_number": page_number,
        "chunk_index": chunk_index,
        "content": content,
        "similarity_score": float(score),
    }
