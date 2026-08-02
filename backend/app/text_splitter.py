def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[str]:
    """Normalize text and split it into fixed-size overlapping chunks."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool):
        raise ValueError("chunk_size must be an integer")
    if not isinstance(overlap, int) or isinstance(overlap, bool):
        raise ValueError("overlap must be an integer")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []

    chunks: list[str] = []
    step = chunk_size - overlap
    start = 0

    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        chunks.append(normalized_text[start:end])
        if end == len(normalized_text):
            break
        start += step

    return chunks
