"""
update_studio_ui.py
===================
Upgrades templates/index.html with:
1. Universal Design Import Button & Modal (CDR, SVG, PDF, AI, EPS, Images)
2. Professional 3D Packaging Mockup Engine (Categories, Presets, PBR finishes, Studio Lighting, 3D Export)
3. Canva-Style Magic Grab / Grab Object & Natural Language AI Prompt-Based Editing
"""

import re

with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Add GLTFLoader to <head>
gltf_loader_script = '  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>\n'
if "GLTFLoader.js" not in html:
    html = html.replace(
        '<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>',
        '<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>\n' + gltf_loader_script
    )

# 2. Add "Import Design" button to .studio-header-mid
import_btn_html = '''
        <button class="studio-action-pill" id="studioImportDesignBtn" style="background:#f0fdf4; border:1px solid #86efac; color:#15803d; font-weight:700;">
          📁 Import Design
        </button>
        <input type="file" id="universalDesignFileInput" accept=".cdr,.svg,.pdf,.ai,.eps,.png,.jpg,.jpeg,.webp,.json" style="display:none;" />
'''
if 'id="studioImportDesignBtn"' not in html:
    html = html.replace(
        '<button class="studio-action-pill" id="canvaPrintGuidesBtn">',
        import_btn_html + '\n        <button class="studio-action-pill" id="canvaPrintGuidesBtn">'
    )

# 3. Add Canva-Style "Magic Grab" and "Magic Edit" to #drawerAiTools
magic_tools_html = '''
                <!-- Canva-Style Magic Edit Prompt Bar -->
                <div style="background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:8px; padding:10px; display:flex; flex-direction:column; gap:6px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11px; font-weight:800; color:#334155; text-transform:uppercase;">✨ Magic AI Edit (Natural Language)</span>
                    <span style="font-size:10px; background:#f3e8ff; color:#7e22ce; padding:2px 6px; border-radius:10px; font-weight:700;">AI Core</span>
                  </div>
                  <div style="display:flex; gap:6px;">
                    <input id="canvaAiPromptInput" placeholder="e.g. Change Belgian Chocolate to Strawberry, make background clean studio" style="flex:1; background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:6px 8px; font-size:11.5px; font-weight:500;" />
                    <button id="canvaAiPromptBtn" style="background:var(--clr-olive); color:#fff; border:none; border-radius:6px; padding:6px 12px; font-size:11px; font-weight:700; cursor:pointer;">Apply</button>
                  </div>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                  <button id="canvaToolMagicGrabBtn" style="background:#ffffff; border:1.5px solid #c084fc; border-radius:8px; padding:12px; cursor:pointer; text-align:center; position:relative;">
                    <span style="position:absolute; top:4px; right:4px; background:#9333ea; color:#fff; font-size:8.5px; padding:1px 5px; border-radius:8px; font-weight:800;">CANVA PRO</span>
                    <div style="font-size:22px;">🎈</div>
                    <div style="font-weight:700; font-size:11.5px; margin-top:4px; color:#7e22ce;">Magic Grab</div>
                  </button>
'''
if 'id="canvaToolMagicGrabBtn"' not in html:
    html = html.replace(
        '<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">\n                  <button id="canvaToolGrabTextBtn"',
        magic_tools_html + '\n                  <button id="canvaToolGrabTextBtn"'
    )

# 4. Replace #canvaLiveJarPanel with the comprehensive Packaging Visualizer
upgraded_3d_panel_html = '''            <!-- COLUMN 3: RIGHT PROFESSIONAL 3D PACKAGING MOCKUP ENGINE -->
            <aside class="studio-right-col" id="canvaLiveJarPanel" style="width:360px; max-width:380px;">
              <div class="mockup-header-box" style="padding:10px 14px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div class="mockup-title" style="font-size:13.5px; font-weight:800; color:#0f172a;">3D Packaging Studio</div>
                  <span style="font-size:10px; background:#dcfce7; color:#15803d; font-weight:800; padding:2px 8px; border-radius:12px;">LIVE PBR</span>
                </div>
                <div class="mockup-spec" id="threePkgDimsTag" style="font-size:11px; color:#64748b; font-weight:600; margin-top:3px;">1 kg Muscle Tub · W 45.2 × H 14.2 cm</div>
              </div>

              <!-- 3D Canvas Viewport -->
              <div class="three-stage-container" id="pacdoraThreeContainer" style="height:280px; position:relative; background:radial-gradient(circle at 50% 40%, #ffffff 0%, #f1f5f9 100%);">
                <div class="three-360-badge">🔄 360° DRAG &amp; ORBIT</div>
              </div>

              <!-- Mockup Customization Controls (Scrollable) -->
              <div class="mockup-controls-card" style="padding:12px; max-height:calc(100vh - 380px); overflow-y:auto; display:flex; flex-direction:column; gap:10px;">
                
                <!-- 1. Category & Preset Selection -->
                <div style="display:flex; flex-direction:column; gap:4px;">
                  <label style="font-size:11px; font-weight:800; color:#475569; text-transform:uppercase;">Packaging Category</label>
                  <select id="threeSelectCategory" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:5px 8px; font-size:11.5px; font-weight:700; color:#0f172a;">
                    <option value="whey">Whey Protein &amp; Mass Gainer Tubs</option>
                    <option value="creatine">Creatine Monohydrate Jars</option>
                    <option value="preworkout">Pre-Workout Energy Jars</option>
                    <option value="bottles">Supplement Capsule Bottles</option>
                    <option value="pouches">Stand-up Zipper Pouches</option>
                    <option value="sachets">Sachets &amp; Stick Packs</option>
                    <option value="boxes">Carton Packaging Boxes</option>
                  </select>
                </div>

                <div style="display:flex; flex-direction:column; gap:4px;">
                  <label style="font-size:11px; font-weight:800; color:#475569; text-transform:uppercase;">Model &amp; Capacity</label>
                  <select id="threeSelectPreset" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:5px 8px; font-size:11.5px; font-weight:700; color:#0f172a;">
                    <!-- Populated dynamically from manifest -->
                  </select>
                </div>

                <!-- 2. PBR Material Finish & Studio Lighting -->
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                  <div style="display:flex; flex-direction:column; gap:4px;">
                    <label style="font-size:10.5px; font-weight:800; color:#475569;">MATERIAL FINISH</label>
                    <select id="threeSelectMaterialFinish" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:5px; font-size:11px; font-weight:600;">
                      <option value="matte_plastic">Matte Plastic</option>
                      <option value="glossy_plastic">Glossy Plastic</option>
                      <option value="matte_pouch">Matte Laminated</option>
                      <option value="glossy_pouch">Glossy Pouch</option>
                      <option value="metallic_foil">Metallic Foil</option>
                      <option value="kraft_paper">Kraft Paper</option>
                      <option value="transparent_pet">Transparent PET</option>
                      <option value="silver_metallic">Silver Chrome</option>
                      <option value="gold_metallic">Gold Metallic</option>
                    </select>
                  </div>
                  <div style="display:flex; flex-direction:column; gap:4px;">
                    <label style="font-size:10.5px; font-weight:800; color:#475569;">STUDIO LIGHTING</label>
                    <select id="threeSelectLighting" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:5px; font-size:11px; font-weight:600;">
                      <option value="white_studio">White Studio</option>
                      <option value="soft_studio">Soft Studio</option>
                      <option value="premium_studio">Premium Studio</option>
                      <option value="dark_studio">Dark Cyber</option>
                      <option value="natural_light">Natural Daylight</option>
                    </select>
                  </div>
                </div>

                <!-- 3. Camera Angle Presets -->
                <div style="display:flex; flex-direction:column; gap:4px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <label style="font-size:10.5px; font-weight:800; color:#475569;">VIEW ANGLE</label>
                    <span id="threeCurrentAngleLabel" style="font-size:10px; color:#64748b; font-weight:700;">Front (0°)</span>
                  </div>
                  <div class="view-angles-row" style="display:grid; grid-template-columns:repeat(5, 1fr); gap:4px;">
                    <button class="view-angle-btn active" id="btnViewFront" title="Front View" style="padding:5px 2px; font-size:10px;">Front</button>
                    <button class="view-angle-btn" id="btnViewBack" title="Back View" style="padding:5px 2px; font-size:10px;">Back</button>
                    <button class="view-angle-btn" id="btnViewLeft" title="Left View" style="padding:5px 2px; font-size:10px;">Left</button>
                    <button class="view-angle-btn" id="btnViewSide" title="Right View" style="padding:5px 2px; font-size:10px;">Right</button>
                    <button class="view-angle-btn" id="btnViewTop" title="Top View" style="padding:5px 2px; font-size:10px;">Top</button>
                  </div>
                </div>

                <!-- 4. Interactive Turntable & Camera Reset -->
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
                  <button id="canvaAutoSpinBtn" style="flex:1; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:6px 10px; font-size:11px; font-weight:700; color:#334155; cursor:pointer; text-align:center;">
                    ▶️ Auto 360° Spin
                  </button>
                  <button id="canvaReset3dCameraBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:6px 10px; color:#475569; font-size:11px; font-weight:700; cursor:pointer;">
                    Reset
                  </button>
                </div>

                <!-- 5. Packaging Color Swatches -->
                <div class="pkg-color-row">
                  <div class="pkg-color-label-row">
                    <span style="font-size:11px; font-weight:800; color:#475569;">Container Color</span>
                    <span id="canvaCurrentPkgColorLabel" style="font-weight:700; color:#0f172a; font-size:11px;">Black Matte</span>
                  </div>
                  <div class="pkg-color-swatches" id="canvaPkgColorSwatches">
                    <button class="color-swatch-btn active" data-color="#18181b" data-name="Black Matte" style="background:#18181b;" title="Black"></button>
                    <button class="color-swatch-btn" data-color="#ffffff" data-name="White Gloss" style="background:#ffffff; border:1px solid #cbd5e1;" title="White"></button>
                    <button class="color-swatch-btn" data-color="#94a3b8" data-name="Silver Grey" style="background:#94a3b8;" title="Grey"></button>
                    <button class="color-swatch-btn" data-color="#d4af37" data-name="Gold Metallic" style="background:#d4af37;" title="Gold"></button>
                    <button class="color-swatch-btn" data-color="#1e3a8a" data-name="Navy Blue" style="background:#1e3a8a;" title="Navy"></button>
                    <button class="color-swatch-btn" data-color="#581c87" data-name="Burgundy Purple" style="background:#581c87;" title="Burgundy"></button>
                    <input type="color" id="customPkgColorPicker" value="#18181b" title="Custom Color" style="width:24px; height:24px; border:none; border-radius:50%; cursor:pointer; padding:0;" />
                  </div>
                </div>

                <!-- 6. High-Resolution 3D Mockup Export Button -->
                <button id="threeExportMockupBtn" style="background:linear-gradient(135deg, #708238, #556b2f); color:#fff; border:none; border-radius:8px; padding:10px; font-size:12px; font-weight:800; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px; box-shadow:0 2px 6px rgba(112,130,56,0.3);">
                  📸 <span>Export 3D Mockup (PNG)</span>
                </button>

              </div>
            </aside>'''

# Replace old aside with upgraded 3D panel
html = re.sub(
    r'<aside class="studio-right-col" id="canvaLiveJarPanel">.*?</aside>',
    upgraded_3d_panel_html,
    html,
    flags=re.DOTALL
)

# 5. Add Modals for Universal Design Import and 3D Export before </body>
modals_html = '''
  <!-- MODAL 1: UNIVERSAL DESIGN IMPORT PREVIEW MODAL -->
  <div id="designImportPreviewModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15,23,42,0.65); z-index:9999; align-items:center; justify-content:center;">
    <div style="background:#ffffff; border-radius:12px; width:90%; max-width:540px; padding:24px; box-shadow:0 20px 40px rgba(0,0,0,0.25); display:flex; flex-direction:column; gap:16px;">
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding-bottom:12px;">
        <div>
          <h2 style="font-size:16px; font-weight:800; color:#0f172a; display:flex; align-items:center; gap:8px;">
            <span>📁</span> <span id="importModalTitle">Import CorelDRAW / Design Artwork</span>
          </h2>
          <p id="importModalSubtitle" style="font-size:11.5px; color:#64748b; margin-top:2px;">Original vector artwork inspected and ready for conversion</p>
        </div>
        <button id="closeImportModalBtn" style="background:transparent; border:none; font-size:18px; color:#94a3b8; cursor:pointer;">✕</button>
      </div>

      <div style="display:flex; gap:16px; align-items:center;">
        <div style="width:160px; height:160px; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; display:flex; align-items:center; justify-content:center; overflow:hidden;">
          <img id="importModalPreviewImg" src="" style="max-width:100%; max-height:100%; object-fit:contain;" />
        </div>
        <div style="flex:1; display:flex; flex-direction:column; gap:8px; font-size:12px;">
          <div><strong style="color:#475569;">Physical Dimensions:</strong> <span id="importModalDims" style="font-weight:700; color:#0f172a;">120 × 140 mm</span></div>
          <div><strong style="color:#475569;">Total Elements:</strong> <span id="importModalTotalObjs" style="font-weight:700; color:#0f172a;">--</span></div>
          <div><strong style="color:#475569;">Editable Text Objects:</strong> <span id="importModalTextObjs" style="font-weight:700; color:#15803d;">--</span></div>
          <div><strong style="color:#475569;">Vector Shapes:</strong> <span id="importModalVectorObjs" style="font-weight:700; color:#0f172a;">--</span></div>
          <div id="importModalWarning" style="color:#b45309; font-size:11px; background:#fef3c7; padding:6px; border-radius:4px; display:none;"></div>
        </div>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:8px; border-top:1px solid #e2e8f0; padding-top:14px;">
        <button id="cancelImportModalBtn" style="background:#f1f5f9; border:1px solid #cbd5e1; color:#475569; padding:8px 14px; border-radius:6px; font-size:12px; font-weight:700; cursor:pointer;">Cancel</button>
        <button id="applyImportImageBtn" style="background:#ffffff; border:1.5px solid #cbd5e1; color:#334155; padding:8px 14px; border-radius:6px; font-size:12px; font-weight:700; cursor:pointer;">Import as Image</button>
        <button id="applyImportEditableBtn" style="background:var(--clr-olive); border:none; color:#ffffff; padding:8px 16px; border-radius:6px; font-size:12px; font-weight:800; cursor:pointer;">✓ Import Editable Design</button>
      </div>
    </div>
  </div>

  <!-- MODAL 2: 3D MOCKUP EXPORT MODAL -->
  <div id="mockupExportModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15,23,42,0.65); z-index:9999; align-items:center; justify-content:center;">
    <div style="background:#ffffff; border-radius:12px; width:90%; max-width:440px; padding:22px; box-shadow:0 20px 40px rgba(0,0,0,0.25); display:flex; flex-direction:column; gap:14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding-bottom:10px;">
        <h3 style="font-size:15px; font-weight:800; color:#0f172a;">📸 Export 3D Packaging Mockup</h3>
        <button id="closeMockupExportModalBtn" style="background:transparent; border:none; font-size:16px; color:#94a3b8; cursor:pointer;">✕</button>
      </div>

      <div style="display:flex; flex-direction:column; gap:8px; font-size:12px;">
        <label style="font-weight:700; color:#475569;">Export Format</label>
        <select id="mockupExportFmt" style="background:#fff; border:1px solid #cbd5e1; border-radius:6px; padding:6px; font-weight:600;">
          <option value="png_transparent">Transparent Background (PNG)</option>
          <option value="png_white">Studio White Floor (PNG)</option>
          <option value="jpg">Commercial Presentation (JPG)</option>
        </select>

        <label style="font-weight:700; color:#475569; margin-top:4px;">Render Quality / Resolution</label>
        <select id="mockupExportRes" style="background:#fff; border:1px solid #cbd5e1; border-radius:6px; padding:6px; font-weight:600;">
          <option value="1920">Full HD (1920 × 1080)</option>
          <option value="2048" selected>2K Ultra Crisp (2048 × 2048)</option>
          <option value="3840">4K Master Print (3840 × 3840)</option>
        </select>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:8px; border-top:1px solid #e2e8f0; padding-top:12px;">
        <button id="cancelMockupExportBtn" style="background:#f1f5f9; border:1px solid #cbd5e1; color:#475569; padding:8px 12px; border-radius:6px; font-size:12px; font-weight:700; cursor:pointer;">Cancel</button>
        <button id="confirmMockupExportBtn" style="background:var(--clr-olive); border:none; color:#ffffff; padding:8px 16px; border-radius:6px; font-size:12px; font-weight:800; cursor:pointer;">Render &amp; Download</button>
      </div>
    </div>
  </div>
'''

if 'id="designImportPreviewModal"' not in html:
    html = html.replace('</body>', modals_html + '\n</body>')

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✓ UI HTML successfully updated with Universal Import, 3D Mockup Studio, and Magic Tools!")
