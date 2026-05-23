from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chunking_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/v1/chunking/strategies")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

