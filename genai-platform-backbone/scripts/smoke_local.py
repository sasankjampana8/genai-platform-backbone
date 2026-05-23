from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    health = client.get("/health")
    print("health:", health.status_code, health.json())
    strategies = client.get("/v1/chunking/strategies")
    print("chunking strategies:", strategies.status_code, strategies.json()["data"])


if __name__ == "__main__":
    main()

