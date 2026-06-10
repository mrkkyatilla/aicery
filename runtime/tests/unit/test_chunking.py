from runtime.intelligence.chunking import chunk_text, is_text_file


def test_is_text_file_md():
    assert is_text_file("docs/readme.md")


def test_chunk_text_overlap():
    text = "a" * 3000
    chunks = chunk_text(text, size=2048, overlap=256)
    assert len(chunks) >= 2
    assert all(len(c) <= 2048 for c in chunks)
