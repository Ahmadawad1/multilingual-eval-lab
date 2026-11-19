import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path, serve_frontend=False), base_url="http://127.0.0.1") as c:
        yield c


@pytest.fixture
def tiny_data():
    return {
        "name": "Test",
        "documents": [{"id": "d1", "text": "إِدارة الخدمات"}, {"id": "d2", "text": "خدمات أخرى"}],
        "queries": [
            {
                "id": "q1",
                "question": "اداره",
                "expected_answer": "إِدارة الخدمات",
                "qrels": {"d1": 3, "d2": 0},
            }
        ],
    }
