"""
render_3d_thumbnails.py
=======================
Renders realistic studio PNG thumbnails directly from our binary .glb packaging assets.
"""
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.abspath("static/models/packaging/thumbnails")
os.makedirs(OUT_DIR, exist_ok=True)

TARGETS = [
    ("jar", "static/models/packaging/whey/whey_1kg.glb", "#141618", "#101214", 0.42, 0.08, 0.0),
    ("pouch", "static/models/packaging/pouches/standup_500g.glb", "#eef1f5", "#dce2e8", 0.46, 0.08, 0.24),
    ("sachet", "static/models/packaging/sachets/sachet_10g.glb", "#d9b664", "#c49b3e", 0.24, 0.86, 0.24),
    ("bottle", "static/models/packaging/bottles/capsule_60.glb", "#ebedf0", "#dde1e6", 0.40, 0.04, 0.0),
    ("box", "static/models/packaging/boxes/carton_box.glb", "#c69663", "#b88754", 0.78, 0.0, -0.52),
]

HTML_RENDERER = """<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
</head>
<body style="margin:0;background:transparent;">
<canvas id="c" width="240" height="240"></canvas>
<script>
window.renderGlbThumbnail = function(glbUrl, bodyHex, lidHex, roughness, metalness, rotY) {
  return new Promise((resolve, reject) => {
    const canvas = document.getElementById('c');
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setSize(240, 240);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.98;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.05, 50);

    const hemi = new THREE.HemisphereLight(0xffffff, 0x2a2f36, 0.55);
    const key = new THREE.DirectionalLight(0xffffff, 1.35);
    key.position.set(2.4, 3.8, 3.2);
    const fill = new THREE.DirectionalLight(0xdce6f2, 0.42);
    fill.position.set(-3.2, 1.0, 1.8);
    const rim = new THREE.DirectionalLight(0xffffff, 0.75);
    rim.position.set(-0.5, 2.5, -3.5);
    scene.add(hemi, key, fill, rim);

    const loader = new THREE.GLTFLoader();
    loader.load(glbUrl, (gltf) => {
      const root = gltf.scene;
      root.traverse((obj) => {
        if (obj.isMesh) {
          const n = (obj.name || '').toLowerCase();
          const c = new THREE.Color((n.includes('lid') || n.includes('cap') || n.includes('seal')) ? lidHex : bodyHex).convertSRGBToLinear();
          const r = (n.includes('lid') || n.includes('cap') || n.includes('seal')) ? Math.max(0.28, roughness - 0.08) : roughness;
          const m = (n.includes('lid') || n.includes('cap') || n.includes('seal')) ? metalness + 0.05 : metalness;
          obj.material = new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });
        }
      });

      root.rotation.y = rotY || 0;
      if (rotY !== 0) root.rotation.x = 0.08;

      scene.add(root);
      const box = new THREE.Box3().setFromObject(root);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const dist = (maxDim / 2) / Math.tan((32 * Math.PI / 180) / 2) * 1.45;
      camera.position.set(center.x, center.y + maxDim * 0.1, center.z + dist);
      camera.lookAt(center);
      renderer.render(scene, camera);
      resolve(canvas.toDataURL('image/png'));
    }, undefined, (err) => reject(String(err)));
  });
};
</script>
</body>
</html>
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    os.makedirs("scratch", exist_ok=True)
    with open("scratch/_thumb_renderer.html", "w", encoding="utf-8") as f:
        f.write(HTML_RENDERER)

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    import base64
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"http://127.0.0.1:{port}/scratch/_thumb_renderer.html", wait_until="load")
        page.wait_for_function("() => typeof THREE !== 'undefined' && typeof THREE.GLTFLoader !== 'undefined'")
        for cid, glb_rel, b_col, l_col, rough, met, rot_y in TARGETS:
            data_url = page.evaluate(
                "([u, b, l, r, m, ry]) => window.renderGlbThumbnail(u, b, l, r, m, ry)",
                [f"/{glb_rel}", b_col, l_col, rough, met, rot_y],
            )
            png_bytes = base64.b64decode(data_url.split(",", 1)[1])
            out_path = os.path.join(OUT_DIR, f"{cid}.png")
            with open(out_path, "wb") as fout:
                fout.write(png_bytes)
            print(f"OK 3D thumbnail: {cid}.png ({len(png_bytes)} bytes)")
        browser.close()
    server.shutdown()


if __name__ == "__main__":
    main()
