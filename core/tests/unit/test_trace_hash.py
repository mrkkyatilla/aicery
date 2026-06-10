from core.trace.hashing import hash_messages, hash_text, hash_tool_input


def test_hash_stability_messages() -> None:
    messages = [{"role": "user", "content": "hello"}]
    assert hash_messages(messages) == hash_messages(messages)


def test_hash_stability_tool() -> None:
    args = {"path": "README.md"}
    assert hash_tool_input("read_file", args) == hash_tool_input("read_file", args)


def test_hash_text_differs() -> None:
    assert hash_text("a") != hash_text("b")
