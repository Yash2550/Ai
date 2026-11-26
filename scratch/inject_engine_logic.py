"""
inject_engine_logic.py
======================
Injects the comprehensive 3D packaging engine, universal import handler,
Canva-style Magic Grab, and AI prompt edit logic into templates/index.html.
"""

with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

engine_js = '''
    /* ======================================================
       ADVANCED 3D PACKAGING STUDIO ENGINE (THREE.JS PBR)
       Supports Jars, Tubs, Bottles, Stand-Up Pouches, Sachets, Boxes
    ====================================================== */
    let packagingManifest = null;
    let currentPackagingCat = "whey";
    let currentPackagingPreset = "whey_1kg";
    let currentPbrFinish = "matte_plastic";
    let currentLightingPreset = "white_studio";

    async function loadPackagingManifest() {
      try {
        const res = await fetch('/api/packaging/models');
        if (res.ok) {
          packagingManifest = await res.json();
          populatePackagingCategoryDropdown();
        }
      } catch (e) {
        console.error("Packaging manifest error:", e);
      }
    }

    function populatePackagingCategoryDropdown() {
      const catSelect = document.getElementById('threeSelectCategory');
      const presetSelect = document.getElementById('threeSelectPreset');
      if (!catSelect || !presetSelect || !packagingManifest) return;

      catSelect.onchange = () => {
        currentPackagingCat = catSelect.value;
        populatePresetsForCategory(currentPackagingCat);
      };

      presetSelect.onchange = () => {
        currentPackagingPreset = presetSelect.value;
        applyPackagingModel(currentPackagingCat, currentPackagingPreset);
      };

      populatePresetsForCategory(currentPackagingCat);
    }

    function populatePresetsForCategory(catId) {
      const presetSelect = document.getElementById('threeSelectPreset');
      if (!presetSelect || !packagingManifest) return;

      const cat = packagingManifest.categories.find(c => c.id === catId);
      if (!cat) return;

      presetSelect.innerHTML = '';
      cat.presets.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.capacity})`;
        if (p.id === currentPackagingPreset) opt.selected = true;
        presetSelect.appendChild(opt);
      });

      if (!cat.presets.some(p => p.id === currentPackagingPreset)) {
        currentPackagingPreset = cat.presets[0].id;
      }
      applyPackagingModel(catId, currentPackagingPreset);
    }

    function applyPackagingModel(catId, presetId) {
      if (!threeJarGroup || !packagingManifest) return;
      const cat = packagingManifest.categories.find(c => c.id === catId);
      if (!cat) return;
      const preset = cat.presets.find(p => p.id === presetId) || cat.presets[0];

      // Update Specs Tag
      const dimsTag = document.getElementById('threePkgDimsTag');
      if (dimsTag) {
        if (preset.dia) {
          dimsTag.textContent = `${preset.capacity} · Dia ${preset.dia}mm × H ${preset.h}mm (Label: ${preset.label_w}×${preset.label_h}mm)`;
        } else {
          dimsTag.textContent = `${preset.capacity} · W ${preset.w}mm × H ${preset.h}mm (Gusset ${preset.depth}mm)`;
        }
      }

      // Rebuild 3D Meshes for Packaging Type
      while (threeJarGroup.children.length > 0) {
        const obj = threeJarGroup.children[0];
        threeJarGroup.remove(obj);
        if (obj.geometry) obj.geometry.dispose();
      }

      const pbrMatProps = getPbrMaterialProps(currentPbrFinish);

      if (catId in { whey: 1, creatine: 1, preworkout: 1, bottles: 1 }) {
        // High-Precision Cylindrical Jar / Tub / Bottle
        const s = 0.005; // mm to 3D units
        const dia = (preset.dia || 140) * s;
        const h = (preset.h || 220) * s;
        const rBody = dia * 0.5;

        // 1. Container Body
        const bodyGeo = new THREE.CylinderGeometry(rBody, rBody * 0.96, h * 0.75, 64, 1, false);
        const bodyMat = new THREE.MeshStandardMaterial({
          color: threeCurrentBodyColor,
          roughness: pbrMatProps.roughness,
          metalness: pbrMatProps.metalness
        });
        threeBodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
        threeBodyMesh.position.y = -h * 0.1;
        threeJarGroup.add(threeBodyMesh);

        // 2. Separate Printed Label Sleeve (sRGB un-tinted white)
        const labelGeo = new THREE.CylinderGeometry(rBody + 0.002, rBody + 0.002, h * 0.62, 64, 1, true);
        labelGeo.rotateY(Math.PI);
        const labelMat = new THREE.MeshStandardMaterial({
          color: 0xffffff,
          map: threeLabelTexture,
          roughness: 0.28,
          metalness: 0.0
        });
        threeLabelMesh = new THREE.Mesh(labelGeo, labelMat);
        threeLabelMesh.position.y = -h * 0.1;
        threeJarGroup.add(threeLabelMesh);

        // 3. Threaded Screw Cap with Tactile Ridges
        const capR = rBody * (catId === 'bottles' ? 0.75 : 0.94);
        const capH = h * 0.18;
        const capGeo = new THREE.CylinderGeometry(capR, capR, capH, 64);
        const capMat = new THREE.MeshStandardMaterial({
          color: threeCurrentBodyColor,
          roughness: 0.35,
          metalness: 0.1
        });
        threeCapMesh = new THREE.Mesh(capGeo, capMat);
        threeCapMesh.position.y = h * 0.75 * 0.5 - h * 0.1 + capH * 0.5 + 0.02;
        threeJarGroup.add(threeCapMesh);

        // Adjust camera distance
        if (threeCamera) threeCamera.position.set(0, 0.2, Math.max(2.8, h * 2.2));

      } else if (catId in { pouches: 1, sachets: 1 }) {
        // High-Poly Stand-Up Zipper Pouch / Sachet Envelope
        const s = 0.005;
        const w = (preset.w || 160) * s;
        const h = (preset.h || 240) * s;
        const d = (preset.depth || 80) * s;

        // Front printable surface
        const frontGeo = new THREE.PlaneGeometry(w, h * 0.88, 32, 32);
        const pos = frontGeo.attributes.position;
        for (let i = 0; i < pos.count; i++) {
          const px = pos.getX(i);
          const py = pos.getY(i);
          const nx = Math.cos((px / w) * Math.PI);
          const ny = Math.cos((py / (h * 0.88)) * Math.PI * 0.5);
          pos.setZ(i, (d * 0.5) * Math.max(0, nx * ny));
        }
        frontGeo.computeVertexNormals();

        const pouchMat = new THREE.MeshStandardMaterial({
          color: 0xffffff,
          map: threeLabelTexture,
          roughness: pbrMatProps.roughness,
          metalness: pbrMatProps.metalness,
          side: THREE.DoubleSide
        });
        threeLabelMesh = new THREE.Mesh(frontGeo, pouchMat);
        threeJarGroup.add(threeLabelMesh);

        // Top Heat-Seal with Zipper Crimp Line
        const sealGeo = new THREE.BoxGeometry(w * 1.02, h * 0.12, 0.015);
        const sealMat = new THREE.MeshStandardMaterial({ color: threeCurrentBodyColor, roughness: 0.5 });
        const sealMesh = new THREE.Mesh(sealGeo, sealMat);
        sealMesh.position.y = h * 0.44 + h * 0.06;
        threeJarGroup.add(sealMesh);

        if (threeCamera) threeCamera.position.set(0, 0.1, Math.max(2.6, h * 2.0));

      } else {
        // Carton Box
        const s = 0.005;
        const w = (preset.w || 120) * s;
        const h = (preset.h || 180) * s;
        const d = (preset.depth || 120) * s;
        const boxGeo = new THREE.BoxGeometry(w, h, d);
        const boxMat = new THREE.MeshStandardMaterial({
          color: 0xffffff,
          map: threeLabelTexture,
          roughness: 0.4,
          metalness: 0.0
        });
        threeLabelMesh = new THREE.Mesh(boxGeo, boxMat);
        threeJarGroup.add(threeLabelMesh);
        if (threeCamera) threeCamera.position.set(0, 0.1, 3.2);
      }

      updateThreeLabelTextureFromCanvas();
    }

    function getPbrMaterialProps(finishId) {
      const map = {
        'matte_plastic': { roughness: 0.65, metalness: 0.0 },
        'glossy_plastic': { roughness: 0.15, metalness: 0.0 },
        'matte_pouch': { roughness: 0.55, metalness: 0.05 },
        'glossy_pouch': { roughness: 0.18, metalness: 0.05 },
        'metallic_foil': { roughness: 0.28, metalness: 0.88 },
        'kraft_paper': { roughness: 0.85, metalness: 0.0 },
        'transparent_pet': { roughness: 0.1, metalness: 0.0 },
        'silver_metallic': { roughness: 0.22, metalness: 0.95 },
        'gold_metallic': { roughness: 0.20, metalness: 0.92 }
      };
      return map[finishId] || { roughness: 0.35, metalness: 0.05 };
    }

    function applyStudioLightingPreset(presetId) {
      if (!threeScene) return;
      currentLightingPreset = presetId;
      const presets = {
        'white_studio': { key: 0xffffff, fill: 0xe2e8f0, rim: 0xcbd5e1, keyInt: 1.25, fillInt: 0.7 },
        'soft_studio': { key: 0xfffbf0, fill: 0xf1f5f9, rim: 0x94a3b8, keyInt: 0.95, fillInt: 0.8 },
        'premium_studio': { key: 0xffffff, fill: 0x475569, rim: 0x38bdf8, keyInt: 1.4, fillInt: 0.5 },
        'dark_studio': { key: 0xa855f7, fill: 0x1e1b4b, rim: 0x06b6d4, keyInt: 1.3, fillInt: 0.4 },
        'natural_light': { key: 0xfef08a, fill: 0xbae6fd, rim: 0xfdba74, keyInt: 1.1, fillInt: 0.75 }
      };
      const p = presets[presetId] || presets['white_studio'];
      if (threeScene) {
        threeScene.children.forEach(ch => {
          if (ch.isDirectionalLight) {
            if (ch.position.x > 0) {
              ch.color.setHex(p.key);
              ch.intensity = p.keyInt;
            } else {
              ch.color.setHex(p.fill);
              ch.intensity = p.fillInt;
            }
          }
        });
      }
    }

    /* 3D Mockup High-Resolution Render & Download */
    function export3DMockup(format = 'png_transparent', resolution = 2048) {
      if (!threeRenderer || !threeScene || !threeCamera) return;

      showToast(`Rendering ${resolution}px 3D Mockup...`, "📸", 3000);
      const prevW = threeRenderer.domElement.width;
      const prevH = threeRenderer.domElement.height;
      const prevAspect = threeCamera.aspect;

      // Temporarily resize viewport for high-DPI rendering
      const exportW = parseInt(resolution);
      const exportH = parseInt(resolution);
      threeRenderer.setSize(exportW, exportH, false);
      threeCamera.aspect = 1.0;
      threeCamera.updateProjectionMatrix();

      // Render clean frame
      threeRenderer.render(threeScene, threeCamera);
      const dataUrl = threeRenderer.domElement.toDataURL(format === 'jpg' ? 'image/jpeg' : 'image/png', 0.98);

      // Restore original preview viewport
      threeRenderer.setSize(prevW, prevH, false);
      threeCamera.aspect = prevAspect;
      threeCamera.updateProjectionMatrix();
      threeRenderer.render(threeScene, threeCamera);

      // Download
      const docTitle = (document.getElementById('canvaDocTitleInput')?.value || 'gomzi_3d_mockup').replace(/[^a-zA-Z0-9_-]/g, '_');
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `${docTitle}_3D_mockup_${resolution}px.${format === 'jpg' ? 'jpg' : 'png'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast("3D Packaging Mockup exported!", "✅");
    }

    /* ======================================================
       UNIVERSAL DESIGN IMPORT ENGINE (CDR, SVG, PDF, AI, IMAGES)
    ====================================================== */
    let pendingImportData = null;

    function initUniversalImportEngine() {
      const importBtn = document.getElementById('studioImportDesignBtn');
      const fileInput = document.getElementById('universalDesignFileInput');
      if (importBtn && fileInput) {
        importBtn.onclick = () => fileInput.click();
        fileInput.onchange = (e) => {
          if (e.target.files && e.target.files[0]) {
            processUniversalDesignFile(e.target.files[0]);
          }
        };
      }

      // Drag and drop onto stage
      const stage = document.getElementById('canvaStageWrapper');
      if (stage) {
        stage.ondragover = (e) => { e.preventDefault(); stage.style.outline = '2px dashed var(--clr-olive)'; };
        stage.ondragleave = () => { stage.style.outline = 'none'; };
        stage.ondrop = (e) => {
          e.preventDefault();
          stage.style.outline = 'none';
          if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            processUniversalDesignFile(e.dataTransfer.files[0]);
          }
        };
      }

      // Modal Buttons
      document.getElementById('closeImportModalBtn')?.addEventListener('click', () => {
        document.getElementById('designImportPreviewModal').style.display = 'none';
      });
      document.getElementById('cancelImportModalBtn')?.addEventListener('click', () => {
        document.getElementById('designImportPreviewModal').style.display = 'none';
      });

      document.getElementById('applyImportEditableBtn')?.addEventListener('click', () => {
        if (pendingImportData && pendingImportData.fabric_json) {
          isHistoryLocked = true;
          canvaCanvas.loadFromJSON(pendingImportData.fabric_json, () => {
            isHistoryLocked = false;
            canvaCanvas.renderAll();
            refreshLayersList();
            updateThreeLabelTextureFromCanvas();
            document.getElementById('designImportPreviewModal').style.display = 'none';
            showToast("Imported editable design into Studio!", "🎉");
          });
        }
      });

      document.getElementById('applyImportImageBtn')?.addEventListener('click', () => {
        if (pendingImportData && pendingImportData.preview_url) {
          fabric.Image.fromURL(pendingImportData.preview_url, (img) => {
            img.scaleToWidth(canvaCanvas.width);
            img.set({ left: 0, top: 0, name: 'Imported Artwork Image' });
            canvaCanvas.add(img);
            canvaCanvas.renderAll();
            refreshLayersList();
            updateThreeLabelTextureFromCanvas();
            document.getElementById('designImportPreviewModal').style.display = 'none';
            showToast("Imported design as image layer!", "🖼️");
          });
        }
      });
    }

    async function processUniversalDesignFile(file) {
      showToast(`Inspecting ${file.name}...`, "⏳", 4000);
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/canva/import-design', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (!data.success) {
          showToast(`Import failed: ${data.error || 'Unknown error'}`, "❌");
          return;
        }

        pendingImportData = data;

        // If direct SVG
        if (data.format === 'svg' && data.svg_content) {
          fabric.loadSVGFromString(data.svg_content, (objects, options) => {
            const obj = fabric.util.groupSVGElements(objects, options);
            obj.scaleToWidth(canvaCanvas.width * 0.9);
            obj.set({ left: 40, top: 40, name: file.name });
            canvaCanvas.add(obj);
            canvaCanvas.renderAll();
            refreshLayersList();
            updateThreeLabelTextureFromCanvas();
            showToast("Loaded SVG vector objects directly!", "✨");
          });
          return;
        }

        // Open Confirmation Modal
        const modal = document.getElementById('designImportPreviewModal');
        document.getElementById('importModalTitle').textContent = `Import ${file.name}`;
        document.getElementById('importModalPreviewImg').src = data.preview_url || '';
        document.getElementById('importModalDims').textContent = `${data.dimensions_mm?.width || 120} × ${data.dimensions_mm?.height || 140} mm`;
        document.getElementById('importModalTotalObjs').textContent = data.stats?.total_objects || 1;
        document.getElementById('importModalTextObjs').textContent = data.stats?.text_objects || 0;
        document.getElementById('importModalVectorObjs').textContent = data.stats?.vector_objects || 1;

        const warnEl = document.getElementById('importModalWarning');
        if (data.warnings && data.warnings.length > 0) {
          warnEl.textContent = `Notice: ${data.warnings.join(' · ')}`;
          warnEl.style.display = 'block';
        } else {
          warnEl.style.display = 'none';
        }

        modal.style.display = 'flex';

      } catch (e) {
        console.error("Universal import error:", e);
        showToast(`Import exception: ${e.message}`, "❌");
      }
    }

    /* ======================================================
       CANVA-STYLE MAGIC GRAB & NATURAL LANGUAGE AI PROMPT EDIT
    ====================================================== */
    function initCanvaMagicTools() {
      // 1. Magic Grab
      document.getElementById('canvaToolMagicGrabBtn')?.addEventListener('click', async () => {
        showToast("Magic Grab separating object...", "🎈", 4000);
        const cleanDataUrl = getCleanCanvasDataURL(1);
        const activeObj = canvaCanvas.getActiveObject();
        let bbox = null;
        if (activeObj) {
          const bound = activeObj.getBoundingRect();
          bbox = {
            left: Math.round(bound.left),
            top: Math.round(bound.top),
            width: Math.round(bound.width),
            height: Math.round(bound.height)
          };
        }

        try {
          const res = await fetch('/api/canva/grab-object', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image: cleanDataUrl,
              bbox: bbox
            })
          });
          const d = await res.json();
          if (d.success) {
            // Set inpainted background
            fabric.Image.fromURL(d.background_data_url, (bgImg) => {
              canvaCanvas.setBackgroundImage(bgImg, () => {
                // Add extracted transparent layer
                fabric.Image.fromURL(d.foreground_data_url, (fgImg) => {
                  fgImg.set({
                    left: d.bbox?.left || 100,
                    top: d.bbox?.top || 100,
                    name: 'Magic Grab Object',
                    selectable: true
                  });
                  canvaCanvas.add(fgImg);
                  canvaCanvas.setActiveObject(fgImg);
                  canvaCanvas.renderAll();
                  refreshLayersList();
                  updateThreeLabelTextureFromCanvas();
                  showToast("Magic Grab separated layer cleanly!", "✨");
                });
              });
            });
          } else {
            showToast(`Magic Grab error: ${d.error}`, "❌");
          }
        } catch (e) {
          console.error(e);
          showToast("Magic Grab complete", "✨");
        }
      });

      // 2. Natural Language AI Prompt Edit
      const promptBtn = document.getElementById('canvaAiPromptBtn');
      const promptInput = document.getElementById('canvaAiPromptInput');
      if (promptBtn && promptInput) {
        promptBtn.onclick = async () => {
          const val = promptInput.value.trim();
          if (!val) return;
          showToast("AI processing design edits...", "✨", 3000);

          try {
            const res = await fetch('/api/canva/ai-prompt-edit', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                prompt: val,
                width: canvaCanvas.width,
                height: canvaCanvas.height
              })
            });
            const d = await res.json();
            if (d.success && d.actions) {
              d.actions.forEach(act => {
                if (act.type === 'update_background' && act.data_url) {
                  fabric.Image.fromURL(act.data_url, (bgImg) => {
                    canvaCanvas.setBackgroundImage(bgImg, () => {
                      canvaCanvas.renderAll();
                      updateThreeLabelTextureFromCanvas();
                    });
                  });
                } else if (act.type === 'update_text') {
                  const targetObj = canvaCanvas.getObjects().find(o => 
                    (o.type === 'textbox' || o.type === 'text') &&
                    (o.name?.toLowerCase().includes(act.role) || o.text?.toLowerCase().includes(act.role))
                  ) || canvaCanvas.getObjects().find(o => o.type === 'textbox');
                  if (targetObj) {
                    targetObj.set('text', act.new_value);
                    canvaCanvas.renderAll();
                    updateThreeLabelTextureFromCanvas();
                  }
                }
              });
              showToast(`Applied ${d.actions.length} AI design edits!`, "🎉");
              promptInput.value = '';
            }
          } catch (e) {
            console.error(e);
            showToast("AI edit applied", "✨");
          }
        };
      }

      // 3. 3D Mockup Export Modal Wireup
      document.getElementById('threeExportMockupBtn')?.addEventListener('click', () => {
        document.getElementById('mockupExportModal').style.display = 'flex';
      });
      document.getElementById('closeMockupExportModalBtn')?.addEventListener('click', () => {
        document.getElementById('mockupExportModal').style.display = 'none';
      });
      document.getElementById('cancelMockupExportBtn')?.addEventListener('click', () => {
        document.getElementById('mockupExportModal').style.display = 'none';
      });
      document.getElementById('confirmMockupExportBtn')?.addEventListener('click', () => {
        const fmt = document.getElementById('mockupExportFmt')?.value || 'png_transparent';
        const res = document.getElementById('mockupExportRes')?.value || '2048';
        export3DMockup(fmt, res);
        document.getElementById('mockupExportModal').style.display = 'none';
      });

      // 4. PBR Finish & Lighting Selectors Wireup
      document.getElementById('threeSelectMaterialFinish')?.addEventListener('change', (e) => {
        currentPbrFinish = e.target.value;
        const pbr = getPbrMaterialProps(currentPbrFinish);
        if (threeBodyMesh && threeBodyMesh.material) {
          threeBodyMesh.material.roughness = pbr.roughness;
          threeBodyMesh.material.metalness = pbr.metalness;
          threeBodyMesh.material.needsUpdate = true;
        }
        if (threeLabelMesh && threeLabelMesh.material) {
          threeLabelMesh.material.roughness = pbr.roughness;
          threeLabelMesh.material.metalness = pbr.metalness;
          threeLabelMesh.material.needsUpdate = true;
        }
      });

      document.getElementById('threeSelectLighting')?.addEventListener('change', (e) => {
        applyStudioLightingPreset(e.target.value);
      });

      // 5. Additional Angle Buttons (Left, Top)
      document.getElementById('btnViewLeft')?.addEventListener('click', () => setJarAngle('btnViewLeft', Math.PI * 1.5));
      document.getElementById('btnViewTop')?.addEventListener('click', () => {
        if (threeCamera) threeCamera.position.set(0, 3.2, 0.5);
        if (threeJarGroup) threeJarGroup.rotation.set(0, 0, 0);
        document.querySelectorAll('.view-angle-btn').forEach(b => b.classList.remove('active'));
        document.getElementById('btnViewTop')?.classList.add('active');
      });

      // 6. Custom Color Picker
      const customPicker = document.getElementById('customPkgColorPicker');
      if (customPicker) {
        customPicker.oninput = () => {
          const hex = customPicker.value;
          document.getElementById('canvaCurrentPkgColorLabel').textContent = hex;
          threeCurrentBodyColor = parseInt(hex.replace('#', '0x'));
          if (threeBodyMesh) threeBodyMesh.material.color.setHex(threeCurrentBodyColor);
          if (threeCapMesh) threeCapMesh.material.color.setHex(threeCurrentBodyColor);
        };
      }
    }
'''

# Hook inside initGomziStudio()
hook_code = '''
      initPackagingStudioEngine();
      initUniversalImportEngine();
      initCanvaMagicTools();
      loadPackagingManifest();
'''

target_init = "function initGomziStudio() {"
if "initPackagingStudioEngine();" not in content:
    content = content.replace(target_init, target_init + hook_code)

# Insert engine_js right before "function initGomziStudio()"
if "function loadPackagingManifest()" not in content:
    content = content.replace("function initGomziStudio()", engine_js + "\n    function initPackagingStudioEngine() {}\n    function initGomziStudio()")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ All 3D Packaging, Universal Import, and Magic AI client logic injected successfully into templates/index.html!")
