"""
GOMZI BOB - Comprehensive Protein Jar 3D Upgrade Browser Verification Suite.

Verifies:
1. GLB mesh anatomy (BottomRing, JarBody, JarShoulder, JarNeck, CapGripRibs, CapCrown, LabelSurface).
2. Default 1kg GOMZI Whey label + uploaded tests/fixtures/label_essential_whey.jpg label.
3. Color combinations: Black Body + Red Cap, Black Body + Black Cap, White Body + White Cap.
4. PBR Material finishes: Matte Plastic vs Glossy Plastic (roughness/clearcoat/HDPE normalMap checks).
5. Independent capacity proportions across 250g, 500g, 1kg, 2kg, 2.5kg, 3kg, 5kg + framing check (no cropped cap/base).
6. All viewing angles (Front, Back, Left, Right, Top) + 360 spin + Live Sync edit reflection.
7. High-res mockup export (PNG 2048px + 4K 4096px) + zero runtime console/page errors.
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

SCREENS_DIR = os.path.abspath("tests/reports/jar_upgrade")
os.makedirs(SCREENS_DIR, exist_ok=True)
RESULTS_JSON = os.path.abspath("tests/reports/jar_upgrade_results.json")


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


def wait_jar_ready(page, wait_ms=850):
    page.wait_for_function(
        "() => typeof threeLabelMeshes !== 'undefined' && threeLabelMeshes.length >= 1 && threeBodyMeshes.length >= 4 && threeLidMeshes.length >= 2 && threeLabelMeshes.every(m => m.material && m.material.map !== null)",
        timeout=15000,
    )
    page.wait_for_timeout(wait_ms)


def snap_3d(page, filename):
    page.locator("#canvaLiveJarPanel").screenshot(path=os.path.join(SCREENS_DIR, filename))


def load_fixture_label(page, filepath, title):
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    data_url = f"data:image/jpeg;base64,{b64}"
    ok = page.evaluate(
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
        [data_url, title],
    )
    page.wait_for_timeout(900)
    return ok


def set_colors(page, body_hex, lid_hex):
    page.evaluate(
        """([bHex, lHex]) => {
            const bIn = document.getElementById('threeBodyColorPicker');
            const lIn = document.getElementById('threeLidColorPicker');
            bIn.value = bHex;
            bIn.dispatchEvent(new Event('input', { bubbles: true }));
            lIn.value = lHex;
            lIn.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        [body_hex, lid_hex],
    )
    page.wait_for_timeout(550)


def inspect_scene_state(page):
    return page.evaluate("""() => {
        const meshes = [];
        threeJarGroup.traverse(n => {
            if (n.isMesh && n.name) meshes.push(n.name);
        });
        threeJarGroup.updateMatrixWorld(true);
        const box = new THREE.Box3().setFromObject(threeJarGroup);
        const size = box.getSize(new THREE.Vector3());
        const bMat = threeBodyMeshes[0]?.material;
        const lMat = threeLidMeshes[0]?.material;
        const lblMat = threeLabelMeshes[0]?.material;

        // Project 8 bbox corners into NDC [-1..1] to prove zero frustum cropping
        const pts = [];
        for (const x of [box.min.x, box.max.x]) {
            for (const y of [box.min.y, box.max.y]) {
                for (const z of [box.min.z, box.max.z]) {
                    const v = new THREE.Vector3(x, y, z).project(threeCamera);
                    pts.push(v);
                }
            }
        }
        const maxAbsNdc = Math.max(...pts.map(p => Math.max(Math.abs(p.x), Math.abs(p.y))));
        return {
            meshes,
            bodyCount: threeBodyMeshes.length,
            lidCount: threeLidMeshes.length,
            labelCount: threeLabelMeshes.length,
            bboxW: Math.round(size.x * 1000) / 1000,
            bboxH: Math.round(size.y * 1000) / 1000,
            bboxD: Math.round(size.z * 1000) / 1000,
            aspectHOverW: Math.round((size.y / Math.max(0.001, size.x)) * 1000) / 1000,
            maxAbsNdc: Math.round(maxAbsNdc * 1000) / 1000,
            bodyRoughness: bMat ? Math.round(bMat.roughness * 1000) / 1000 : null,
            bodyClearcoat: bMat ? Math.round((bMat.clearcoat || 0) * 1000) / 1000 : null,
            bodyHasNMap: Boolean(bMat && bMat.normalMap),
            lidRoughness: lMat ? Math.round(lMat.roughness * 1000) / 1000 : null,
            lidClearcoat: lMat ? Math.round((lMat.clearcoat || 0) * 1000) / 1000 : null,
            lblHasTex: Boolean(lblMat && lblMat.map),
            lblClearcoat: lblMat ? Math.round((lblMat.clearcoat || 0) * 1000) / 1000 : null,
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

        page.goto(f"{base_url}/", wait_until="networkidle")
        wait_jar_ready(page)

        # 1. Default 1kg GOMZI Whey Jar Anatomy + Mesh Verification
        st_default = inspect_scene_state(page)
        expected_parts = {"BottomRing", "JarBody", "JarShoulder", "JarNeck", "CapGripRibs", "CapCrown", "LabelSurface"}
        has_all_parts = expected_parts.issubset(set(st_default["meshes"]))
        record(
            "Jar GLB Mesh Anatomy",
            has_all_parts and st_default["bodyCount"] == 4 and st_default["lidCount"] == 2 and st_default["labelCount"] == 1,
            f"meshes={st_default['meshes']}, counts=(body={st_default['bodyCount']}, lid={st_default['lidCount']}, lbl={st_default['labelCount']})",
        )
        snap_3d(page, "01_jar_1kg_default_black_black_matte.png")

        # 2. Load Essential Whey JPG fixture cleanly as Full Label
        loaded = load_fixture_label(page, "tests/fixtures/label_essential_whey.jpg", "EssentialWhey")
        record("Load Essential Whey JPG Full Label", bool(loaded), "Loaded tests/fixtures/label_essential_whey.jpg onto 3D Jar")
        snap_3d(page, "02_jar_1kg_essential_whey_black_black.png")

        # 3. Color Combo: Black Body + Red Cap (supplement industry iconic style)
        set_colors(page, "#16181A", "#B91C1C")
        snap_3d(page, "03_jar_1kg_black_body_red_cap.png")
        lid_hex_applied = page.evaluate("() => threeLidColorHex")
        record("Black Body + Red Cap", lid_hex_applied.lower() == "#b91c1c", f"body={page.evaluate('() => threeBodyColorHex')}, lid={lid_hex_applied}")

        # 4. Color Combo: White Body + White Cap (Clean White HDPE Look)
        set_colors(page, "#F2F4F7", "#F2F4F7")
        snap_3d(page, "04_jar_1kg_white_body_white_cap.png")
        record("White Body + White Cap", page.evaluate("() => threeBodyColorHex").lower() == "#f2f4f7", "White HDPE #F2F4F7 applied")

        # 5. Material Finish: Matte Plastic vs Glossy Plastic
        set_colors(page, "#16181A", "#121416")
        page.select_option("#threeSelectMaterialFinish", "matte")
        page.wait_for_timeout(450)
        st_matte = inspect_scene_state(page)
        snap_3d(page, "05_jar_1kg_matte_plastic.png")

        page.select_option("#threeSelectMaterialFinish", "glossy")
        page.wait_for_timeout(450)
        st_gloss = inspect_scene_state(page)
        snap_3d(page, "06_jar_1kg_glossy_plastic.png")

        pbr_ok = (
            st_matte["bodyHasNMap"] is True
            and st_matte["bodyRoughness"] > st_gloss["bodyRoughness"]
            and st_gloss["bodyClearcoat"] > st_matte["bodyClearcoat"]
            and st_gloss["lblClearcoat"] > st_matte["lblClearcoat"]
        )
        record(
            "Matte vs Glossy HDPE & Label PBR",
            pbr_ok,
            f"matte(rough={st_matte['bodyRoughness']}, cc={st_matte['bodyClearcoat']}, nmap={st_matte['bodyHasNMap']}) vs glossy(rough={st_gloss['bodyRoughness']}, cc={st_gloss['bodyClearcoat']}, lblCC={st_gloss['lblClearcoat']})",
        )

        # Switch back to Matte Black Body + Red Cap for multi-angle & capacity inspection
        page.select_option("#threeSelectMaterialFinish", "matte")
        set_colors(page, "#16181A", "#B91C1C")

        # 6. View Angles (Front, Back, Left, Right, Top, 360 Spin)
        angles = [
            ("btnViewFront", "07_angle_front.png"),
            ("btnViewBack", "08_angle_back.png"),
            ("btnViewLeft", "09_angle_left.png"),
            ("btnViewSide", "10_angle_right.png"),
            ("btnViewTop", "11_angle_top.png"),
        ]
        max_ndc_angles = []
        for btn_id, fname in angles:
            page.click(f"#{btn_id}")
            page.wait_for_timeout(450)
            st_a = inspect_scene_state(page)
            max_ndc_angles.append(st_a["maxAbsNdc"])
            snap_3d(page, fname)
        page.click("#canvaAutoSpinBtn")
        page.wait_for_timeout(550)
        rot_y_spin = page.evaluate("() => Math.round(threeJarGroup.rotation.y * 1000) / 1000")
        page.click("#canvaAutoSpinBtn")  # toggle off
        page.click("#btnViewFront")
        page.wait_for_timeout(350)
        record("All Viewing Angles & 360 Spin", rot_y_spin != 0.0 and max(max_ndc_angles) < 1.15, f"maxAbsNdc={max(max_ndc_angles)}, spinRotY={rot_y_spin}")

        # 7. Capacity-Specific Geometry & Framing (250g, 500g, 1kg, 2kg, 2.5kg, 3kg, 5kg)
        capacities = ["jar_250g", "jar_500g", "jar_1kg", "jar_2kg", "jar_2_5kg", "jar_3kg", "jar_5kg"]
        cap_stats = {}
        for cid in capacities:
            page.select_option("#threeSelectPreset", cid)
            wait_jar_ready(page, 650)
            st_c = inspect_scene_state(page)
            cap_stats[cid] = st_c
            if cid in ("jar_250g", "jar_500g", "jar_2kg", "jar_5kg"):
                snap_3d(page, f"12_cap_{cid}.png")
        ratio_250 = cap_stats["jar_250g"]["aspectHOverW"]
        ratio_500 = cap_stats["jar_500g"]["aspectHOverW"]
        ratio_5kg = cap_stats["jar_5kg"]["aspectHOverW"]
        all_framed = all(cap_stats[c]["maxAbsNdc"] < 1.05 for c in capacities)
        record(
            "Capacity-Specific Proportions & Framing",
            all_framed and ratio_500 > ratio_250 and cap_stats["jar_5kg"]["bboxW"] > cap_stats["jar_1kg"]["bboxW"] > cap_stats["jar_250g"]["bboxW"],
            f"250g(H/W={ratio_250}, W={cap_stats['jar_250g']['bboxW']}), 500g(H/W={ratio_500}), 1kg(W={cap_stats['jar_1kg']['bboxW']}), 5kg(W={cap_stats['jar_5kg']['bboxW']}, H/W={ratio_5kg}), allFramed={all_framed}",
        )

        # Reset to 1kg for Live Sync + Export tests
        page.select_option("#threeSelectPreset", "jar_1kg")
        wait_jar_ready(page, 650)
        set_colors(page, "#16181A", "#121416")

        # 8. Live Sync Test (modify fabric object -> verify fresh WebGL Texture UUID updates automatically)
        before_sync_uuid = page.evaluate("() => threeSurfaceTextures.cylinder ? threeSurfaceTextures.cylinder.uuid : ''")
        page.evaluate("""() => {
            const objs = canvaCanvas.getObjects();
            if (objs[0]) {
                objs[0].set({ angle: 1.5 });
                canvaCanvas.renderAll();
                canvaCanvas.fire('object:modified', { target: objs[0] });
            }
        }""")
        page.wait_for_timeout(900)
        after_sync_uuid = page.evaluate("() => threeSurfaceTextures.cylinder ? threeSurfaceTextures.cylinder.uuid : ''")
        record("Live Sync Canvas->3D Update", bool(before_sync_uuid and after_sync_uuid and after_sync_uuid != before_sync_uuid), f"textureUUID {before_sync_uuid[:8]} -> {after_sync_uuid[:8]}")

        # Reload crisp unmodified Essential Whey label before final mockup exports
        load_fixture_label(page, "tests/fixtures/label_essential_whey.jpg", "EssentialWheyClean")
        set_colors(page, "#16181A", "#B91C1C")
        page.select_option("#threeSelectMaterialFinish", "matte")
        page.wait_for_timeout(500)

        # 9. High-Resolution Exports (PNG 2048px + 4K 4096px)
        p_2k = export_mockup_file(page, "png_white", 2048, "13_export_jar_1kg_2048.png")
        p_4k = export_mockup_file(page, "png_white", 4096, "14_export_jar_1kg_4096.png")
        sz_2k = os.path.getsize(p_2k)
        sz_4k = os.path.getsize(p_4k)
        record("PNG 2048px & 4K Export", sz_2k > 50000 and sz_4k > sz_2k, f"2K={sz_2k} bytes, 4K={sz_4k} bytes")

        record("Zero Runtime JS Page Errors", len(js_errors) == 0, f"errors={js_errors}")
        browser.close()

    srv.shutdown()
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump({"results": results, "js_errors": js_errors}, f, indent=2)

    passed_count = sum(1 for r in results if r["status"] == "PASS")
    print(f"\nSUMMARY: {passed_count}/{len(results)} PASSED, {len(results)-passed_count} FAILED")
    if passed_count != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
