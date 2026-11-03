import os
import json
import base64
import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_roundtrip_save_and_cache_clear(client):
    # 1. Create a dummy test image in static/results/
    test_filename = "test_roundtrip_master.png"
    results_dir = app.config.get("RESULTS_FOLDER", "static/results")
    os.makedirs(results_dir, exist_ok=True)
    target_path = os.path.join(results_dir, test_filename)
    cache_path = os.path.join(results_dir, "test_roundtrip_master_ultrahd_8000.png")

    # Write initial dummy files
    with open(target_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
    with open(cache_path, "wb") as f:
        f.write(b"dummy_cache_data")

    assert os.path.exists(cache_path)

    # 2. Call /save-editor-result with updated canvas data
    new_data_b64 = "data:image/png;base64," + base64.b64encode(b"new_image_data_bytes").decode("ascii")
    resp = client.post("/save-editor-result", json={
        "filename": test_filename,
        "image_data": new_data_b64
    })

    assert resp.status_code == 200
    res_data = resp.get_json()
    assert res_data["success"] is True
    assert test_filename in res_data["result_image"]

    # 3. Cache MUST be cleared
    assert not os.path.exists(cache_path), "Cache was not invalidated on save!"

    # Clean up test files
    if os.path.exists(target_path): os.remove(target_path)

