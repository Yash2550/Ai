"""
apply_full_label_fix.py
=======================
Applies the full label upload fix, asset gallery action choices,
dynamic 3D camera bounding box framing, and container color synchronization.
"""

import re

with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update Drawer 5 (Uploads) HTML
new_uploads_drawer = '''              <!-- DRAWER 5: UPLOADS & FULL LABEL IMPORT -->
              <div class="drawer-view" id="drawerUploads">
                <div class="drawer-header">
                  <span class="drawer-title">Import &amp; Media</span>
                </div>

                <div style="display:flex; flex-direction:column; gap:8px;">
                  <!-- Option 1: Upload Full Label (Primary) -->
                  <button id="btnUploadFullLabel" style="background:var(--clr-olive); color:#fff; border:none; border-radius:8px; padding:12px; font-size:12px; font-weight:800; cursor:pointer; text-align:left; display:flex; align-items:center; gap:10px; box-shadow:0 2px 6px rgba(112,130,56,0.3);">
                    <span style="font-size:22px;">🖼️</span>
                    <div>
                      <div>Upload Full Label</div>
                      <div style="font-size:10px; opacity:0.88; font-weight:500;">Replaces current artwork &amp; clears old template</div>
                    </div>
                  </button>
                  <input type="file" id="inputUploadFullLabel" accept="image/*" style="display:none;" />

                  <!-- Option 2: Import Vector CDR / SVG / PDF -->
                  <button id="btnDrawerImportVector" style="background:#ffffff; color:#0f172a; border:1.5px solid #cbd5e1; border-radius:8px; padding:10px; font-size:12px; font-weight:700; cursor:pointer; text-align:left; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:20px;">📁</span>
                    <div>
                      <div>Import CDR / SVG / PDF</div>
                      <div style="font-size:10px; color:#64748b; font-weight:500;">Extracts editable text &amp; vector layers</div>
                    </div>
                  </button>

                  <!-- Option 3: Add Image / Logo / Sticker (Secondary) -->
                  <button id="btnAddSticker" style="background:#f8fafc; color:#334155; border:1px solid #cbd5e1; border-radius:8px; padding:10px; font-size:12px; font-weight:700; cursor:pointer; text-align:left; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:20px;">➕</span>
                    <div>
                      <div>Add Sticker / Logo / Photo</div>
                      <div style="font-size:10px; color:#64748b; font-weight:500;">Inserts an additional layer onto design</div>
                    </div>
                  </button>
                  <input type="file" id="canvaDrawerUploadInput" accept="image/*" style="display:none;" />
                </div>

                <div style="font-size:11px; font-weight:700; color:#64748b; margin-top:10px; text-transform:uppercase;">
                  Uploaded Assets Gallery
                </div>
                <div id="uploadsGalleryGrid" style="display:flex; flex-direction:column; gap:8px; max-height:calc(100vh - 360px); overflow-y:auto;">
                  <!-- Populated with Open as Full Label / Add Sticker options -->
                </div>
              </div>'''

html = re.sub(
    r'<!-- DRAWER 5: UPLOADS -->.*?<!-- DRAWER 6: LAYERS -->',
    new_uploads_drawer + '\n\n              <!-- DRAWER 6: LAYERS -->',
    html,
    flags=re.DOTALL
)

# 2. Add "🖼️ Full Label" button in top toolbar if not present
if 'id="headerUploadFullLabelBtn"' not in html:
    html = html.replace(
        '<button class="studio-action-pill" id="studioImportDesignBtn"',
        '<button class="studio-action-pill" id="headerUploadFullLabelBtn" style="background:#f0fdf4; border:1px solid #86efac; color:#15803d; font-weight:700;" title="Upload Full Label to replace artwork">🖼️ Full Label</button>\n              <button class="studio-action-pill" id="studioImportDesignBtn"'
    )

# 3. Add full label upload handlers and camera framing functions into JavaScript
new_js_code = '''
    /* ======================================================
       CRITICAL FIX: FULL LABEL UPLOAD VS STICKER SEPARATION
    ====================================================== */
    function initFullLabelUploadEngine() {
      const fullLabelBtn = document.getElementById('btnUploadFullLabel');
      const headerFullLabelBtn = document.getElementById('headerUploadFullLabelBtn');
      const fullLabelInput = document.getElementById('inputUploadFullLabel');

      if (fullLabelBtn && fullLabelInput) {
        fullLabelBtn.onclick = () => fullLabelInput.click();
      }
      if (headerFullLabelBtn && fullLabelInput) {
        headerFullLabelBtn.onclick = () => fullLabelInput.click();
      }

      if (fullLabelInput) {
        fullLabelInput.onchange = (e) => {
          if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            const reader = new FileReader();
            reader.onload = (f) => {
              openImageAsFullLabel(f.target.result, file.name);
            };
            reader.readAsDataURL(file);
          }
        };
      }

      // Option 2: Drawer Vector Import
      document.getElementById('btnDrawerImportVector')?.addEventListener('click', () => {
        document.getElementById('studioImportDesignBtn')?.click();
      });

      // Option 3: Add Sticker / Graphic
      const addStickerBtn = document.getElementById('btnAddSticker');
      const stickerInput = document.getElementById('canvaDrawerUploadInput');
      if (addStickerBtn && stickerInput) {
        addStickerBtn.onclick = () => stickerInput.click();
      }
      if (stickerInput) {
        stickerInput.onchange = (e) => {
          if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            const reader = new FileReader();
            reader.onload = (f) => {
              addStickerToCanvas(f.target.result, file.name);
            };
            reader.readAsDataURL(file);
          }
        };
      }
    }

    /* Opens an image as a complete full artwork, removing previous template */
    function openImageAsFullLabel(dataUrl, fileName = 'Product Label') {
      if (!canvaCanvas) return;

      // 1. Confirm replacement if canvas has existing objects
      if (canvaCanvas.getObjects().length > 0) {
        if (!confirm(`Replace current artwork with "${fileName}"? This will clear the previous template.`)) {
          return;
        }
      }

      showToast(`Loading "${fileName}" as full label design...`, "🖼️", 3000);

      const img = new Image();
      img.onload = () => {
        const naturalW = img.naturalWidth || img.width || 1536;
        const naturalH = img.naturalHeight || img.height || 512;
        const aspect = naturalW / naturalH;

        // 2. Completely clear previous template objects
        isHistoryLocked = true;
        canvaCanvas.clear();
        canvaCanvas.backgroundColor = '#ffffff';

        // 3. Set logical canvas dimensions preserving aspect ratio
        const targetW = 1536;
        const targetH = Math.round(targetW / aspect);
        canvaCanvas.setWidth(targetW);
        canvaCanvas.setHeight(targetH);

        // 4. Add uploaded full label as complete base artwork
        fabric.Image.fromURL(dataUrl, (fabImg) => {
          fabImg.set({
            left: 0,
            top: 0,
            scaleX: targetW / naturalW,
            scaleY: targetH / naturalH,
            selectable: true,
            evented: true,
            assetType: 'full_label_artwork',
            name: `Full Label: ${fileName}`
          });
          canvaCanvas.add(fabImg);
          canvaCanvas.sendToBack(fabImg);
          canvaCanvas.setActiveObject(fabImg);

          // 5. Fit to workspace viewport
          fitLabelToWorkspace();

          // 6. Reset brand logo object
          brandLogoObject = null;

          // 7. Update Project Title & UI Headers
          const cleanTitle = fileName.replace(/\\.[^/.]+$/, "").replace(/_/g, " ");
          const titleInput = document.getElementById('canvaDocTitleInput');
          if (titleInput) titleInput.value = cleanTitle;

          const prodPill = document.getElementById('studioProductPillName');
          if (prodPill) prodPill.textContent = cleanTitle;

          const specTag = document.getElementById('studioSpecTag');
          if (specTag) specTag.textContent = `${naturalW} × ${naturalH} px (Aspect ${aspect.toFixed(2)}:1)`;

          // 8. Clear stale Whey Protein facts
          const factsTitle = document.getElementById('factsProductTitle');
          if (factsTitle) factsTitle.value = cleanTitle;
          const factsFlavour = document.getElementById('factsFlavour');
          if (factsFlavour) factsFlavour.value = "";
          const factsNetWeight = document.getElementById('factsNetWeight');
          if (factsNetWeight) factsNetWeight.value = "";

          isHistoryLocked = false;
          saveCanvasState();
          refreshLayersList();

          // 9. Immediately update 3D texture!
          updateThreeLabelTextureFromCanvas();

          // 10. Auto-switch packaging category if appropriate (e.g. Capsule Bottle for aspect < 2.5)
          if (aspect < 2.5 && packagingManifest) {
            const catSelect = document.getElementById('threeSelectCategory');
            if (catSelect) {
              catSelect.value = 'bottles';
              populatePresetsForCategory('bottles');
            }
          }

          // 11. Add to gallery
          addAssetToGallery(dataUrl, fileName);

          showToast(`"${cleanTitle}" loaded as active full design!`, "🎉");
        });
      };
      img.src = dataUrl;
    }

    /* Inserts an additional sticker / image layer onto the current canvas */
    function addStickerToCanvas(dataUrl, fileName = 'Sticker') {
      if (!canvaCanvas) return;
      fabric.Image.fromURL(dataUrl, (img) => {
        img.scaleToWidth(220);
        img.set({
          left: canvaCanvas.width / 2 - 110,
          top: canvaCanvas.height / 2 - 110,
          assetType: 'sticker',
          name: fileName
        });
        canvaCanvas.add(img);
        canvaCanvas.setActiveObject(img);
        canvaCanvas.renderAll();
        refreshLayersList();
        updateThreeLabelTextureFromCanvas();
        addAssetToGallery(dataUrl, fileName);
        showToast("Added layer to canvas!", "➕");
      });
    }

    /* Uploaded Assets Gallery with Action Choices */
    function addAssetToGallery(dataUrl, name) {
      const grid = document.getElementById('uploadsGalleryGrid');
      if (!grid) return;

      const card = document.createElement('div');
      card.style = "border:1px solid #cbd5e1; border-radius:8px; padding:8px; background:#fff; display:flex; flex-direction:column; gap:6px;";
      card.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px;">
          <img src="${dataUrl}" style="width:60px; height:45px; object-fit:contain; background:#f8fafc; border-radius:4px; border:1px solid #e2e8f0;" />
          <div style="flex:1; overflow:hidden;">
            <div style="font-size:11.5px; font-weight:700; color:#0f172a; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${name}</div>
            <div style="font-size:10px; color:#64748b;">Uploaded Asset</div>
          </div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px; margin-top:2px;">
          <button class="gallery-action-btn full-label-btn" style="background:var(--clr-olive-light); border:1px solid var(--clr-olive-border); color:var(--clr-olive-dark); font-size:10px; font-weight:700; padding:4px 6px; border-radius:4px; cursor:pointer;">
            🖼️ Full Label
          </button>
          <button class="gallery-action-btn sticker-btn" style="background:#f1f5f9; border:1px solid #cbd5e1; color:#334155; font-size:10px; font-weight:700; padding:4px 6px; border-radius:4px; cursor:pointer;">
            ➕ Sticker
          </button>
        </div>
      `;

      card.querySelector('.full-label-btn').onclick = () => openImageAsFullLabel(dataUrl, name);
      card.querySelector('.sticker-btn').onclick = () => addStickerToCanvas(dataUrl, name);

      grid.prepend(card);
    }

    /* Dynamic Camera Bounding Box Framing (Prevents 5kg tub or large models from being cropped!) */
    function fitCameraToModel() {
      if (!threeCamera || !threeJarGroup) return;
      const box = new THREE.Box3().setFromObject(threeJarGroup);
      if (box.isEmpty()) return;

      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);

      const fovRad = (threeCamera.fov * Math.PI) / 180;
      let dist = (maxDim / 2) / Math.tan(fovRad / 2);
      dist *= 1.35; // 35% margin for aesthetic framing

      threeCamera.position.set(0, center.y + 0.05, dist);
      threeCamera.lookAt(center);

      if (threeOrbitControls) {
        threeOrbitControls.target.copy(center);
        threeOrbitControls.minDistance = dist * 0.35;
        threeOrbitControls.maxDistance = dist * 2.5;
        threeOrbitControls.update();
      }
    }
'''

# 4. Replace applyPackagingModel camera logic with fitCameraToModel()
# Also ensure container color is explicitly applied to bodyMat and capMat
if "fitCameraToModel();" not in html:
    html = re.sub(
        r'if \(threeCamera\) threeCamera\.position\.set\(.*?\);',
        'fitCameraToModel();',
        html
    )

# 5. Insert new_js_code right before initGomziStudio()
if "function initFullLabelUploadEngine()" not in html:
    html = html.replace(
        "function initGomziStudio() {",
        new_js_code + "\n    function initGomziStudio() {\n      initFullLabelUploadEngine();"
    )

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✓ Full Label Upload vs Sticker separation and 3D Camera framing successfully applied!")
