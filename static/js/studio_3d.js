/* ============================================================================
   studio_3d.js - GOMZI BOB Realistic 3D Packaging Engine (Three.js + GLTFLoader + PBR + PMREM)
   ============================================================================ */

let packagingManifest = null;
let threeRenderer = null, threeCamera = null, threeScene = null, threeOrbitControls = null;
let threePmremGen = null, threeEnvRT = null;
let threeJarGroup = null, threeLabelTexture = null;
let threeBodyMeshes = [], threeLidMeshes = [], threeLabelMeshes = [];
let threeSurfaceMeshes = {};
let threeSurfaceTextures = {};
let threeNormalMaps = { foil: null, paper: null, hdpe: null };
let threeAmbientLight = null, threeHemiLight = null, threeKeyLight = null, threeFillLight = null, threeRimLight = null;
let _syncTexTimer = null;
let _lastFrontOnlyToastSig = '';

let currentPackagingCat = 'jar';
let currentPackagingPreset = 'jar_1kg';
let currentPbrFinish = 'matte';
let currentLightingPreset = 'studio';
let threeBodyColorHex = '#181A1C';
let threeLidColorHex = '#141618';
let isAutoSpinning = false;
let isLiveSyncEnabled = true;

const CATEGORY_DEFAULTS = {
  jar: { body: '#181A1C', lid: '#141618', finish: 'matte' },
  bottle: { body: '#181A1C', lid: '#141618', finish: 'matte' },
  pouch: { body: '#EFF2F5', lid: '#DCE2E8', finish: 'matte' },
  sachet: { body: '#D9B664', lid: '#C49B3E', finish: 'metallic_foil' },
  box: { body: '#C49F72', lid: '#B28B5E', finish: 'cardboard' },
};
const threeCategoryColorState = {};

const PACKAGING_THUMBNAILS = {
  jar: '/static/models/packaging/thumbnails/jar.png',
  pouch: '/static/models/packaging/thumbnails/pouch.png',
  sachet: '/static/models/packaging/thumbnails/sachet.png',
  bottle: '/static/models/packaging/thumbnails/bottle.png',
  box: '/static/models/packaging/thumbnails/box.png',
};

const CATEGORY_MATERIALS = {
  jar: ['matte', 'glossy', 'satin', 'soft_touch', 'transparent', 'frosted', 'metallic_foil'],
  bottle: ['matte', 'glossy', 'satin', 'transparent', 'frosted', 'soft_touch'],
  pouch: ['matte', 'glossy', 'metallic_foil', 'matte_foil', 'glossy_foil', 'kraft_paper'],
  sachet: ['metallic_foil', 'matte_foil', 'glossy_foil', 'matte', 'glossy'],
  box: ['cardboard', 'kraft_paper', 'matte', 'glossy', 'matte_foil', 'glossy_foil'],
};

function getPackagingNormalMap(kind) {
  if (threeNormalMaps[kind]) return threeNormalMaps[kind];
  if (typeof document === 'undefined' || typeof THREE === 'undefined') return null;

  const size = 256;
  const hCanvas = document.createElement('canvas');
  hCanvas.width = size; hCanvas.height = size;
  const hctx = hCanvas.getContext('2d');
  const hImg = hctx.createImageData(size, size);
  const hData = new Float32Array(size * size);

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let val = 0;
      if (kind === 'foil') {
        // Subtle organic foil fold + metallic micro-grain waves
        const u = (x / size) * Math.PI * 2;
        const v = (y / size) * Math.PI * 2;
        val = 0.5
          + 0.22 * Math.sin(u * 2 + v * 1)
          + 0.16 * Math.sin(u * 3 - v * 2)
          + 0.08 * Math.sin(u * 7 + v * 5);
      } else if (kind === 'hdpe') {
        // Delicate injection/blow-molded HDPE micro-pebble grain for soft studio reflections
        const h1 = Math.sin(x * 18.91 + y * 43.17) * 43758.5453;
        const h2 = Math.sin((x + 17) * 31.41 + (y + 29) * 19.73) * 19341.123;
        const n1 = h1 - Math.floor(h1);
        const n2 = h2 - Math.floor(h2);
        val = 0.45 + 0.18 * (n1 * 0.65 + n2 * 0.35);
      } else {
        // Cardboard / Kraft paper tactile fiber grain
        const hash = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
        const grain = hash - Math.floor(hash);
        const rib = 0.08 * Math.sin((x / size) * Math.PI * 16);
        val = 0.45 + 0.25 * grain + rib;
      }
      hData[y * size + x] = val;
    }
  }

  // Sobel gradient -> RGB tangent-space normal map
  const nCanvas = document.createElement('canvas');
  nCanvas.width = size; nCanvas.height = size;
  const nctx = nCanvas.getContext('2d');
  const nImg = nctx.createImageData(size, size);
  const strength = kind === 'foil' ? 2.4 : (kind === 'hdpe' ? 0.85 : 1.6);
  for (let y = 0; y < size; y++) {
    const ym = (y - 1 + size) % size;
    const yp = (y + 1) % size;
    for (let x = 0; x < size; x++) {
      const xm = (x - 1 + size) % size;
      const xp = (x + 1) % size;
      const dx = (hData[y * size + xp] - hData[y * size + xm]) * strength;
      const dy = (hData[yp * size + x] - hData[ym * size + x]) * strength;
      const nx = -dx, ny = -dy, nz = 1.0;
      const invLen = 1.0 / Math.hypot(nx, ny, nz);
      const idx = (y * size + x) * 4;
      nImg.data[idx] = Math.round((nx * invLen * 0.5 + 0.5) * 255);
      nImg.data[idx + 1] = Math.round((ny * invLen * 0.5 + 0.5) * 255);
      nImg.data[idx + 2] = Math.round((nz * invLen * 0.5 + 0.5) * 255);
      nImg.data[idx + 3] = 255;
    }
  }
  nctx.putImageData(nImg, 0, 0);
  void hImg;

  const tex = new THREE.CanvasTexture(nCanvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  const rep = kind === 'foil' ? 2 : (kind === 'hdpe' ? 8 : 4);
  tex.repeat.set(rep, rep);
  tex.needsUpdate = true;
  threeNormalMaps[kind] = tex;
  return tex;
}

async function initThreePackagingEngine() {
  initThreeViewport();
  bindThreeControlListeners();
  await loadPackagingManifest();
}

function createStudioEnvironmentTexture() {
  if (!threePmremGen) return null;
  const envScene = new THREE.Scene();
  // Dark neutral studio cyclorama prevents milky gray washout over rich black & gold packaging prints!
  envScene.background = new THREE.Color(0x1C2026);

  // Calibrated directional studio softboxes for crisp foil & bevel highlights
  const topBox = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.MeshBasicMaterial({ color: 0xFFFFFF }));
  topBox.position.set(0, 8, 1);
  topBox.rotation.x = Math.PI / 2;
  envScene.add(topBox);

  const sideLeft = new THREE.Mesh(new THREE.PlaneGeometry(7, 10), new THREE.MeshBasicMaterial({ color: 0xE8EEF5 }));
  sideLeft.position.set(-8, 2.5, 4);
  sideLeft.lookAt(0, 0, 0);
  envScene.add(sideLeft);

  const sideRight = new THREE.Mesh(new THREE.PlaneGeometry(7, 10), new THREE.MeshBasicMaterial({ color: 0xDCE4EE }));
  sideRight.position.set(8, 2.5, 3);
  sideRight.lookAt(0, 0, 0);
  envScene.add(sideRight);

  const rimStrip = new THREE.Mesh(new THREE.PlaneGeometry(10, 4), new THREE.MeshBasicMaterial({ color: 0xFFF4DC }));
  rimStrip.position.set(0, 3, -8);
  rimStrip.lookAt(0, 0, 0);
  envScene.add(rimStrip);

  if (threeEnvRT) threeEnvRT.dispose();
  threeEnvRT = threePmremGen.fromScene(envScene, 0.04);
  return threeEnvRT.texture;
}

function initThreeViewport() {
  const container = document.getElementById('pacdoraThreeContainer');
  if (!container || typeof THREE === 'undefined') return;

  const w = container.clientWidth || 368;
  const h = container.clientHeight || 256;

  threeScene = new THREE.Scene();
  threeCamera = new THREE.PerspectiveCamera(34, w / h, 0.05, 60);
  threeCamera.position.set(0, 0.25, 2.8);

  threeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  threeRenderer.setSize(w, h);
  threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  threeRenderer.outputEncoding = THREE.sRGBEncoding;
  threeRenderer.toneMapping = THREE.ACESFilmicToneMapping;
  threeRenderer.toneMappingExposure = 1.0;

  container.innerHTML = '';
  container.appendChild(threeRenderer.domElement);

  if (THREE.PMREMGenerator) {
    threePmremGen = new THREE.PMREMGenerator(threeRenderer);
    threePmremGen.compileEquirectangularShader();
    threeScene.environment = createStudioEnvironmentTexture();
  }

  if (THREE.OrbitControls) {
    threeOrbitControls = new THREE.OrbitControls(threeCamera, threeRenderer.domElement);
    threeOrbitControls.enableDamping = true;
    threeOrbitControls.dampingFactor = 0.08;
    threeOrbitControls.enablePan = false;
    threeOrbitControls.minPolarAngle = Math.PI * 0.10;
    threeOrbitControls.maxPolarAngle = Math.PI * 0.65;
  }

  // Calibrated Studio Lights (preserves true black/graphite print & vivid colors without gray glare)
  threeAmbientLight = new THREE.AmbientLight(0xFFFFFF, 0.36);
  threeHemiLight = new THREE.HemisphereLight(0xFFFFFF, 0x20242A, 0.50);
  threeKeyLight = new THREE.DirectionalLight(0xFFFFFF, 1.08);
  threeKeyLight.position.set(2.8, 4.2, 3.6);
  threeFillLight = new THREE.DirectionalLight(0xE8EDF2, 0.42);
  threeFillLight.position.set(-3.2, 1.4, 2.4);
  threeRimLight = new THREE.DirectionalLight(0xFFFFFF, 0.55);
  threeRimLight.position.set(0.0, 2.4, -3.5);
  threeScene.add(threeAmbientLight, threeHemiLight, threeKeyLight, threeFillLight, threeRimLight);

  threeJarGroup = new THREE.Group();
  threeScene.add(threeJarGroup);

  function animate() {
    requestAnimationFrame(animate);
    if (isAutoSpinning && threeJarGroup) {
      threeJarGroup.rotation.y += 0.01;
    }
    if (threeOrbitControls) threeOrbitControls.update();
    threeRenderer.render(threeScene, threeCamera);
  }
  animate();
}

function resizeThreeViewport() {
  const container = document.getElementById('pacdoraThreeContainer');
  if (!container || !threeRenderer || !threeCamera) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w > 20 && h > 20) {
    threeRenderer.setSize(w, h);
    threeCamera.aspect = w / h;
    threeCamera.updateProjectionMatrix();
    fitCameraToModel();
  }
}

async function loadPackagingManifest() {
  try {
    const res = await fetch('/api/packaging/models');
    if (!res.ok) return;
    packagingManifest = await res.json();
    renderPackagingCategoryCards();
    select3DCategory(currentPackagingCat, currentPackagingPreset);
  } catch (e) {
    console.error('Manifest error:', e);
  }
}

function renderPackagingCategoryCards() {
  const strip = document.getElementById('pkgVisualSelectorStrip');
  if (!strip || !packagingManifest) return;
  strip.innerHTML = '';

  packagingManifest.categories.forEach(cat => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = `pkg-thumb-card ${cat.id === currentPackagingCat ? 'active' : ''}`;
    card.setAttribute('data-cat', cat.id);
    card.innerHTML = `
      <img src="${cat.thumbnail || PACKAGING_THUMBNAILS[cat.id]}" alt="${cat.name}" class="pkg-thumb-img" />
      <span class="pkg-thumb-label">${cat.name}</span>
    `;
    card.onclick = () => select3DCategory(cat.id);
    strip.appendChild(card);
  });
}

function select3DCategory(catId, preferredPresetId = null) {
  if (!packagingManifest) return;
  const cat = packagingManifest.categories.find(c => c.id === catId) || packagingManifest.categories[0];
  if (!cat) return;

  currentPackagingCat = cat.id;
  document.querySelectorAll('.pkg-thumb-card').forEach(c => {
    c.classList.toggle('active', c.getAttribute('data-cat') === cat.id);
  });

  // Update hidden compatibility select if present
  const catSel = document.getElementById('threeSelectCategory');
  if (catSel) catSel.value = cat.id;

  // Apply category-appropriate authentic substrate colors & default material finish
  const def = CATEGORY_DEFAULTS[cat.id] || { body: '#181A1C', lid: '#141618', finish: 'matte' };
  const state = threeCategoryColorState[cat.id] || { body: def.body, lid: def.lid, finish: def.finish };
  threeCategoryColorState[cat.id] = state;
  threeBodyColorHex = state.body;
  threeLidColorHex = state.lid;
  currentPbrFinish = state.finish;

  const bPick = document.getElementById('threeBodyColorPicker');
  const bBox = document.getElementById('threeBodyColorBox');
  if (bPick) bPick.value = threeBodyColorHex;
  if (bBox) bBox.style.background = threeBodyColorHex;
  const lPick = document.getElementById('threeLidColorPicker');
  const lBox = document.getElementById('threeLidColorBox');
  if (lPick) lPick.value = threeLidColorHex;
  if (lBox) lBox.style.background = threeLidColorHex;

  // Populate Capacity / Preset dropdown
  const presetSel = document.getElementById('threeSelectPreset');
  if (presetSel) {
    presetSel.innerHTML = '';
    cat.presets.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      presetSel.appendChild(opt);
    });
    const chosen = (preferredPresetId && cat.presets.some(p => p.id === preferredPresetId))
      ? preferredPresetId
      : (cat.id === 'jar' && cat.presets.some(p => p.id === 'jar_1kg') ? 'jar_1kg' : cat.presets[0].id);
    currentPackagingPreset = chosen;
    presetSel.value = chosen;
  }

  // Filter Material Finishes appropriate for this packaging category
  populateMaterialsForCategory(cat.id);
  loadPackagingGlbModel(cat.id, currentPackagingPreset);
}

function populateMaterialsForCategory(catId) {
  const matSel = document.getElementById('threeSelectMaterialFinish');
  if (!matSel || !packagingManifest) return;
  const allowed = CATEGORY_MATERIALS[catId] || ['matte', 'glossy'];
  matSel.innerHTML = '';
  packagingManifest.materials.filter(m => allowed.includes(m.id)).forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = m.name;
    matSel.appendChild(opt);
  });
  if (!allowed.includes(currentPbrFinish)) {
    currentPbrFinish = (CATEGORY_DEFAULTS[catId]?.finish && allowed.includes(CATEGORY_DEFAULTS[catId].finish))
      ? CATEGORY_DEFAULTS[catId].finish
      : allowed[0];
  }
  matSel.value = currentPbrFinish;
}

function getMaterialConfig(matId) {
  const found = packagingManifest?.materials?.find(m => m.id === matId);
  return found || { id: 'matte', roughness: 0.65, metalness: 0.02, clearcoat: 0.05 };
}

function _makeSrgbColor(hexStr) {
  return new THREE.Color(hexStr).convertSRGBToLinear();
}

function _disposeSurfaceTextures() {
  Object.keys(threeSurfaceTextures).forEach((k) => {
    const t = threeSurfaceTextures[k];
    if (t && typeof t.dispose === 'function') t.dispose();
  });
  threeSurfaceTextures = {};
}

function _disposeThreeGroup(grp) {
  _disposeSurfaceTextures();
  while (grp.children.length > 0) {
    const child = grp.children[0];
    grp.remove(child);
    child.traverse((n) => {
      if (n.geometry) n.geometry.dispose();
      if (n.material) {
        if (Array.isArray(n.material)) {
          n.material.forEach(m => {
            if (m.map && m.map !== threeLabelTexture && !Object.values(threeNormalMaps).includes(m.map)) m.map.dispose();
            m.dispose();
          });
        } else {
          if (n.material.map && n.material.map !== threeLabelTexture && !Object.values(threeNormalMaps).includes(n.material.map)) n.material.map.dispose();
          n.material.dispose();
        }
      }
    });
  }
}

function _normalMapForMaterial(matCfg, isFoilBody = false, isPlasticContainer = false) {
  const id = (matCfg?.id || '').toLowerCase();
  if (id.includes('foil') || (isFoilBody && currentPackagingCat === 'sachet')) return getPackagingNormalMap('foil');
  if (id === 'kraft_paper' || id === 'cardboard') return getPackagingNormalMap('paper');
  if (isPlasticContainer && (id === 'matte' || id === 'soft_touch' || id === 'frosted' || id === 'satin')) {
    return getPackagingNormalMap('hdpe');
  }
  return null;
}

function _buildPlasticScale(matCfg, isLid = false) {
  const id = (matCfg?.id || '').toLowerCase();
  if (id === 'satin') return isLid ? 0.015 : 0.025;
  if (id === 'matte' || id === 'soft_touch' || id === 'frosted') return isLid ? 0.032 : 0.055;
  return 0.0;
}

let _activeGlbLoadId = 0;

function loadPackagingGlbModel(catId, presetId) {
  if (!threeJarGroup || !packagingManifest) return;
  const cat = packagingManifest.categories.find(c => c.id === catId);
  const preset = cat?.presets.find(p => p.id === presetId) || cat?.presets[0];
  if (!preset) return;

  const dimsTag = document.getElementById('threePkgDimsTag');
  if (dimsTag) {
    dimsTag.textContent = preset.dia
      ? `${preset.capacity} · Dia ${preset.dia}mm × H ${preset.h}mm (Label ${preset.label_w}×${preset.label_h}mm)`
      : `${preset.capacity} · ${preset.w}×${preset.h}×${preset.depth}mm`;
  }
  checkArtworkDimensionWarning(preset);

  const glbUrl = `/static/models/packaging/${preset.file}`;
  if (!THREE.GLTFLoader) return;

  const loadToken = ++_activeGlbLoadId;
  const loader = new THREE.GLTFLoader();
  loader.load(glbUrl, (gltf) => {
    // Discard stale async GLB completions if user switched packaging rapidly
    if (loadToken !== _activeGlbLoadId) return;

    _disposeThreeGroup(threeJarGroup);
    threeBodyMeshes = [];
    threeLidMeshes = [];
    threeLabelMeshes = [];
    threeSurfaceMeshes = {};

    const modelRoot = gltf.scene;
    const matCfg = getMaterialConfig(currentPbrFinish);
    const bodyLinear = _makeSrgbColor(threeBodyColorHex);
    const lidLinear = _makeSrgbColor(threeLidColorHex);
    const isJarOrBottle = (catId === 'jar' || catId === 'bottle');
    const surfNMap = _normalMapForMaterial(matCfg, true, false);
    const plasticNMap = isJarOrBottle ? _normalMapForMaterial(matCfg, false, true) : surfNMap;
    const isFoilFinish = (matCfg.id || '').includes('foil');
    const isGlossFinish = (matCfg.id === 'glossy' || matCfg.id === 'satin');
    const bodyPlasticScale = isJarOrBottle ? _buildPlasticScale(matCfg, false) : (surfNMap ? 0.15 : 0);
    const lidPlasticScale = isJarOrBottle ? _buildPlasticScale(matCfg, true) : 0;

    modelRoot.traverse((node) => {
      if (!node.isMesh) return;
      const nameLower = (node.name || '').toLowerCase();

      if (nameLower.includes('lid') || nameLower.includes('cap')) {
        const lidRough = isJarOrBottle
          ? (isGlossFinish ? Math.max(0.14, (matCfg.roughness ?? 0.22)) : Math.max(0.28, (matCfg.roughness ?? 0.56) - 0.18))
          : Math.max(0.22, (matCfg.roughness ?? 0.45) - 0.1);
        const lidClear = isJarOrBottle
          ? (isGlossFinish ? Math.max(0.75, matCfg.clearcoat ?? 0.85) : Math.max(0.22, (matCfg.clearcoat ?? 0.08) + 0.16))
          : (matCfg.clearcoat ?? 0.08);
        node.material = new THREE.MeshPhysicalMaterial({
          color: lidLinear,
          roughness: lidRough,
          metalness: matCfg.metalness ?? 0.04,
          clearcoat: lidClear,
          clearcoatRoughness: isGlossFinish ? 0.14 : 0.28,
          normalMap: plasticNMap,
          normalScale: plasticNMap ? new THREE.Vector2(lidPlasticScale, lidPlasticScale) : new THREE.Vector2(0, 0),
          envMapIntensity: isJarOrBottle ? 0.88 : 0.78,
        });
        threeLidMeshes.push(node);
      } else if (nameLower === 'sealmaterial' || nameLower.includes('sealrim') || nameLower === 'cartonbody') {
        const isFoilCat = (catId === 'sachet' || isFoilFinish);
        node.material = new THREE.MeshPhysicalMaterial({
          color: bodyLinear,
          roughness: matCfg.roughness ?? (isFoilCat ? 0.25 : 0.65),
          metalness: isFoilCat ? Math.max(0.75, matCfg.metalness ?? 0.85) : (matCfg.metalness ?? 0.02),
          clearcoat: matCfg.clearcoat ?? 0.08,
          normalMap: surfNMap,
          normalScale: surfNMap ? new THREE.Vector2(0.18, 0.18) : new THREE.Vector2(0, 0),
          envMapIntensity: isFoilCat ? 0.92 : 0.36,
        });
        threeBodyMeshes.push(node);
      } else if (
        nameLower.includes('surface')
        || nameLower.includes('label')
        || nameLower.includes('front')
        || nameLower.includes('back')
        || nameLower.includes('gusset')
      ) {
        let slotKey = 'cylinder';
        if (nameLower.includes('gusset')) slotKey = 'gusset';
        else if (nameLower.includes('back')) slotKey = 'back';
        else if (nameLower.includes('front')) slotKey = 'front';
        else if (nameLower.includes('left')) slotKey = 'left';
        else if (nameLower.includes('right')) slotKey = 'right';
        else if (nameLower.includes('top')) slotKey = 'top';
        else if (nameLower.includes('bottom')) slotKey = 'bottom';

        // Calibrated print PBR: preserves deep black & gold print inks without milky gray glare
        const printMetal = isFoilFinish ? Math.min(0.36, (matCfg.metalness || 0.7) * 0.36) : (catId === 'sachet' ? 0.18 : 0.0);
        const printRough = isFoilFinish ? Math.max(0.20, (matCfg.roughness || 0.30) * 0.92) : (isGlossFinish ? 0.22 : (isJarOrBottle ? 0.58 : 0.74));
        const printClearcoat = isFoilFinish ? 0.22 : (isGlossFinish ? 0.48 : (isJarOrBottle ? 0.08 : 0.03));
        const printEnv = isFoilFinish ? 0.58 : (isGlossFinish ? 0.50 : (isJarOrBottle ? 0.24 : 0.20));
        node.material = new THREE.MeshPhysicalMaterial({
          color: new THREE.Color(0xFFFFFF),
          map: threeSurfaceTextures[slotKey] || threeLabelTexture || null,
          roughness: printRough,
          metalness: printMetal,
          clearcoat: printClearcoat,
          clearcoatRoughness: isGlossFinish ? 0.16 : 0.40,
          normalMap: surfNMap,
          normalScale: surfNMap ? new THREE.Vector2(0.14, 0.14) : new THREE.Vector2(0, 0),
          envMapIntensity: printEnv,
        });
        node.userData.surfaceSlot = slotKey;
        threeLabelMeshes.push(node);
        if (!threeSurfaceMeshes[slotKey]) threeSurfaceMeshes[slotKey] = [];
        threeSurfaceMeshes[slotKey].push(node);
      } else {
        const isNeckRecess = isJarOrBottle && nameLower.includes('neck');
        const bodyRough = isJarOrBottle
          ? (isNeckRecess ? Math.min(0.82, (matCfg.roughness ?? 0.6) + 0.12) : (isGlossFinish ? (matCfg.roughness ?? 0.16) : Math.min(0.58, matCfg.roughness ?? 0.54)))
          : (matCfg.roughness ?? 0.6);
        const bodyClear = isJarOrBottle
          ? (isGlossFinish ? Math.max(0.75, matCfg.clearcoat ?? 0.85) : (matCfg.id === 'soft_touch' ? 0.0 : Math.max(0.12, matCfg.clearcoat ?? 0.05)))
          : (matCfg.clearcoat ?? 0.05);
        const matOpts = {
          color: bodyLinear,
          roughness: bodyRough,
          metalness: matCfg.metalness ?? 0.02,
          clearcoat: bodyClear,
          clearcoatRoughness: isGlossFinish ? 0.14 : 0.38,
          normalMap: plasticNMap,
          normalScale: plasticNMap ? new THREE.Vector2(bodyPlasticScale, bodyPlasticScale) : new THREE.Vector2(0, 0),
          envMapIntensity: isJarOrBottle ? (isNeckRecess ? 0.42 : 0.64) : 0.75,
        };
        if (matCfg.transmission) {
          matOpts.transparent = true;
          matOpts.opacity = matCfg.opacity ?? 0.65;
        }
        node.material = new THREE.MeshPhysicalMaterial(matOpts);
        threeBodyMeshes.push(node);
      }
    });

    const box = new THREE.Box3().setFromObject(modelRoot);
    const size = box.getSize(new THREE.Vector3());
    const shadowW = Math.max(size.x, size.z) * 1.65;
    const shadowGeo = new THREE.PlaneGeometry(shadowW, shadowW);
    // Infinite-resolution analytical GLSL contact shadow (eliminates 128px banding & noisy 4K PNG artifacts)
    const shadowMat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
      uniforms: {
        uColor: { value: new THREE.Color(0x0D1110) },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        varying vec2 vUv;
        void main() {
          vec2 p = (vUv - 0.5) * 2.0;
          float r = length(p);
          float r2 = dot(p, p);
          float core = exp(-r2 * 8.5) * 0.24;
          float soft = exp(-r2 * 2.8) * 0.12;
          float edgeFade = smoothstep(1.0, 0.58, r);
          float alpha = clamp((core + soft) * edgeFade, 0.0, 0.34);
          gl_FragColor = vec4(uColor, alpha);
        }
      `,
    });
    const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
    shadowMesh.rotation.x = -Math.PI / 2;
    shadowMesh.position.y = box.min.y - 0.012;

    threeJarGroup.add(modelRoot);
    threeJarGroup.add(shadowMesh);
    const defaultRotY = catId === 'box' ? -0.35 : (catId === 'pouch' || catId === 'sachet' ? 0.14 : 0);
    threeJarGroup.rotation.set(0, defaultRotY, 0);

    document.querySelectorAll('.view-angle-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btnViewFront')?.classList.add('active');

    fitCameraToModel();
    updateThreeLabelTextureFromCanvas(true);
  }, undefined, (err) => {
    console.error('GLB load failed:', err);
  });
}

function checkArtworkDimensionWarning(preset) {
  const warnBox = document.getElementById('threeDimensionWarning');
  if (!warnBox || !canvaCanvas || !preset) return;
  const cw = canvaCanvas._logicalWidth || 1536;
  const ch = canvaCanvas._logicalHeight || 512;
  const artRatio = cw / ch;
  const pkgRatio = (preset.label_w || preset.w || 3) / (preset.label_h || preset.h || 1);
  if (Math.abs(artRatio - pkgRatio) > Math.max(0.85, pkgRatio * 0.45)) {
    warnBox.textContent = `Recommended artwork for ${preset.name}: ${preset.label_w}×${preset.label_h} mm (Ratio ${pkgRatio.toFixed(1)}:1). Full-bleed auto-composed.`;
    warnBox.style.display = 'block';
  } else {
    warnBox.style.display = 'none';
  }
}

function fitCameraToModel() {
  if (!threeCamera || !threeJarGroup) return;
  threeJarGroup.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(threeJarGroup);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z);
  const vFovRad = (threeCamera.fov * Math.PI) / 180;
  const aspect = Math.max(0.4, threeCamera.aspect || 1.4);
  const distV = (size.y * 0.5) / Math.tan(vFovRad * 0.5);
  const distH = (Math.max(size.x, size.z) * 0.54) / (Math.tan(vFovRad * 0.5) * aspect);
  const dist = Math.max(distV, distH, maxDim * 0.48) * 1.48;

  threeCamera.near = Math.max(0.01, dist * 0.02);
  threeCamera.far = Math.max(60, dist * 12);
  threeCamera.updateProjectionMatrix();

  threeCamera.position.set(center.x, center.y + maxDim * 0.09, center.z + dist);
  threeCamera.lookAt(center);
  if (threeOrbitControls) {
    threeOrbitControls.target.copy(center);
    threeOrbitControls.minDistance = dist * 0.45;
    threeOrbitControls.maxDistance = dist * 2.5;
    threeOrbitControls.update();
  }
}

function _rgbToCss(r, g, b) {
  return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
}

function _rgbLuminance(r, g, b) {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function analyzeArtworkLayout(img) {
  const aw = 192, ah = 96;
  const ac = document.createElement('canvas');
  ac.width = aw; ac.height = ah;
  const actx = ac.getContext('2d');
  actx.drawImage(img, 0, 0, aw, ah);
  const data = actx.getImageData(0, 0, aw, ah).data;

  const getPx = (x, y) => {
    const cx = Math.min(aw - 1, Math.max(0, x));
    const cy = Math.min(ah - 1, Math.max(0, y));
    const i = (cy * aw + cx) * 4;
    return [data[i], data[i + 1], data[i + 2], data[i + 3]];
  };

  // 1. Detect accidental outer pure-white scanner margin (only if interior is significantly darker/colored)
  const sampleInteriorLum = (() => {
    let sum = 0, cnt = 0;
    for (let y = 12; y < ah - 12; y += 6) {
      for (let x = 16; x < aw - 16; x += 8) {
        const [r, g, b] = getPx(x, y);
        sum += _rgbLuminance(r, g, b);
        cnt++;
      }
    }
    return sum / Math.max(1, cnt);
  })();

  let trimLeft = 0, trimRight = aw - 1, trimTop = 0, trimBot = ah - 1;
  if (sampleInteriorLum < 225) {
    const isNearWhiteCol = (x) => {
      let wCnt = 0, tot = 0;
      for (let y = 8; y < ah - 8; y += 4) {
        const [r, g, b] = getPx(x, y);
        if (r > 245 && g > 245 && b > 245) wCnt++;
        tot++;
      }
      return (wCnt / Math.max(1, tot)) > 0.90;
    };
    const isNearWhiteRow = (y) => {
      let wCnt = 0, tot = 0;
      for (let x = 8; x < aw - 8; x += 6) {
        const [r, g, b] = getPx(x, y);
        if (r > 245 && g > 245 && b > 245) wCnt++;
        tot++;
      }
      return (wCnt / Math.max(1, tot)) > 0.90;
    };
    while (trimLeft < 8 && isNearWhiteCol(trimLeft)) trimLeft++;
    while (trimRight > aw - 9 && isNearWhiteCol(trimRight)) trimRight--;
    while (trimTop < 6 && isNearWhiteRow(trimTop)) trimTop++;
    while (trimBot > ah - 7 && isNearWhiteRow(trimBot)) trimBot--;
  }

  // 2. Dominant smooth interior background cluster (prevents tiny borders from overriding black/cream canvas!)
  const buckets = new Map();
  let accentBest = { sat: 0, rgb: [180, 145, 72] };
  for (let y = trimTop + 2; y <= trimBot - 2; y += 2) {
    for (let x = trimLeft + 2; x <= trimRight - 2; x += 2) {
      const [r, g, b, a] = getPx(x, y);
      if (a < 200) continue;
      const [nr, ng, nb] = getPx(x + 1, y);
      const grad = Math.abs(r - nr) + Math.abs(g - ng) + Math.abs(b - nb);
      const isBorder = (y < trimTop + 12 || y > trimBot - 12 || x < trimLeft + 14 || x > trimRight - 14);
      const weight = (grad < 18 ? 4 : 1) * (isBorder ? 2.5 : 1);
      const key = `${r >> 4}_${g >> 4}_${b >> 4}`;
      const cur = buckets.get(key) || { w: 0, sr: 0, sg: 0, sb: 0 };
      cur.w += weight;
      cur.sr += r * weight;
      cur.sg += g * weight;
      cur.sb += b * weight;
      buckets.set(key, cur);

      const maxC = Math.max(r, g, b), minC = Math.min(r, g, b);
      const sat = maxC - minC;
      if (sat > accentBest.sat && maxC > 60 && maxC < 245) {
        accentBest = { sat, rgb: [r, g, b] };
      }
    }
  }

  let domBucket = { w: 1, sr: 250, sg: 248, sb: 241 };
  buckets.forEach((v) => { if (v.w > domBucket.w) domBucket = v; });
  const domRgb = [domBucket.sr / domBucket.w, domBucket.sg / domBucket.w, domBucket.sb / domBucket.w];
  const bgHex = _rgbToCss(domRgb[0], domRgb[1], domRgb[2]);

  // Sample top/bottom median interior strip colors in center third for gradient continuity
  const medianBandCss = (yStart, yEnd) => {
    let sr = 0, sg = 0, sb = 0, cnt = 0;
    for (let y = yStart; y <= yEnd; y++) {
      for (let x = Math.round(aw * 0.36); x <= Math.round(aw * 0.64); x += 3) {
        const [r, g, b] = getPx(x, y);
        const [nr, ng, nb] = getPx(x + 1, y);
        if (Math.abs(r - nr) + Math.abs(g - ng) + Math.abs(b - nb) < 25) {
          sr += r; sg += g; sb += b; cnt++;
        }
      }
    }
    return cnt > 3 ? _rgbToCss(sr / cnt, sg / cnt, sb / cnt) : bgHex;
  };
  const bgTop = medianBandCss(trimTop + 2, trimTop + 7);
  const bgBot = medianBandCss(trimBot - 7, trimBot - 2);
  const accentCss = _rgbToCss(accentBest.rgb[0], accentBest.rgb[1], accentBest.rgb[2]);

  // 3. Smart vertical gutter/divider detection for 3-panel labels
  const findColMin = (x0Frac, x1Frac, fallbackFrac) => {
    const x0 = Math.round(aw * x0Frac);
    const x1 = Math.round(aw * x1Frac);
    let bestX = Math.round(aw * fallbackFrac);
    let bestScore = Infinity;
    for (let x = x0; x <= x1; x++) {
      let fgEnergy = 0;
      for (let y = trimTop + 6; y <= trimBot - 6; y += 2) {
        const [r, g, b] = getPx(x, y);
        const diff = Math.abs(r - domRgb[0]) + Math.abs(g - domRgb[1]) + Math.abs(b - domRgb[2]);
        if (diff > 32) fgEnergy += 1;
        // Prefer columns that act as a vertical boundary next to smooth background
        const [lr, lg, lb] = getPx(x - 1, y);
        const [rr, rg, rb] = getPx(x + 1, y);
        fgEnergy += 0.15 * (Math.abs(lr - rr) + Math.abs(lg - rg) + Math.abs(lb - rb)) / 255;
      }
      if (fgEnergy < bestScore) {
        bestScore = fgEnergy;
        bestX = x;
      }
    }
    return bestX / aw;
  };

  let splitL = findColMin(0.25, 0.36, 0.31);
  let splitR = findColMin(0.64, 0.75, 0.69);
  if (splitR - splitL < 0.28) { splitL = 0.31; splitR = 0.69; }

  // 4. Inspect Fabric.js live objects (when editable layers exist) to ensure HERO panel maps to FRONT!
  let heroSlot = 'center';
  if (canvaCanvas && typeof canvaCanvas.getObjects === 'function') {
    const objs = canvaCanvas.getObjects().filter(o => o.visible !== false && !o.isGuideLine && !o.excludeFromExport);
    if (objs.length >= 4) {
      const cw = canvaCanvas._logicalWidth || 1536;
      const scores = { left: 0, center: 0, right: 0 };
      objs.forEach(o => {
        const br = o.getBoundingRect ? o.getBoundingRect(true) : { left: o.left || 0, width: o.width || 0 };
        const cxFrac = (br.left + br.width * 0.5) / Math.max(1, cw);
        const bucket = cxFrac < splitL ? 'left' : (cxFrac > splitR ? 'right' : 'center');
        if (o.isBrandLogo || o.assetType === 'brand_logo') scores[bucket] += 120;
        else if ((o.fontSize || 0) >= 34) scores[bucket] += (o.fontSize || 34) * 2.2;
        else if (o.type === 'image' && (br.width / Math.max(1, cw)) < 0.45) scores[bucket] += 40;
      });
      if (scores.left > scores.center + 30 && scores.left > scores.right + 30) heroSlot = 'left';
      else if (scores.right > scores.center + 30 && scores.right > scores.left + 30) heroSlot = 'right';
    }
  }

  return {
    analysisCanvas: ac,
    aw, ah,
    data,
    trimFrac: {
      l: trimLeft / aw,
      r: (trimRight + 1) / aw,
      t: trimTop / ah,
      b: (trimBot + 1) / ah,
    },
    splitL,
    splitR,
    heroSlot,
    domRgb,
    bgHex,
    bgTop,
    bgBot,
    accentCss,
    isDarkTheme: _rgbLuminance(domRgb[0], domRgb[1], domRgb[2]) < 110,
  };
}

function _extractPanelSections(layout, x0Frac, x1Frac) {
  const { aw, ah, data, domRgb, trimFrac } = layout;
  const x0 = Math.max(1, Math.round(aw * x0Frac));
  const x1 = Math.min(aw - 2, Math.round(aw * x1Frac));
  const yTopPx = Math.max(1, Math.round(ah * trimFrac.t));
  const yBotPx = Math.min(ah - 2, Math.round(ah * trimFrac.b));

  // Scan foreground ink ratio per horizontal row
  const rowFg = new Float32Array(ah);
  for (let y = yTopPx; y <= yBotPx; y++) {
    let fg = 0, tot = 0;
    for (let x = x0; x <= x1; x++) {
      const i = (y * aw + x) * 4;
      const diff = Math.abs(data[i] - domRgb[0]) + Math.abs(data[i + 1] - domRgb[1]) + Math.abs(data[i + 2] - domRgb[2]);
      if (diff > 28) fg++;
      tot++;
    }
    rowFg[y] = fg / Math.max(1, tot);
  }

  // Locate clean horizontal divider gaps (minimum spacing >= 14% of height so no text line gets sliced)
  const splitFracs = [trimFrac.t];
  let lastSplitY = yTopPx;
  const minGapRows = Math.max(12, Math.round(ah * 0.16));

  for (let y = yTopPx + minGapRows; y <= yBotPx - minGapRows; y++) {
    if (rowFg[y] < 0.10 && (y - lastSplitY) >= minGapRows) {
      // Advance to the center of the clean horizontal gap run
      let endRun = y;
      while (endRun < yBotPx - minGapRows && rowFg[endRun + 1] < 0.10) endRun++;
      const midGap = Math.round((y + endRun) * 0.5);
      splitFracs.push(midGap / ah);
      lastSplitY = midGap;
      y = endRun + minGapRows;
    }
  }
  splitFracs.push(trimFrac.b);

  // Build bounding-trimmed sub-sections
  const sections = [];
  for (let k = 0; k < splitFracs.length - 1; k++) {
    const ya = splitFracs[k];
    const yb = splitFracs[k + 1];
    // Trim blank outer horizontal margin inside each section so text fills 94-96% of column width
    const yStartPx = Math.round(ya * ah), yEndPx = Math.round(yb * ah);
    let lx0 = x0, lx1 = x1;
    while (lx0 < x1 - 4) {
      let colInk = 0;
      for (let yy = yStartPx; yy <= yEndPx; yy++) {
        const i = (yy * aw + lx0) * 4;
        if (Math.abs(data[i] - domRgb[0]) + Math.abs(data[i + 1] - domRgb[1]) + Math.abs(data[i + 2] - domRgb[2]) > 26) colInk++;
      }
      if (colInk / Math.max(1, yEndPx - yStartPx) > 0.08) break;
      lx0++;
    }
    while (lx1 > lx0 + 4) {
      let colInk = 0;
      for (let yy = yStartPx; yy <= yEndPx; yy++) {
        const i = (yy * aw + lx1) * 4;
        if (Math.abs(data[i] - domRgb[0]) + Math.abs(data[i + 1] - domRgb[1]) + Math.abs(data[i + 2] - domRgb[2]) > 26) colInk++;
      }
      if (colInk / Math.max(1, yEndPx - yStartPx) > 0.08) break;
      lx1--;
    }
    const padX = 1 / aw;
    const fx0 = Math.max(x0Frac, (lx0 / aw) - padX);
    const fx1 = Math.min(x1Frac, ((lx1 + 1) / aw) + padX);
    if ((yb - ya) > 0.08 && (fx1 - fx0) > 0.06) {
      sections.push({ x0Frac: fx0, x1Frac: fx1, y0Frac: ya, y1Frac: yb });
    }
  }
  return sections.length ? sections : [{ x0Frac, x1Frac, y0Frac: trimFrac.t, y1Frac: trimFrac.b }];
}

function _makeCanvasTex(canvasEl) {
  const t = new THREE.CanvasTexture(canvasEl);
  t.encoding = THREE.sRGBEncoding;
  t.flipY = false;
  t.wrapS = THREE.ClampToEdgeWrapping;
  t.wrapT = THREE.ClampToEdgeWrapping;
  t.anisotropy = 8;
  t.needsUpdate = true;
  return t;
}

function _drawSeamlessEdgeExtendedRegion(ctx, tw, th, img, sx, sy, sw, sh, layout, dx, dy, dw, dh) {
  const grad = ctx.createLinearGradient(0, 0, 0, th);
  grad.addColorStop(0, layout.bgTop || layout.bgHex);
  grad.addColorStop(0.5, layout.bgHex);
  grad.addColorStop(1, layout.bgBot || layout.bgHex);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, tw, th);

  const eY = Math.max(2, Math.round(sh * 0.025));
  const eX = Math.max(2, Math.round(sw * 0.025));
  try {
    if (dy > 0) ctx.drawImage(img, sx, sy, sw, eY, dx, 0, dw, dy + 2);
    if (dy + dh < th) ctx.drawImage(img, sx, sy + sh - eY, sw, eY, dx, dy + dh - 2, dw, th - (dy + dh) + 2);
    if (dx > 0) ctx.drawImage(img, sx, sy, eX, sh, 0, dy, dx + 2, dh);
    if (dx + dw < tw) ctx.drawImage(img, sx + sw - eX, sy, eX, sh, dx + dw - 2, dy, tw - (dx + dw) + 2, dh);
  } catch (_) { }

  ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh);
}

function _drawFullWidthPreservedRegion(ctx, tw, th, img, sx, sy, sw, sh, layout, topPad = 0, botPad = 0, sidePadFrac = 0.025) {
  const availW = Math.max(40, tw * (1.0 - sidePadFrac * 2));
  const availH = Math.max(40, th * (1.0 - topPad - botPad));
  const scale = Math.min(availW / sw, availH / sh);
  const dw = sw * scale;
  const dh = sh * scale;
  const dx = (tw - dw) * 0.5;
  const dy = th * topPad + (availH - dh) * 0.5;
  _drawSeamlessEdgeExtendedRegion(ctx, tw, th, img, sx, sy, sw, sh, layout, dx, dy, dw, dh);
}

function _drawSectionsIntoColumn(ctx, img, sections, colX, colW, colY, colH, gapY) {
  const swImg = img.naturalWidth || img.width;
  const shImg = img.naturalHeight || img.height;
  const natH = sections.map(b => colW * ((b.y1Frac - b.y0Frac) * shImg) / Math.max(1, (b.x1Frac - b.x0Frac) * swImg));
  const totH = natH.reduce((a, b) => a + b, 0) + gapY * Math.max(0, sections.length - 1);
  const scale = totH > colH ? (colH / totH) : 1.0;

  let curY = colY + Math.max(0, (colH - totH * scale) * 0.5);
  sections.forEach((b, idx) => {
    const sx = Math.round(swImg * b.x0Frac);
    const sw = Math.max(8, Math.round(swImg * (b.x1Frac - b.x0Frac)));
    const sy = Math.round(shImg * b.y0Frac);
    const sh = Math.max(8, Math.round(shImg * (b.y1Frac - b.y0Frac)));
    const dw = Math.round(colW * scale);
    const dh = Math.round(natH[idx] * scale);
    const dx = Math.round(colX + (colW - dw) * 0.5);
    ctx.drawImage(img, sx, sy, sw, sh, dx, Math.round(curY), dw, dh);
    curY += dh + gapY * scale;
  });
  return scale;
}

function _buildSmartBackCanvas(img, tw, th, panels, layout, topPad = 0.06, botPad = 0.04) {
  const c = document.createElement('canvas');
  c.width = tw; c.height = th;
  const ctx = c.getContext('2d');
  const swImg = img.naturalWidth || img.width;
  const shImg = img.naturalHeight || img.height;

  const grad = ctx.createLinearGradient(0, 0, 0, th);
  grad.addColorStop(0, layout.bgTop || layout.bgHex);
  grad.addColorStop(0.5, layout.bgHex);
  grad.addColorStop(1, layout.bgBot || layout.bgHex);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, tw, th);

  const padX = Math.round(tw * 0.03); // ~2.5-3mm equivalent safe side margin -> 94% usable width!
  const innerW = tw - padX * 2;
  const usableY = Math.round(th * topPad);
  const usableH = Math.round(th * (1.0 - topPad - botPad));
  const gapY = Math.round(th * 0.015);
  const gapCol = Math.round(tw * 0.025);

  const groupedSections = panels.map(p => _extractPanelSections(layout, p.x0Frac, p.x1Frac));
  const allSections = groupedSections.flat();

  // Compute total height if stacked at full 94% printable width
  const natSingleH = allSections.map(b => innerW * ((b.y1Frac - b.y0Frac) * shImg) / Math.max(1, (b.x1Frac - b.x0Frac) * swImg));
  const singleSumH = natSingleH.reduce((a, b) => a + b, 0) + gapY * Math.max(0, allSections.length - 1);

  if (singleSumH <= usableH * 1.12 || panels.length === 1) {
    // 1-Column Full-Width Reflow (occupies ~90-94% printable width without narrow strip shrinking!)
    _drawSectionsIntoColumn(ctx, img, allSections, padX, innerW, usableY, usableH, gapY);
  } else if (allSections.length >= 2 && (natSingleH[0] < usableH * 0.44)) {
    // Hybrid Editorial Reflow: Full-Width Top Nutrition Banner (94% width) + Balanced 2-Column Info Grid below (94% total width!)
    const topBanner = allSections[0];
    const bannerH = Math.round(natSingleH[0]);
    const sx0 = Math.round(swImg * topBanner.x0Frac);
    const sw0 = Math.max(8, Math.round(swImg * (topBanner.x1Frac - topBanner.x0Frac)));
    const sy0 = Math.round(shImg * topBanner.y0Frac);
    const sh0 = Math.max(8, Math.round(shImg * (topBanner.y1Frac - topBanner.y0Frac)));
    ctx.drawImage(img, sx0, sy0, sw0, sh0, padX, usableY, innerW, bannerH);

    const rest = allSections.slice(1);
    const col1 = [], col2 = [];
    let h1 = 0, h2 = 0;
    const colW = Math.floor((innerW - gapCol) * 0.5);
    rest.forEach((b) => {
      const bh = colW * ((b.y1Frac - b.y0Frac) * shImg) / Math.max(1, (b.x1Frac - b.x0Frac) * swImg);
      if (h1 <= h2) { col1.push(b); h1 += bh; }
      else { col2.push(b); h2 += bh; }
    });
    const remY = usableY + bannerH + gapY;
    const remH = usableH - bannerH - gapY;
    if (col1.length) _drawSectionsIntoColumn(ctx, img, col1, padX, colW, remY, remH, gapY);
    if (col2.length) _drawSectionsIntoColumn(ctx, img, col2, padX + colW + gapCol, colW, remY, remH, gapY);
  } else {
    // 2-Column Commercial Back Layout (94% total width across Left + Right columns)
    const colW = Math.floor((innerW - gapCol) * 0.5);
    const colLeft = groupedSections[0] || allSections.slice(0, Math.ceil(allSections.length / 2));
    const colRight = groupedSections[1] || allSections.slice(Math.ceil(allSections.length / 2));
    _drawSectionsIntoColumn(ctx, img, colLeft, padX, colW, usableY, usableH, gapY);
    if (colRight.length) {
      _drawSectionsIntoColumn(ctx, img, colRight, padX + colW + gapCol, colW, usableY, usableH, gapY);
    }
  }
  return c;
}

function _buildBoxFlapCanvas(img, tw, th, layout, isTop = true, heroRegion = null) {
  const c = document.createElement('canvas');
  c.width = tw; c.height = th;
  const ctx = c.getContext('2d');
  const sw = img.naturalWidth || img.width;
  const sh = img.naturalHeight || img.height;

  const grad = ctx.createLinearGradient(0, 0, tw, th);
  grad.addColorStop(0, layout.bgTop || layout.bgHex);
  grad.addColorStop(1, layout.bgBot || layout.bgHex);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, tw, th);

  ctx.fillStyle = layout.accentCss || '#C9A44C';
  ctx.globalAlpha = layout.isDarkTheme ? 0.35 : 0.22;
  ctx.fillRect(0, isTop ? 0 : th - Math.round(th * 0.12), tw, Math.round(th * 0.12));
  ctx.globalAlpha = 1.0;

  if (isTop && heroRegion) {
    const crestSx = Math.round(sw * (heroRegion.x0Frac + (heroRegion.x1Frac - heroRegion.x0Frac) * 0.14));
    const crestSw = Math.round(sw * (heroRegion.x1Frac - heroRegion.x0Frac) * 0.72);
    const crestSy = Math.round(sh * layout.trimFrac.t);
    const { aw, ah, data, domRgb } = layout;
    const gx0 = Math.max(1, Math.round(aw * (heroRegion.x0Frac + 0.04)));
    const gx1 = Math.min(aw - 2, Math.round(aw * (heroRegion.x1Frac - 0.04)));
    let bestEndFrac = 0.18, bestRatio = 1.0;
    for (let y = Math.round(ah * 0.12); y <= Math.round(ah * 0.26); y++) {
      let fg = 0, tot = 0;
      for (let x = gx0; x <= gx1; x++) {
        const i = (y * aw + x) * 4;
        if (Math.abs(data[i] - domRgb[0]) + Math.abs(data[i + 1] - domRgb[1]) + Math.abs(data[i + 2] - domRgb[2]) > 28) fg++;
        tot++;
      }
      const r = fg / Math.max(1, tot);
      if (r < bestRatio) { bestRatio = r; bestEndFrac = y / ah; }
    }
    const crestEndY = Math.round(sh * (bestRatio < 0.12 ? bestEndFrac : 0.18));
    const crestSh = Math.max(16, crestEndY - crestSy);
    const scale = Math.min((tw * 0.66) / crestSw, (th * 0.44) / crestSh);
    const dw = crestSw * scale, dh = crestSh * scale;
    ctx.drawImage(img, crestSx, crestSy, crestSw, crestSh, (tw - dw) * 0.5, (th - dh) * 0.5, dw, dh);
  }

  ctx.strokeStyle = layout.isDarkTheme ? 'rgba(220, 195, 120, 0.28)' : 'rgba(32, 40, 32, 0.16)';
  ctx.lineWidth = 2;
  ctx.strokeRect(10, 10, tw - 20, th - 20);
  return c;
}

function _buildSolidSubstrateCanvas(hexColor, w = 256, h = 256) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  ctx.fillStyle = hexColor;
  ctx.fillRect(0, 0, w, h);
  return c;
}

function _syncSealRimSubstrate(catId, layout) {
  if (catId === 'jar' || catId === 'bottle') return;
  const hexOrRgb = layout.bgHex || threeBodyColorHex;
  const lin = _makeSrgbColor(hexOrRgb);
  threeBodyMeshes.forEach((m) => {
    if (m.material && m.material.color) m.material.color.copy(lin);
  });
}

let _diagnosticUvEnabled = false;

function _buildUvDiagnosticCanvas(labelName, colorHex, w = 512, h = 768) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  ctx.fillStyle = colorHex;
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = '#FFFFFF';
  ctx.lineWidth = 10;
  ctx.strokeRect(5, 5, w - 10, h - 10);
  ctx.strokeStyle = 'rgba(255,255,255,0.28)';
  ctx.lineWidth = 1;
  for (let gx = 64; gx < w; gx += 64) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, h); ctx.stroke(); }
  for (let gy = 64; gy < h; gy += 64) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke(); }
  ctx.fillStyle = '#FFFFFF';
  ctx.textAlign = 'center';
  ctx.font = 'bold 54px sans-serif';
  ctx.fillText(labelName, w * 0.5, h * 0.45);
  ctx.font = 'bold 34px sans-serif';
  ctx.fillText('TOP UP (0,0) -> (1,1)', w * 0.5, h * 0.58);
  return c;
}

function _setDiagnosticUvMode(enabled) {
  _diagnosticUvEnabled = Boolean(enabled);
  updateThreeLabelTextureFromCanvas(true);
}

function buildSurfaceTextureMap(img, catId, preset) {
  if (_diagnosticUvEnabled) {
    const out = {
      cylinder: _makeCanvasTex(_buildUvDiagnosticCanvas('CYLINDER 360', '#1D4ED8', 1024, 512)),
      front: _makeCanvasTex(_buildUvDiagnosticCanvas('FRONT (+Z)', '#166534')),
      back: _makeCanvasTex(_buildUvDiagnosticCanvas('BACK (-Z)', '#991B1B')),
      left: _makeCanvasTex(_buildUvDiagnosticCanvas('LEFT (-X)', '#9A3412', 420, 768)),
      right: _makeCanvasTex(_buildUvDiagnosticCanvas('RIGHT (+X)', '#6B21A8', 420, 768)),
      top: _makeCanvasTex(_buildUvDiagnosticCanvas('TOP (+Y)', '#0F766E', 512, 420)),
      bottom: _makeCanvasTex(_buildUvDiagnosticCanvas('BOTTOM (-Y)', '#334155', 512, 420)),
      gusset: _makeCanvasTex(_buildUvDiagnosticCanvas('GUSSET', '#475569', 512, 256)),
    };
    threeLabelTexture = out.front;
    return out;
  }

  const sw = img.naturalWidth || img.width || 1536;
  const sh = img.naturalHeight || img.height || 512;
  const artAspect = sw / Math.max(1, sh);
  const outTextures = {};

  if (catId === 'jar' || catId === 'bottle') {
    const tex = new THREE.Texture(img);
    tex.encoding = THREE.sRGBEncoding;
    tex.flipY = false;
    tex.wrapS = THREE.ClampToEdgeWrapping;
    tex.wrapT = THREE.ClampToEdgeWrapping;
    tex.anisotropy = 8;
    tex.needsUpdate = true;
    outTextures.cylinder = tex;
    threeLabelTexture = tex;
    return outTextures;
  }

  const layout = analyzeArtworkLayout(img);
  _syncSealRimSubstrate(catId, layout);

  const pw = preset?.w || 110;
  const ph = preset?.h || 170;
  const pd = preset?.depth || 60;
  const targetRatio = pw / Math.max(1, ph);
  // Derive high-clarity texture resolution proportional to physical packaging size
  const surfH = ph >= 240 ? 1792 : 1440;
  const surfW = Math.min(1600, Math.max(540, Math.round(surfH * targetRatio)));
  const sideW = Math.min(1280, Math.max(480, Math.round(surfH * (pd / Math.max(1, ph)))));
  const topW = 1024;
  const topH = Math.min(1024, Math.max(480, Math.round(topW * (pd / Math.max(1, pw)))));

  const isPouch = (catId === 'pouch');
  const isSachet = (catId === 'sachet');
  const frontTopPad = isPouch ? 0.10 : (isSachet ? 0.08 : 0.02);
  const frontBotPad = isPouch ? 0.04 : (isSachet ? 0.08 : 0.02);
  const backTopPad = isPouch ? 0.11 : (isSachet ? 0.085 : 0.025);
  const backBotPad = isPouch ? 0.045 : (isSachet ? 0.085 : 0.025);

  const syT = Math.round(sh * layout.trimFrac.t);
  const syH = Math.max(16, Math.round(sh * (layout.trimFrac.b - layout.trimFrac.t)));

  if (artAspect >= 3.4 && catId === 'box') {
    const q = Math.floor(sw * 0.25);
    const makePanel = (sx, wBox, hBox) => {
      const c = document.createElement('canvas'); c.width = wBox; c.height = hBox;
      _drawFullWidthPreservedRegion(c.getContext('2d'), wBox, hBox, img, sx, syT, q, syH, layout, 0.02, 0.02, 0.02);
      return _makeCanvasTex(c);
    };
    outTextures.left = makePanel(0, sideW, surfH);
    outTextures.front = makePanel(q, surfW, surfH);
    outTextures.right = makePanel(q * 2, sideW, surfH);
    outTextures.back = makePanel(q * 3, surfW, surfH);
    outTextures.top = _makeCanvasTex(_buildBoxFlapCanvas(img, topW, topH, layout, true, { x0Frac: 0.25, x1Frac: 0.50 }));
    outTextures.bottom = _makeCanvasTex(_buildBoxFlapCanvas(img, topW, topH, layout, false, null));
  } else if (artAspect >= 2.0) {
    const panelsByKey = {
      left: { x0Frac: layout.trimFrac.l, x1Frac: layout.splitL },
      center: { x0Frac: layout.splitL, x1Frac: layout.splitR },
      right: { x0Frac: layout.splitR, x1Frac: layout.trimFrac.r },
    };
    const heroPanel = panelsByKey[layout.heroSlot] || panelsByKey.center;
    const infoPanels = ['left', 'center', 'right'].filter(k => k !== layout.heroSlot).map(k => panelsByKey[k]);

    // Trimmed Front Hero bounds (removes white side margin so branding hits ~94% usable width!)
    const heroSections = _extractPanelSections(layout, heroPanel.x0Frac, heroPanel.x1Frac);
    const hX0 = Math.min(...heroSections.map(s => s.x0Frac));
    const hX1 = Math.max(...heroSections.map(s => s.x1Frac));

    const fc = document.createElement('canvas');
    fc.width = surfW; fc.height = surfH;
    _drawFullWidthPreservedRegion(fc.getContext('2d'), surfW, surfH, img, Math.round(sw * hX0), syT, Math.max(16, Math.round(sw * (hX1 - hX0))), syH, layout, frontTopPad, frontBotPad, 0.025);
    outTextures.front = _makeCanvasTex(fc);

    if (catId === 'box') {
      // Box Rule (Req 10): ZERO duplicated nutrition across faces!
      // Back = Info Panel 0 (Nutrition/Ingredients/Description/Usage) full-width
      // Left & Right = Sub-sections from Info Panel 1 (Left = Benefits, Right = Manufacturer/Batch/FSSAI)
      const pInfo0 = infoPanels[0] || panelsByKey.left;
      const pInfo1 = infoPanels[1] || panelsByKey.right;
      const bc = _buildSmartBackCanvas(img, surfW, surfH, [pInfo0], layout, backTopPad, backBotPad);
      outTextures.back = _makeCanvasTex(bc);

      const rightSections = _extractPanelSections(layout, pInfo1.x0Frac, pInfo1.x1Frac);
      const makeBoxSideFromSections = (secs) => {
        const sc = document.createElement('canvas');
        sc.width = sideW; sc.height = surfH;
        const sctx = sc.getContext('2d');
        const g = sctx.createLinearGradient(0, 0, 0, surfH);
        g.addColorStop(0, layout.bgTop || layout.bgHex);
        g.addColorStop(1, layout.bgBot || layout.bgHex);
        sctx.fillStyle = g;
        sctx.fillRect(0, 0, sideW, surfH);
        _drawSectionsIntoColumn(sctx, img, secs, Math.round(sideW * 0.04), Math.round(sideW * 0.92), Math.round(surfH * 0.04), Math.round(surfH * 0.92), Math.round(surfH * 0.02));
        return _makeCanvasTex(sc);
      };

      if (rightSections.length >= 2) {
        const mid = Math.ceil(rightSections.length * 0.5);
        outTextures.left = makeBoxSideFromSections(rightSections.slice(0, mid));
        outTextures.right = makeBoxSideFromSections(rightSections.slice(mid));
      } else {
        // Fallback if Right panel is 1 indivisible block: Benefits/Right on Right, Logo/Clean Complementary panel on Left
        outTextures.right = makeBoxSideFromSections(rightSections);
        outTextures.left = _makeCanvasTex(_buildBoxFlapCanvas(img, sideW, surfH, layout, false, null));
      }
      outTextures.top = _makeCanvasTex(_buildBoxFlapCanvas(img, topW, topH, layout, true, heroPanel));
      outTextures.bottom = _makeCanvasTex(_buildBoxFlapCanvas(img, topW, topH, layout, false, null));
    } else {
      // Sachet & Pouch: Full-width adaptive multi-column / hybrid Backside reflow of ALL info blocks!
      const bc = _buildSmartBackCanvas(img, surfW, surfH, infoPanels, layout, backTopPad, backBotPad);
      outTextures.back = _makeCanvasTex(bc);
      if (isPouch) {
        outTextures.gusset = _makeCanvasTex(_buildSolidSubstrateCanvas(layout.bgBot || layout.bgHex, 256, 256));
      }
    }
  } else if (artAspect >= 1.30) {
    const halfW = Math.floor(sw * 0.5);
    const makeHalf = (sx, topP, botP) => {
      const c = document.createElement('canvas'); c.width = surfW; c.height = surfH;
      _drawFullWidthPreservedRegion(c.getContext('2d'), surfW, surfH, img, sx, syT, halfW, syH, layout, topP, botP, 0.025);
      return _makeCanvasTex(c);
    };
    outTextures.front = makeHalf(0, frontTopPad, frontBotPad);
    outTextures.back = makeHalf(halfW, backTopPad, backBotPad);
    if (isPouch) outTextures.gusset = _makeCanvasTex(_buildSolidSubstrateCanvas(layout.bgBot || layout.bgHex));
    if (catId === 'box') {
      outTextures.left = _makeCanvasTex(_buildBoxFlapCanvas(img, sideW, surfH, layout, false, null));
      outTextures.right = _makeCanvasTex(_buildBoxFlapCanvas(img, sideW, surfH, layout, false, null));
      outTextures.top = _makeCanvasTex(_buildBoxFlapCanvas(img, topW, topH, layout, true, { x0Frac: 0.05, x1Frac: 0.45 }));
      outTextures.bottom = _makeCanvasTex(_buildBoxFlapCanvas(img, topW, topH, layout, false, null));
    }
  } else {
    const fc = document.createElement('canvas');
    fc.width = surfW; fc.height = surfH;
    const fSx = Math.round(sw * layout.trimFrac.l);
    const fSw = Math.max(16, Math.round(sw * (layout.trimFrac.r - layout.trimFrac.l)));
    _drawFullWidthPreservedRegion(fc.getContext('2d'), surfW, surfH, img, fSx, syT, fSw, syH, layout, frontTopPad, frontBotPad, 0.025);
    outTextures.front = _makeCanvasTex(fc);

    const subCol = layout.bgHex || threeBodyColorHex;
    outTextures.back = _makeCanvasTex(_buildSolidSubstrateCanvas(subCol));
    if (isPouch) outTextures.gusset = _makeCanvasTex(_buildSolidSubstrateCanvas(subCol));
    if (catId === 'box') {
      outTextures.left = _makeCanvasTex(_buildSolidSubstrateCanvas(subCol));
      outTextures.right = _makeCanvasTex(_buildSolidSubstrateCanvas(subCol));
      outTextures.top = _makeCanvasTex(_buildSolidSubstrateCanvas(subCol));
      outTextures.bottom = _makeCanvasTex(_buildSolidSubstrateCanvas(subCol));
    }
    const sig = `${catId}_${sw}x${sh}`;
    if (_lastFrontOnlyToastSig !== sig) {
      _lastFrontOnlyToastSig = sig;
      if (typeof showToast === 'function') {
        showToast('Front-only design detected: back/side surfaces preserve artwork substrate (no back artwork supplied).', 'info', 3400);
      }
    }
  }

  threeLabelTexture = outTextures.front || outTextures.cylinder || null;
  return outTextures;
}

function updateThreeLabelTextureFromCanvas(immediate = false) {
  if (!isLiveSyncEnabled || !canvaCanvas || !threeLabelMeshes.length) return;
  if (!immediate) {
    clearTimeout(_syncTexTimer);
    _syncTexTimer = setTimeout(() => updateThreeLabelTextureFromCanvas(true), 60);
    return;
  }
  if (typeof getCleanCanvasDataURL !== 'function') return;
  const cleanUrl = getCleanCanvasDataURL(1);
  if (!cleanUrl) return;

  const targetCatAtReq = currentPackagingCat;
  const targetPresetAtReq = currentPackagingPreset;
  const cat = packagingManifest?.categories?.find(c => c.id === targetCatAtReq);
  const preset = cat?.presets?.find(p => p.id === targetPresetAtReq) || cat?.presets?.[0];

  const img = new Image();
  img.onload = () => {
    if (currentPackagingCat !== targetCatAtReq) return;
    const prevMap = { ...threeSurfaceTextures };
    const newMap = buildSurfaceTextureMap(img, targetCatAtReq, preset);
    threeSurfaceTextures = newMap;

    threeLabelMeshes.forEach(mesh => {
      if (!mesh.material) return;
      const slot = mesh.userData?.surfaceSlot || 'front';
      const tex = newMap[slot] || newMap.front || newMap.cylinder || null;
      mesh.material.map = tex;
      mesh.material.needsUpdate = true;
    });

    const newSet = new Set(Object.values(newMap));
    Object.values(prevMap).forEach(oldTex => {
      if (oldTex && !newSet.has(oldTex) && typeof oldTex.dispose === 'function') oldTex.dispose();
    });
  };
  img.src = cleanUrl;
}

function applyPbrMaterialFinish(finishId) {
  currentPbrFinish = finishId;
  if (!threeCategoryColorState[currentPackagingCat]) {
    threeCategoryColorState[currentPackagingCat] = { ...(CATEGORY_DEFAULTS[currentPackagingCat] || { body: threeBodyColorHex, lid: threeLidColorHex, finish: finishId }) };
  }
  threeCategoryColorState[currentPackagingCat].finish = finishId;

  const cfg = getMaterialConfig(finishId);
  const isFoilFinish = (cfg.id || '').includes('foil');
  const isGlossFinish = (cfg.id === 'glossy' || cfg.id === 'satin');
  const isFoilCat = (currentPackagingCat === 'sachet' || isFoilFinish);
  const isJarOrBottle = (currentPackagingCat === 'jar' || currentPackagingCat === 'bottle');
  const surfNMap = _normalMapForMaterial(cfg, true, false);
  const plasticNMap = isJarOrBottle ? _normalMapForMaterial(cfg, false, true) : surfNMap;
  const bodyPlasticScale = isJarOrBottle ? _buildPlasticScale(cfg, false) : (surfNMap ? 0.18 : 0);
  const lidPlasticScale = isJarOrBottle ? _buildPlasticScale(cfg, true) : 0;

  threeBodyMeshes.forEach(m => {
    if (!m.material) return;
    const mName = (m.name || '').toLowerCase();
    const isSealOrCarton = (mName === 'sealmaterial' || mName.includes('sealrim') || mName === 'cartonbody');
    const isNeckRecess = isJarOrBottle && mName.includes('neck');
    if (isJarOrBottle && !isSealOrCarton) {
      m.material.roughness = isNeckRecess ? Math.min(0.82, (cfg.roughness ?? 0.6) + 0.12) : (isGlossFinish ? (cfg.roughness ?? 0.16) : Math.min(0.58, cfg.roughness ?? 0.54));
      m.material.clearcoat = isGlossFinish ? Math.max(0.75, cfg.clearcoat ?? 0.85) : (cfg.id === 'soft_touch' ? 0.0 : Math.max(0.12, cfg.clearcoat ?? 0.05));
      m.material.clearcoatRoughness = isGlossFinish ? 0.14 : 0.38;
      m.material.envMapIntensity = isNeckRecess ? 0.42 : 0.64;
      m.material.normalMap = plasticNMap;
      if (m.material.normalScale) m.material.normalScale.set(plasticNMap ? bodyPlasticScale : 0, plasticNMap ? bodyPlasticScale : 0);
    } else {
      m.material.roughness = cfg.roughness ?? 0.6;
      m.material.clearcoat = cfg.clearcoat ?? 0.05;
      m.material.normalMap = surfNMap;
      if (m.material.normalScale) m.material.normalScale.set(surfNMap ? 0.18 : 0, surfNMap ? 0.18 : 0);
    }
    m.material.metalness = isFoilCat ? Math.max(0.75, cfg.metalness ?? 0.85) : (cfg.metalness ?? 0.02);
    m.material.transparent = Boolean(cfg.transmission);
    m.material.opacity = cfg.transmission ? (cfg.opacity ?? 0.65) : 1.0;
    m.material.needsUpdate = true;
  });
  threeLidMeshes.forEach(m => {
    if (!m.material) return;
    if (isJarOrBottle) {
      m.material.roughness = isGlossFinish ? Math.max(0.14, cfg.roughness ?? 0.22) : Math.max(0.28, (cfg.roughness ?? 0.56) - 0.18);
      m.material.clearcoat = isGlossFinish ? Math.max(0.75, cfg.clearcoat ?? 0.85) : Math.max(0.22, (cfg.clearcoat ?? 0.08) + 0.16);
      m.material.clearcoatRoughness = isGlossFinish ? 0.14 : 0.28;
      m.material.envMapIntensity = 0.88;
      m.material.normalMap = plasticNMap;
      if (m.material.normalScale) m.material.normalScale.set(plasticNMap ? lidPlasticScale : 0, plasticNMap ? lidPlasticScale : 0);
    } else {
      m.material.roughness = Math.max(0.22, (cfg.roughness ?? 0.45) - 0.1);
      m.material.clearcoat = cfg.clearcoat ?? 0.08;
    }
    m.material.metalness = cfg.metalness ?? 0.04;
    m.material.needsUpdate = true;
  });
  threeLabelMeshes.forEach(m => {
    if (!m.material) return;
    m.material.roughness = isFoilFinish ? Math.max(0.20, (cfg.roughness || 0.30) * 0.92) : (isGlossFinish ? 0.22 : (isJarOrBottle ? 0.58 : 0.74));
    m.material.metalness = isFoilFinish ? Math.min(0.36, (cfg.metalness ?? 0.7) * 0.36) : (currentPackagingCat === 'sachet' ? 0.18 : 0.0);
    m.material.clearcoat = isFoilFinish ? 0.22 : (isGlossFinish ? 0.48 : (isJarOrBottle ? 0.08 : 0.03));
    m.material.clearcoatRoughness = isGlossFinish ? 0.16 : 0.40;
    m.material.envMapIntensity = isFoilFinish ? 0.58 : (isGlossFinish ? 0.50 : (isJarOrBottle ? 0.24 : 0.20));
    m.material.normalMap = surfNMap;
    if (m.material.normalScale) m.material.normalScale.set(surfNMap ? 0.14 : 0, surfNMap ? 0.14 : 0);
    m.material.needsUpdate = true;
  });
}

function applyStudioLightingPreset(presetId) {
  currentLightingPreset = presetId;
  document.querySelectorAll('.lighting-card-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-lighting') === presetId);
  });
  const sel = document.getElementById('threeSelectLighting');
  if (sel) sel.value = presetId;

  const p = packagingManifest?.lighting_presets?.find(x => x.id === presetId) || { key: '#ffffff', fill: '#e8edf2', rim: '#cbd5e1', keyInt: 1.15, fillInt: 0.72, env: 1.0 };
  if (threeKeyLight) { threeKeyLight.color.set(p.key); threeKeyLight.intensity = p.keyInt || 1.2; }
  if (threeFillLight) { threeFillLight.color.set(p.fill); threeFillLight.intensity = p.fillInt || 0.6; }
  if (threeRimLight) { threeRimLight.color.set(p.rim); }
  if (threeRenderer) threeRenderer.toneMappingExposure = p.env || 1.0;
}

function bindThreeControlListeners() {
  document.getElementById('threeLiveSyncToggle')?.addEventListener('change', (e) => {
    isLiveSyncEnabled = e.target.checked;
    if (isLiveSyncEnabled) updateThreeLabelTextureFromCanvas();
  });

  document.getElementById('threeSelectPreset')?.addEventListener('change', (e) => {
    currentPackagingPreset = e.target.value;
    loadPackagingGlbModel(currentPackagingCat, currentPackagingPreset);
  });

  document.getElementById('threeSelectMaterialFinish')?.addEventListener('change', (e) => {
    applyPbrMaterialFinish(e.target.value);
  });

  document.getElementById('threeBodyColorPicker')?.addEventListener('input', (e) => {
    threeBodyColorHex = e.target.value;
    if (threeCategoryColorState[currentPackagingCat]) threeCategoryColorState[currentPackagingCat].body = threeBodyColorHex;
    const boxEl = document.getElementById('threeBodyColorBox');
    if (boxEl) boxEl.style.background = threeBodyColorHex;
    const lin = _makeSrgbColor(threeBodyColorHex);
    threeBodyMeshes.forEach(m => { if (m.material) m.material.color.copy(lin); });
  });

  document.getElementById('threeLidColorPicker')?.addEventListener('input', (e) => {
    threeLidColorHex = e.target.value;
    if (threeCategoryColorState[currentPackagingCat]) threeCategoryColorState[currentPackagingCat].lid = threeLidColorHex;
    const boxEl = document.getElementById('threeLidColorBox');
    if (boxEl) boxEl.style.background = threeLidColorHex;
    const lin = _makeSrgbColor(threeLidColorHex);
    threeLidMeshes.forEach(m => { if (m.material) m.material.color.copy(lin); });
  });

  // View Angles + 360 Spin
  function setAngle(btnId, rx, ry) {
    isAutoSpinning = false;
    document.querySelectorAll('.view-angle-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(btnId)?.classList.add('active');
    if (threeJarGroup) { threeJarGroup.rotation.set(rx, ry, 0); }
    fitCameraToModel();
  }
  document.getElementById('btnViewFront')?.addEventListener('click', () => setAngle('btnViewFront', 0, 0));
  document.getElementById('btnViewBack')?.addEventListener('click', () => setAngle('btnViewBack', 0, Math.PI));
  document.getElementById('btnViewLeft')?.addEventListener('click', () => setAngle('btnViewLeft', 0, Math.PI / 2));
  document.getElementById('btnViewSide')?.addEventListener('click', () => setAngle('btnViewSide', 0, -Math.PI / 2));
  document.getElementById('btnViewTop')?.addEventListener('click', () => setAngle('btnViewTop', 1.05, 0));
  document.getElementById('canvaAutoSpinBtn')?.addEventListener('click', () => {
    isAutoSpinning = !isAutoSpinning;
    document.querySelectorAll('.view-angle-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('canvaAutoSpinBtn')?.classList.toggle('active', isAutoSpinning);
  });

  // Viewport overlay buttons
  document.getElementById('threeResetCameraBtn')?.addEventListener('click', () => {
    const defRot = currentPackagingCat === 'box' ? -0.35 : (currentPackagingCat === 'pouch' || currentPackagingCat === 'sachet' ? 0.14 : 0);
    setAngle('btnViewFront', 0, defRot);
  });
  document.getElementById('threeQuickSnapshotBtn')?.addEventListener('click', () => export3DMockup('png_transparent', 2048));
  document.getElementById('threeFullscreenBtn')?.addEventListener('click', () => {
    const el = document.getElementById('threeStageWrapper');
    if (el?.requestFullscreen) el.requestFullscreen();
  });
  window.addEventListener('resize', resizeThreeViewport);
  document.addEventListener('fullscreenchange', () => setTimeout(resizeThreeViewport, 80));

  // Studio Lighting cards
  document.querySelectorAll('.lighting-card-btn').forEach(btn => {
    btn.onclick = () => applyStudioLightingPreset(btn.getAttribute('data-lighting'));
  });

  // Mockup Export Modal
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
}

function export3DMockup(format = 'png_transparent', resolution = 2048) {
  if (!threeRenderer || !threeScene || !threeCamera) return;
  showToast(`Rendering ${resolution}px 3D studio mockup...`, 'info', 3000);
  const prevW = threeRenderer.domElement.width;
  const prevH = threeRenderer.domElement.height;
  const prevAspect = threeCamera.aspect;
  const prevBg = threeScene.background;
  const prevPos = threeCamera.position.clone();
  const prevTarget = threeOrbitControls ? threeOrbitControls.target.clone() : null;

  const size = parseInt(resolution, 10) || 2048;
  threeScene.background = format === 'png_transparent' ? null : new THREE.Color(0xF5F6F8);
  threeRenderer.setSize(size, size, false);
  threeCamera.aspect = 1.0;
  // Auto-fit full packaging bounding box cleanly for 1:1 2K/4K output so no seal/cap/gusset is cropped
  fitCameraToModel();
  threeRenderer.render(threeScene, threeCamera);

  const mime = format === 'jpg' ? 'image/jpeg' : 'image/png';
  const dataUrl = threeRenderer.domElement.toDataURL(mime, 0.96);

  threeScene.background = prevBg;
  threeRenderer.setSize(prevW, prevH, false);
  threeCamera.aspect = prevAspect;
  threeCamera.position.copy(prevPos);
  if (threeOrbitControls && prevTarget) {
    threeOrbitControls.target.copy(prevTarget);
    threeOrbitControls.update();
  }
  threeCamera.updateProjectionMatrix();
  threeRenderer.render(threeScene, threeCamera);

  const title = (document.getElementById('canvaDocTitleInput')?.value || 'gomzi_3d_mockup').replace(/[^a-zA-Z0-9_-]/g, '_');
  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = `${title}_3D_${size}px.${format === 'jpg' ? 'jpg' : 'png'}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  showToast('Exported 3D Packaging Mockup cleanly', 'success');
}
