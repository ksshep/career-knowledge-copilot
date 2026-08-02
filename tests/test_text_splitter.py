import pytest

from backend.app.text_splitter import split_text_into_chunks


def test_short_text_is_not_split():
    assert split_text_into_chunks("short text", chunk_size=20, overlap=5) == [
        "short text"
    ]


def test_long_text_is_split_into_multiple_chunks():
    chunks = split_text_into_chunks("abcdefghijklmnopqrstuvwxyz", chunk_size=10, overlap=2)

    assert len(chunks) > 1
    assert "".join(chunks) != "abcdefghijklmnopqrstuvwxyz"


def test_each_chunk_is_at_most_chunk_size():
    chunks = split_text_into_chunks("abcdefghijklmnopqrstuvwxyz", chunk_size=10, overlap=2)

    assert all(len(chunk) <= 10 for chunk in chunks)


def test_adjacent_chunks_keep_the_requested_overlap():
    chunks = split_text_into_chunks("abcdefghijklmnopqrstuvwxyz", chunk_size=10, overlap=3)

    for previous, current in zip(chunks, chunks[1:]):
        assert previous[-3:] == current[:3]


def test_empty_text_returns_empty_list():
    assert split_text_into_chunks("") == []


def test_whitespace_only_text_returns_empty_list():
    assert split_text_into_chunks(" \n\t  ") == []


def test_multiple_whitespace_is_collapsed():
    assert split_text_into_chunks("  hello\n\n world\tagain  ") == [
        "hello world again"
    ]


def test_non_positive_chunk_size_raises_value_error():
    with pytest.raises(ValueError, match="chunk_size"):
        split_text_into_chunks("text", chunk_size=0)


def test_negative_overlap_raises_value_error():
    with pytest.raises(ValueError, match="overlap"):
        split_text_into_chunks("text", overlap=-1)


def test_overlap_equal_to_or_greater_than_chunk_size_raises_value_error():
    with pytest.raises(ValueError, match="overlap"):
        split_text_into_chunks("text", chunk_size=10, overlap=10)
    with pytest.raises(ValueError, match="overlap"):
        split_text_into_chunks("text", chunk_size=10, overlap=11)


def test_chinese_text_is_split_by_character_length():
    chunks = split_text_into_chunks("这是一个用于测试文本切片的中文句子", chunk_size=8, overlap=2)

    assert len(chunks) > 1
    assert all(len(chunk) <= 8 for chunk in chunks)
    for previous, current in zip(chunks, chunks[1:]):
        assert previous[-2:] == current[:2]
