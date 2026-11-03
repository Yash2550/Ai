import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_dashboard_and_export_endpoints(client):
    # 1. Main index loads successfully
    resp = client.get("/")
    assert resp.status_code == 200

    # 2. Health check route loads
    resp_h = client.get("/health")
    assert resp_h.status_code == 200

    # 3. Official Canva integration returns friendly error without crash when unconfigured
    resp_c = client.post("/api/canva/official/import-design", json={
        "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "title": "Test Design"
    })
    # Should return 400 or 500 with friendly message, never crash
    assert resp_c.status_code in (400, 500)
    data = resp_c.get_json()
    assert "error" in data or "message" in data

