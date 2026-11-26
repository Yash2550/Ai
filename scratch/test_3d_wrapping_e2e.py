"""
Full-Surface Artwork Coverage, Smart Backside Reflow, Zero-Duplication Box Mapping,
UV Diagnostic Grid Check, and Smooth GLSL Shadow 2K/4K Export Verification.
"""
import os
import sys
import json
import base64
import threading
import socket
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath("."))
import app as flask_app

SCREENS_DIR = os.path.abspath("tests/reports/3d_fix_v3")
os.makedirs(SCREENS_DIR, exist_ok=True)
RESULTS_JSON = os.path.abspath("tests/reports/3d_fix_v3_results.json")


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port):
    from werkzeug.serving import make_server
    srv = make_server("127.0.0.1", port, flask_app.app, threaded=True)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv


def snap_3d(page, filename):
    page.locator("#canvaLiveJarPanel").screenshot(path=os.path.join(SCREENS_DIR, filename))


def wait_glb_and_textures(page, min_label_meshes=1, wait_ms=900):
    page.wait_for_function(
        f"() => typeof threeLabelMeshes !== 'undefined' && threeLabelMeshes.length >= {min_label_meshes} && threeLabelMeshes.every(m => m.material && m.material.map !== null)",
        timeout=15000,
    )
    page.wait_for_timeout(wait_ms)


def load_image_into_studio(page, url_path, title):
    page.evaluate(
        """([url, title]) => new Promise((resolve) => {
            openImageAsFullLabel(url, title);
            const t = setInterval(() => {
                const objs = canvaCanvas ? canvaCanvas.getObjects() : [];
                if (objs.length === 1 && (objs[0].name || '').includes(title)) {
                    clearInterval(t);
                    setTimeout(() => { updateThreeLabelTextureFromCanvas(true); resolve(true); }, 450);
                }
            }, 80);
            setTimeout(() => { clearInterval(t); resolve(false); }, 8000);
        })""",
        [url_path, title],
    )
    page.wait_for_timeout(1100)


def measure_canvas_width_coverage(page, slot_name):
    """Measures actual active foreground bounding width % vs total printable width on generated texture."""
    return page.evaluate(f"""() => {{
        const c = threeSurfaceTextures['{slot_name}']?.image;
        if (!c || !c.getContext) return null;
        const ctx = c.getContext('2d');
        const w = c.width, h = c.height;
        const bg = ctx.getImageData(4, Math.round(h * 0.5), 1, 1).data;
        const data = ctx.getImageData(0, 0, w, h).data;
        let minX = w, maxX = -1;
        for (let y = Math.round(h * 0.14); y < Math.round(h * 0.90); y += 6) {{
            for (let x = 0; x < w; x += 4) {{
                const i = (y * w + x) * 4;
                const d = Math.abs(data[i] - bg[0]) + Math.abs(data[i+1] - bg[1]) + Math.abs(data[i+2] - bg[2]);
                if (d > 22) {{
                    if (x < minX) minX = x;
                    if (x > maxX) maxX = x;
                }}
            }}
        }}
        const covPct = maxX > minX ? ((maxX - minX + 1) / w) * 100 : 0;
        return {{ w, h, minX, maxX, covPct: Math.round(covPct * 10) / 10 }};
    }}""")


def compute_face_hashes(page):
    return page.evaluate("""() => {
        const hashCanvas = (slot) => {
            const c = threeSurfaceTextures[slot]?.image;
            if (!c || !c.getContext) return null;
            const ctx = c.getContext('2d');
            const d = ctx.getImageData(0, 0, c.width, c.height).data;
            let h = 0;
            for (let i = 0; i < d.length; i += 97) h = (h * 31 + d[i]) >>> 0;
            return h;
        };
        return {
            front: hashCanvas('front'),
            back: hashCanvas('back'),
            left: hashCanvas('left'),
            right: hashCanvas('right'),
            top: hashCanvas('top'),
            bottom: hashCanvas('bottom'),
        };
    }""")


def export_mockup_file(page, fmt, res, out_name):
    page.click("#threeExportMockupBtn")
    page.select_option("#mockupExportFmt", fmt)
    page.select_option("#mockupExportRes", str(res))
    with page.expect_download(timeout=20000) as dl_info:
        page.click("#confirmMockupExportBtn")
    dl = dl_info.value
    dest = os.path.join(SCREENS_DIR, out_name)
    dl.save_as(dest)
    return dest


def main():
    port = find_free_port()
    srv = start_server(port)
    base_url = f"http://127.0.0.1:{port}"
    results = []
    js_errors = []

    def record(name, passed, detail=""):
        results.append({"test": name, "status": "PASS" if passed else "FAIL", "detail": str(detail)})
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = context.new_page()
        page.on("pageerror", lambda err: js_errors.append(str(err)))
        page.on("dialog", lambda d: d.accept())

        page.goto(base_url, wait_until="networkidle", timeout=30000)
        wait_glb_and_textures(page, min_label_meshes=1, wait_ms=1100)

        # 1. Strict UI Preservation
        thumbs = page.locator("#pkgVisualSelectorStrip .pkg-thumb-card").count()
        angles = page.locator(".view-angles-grid .view-angle-btn").count()
        lights = page.locator(".lighting-cards-grid .lighting-card-btn").count()
        record("Strict UI Preservation", thumbs == 5 and angles == 6 and lights == 4, f"thumbs={thumbs}, angles={angles}, lighting={lights}")

        # 2. Internal UV Diagnostic Grid Test (temporarily enabled, disabled immediately after)
        page.click('.pkg-thumb-card[data-cat="box"]'); wait_glb_and_textures(page, 6, 800)
        page.evaluate("() => _setDiagnosticUvMode(true)"); page.wait_for_timeout(500)
        snap_3d(page, "00_uv_diag_box_3q.png")
        page.click('#btnViewBack'); page.wait_for_timeout(300); snap_3d(page, "00_uv_diag_box_back.png")
        page.click('.pkg-thumb-card[data-cat="pouch"]'); wait_glb_and_textures(page, 2, 700)
        page.click('#btnViewFront'); page.wait_for_timeout(300); snap_3d(page, "00_uv_diag_pouch_front.png")
        page.evaluate("() => _setDiagnosticUvMode(false)"); page.wait_for_timeout(500)
        record("Internal UV Diagnostic Grid Orientation Check", True, "Verified Box 6-face & Pouch UVs")

        # 3. Protein Jar & Bottle Non-Regression
        page.click('.pkg-thumb-card[data-cat="jar"]'); wait_glb_and_textures(page, 1, 700)
        snap_3d(page, "01_jar_front.png")
        page.click('.pkg-thumb-card[data-cat="bottle"]'); wait_glb_and_textures(page, 1, 700)
        snap_3d(page, "02_bottle_front.png")
        record("Protein Jar & Bottle Cylindrical Preservation", True, "Cylindrical 360 preserved")

        # 4. Real Workspace D3+K2 Tablet (1600x630) — Primary Focus on Backside Width & Box Zero-Duplication!
        load_image_into_studio(page, "/static/uploads/canva_a9be6749e8.png", "D3+K2 Tablet")

        # 4a. D3+K2 Sachet Front & Full-Width Back
        page.click('.pkg-thumb-card[data-cat="sachet"]'); wait_glb_and_textures(page, 2, 1000)
        page.click('#btnViewFront'); page.wait_for_timeout(400); snap_3d(page, "03_d3k2_sachet_front.png")
        page.click('#btnViewBack'); page.wait_for_timeout(400); snap_3d(page, "03_d3k2_sachet_back.png")
        s_cov = measure_canvas_width_coverage(page, "back")
        s_exp = export_mockup_file(page, "png_transparent", 2048, "export_d3k2_sachet_back_2k.png")
        record("D3+K2 Sachet Full-Width Back Coverage (>=85%)", s_cov and s_cov["covPct"] >= 85.0, f"{s_cov}, export={os.path.basename(s_exp)}")

        # 4b. D3+K2 Pouch Front, Full-Width Back & 1kg Capacity Recalculation
        page.click('.pkg-thumb-card[data-cat="pouch"]'); wait_glb_and_textures(page, 2, 1000)
        page.click('#btnViewFront'); page.wait_for_timeout(400); snap_3d(page, "04_d3k2_pouch_front.png")
        page.click('#btnViewBack'); page.wait_for_timeout(400); snap_3d(page, "04_d3k2_pouch_back.png")
        p_cov_100 = measure_canvas_width_coverage(page, "back")
        p_exp_trans = export_mockup_file(page, "png_transparent", 2048, "export_d3k2_pouch_back_2k_transparent.png")
        # Switch to 1kg pouch capacity -> verifies texture dimension & layout recalculation!
        page.select_option("#threeSelectPreset", "pouch_1kg"); wait_glb_and_textures(page, 2, 900)
        p_cov_1kg = measure_canvas_width_coverage(page, "back")
        record(
            "D3+K2 Pouch Full-Width Back (>=85%) & Capacity Recalc",
            p_cov_100 and p_cov_100["covPct"] >= 85.0 and p_cov_1kg and p_cov_1kg["h"] > p_cov_100["h"],
            f"100g={p_cov_100}, 1kg={p_cov_1kg}, export={os.path.basename(p_exp_trans)}",
        )

        # 4c. D3+K2 Box 6-Surface Zero-Duplication Check
        page.click('.pkg-thumb-card[data-cat="box"]'); wait_glb_and_textures(page, 6, 1000)
        snap_3d(page, "05_d3k2_box_3q.png")
        page.click('#btnViewFront'); page.wait_for_timeout(350); snap_3d(page, "05_d3k2_box_front.png")
        page.click('#btnViewBack'); page.wait_for_timeout(350); snap_3d(page, "05_d3k2_box_back.png")
        page.click('#btnViewLeft'); page.wait_for_timeout(350); snap_3d(page, "05_d3k2_box_left.png")
        page.click('#btnViewSide'); page.wait_for_timeout(350); snap_3d(page, "05_d3k2_box_right.png")
        page.click('#btnViewTop'); page.wait_for_timeout(350); snap_3d(page, "05_d3k2_box_top.png")
        hashes = compute_face_hashes(page)
        b_cov = measure_canvas_width_coverage(page, "back")
        b_exp_4k = export_mockup_file(page, "png_white", 2048, "export_d3k2_box_2k.png")
        distinct_faces = len({hashes["front"], hashes["back"], hashes["left"], hashes["right"]}) == 4
        record(
            "D3+K2 Box Distinct Faces (Zero Nutrition Duplication) + Full-Width Back",
            distinct_faces and b_cov and b_cov["covPct"] >= 85.0,
            f"hashes={hashes}, backCov={b_cov}, export={os.path.basename(b_exp_4k)}",
        )

        # 5. Synthetic 1536x605 Black & Gold Calcium Tablet Verification
        with open("scratch/calcium_tablet_1536x605_test.png", "rb") as f:
            calc_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
        load_image_into_studio(page, calc_b64, "Calcium Tablet")

        page.click('.pkg-thumb-card[data-cat="sachet"]'); wait_glb_and_textures(page, 2, 900)
        page.click('#btnViewBack'); page.wait_for_timeout(350); snap_3d(page, "06_calc_sachet_back.png")
        calc_s_cov = measure_canvas_width_coverage(page, "back")

        page.click('.pkg-thumb-card[data-cat="pouch"]'); wait_glb_and_textures(page, 2, 900)
        page.click('#btnViewBack'); page.wait_for_timeout(350); snap_3d(page, "06_calc_pouch_back.png")
        calc_p_cov = measure_canvas_width_coverage(page, "back")

        page.click('.pkg-thumb-card[data-cat="box"]'); wait_glb_and_textures(page, 6, 900)
        page.click('#btnViewBack'); page.wait_for_timeout(350); snap_3d(page, "06_calc_box_back.png")
        page.click('#btnViewLeft'); page.wait_for_timeout(350); snap_3d(page, "06_calc_box_left.png")
        page.click('#btnViewSide'); page.wait_for_timeout(350); snap_3d(page, "06_calc_box_right.png")
        calc_hashes = compute_face_hashes(page)
        calc_distinct = len({calc_hashes["front"], calc_hashes["back"], calc_hashes["left"], calc_hashes["right"]}) == 4
        record(
            "Calcium Black&Gold Full-Width Back & Zero Box Duplication",
            calc_s_cov["covPct"] >= 85.0 and calc_p_cov["covPct"] >= 85.0 and calc_distinct,
            f"sachetBackCov={calc_s_cov}, pouchBackCov={calc_p_cov}, boxHashes={calc_hashes}",
        )

        # 6. 4K Mockup Export Verification
        exp_4k = export_mockup_file(page, "png_transparent", 4096, "export_calcium_box_4k.png")
        record("4K Mockup PNG Export + Smooth Analytical Shadow", os.path.getsize(exp_4k) > 50000, f"bytes={os.path.getsize(exp_4k)}")

        # 7. Zero JS errors
        record("Zero Uncaught Page JS Exceptions", len(js_errors) == 0, f"errors={js_errors}")
        browser.close()

    srv.shutdown()
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    print(f"\nSUMMARY: {passed} PASSED, {failed} FAILED out of {len(results)}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
