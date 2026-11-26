import sys
import os
sys.path.insert(0, os.path.abspath("."))
import app

def test_new_routes():
    client = app.app.test_client()
    
    # 1. Dashboard stats
    r = client.get('/api/dashboard/stats')
    assert r.status_code == 200, f"Stats failed: {r.status_code}"
    stats = r.get_json()
    print("Stats API OK:", stats["provider_status"])
    
    # 2. Products
    r = client.get('/api/products')
    assert r.status_code == 200, f"Products failed: {r.status_code}"
    prods = r.get_json()["products"]
    assert len(prods) >= 4
    print("Products API OK, count:", len(prods))

    # 3. Orders
    r = client.get('/api/orders')
    assert r.status_code == 200, f"Orders failed: {r.status_code}"
    orders = r.get_json()["orders"]
    assert len(orders) >= 3
    print("Orders API OK, count:", len(orders))

    # 4. Save and Get Project
    r = client.post('/api/projects', json={
        "id": "test_proj_1",
        "title": "GOMZI Whey Belgian Chocolate 1kg",
        "product": "Whey Protein Standard",
        "brand_name": "GOMZI NUTRITION",
        "container_color": "#18181b",
        "canvas_json": {"objects": []}
    })
    assert r.status_code == 200, f"Save project failed: {r.status_code}"
    
    r = client.get('/api/projects')
    assert r.status_code == 200
    projects = r.get_json()["projects"]
    assert any(p["id"] == "test_proj_1" for p in projects)
    print("Projects list API OK, found test_proj_1")

    r = client.get('/api/projects/test_proj_1')
    assert r.status_code == 200
    proj_data = r.get_json()
    assert proj_data["title"] == "GOMZI Whey Belgian Chocolate 1kg"
    print("Get project API OK")

    # Clean up test project
    r = client.delete('/api/projects/test_proj_1')
    assert r.status_code == 200
    print("Delete project API OK")
    print("ALL NEW BACKEND API ENDPOINTS VERIFIED!")

if __name__ == "__main__":
    test_new_routes()
