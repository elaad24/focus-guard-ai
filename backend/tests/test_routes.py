from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_invalid_mode_returns_400(client: TestClient) -> None:
    response = client.post("/mode", json={"mode": "not_a_real_mode"})
    assert response.status_code == 400
    assert "Invalid mode" in response.json()["detail"]


def test_invalid_settings_mode_returns_400(client: TestClient) -> None:
    response = client.post("/settings", json={"mode": "not_a_real_mode"})
    assert response.status_code == 400


def test_invalid_warning_threshold_order_returns_400(client: TestClient) -> None:
    response = client.post(
        "/settings",
        json={
            "softWarningAfterSeconds": 200,
            "mediumWarningAfterSeconds": 10,
            "finalAlertAfterSeconds": 5,
        },
    )
    assert response.status_code == 400
    assert "soft < medium < final" in response.json()["detail"]
