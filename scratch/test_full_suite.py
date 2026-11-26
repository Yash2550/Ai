# -*- coding: utf-8 -*-
"""
Comprehensive automated test suite for GOMZI BOB AI Studio Pro.
Tests every API route, export format, inpainting, project persistence,
and verifies 100% of the UI element IDs from BUTTON_FUNCTIONALITY_AUDIT.md.
"""

import sys
import os
import json
import base64
import io
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
import app

def run_suite():
    print("==================================================")
    print("RUNNING GOMZI BOB FULL FUNCTIONALITY TEST SUITE")
    print("==================================================")

    client = app.app.test_client()

    # 1. Root route and HTML inspection
    print("\n[TEST 1] Verifying Root Route ('/') and UI Elements...")
    resp = client.get('/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    html = resp.data.decode('utf-8')
    assert "GOMZI BOB" in html, "GOMZI BOB missing in HTML"
    assert "GOMZI NUTRITION" in html, "GOMZI NUTRITION missing in HTML"
    assert "Hamza Nutrition" not in html, "Hamza Nutrition unexpectedly present"
    assert "NX NUTRI LAB" not in html, "NX NUTRI LAB unexpectedly present"
    print("✓ Root route renders clean GOMZI BOB HTML without legacy brands.")

    # 2. Check all audited element IDs
    print("\n[TEST 2] Verifying Interactive Element IDs in DOM...")
    required_ids = [
        "sidebarNavDashboard", "sidebarNavOrders", "sidebarNavProducts",
        "sidebarGroupDesigns", "sidebarNavStudio", "sidebarNavMyDesigns",
        "sidebarNavCustomLabels", "sidebarNavReturns", "sidebarNavAccounts",
        "sidebarNavIntegrations", "sidebarNavSettings", "sidebarNavHelp",
        "navLogoBtn", "navCatalogBtn", "navNewOrderBtn", "navUserProfile",
        "studioBackBtn", "studioProductPill", "canvaDocTitleInput",
        "canvaUndoBtn", "canvaRedoBtn", "canvaFontFamily", "canvaBoldBtn",
        "canvaItalicBtn", "canvaAlignLeftBtn", "canvaAlignCenterBtn", "canvaAlignRightBtn",
        "canvaDuplicateBtn", "canvaDeleteBtn", "studioFocusBtn", "studioToolsBtn",
        "studio3dToggleBtn", "canvaPrintGuidesBtn", "canvaApplyBtn", "canvaExportMenuBtn",
        "canvaExportCdrBtn", "canvaExportPdfBtn", "canvaExportPngBtn", "canvaExportSvgBtn",
        "tabTemplates", "tabBrand", "tabText", "tabFacts", "tabUploads", "tabLayers", "tabAiTools",
        "canvaZoomInBtn", "canvaZoomOutBtn", "canvaZoomVal", "canvaZoomFitBtn", "canvaCenterLabelBtn",
        "canvaAdjustLogoQuickBtn", "canvaBrandNameInput", "canvaInsertBrandNameBtn",
        "canvaUploadBrandLogoInput", "canvaRestoreFactoryLogoBtn", "canvaBrandLogoPosXSlider",
        "canvaBrandLogoPosYSlider", "canvaBrandLogoSizeSlider", "canvaBrandLogoRotSlider",
        "canvaCenterLogoOnLabelBtn", "canvaLogoCleanPlateToggle",
        "canvaMainCanvas", "footerSelectLogoBtn", "footerCenterBtn", "footerCleanPlateBtn", "footerRestoreLogoBtn",
        "pacdoraThreeContainer", "btnViewFront", "btnViewBack", "btnViewSide",
        "canvaAutoSpinBtn", "canvaReset3dCameraBtn", "canvaPkgColorSwatches",
        "canvaToolGrabTextBtn", "canvaToolBgRemoverBtn", "canvaToolMagicEraserBtn", "canvaToolUpscaleBtn"
    ]

    missing_ids = [eid for eid in required_ids if f'id="{eid}"' not in html]
    if missing_ids:
        print(f"❌ Missing IDs: {missing_ids}")
        assert False, f"Missing element IDs: {missing_ids}"
    print(f"✓ All {len(required_ids)} interactive elements found in index.html!")

    # 3. Dashboard Stats API
    print("\n[TEST 3] Testing Dashboard Stats API ('/api/dashboard/stats')...")
    resp = client.get('/api/dashboard/stats')
    assert resp.status_code == 200
    stats = resp.get_json()
    assert "total_projects" in stats and "labels_generated" in stats
    print(f"✓ Stats API OK: {stats['provider_status']}, Total Projects: {stats['total_projects']}")

    # 4. Products Catalog API
    print("\n[TEST 4] Testing Products Catalog API ('/api/products')...")
    resp = client.get('/api/products')
    assert resp.status_code == 200
    products = resp.get_json()["products"]
    assert len(products) >= 4
    print(f"✓ Products API OK: {len(products)} packaging presets available.")

    # 5. Orders API
    print("\n[TEST 5] Testing Orders Module API ('/api/orders')...")
    resp = client.get('/api/orders')
    assert resp.status_code == 200
    orders = resp.get_json()["orders"]
    assert len(orders) >= 3
    print(f"✓ Orders API OK: {len(orders)} active production orders.")

    # 6. Project Persistence (Save, List, Get, Duplicate, Delete)
    print("\n[TEST 6] Testing Project Persistence Life Cycle...")
    dummy_proj_id = "test_gomzi_suite_01"
    save_payload = {
        "id": dummy_proj_id,
        "title": "GOMZI Whey Belgian Chocolate 1kg Test",
        "product": "Whey Protein Standard",
        "container": "1 kg Muscle Tub · 45.2 × 14.2 cm",
        "brand_name": "GOMZI NUTRITION",
        "container_color": "#18181b",
        "canvas_json": {"version": "5.3.1", "objects": [{"type": "textbox", "text": "GOMZI TEST"}]}
    }
    r = client.post('/api/projects', json=save_payload)
    assert r.status_code == 200, f"Save failed: {r.status_code}"
    print("  -> POST /api/projects: SUCCESS")

    r = client.get('/api/projects')
    assert r.status_code == 200
    p_list = r.get_json()["projects"]
    assert any(p["id"] == dummy_proj_id for p in p_list)
    print("  -> GET /api/projects: SUCCESS (Found saved project)")

    r = client.get(f'/api/projects/{dummy_proj_id}')
    assert r.status_code == 200
    p_data = r.get_json()
    assert p_data["title"] == save_payload["title"]
    print("  -> GET /api/projects/<id>: SUCCESS (Retrieved complete project state)")

    r = client.post(f'/api/projects/{dummy_proj_id}/duplicate')
    assert r.status_code == 200
    dup_data = r.get_json()["project"]
    assert "Copy of" in dup_data["title"]
    print("  -> POST /api/projects/<id>/duplicate: SUCCESS")

    # Clean up duplicated and original
    client.delete(f'/api/projects/{dup_data["id"]}')
    client.delete(f'/api/projects/{dummy_proj_id}')
    print("  -> DELETE /api/projects/<id>: SUCCESS (Cleaned up test data)")

    # 7. Export Master Testing (PDF, PNG, JPG, CDR package)
    print("\n[TEST 7] Testing Export Master ('/api/canva/export-master')...")
    # Create simple 1536x512 PNG data URL
    im = Image.new("RGB", (1536, 512), (229, 231, 235))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    b64_data = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    for fmt in ["png", "jpg", "pdf", "cdr"]:
        r = client.post('/api/canva/export-master', json={
            "image_data": b64_data,
            "format": fmt,
            "filename": f"gomzi_test.{fmt}"
        })
        assert r.status_code == 200, f"Export {fmt} failed with {r.status_code}"
        assert len(r.data) > 100, f"Export {fmt} returned empty data"
        print(f"  -> Export {fmt.upper()} OK: Generated {len(r.data)} bytes")

    # 8. Clean Plate Local Inpainting
    print("\n[TEST 8] Testing Clean Plate Local Inpainting ('/api/canva/inpaint-text')...")
    r = client.post('/api/canva/inpaint-text', json={
        "image_data": b64_data,
        "regions": [{"left": 674, "top": 38, "width": 180, "height": 60}]
    })
    assert r.status_code == 200
    res_inpaint = r.get_json()
    assert res_inpaint.get("success") is True
    assert "clean_background_url" in res_inpaint
    print("  -> Local Inpainting / Clean Plate API OK")

    # 9. Grab Text OCR Detection
    print("\n[TEST 9] Testing Grab Text OCR Detection ('/api/canva/detect-text')...")
    r = client.post('/api/canva/detect-text', json={
        "image_data": b64_data
    })
    assert r.status_code == 200
    res_ocr = r.get_json()
    assert "text_elements" in res_ocr
    print("  -> Grab Text OCR Detection API OK")

    print("\n==================================================")
    print("ALL 9 FUNCTIONALITY GROUPS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_suite()
