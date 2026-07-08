from fastapi.testclient import TestClient

from pipeline.api.app import app

client = TestClient(app)


def test_openapi_lists_all_expected_routes():
    paths = app.openapi()["paths"]
    expected = {
        "/status",
        "/books",
        "/books/{book_id}",
        "/books/{book_id}/files",
        "/books/{book_id}/files/{source_file}",
        "/books/{book_id}/conversations",
        "/books/{book_id}/conversations/{conversation_id}",
        "/books/{book_id}/conversations/{conversation_id}/ask",
    }
    assert expected.issubset(set(paths.keys()))
