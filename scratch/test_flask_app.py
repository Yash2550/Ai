import sys
import os
sys.path.insert(0, os.path.abspath("."))
import app

def test_app():
    client = app.app.test_client()
    resp = client.get('/')
    print("GET / status code:", resp.status_code)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    html = resp.data.decode('utf-8')
    assert "GOMZI BOB" in html, "GOMZI BOB title missing"
    assert "GOMZI NUTRITION" in html, "GOMZI NUTRITION branding missing"
    assert "Hamza Nutrition" not in html, "Hamza Nutrition still present"
    assert "NX NUTRI LAB" not in html, "NX NUTRI LAB still present"
    assert "Live 3D Container" in html, "Live 3D Container missing"
    assert "pacdoraThreeContainer" in html, "3D Container element missing"
    assert "Merchant Brand Kit" in html, "Merchant Brand Kit missing"
    print("ALL ASSERTIONS PASSED! Root route renders GOMZI BOB studio cleanly.")

if __name__ == "__main__":
    test_app()
