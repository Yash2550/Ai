"""
End-to-End Acceptance Tests for CorelDRAW Desktop Bridge, TIFF Support,
Convert to Vector, and High-Res Print Export (300/600 DPI + Bleed).
"""
import base64
import io
import json
import os
import sys
import threading
import urllib.error
import urllib.request

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app
from coreldraw_bridge.bridge_server import create_bridge_server
from reconstruction_engine.security_validator import validate_uploaded_file
from reconstruction_engine.smart_importer import detect_file_type_strict


def _make_sample_image_bytes(fmt: str = "PNG", rgba: bool = False) -> bytes:
    mode = "RGBA" if rgba else "RGB"
    bg = (255, 255, 255, 0) if rgba else (246, 244, 236)
    img = Image.new(mode, (640, 260), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 620, 240], fill=(32, 48, 28, 255) if rgba else (32, 48, 28))
    draw.rectangle([40, 45, 320, 120], fill=(116, 136, 61, 255) if rgba else (116, 136, 61))
    draw.text((55, 70), "GOMZI WHEY 1KG", fill=(255, 255, 255, 255) if rgba else (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def main():
    results = []
    client = app.test_client()

    def record(name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}" + (f" -> {detail}" if detail else ""))
        results.append({"name": name, "passed": passed, "detail": detail})
        assert passed, f"Test failed: {name} ({detail})"

    # 1. TIFF magic-byte detection & security validator
    tiff_bytes = _make_sample_image_bytes("TIFF", rgba=False)
    det = detect_file_type_strict(tiff_bytes, "label_test.tiff")
    val = validate_uploaded_file(tiff_bytes, "label_test.tiff")
    record("TIFF magic detection & validator", det == "tiff" and val.get("pixel_width") == 640, f"fmt={det}, meta={val}")

    # 2. TIFF import through /api/canva/import-design
    resp_imp = client.post(
        "/api/canva/import-design",
        data={"file": (io.BytesIO(tiff_bytes), "label_test.tiff"), "use_vision": "false"},
        content_type="multipart/form-data",
    )
    imp_json = resp_imp.get_json() or {}
    record(
        "TIFF import via /api/canva/import-design",
        resp_imp.status_code == 200 and imp_json.get("success") is True and bool(imp_json.get("fabric_json")),
        f"status={resp_imp.status_code}, objs={len((imp_json.get('fabric_json') or {}).get('objects', []))}",
    )

    # 3. Print Export: PNG 300 DPI (160x65mm, 0mm bleed)
    png_b64 = "data:image/png;base64," + base64.b64encode(_make_sample_image_bytes("PNG", rgba=True)).decode("ascii")
    resp_png = client.post(
        "/api/canva/export-print",
        json={"image_data": png_b64, "format": "png", "width_mm": 160, "height_mm": 65, "dpi": 300, "bleed_mm": 0},
    )
    with Image.open(io.BytesIO(resp_png.data)) as im:
        exp_w, exp_h = round(160 * 300 / 25.4), round(65 * 300 / 25.4)
        dpi_info = im.info.get("dpi", (0, 0))
        record(
            "Print Export PNG 300 DPI exact mm",
            resp_png.status_code == 200 and im.size == (exp_w, exp_h) and round(dpi_info[0]) == 300,
            f"size={im.size}, expected={(exp_w, exp_h)}, dpi={dpi_info}",
        )

    # 4. Print Export: Transparent PNG 300 DPI
    resp_trans = client.post(
        "/api/canva/export-print",
        json={"image_data": png_b64, "format": "png_transparent", "width_mm": 100, "height_mm": 50, "dpi": 300, "bleed_mm": 0},
    )
    with Image.open(io.BytesIO(resp_trans.data)) as im:
        record(
            "Print Export Transparent PNG preserves RGBA",
            resp_trans.status_code == 200 and im.mode == "RGBA",
            f"mode={im.mode}",
        )

    # 5. Print Export: JPG 600 DPI + 3mm Bleed + Honest RGB header
    resp_jpg = client.post(
        "/api/canva/export-print",
        json={"image_data": png_b64, "format": "jpg", "width_mm": 80, "height_mm": 40, "dpi": 600, "bleed_mm": 3},
    )
    with Image.open(io.BytesIO(resp_jpg.data)) as im:
        bleed_px = round(3 * 600 / 25.4)
        exp_w = round(80 * 600 / 25.4) + 2 * bleed_px
        exp_h = round(40 * 600 / 25.4) + 2 * bleed_px
        cs = resp_jpg.headers.get("X-Print-Color-Space")
        record(
            "Print Export JPG 600 DPI + 3mm bleed + honest RGB",
            resp_jpg.status_code == 200 and im.size == (exp_w, exp_h) and cs == "RGB",
            f"size={im.size}, expected={(exp_w, exp_h)}, color_space={cs}",
        )

    # 6. Print Export: TIFF 300 DPI + 3mm Bleed
    resp_tiff = client.post(
        "/api/canva/export-print",
        json={"image_data": png_b64, "format": "tiff", "width_mm": 120, "height_mm": 60, "dpi": 300, "bleed_mm": 3},
    )
    with Image.open(io.BytesIO(resp_tiff.data)) as im:
        record(
            "Print Export TIFF LZW 300 DPI + bleed",
            resp_tiff.status_code == 200 and im.format == "TIFF" and resp_tiff.headers.get("X-Print-Bleed-MM") == "3.0",
            f"format={im.format}, size={im.size}",
        )

    # 7. Convert to Vector endpoint
    resp_vec = client.post(
        "/api/canva/convert-to-vector",
        json={"image_data": png_b64, "width_mm": 160, "height_mm": 65, "use_vision": False},
    )
    vec_json = resp_vec.get_json() or {}
    record(
        "Convert to Vector endpoint",
        resp_vec.status_code == 200 and vec_json.get("success") is True and len((vec_json.get("fabric_json") or {}).get("objects", [])) >= 1,
        f"stats={vec_json.get('stats')}",
    )

    # 8. CorelDRAW Desktop Bridge server auth, origin check & honest absent-CorelDRAW response
    srv, tok = create_bridge_server(host="127.0.0.1", port=0, token="gomzi-test-bridge-token")
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        base_url = f"http://127.0.0.1:{port}"

        # Unauthenticated request -> 401
        try:
            urllib.request.urlopen(f"{base_url}/bridge/status", timeout=2)
            unauth_code = 200
        except urllib.error.HTTPError as he:
            unauth_code = he.code
        record("Bridge rejects unauthenticated request (401)", unauth_code == 401, f"code={unauth_code}")

        # Disallowed origin -> 403
        req_orig = urllib.request.Request(
            f"{base_url}/bridge/status",
            headers={"Authorization": f"Bearer {tok}", "Origin": "https://untrusted.example"},
        )
        try:
            urllib.request.urlopen(req_orig, timeout=2)
            orig_code = 200
        except urllib.error.HTTPError as he:
            orig_code = he.code
        record("Bridge rejects disallowed Origin (403)", orig_code == 403, f"code={orig_code}")

        # Authenticated status -> 200 & honest coreldraw_installed=False on this host
        req_ok = urllib.request.Request(
            f"{base_url}/bridge/status",
            headers={"Authorization": f"Bearer {tok}"},
        )
        with urllib.request.urlopen(req_ok, timeout=2) as r:
            st_data = json.loads(r.read().decode("utf-8"))
        record(
            "Bridge authenticated status is honest",
            st_data.get("ok") is True and st_data.get("coreldraw_installed") is False,
            f"status={st_data}",
        )

        # Wire Flask env to test bridge & verify /api/coreldraw/status + /api/coreldraw/export-cdr never fake .cdr
        old_url = os.environ.get("CORELDRAW_BRIDGE_URL")
        old_tok = os.environ.get("CORELDRAW_BRIDGE_TOKEN")
        os.environ["CORELDRAW_BRIDGE_URL"] = base_url
        os.environ["CORELDRAW_BRIDGE_TOKEN"] = tok
        try:
            r_st = client.get("/api/coreldraw/status")
            d_st = r_st.get_json() or {}
            record(
                "Flask /api/coreldraw/status reports bridge_running=True & native_cdr_available=False",
                r_st.status_code == 200 and d_st.get("bridge_running") is True and d_st.get("native_cdr_available") is False,
                f"payload={d_st}",
            )

            r_cdr = client.post(
                "/api/coreldraw/export-cdr",
                json={"fabric_json": {"width": 800, "height": 400, "objects": []}, "filename": "test"},
            )
            record(
                "Flask /api/coreldraw/export-cdr returns 503 instead of fake .cdr",
                r_cdr.status_code == 503 and "application/json" in (r_cdr.content_type or ""),
                f"status={r_cdr.status_code}",
            )
        finally:
            if old_url is None:
                os.environ.pop("CORELDRAW_BRIDGE_URL", None)
            else:
                os.environ["CORELDRAW_BRIDGE_URL"] = old_url
            if old_tok is None:
                os.environ.pop("CORELDRAW_BRIDGE_TOKEN", None)
            else:
                os.environ["CORELDRAW_BRIDGE_TOKEN"] = old_tok
    finally:
        srv.shutdown()
        srv.server_close()

    # 9. UI controls present in rendered HTML
    html = client.get("/").get_data(as_text=True)
    required_ids = [
        'id="canvaToolConvertVectorBtn"',
        'id="canvaToolRestoreOriginalBtn"',
        'id="smartReconProgressPill"',
        'id="canvaExportPngTransBtn"',
        'id="canvaExportTiffBtn"',
        'id="exportPrintDpiSelect"',
        'id="exportPrintBleedSelect"',
        'id="canvaOpenCorelBtn"',
        'id="canvaDownloadNativeCdrBtn"',
    ]
    missing = [rid for rid in required_ids if rid not in html]
    record(
        "Studio HTML contains all print, vector, Smart Import, and CorelDRAW bridge controls",
        len(missing) == 0 and 'id="canvaDownloadNativeCdrBtn" class="btn-outline-clean" style="border:none;justify-content:flex-start;" disabled' in html,
        f"missing={missing}",
    )

    # 10. Live Browser test: Upload Full Label auto-reconstructs into editable text + clean plate + hidden Original Reference + Restore Original
    import socket
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    live_port = sock.getsockname()[1]
    sock.close()
    live_srv = make_server("127.0.0.1", live_port, app, threaded=True)
    srv_thread = threading.Thread(target=live_srv.serve_forever, daemon=True)
    srv_thread.start()
    try:
        sample_label = os.path.join(ROOT, "tests", "fixtures", "label_essential_whey.jpg")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("dialog", lambda d: d.accept())
            page.goto(f"http://127.0.0.1:{live_port}/", wait_until="domcontentloaded")
            page.wait_for_function("() => typeof canvaCanvas !== 'undefined' && canvaCanvas && typeof runAutoSmartReconstruct === 'function'", timeout=25000)

            page.set_input_files("#inputUploadFullLabel", sample_label)
            page.wait_for_function(
                "() => typeof canvaCanvas !== 'undefined' && canvaCanvas && canvaCanvas.getObjects().some(o => o.assetType === 'original_reference')",
                timeout=90000,
            )
            stats_after = page.evaluate("""() => {
                const objs = canvaCanvas.getObjects();
                const ref = objs.find(o => o.assetType === 'original_reference');
                const texts = objs.filter(o => o.type === 'textbox' || o.type === 'i-text');
                return {
                    total: objs.length,
                    textCount: texts.length,
                    hasHiddenLockedRef: Boolean(ref && ref.visible === false && ref.selectable === false),
                };
            }""")
            record(
                "Upload Full Label auto-reconstructs editable text + hidden locked reference",
                stats_after["total"] >= 3 and stats_after["textCount"] >= 1 and stats_after["hasHiddenLockedRef"],
                f"stats={stats_after}",
            )

            page.click("#canvaToolRestoreOriginalBtn")
            page.wait_for_timeout(400)
            restored = page.evaluate("""() => {
                const objs = canvaCanvas.getObjects();
                return { total: objs.length, assetType: objs[0]?.assetType };
            }""")
            record(
                "Restore Original restores full-label artwork non-destructively",
                restored["total"] == 1 and restored["assetType"] == "full_label_artwork",
                f"restored={restored}",
            )
            browser.close()
    finally:
        live_srv.shutdown()

    print(f"\nSUMMARY: {sum(1 for r in results if r['passed'])}/{len(results)} PASSED")


if __name__ == "__main__":
    main()
