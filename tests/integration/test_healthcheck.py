import pytest


@pytest.mark.django_db
def test_healthcheck_returns_minimal_public_contract(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
