from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

from runtime.adapters.blob.minio_store import MinioBlobStore


class MemoryBlobStore:
    """Minimal BlobStorePort for unit tests."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, *, content_type: str = "text/plain") -> str:
        self._objects[key] = data
        return key

    def get(self, key: str) -> bytes:
        return self._objects[key]

    def delete(self, key: str) -> None:
        del self._objects[key]


def test_memory_blob_store_roundtrip():
    store = MemoryBlobStore()
    key = store.put("workspaces/ws/a.md", b"hello", content_type="text/plain")
    assert key == "workspaces/ws/a.md"
    assert store.get(key) == b"hello"
    store.delete(key)
    assert key not in store._objects


@patch("minio.Minio")
def test_minio_blob_store_put_get_delete(mock_minio_cls):
    client = MagicMock()
    client.bucket_exists.return_value = True
    mock_minio_cls.return_value = client

    store = MinioBlobStore(
        endpoint="localhost:9000",
        access_key="k",
        secret_key="s",
        bucket="test-bucket",
    )
    data = b"payload"
    key = store.put("workspaces/local/docs/x.md", data)
    assert key == "workspaces/local/docs/x.md"
    client.put_object.assert_called_once()
    args = client.put_object.call_args[0]
    assert args[0] == "test-bucket"
    assert args[1] == key
    assert isinstance(args[2], BytesIO)

    response = MagicMock()
    response.read.return_value = data
    client.get_object.return_value = response
    assert store.get(key) == data

    store.delete(key)
    client.remove_object.assert_called_with("test-bucket", key)
