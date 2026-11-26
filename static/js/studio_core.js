/* ============================================================================
   studio_core.js - GOMZI BOB 2D Studio, Fabric.js Workspace, Rulers, Layers,
   Import/Export, Full Label Replacement & Undo/Redo History
   ============================================================================ */

let canvaCanvas = null;
let brandLogoObject = null;
let activeProjectId = null;
let hasUnsavedChanges = false;
let lastSavedTimestamp = null;
let canvasHistory = [];
let historyIndex = -1;
let isHistoryLocked = false;
let isBleedGuideVisible = false;
let isSnapEnabled = true;
let isHandPanMode = false;
let isPanDragging = false;
let panLastPos = { x: 0, y: 0 };

// Multi-artboard storage
let studioArtboards = [
  { id: 'artboard_1', name: 'Artboard 1', width: 1536, height: 512, ratio: '3:1 (Wrap Label)', json: null }
];
let activeArtboardIdx = 0;

function refreshLucideIcons() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

function showToast(msg, icon = 'info', duration = 2800) {
  const toast = document.getElementById('canvaStudioToast');
  const msgEl = document.getElementById('canvaToastMsg');
  const iconEl = document.getElementById('canvaToastIcon');
  if (!toast) return;
  msgEl.textContent = msg;
  if (iconEl) {
    const emojiOrIcon = {
      info: '<i data-lucide="info" style="width:14px;height:14px;color:#74883D"></i>',
      success: '<i data-lucide="check-circle-2" style="width:14px;height:14px;color:#459568"></i>',
      warn: '<i data-lucide="alert-triangle" style="width:14px;height:14px;color:#D4A14A"></i>',
      error: '<i data-lucide="x-circle" style="width:14px;height:14px;color:#D65D5D"></i>',
    };
    iconEl.innerHTML = emojiOrIcon[icon] || iconEl.innerHTML;
    refreshLucideIcons();
  }
  toast.style.display = 'flex';
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => { toast.style.display = 'none'; }, duration);
}

function setSaveStatus(state, timeLabel = '') {
  const pill = document.getElementById('topSaveStatusPill');
  const txt = document.getElementById('topSaveStatusText');
  const botTxt = document.getElementById('bottomSaveStatusLabel');
  if (!pill || !txt) return;
  pill.classList.remove('saved', 'unsaved');
  if (state === 'saving') {
    txt.textContent = 'Saving...';
    if (botTxt) botTxt.textContent = 'Saving...';
  } else if (state === 'saved') {
    pill.classList.add('saved');
    const lbl = timeLabel ? `Saved at ${timeLabel}` : 'Saved';
    txt.textContent = lbl;
    if (botTxt) botTxt.textContent = lbl;
    hasUnsavedChanges = false;
  } else {
    pill.classList.add('unsaved');
    txt.textContent = 'Unsaved edits';
    if (botTxt) botTxt.textContent = 'Unsaved edits';
    hasUnsavedChanges = true;
  }
}

/* ============================================================================
   SIDEBAR NAVIGATION SWITCHER (All 13 Pages)
   ============================================================================ */
function switchMainView(viewName) {
  document.querySelectorAll('.app-view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));

  const navMatch = document.querySelector(`.sidebar-item[data-view="${viewName}"]`);
  if (navMatch) navMatch.classList.add('active');

  if (viewName === 'studio' || viewName === 'ai-generator' || viewName === '3d-studio') {
    document.getElementById('viewDesignStudio')?.classList.add('active');
    if (viewName === 'ai-generator') {
      switchStudioDrawer('aitools');
    } else if (viewName === '3d-studio') {
      const p = document.getElementById('canvaLiveJarPanel');
      if (p) p.classList.remove('collapsed');
      document.getElementById('studio3dToggleBtn')?.classList.add('active');
    }
    setTimeout(() => {
      fitCanvasToStage();
      if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
      if (typeof resizeThreeViewport === 'function') resizeThreeViewport();
    }, 80);
    return;
  }

  const viewMap = {
    'dashboard': 'viewDashboard',
    'my-designs': 'viewMyDesigns',
    'templates': 'viewTemplates',
    'brand-kit': 'viewBrandKit',
    'asset-library': 'viewAssetLibrary',
    'prompt-library': 'viewPromptLibrary',
    'nutrition-facts': 'viewNutritionFacts',
    'api-management': 'viewApiManagement',
    'settings': 'viewSettings',
    'help': 'viewHelp',
  };

  const elId = viewMap[viewName];
  if (elId && document.getElementById(elId)) {
    document.getElementById(elId).classList.add('active');
  }

  // Trigger real data loaders
  if (viewName === 'dashboard' && typeof loadDashboardStats === 'function') loadDashboardStats();
  if (viewName === 'my-designs' && typeof loadMyDesigns === 'function') loadMyDesigns();
  if (viewName === 'templates' && typeof loadTemplatesPage === 'function') loadTemplatesPage();
  if (viewName === 'brand-kit' && typeof loadBrandKitPage === 'function') loadBrandKitPage();
  if (viewName === 'asset-library' && typeof loadAssetLibraryPage === 'function') loadAssetLibraryPage();
  if (viewName === 'prompt-library' && typeof loadPromptLibraryPage === 'function') loadPromptLibraryPage();
  if (viewName === 'nutrition-facts' && typeof loadNutritionPage === 'function') loadNutritionPage();
  if (viewName === 'api-management' && typeof loadApiManagementPage === 'function') loadApiManagementPage();
  if (viewName === 'settings' && typeof loadSettingsPage === 'function') loadSettingsPage();
}

/* ============================================================================
   VERTICAL EDITING TOOL RAIL & CONTEXTUAL DRAWERS
   ============================================================================ */
function switchStudioDrawer(drawerKey) {
  const leftCol = document.getElementById('studioLeftPanel');
  if (leftCol && leftCol.classList.contains('collapsed')) {
    leftCol.classList.remove('collapsed');
  }

  document.querySelectorAll('.rail-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-drawer') === drawerKey);
  });
  document.querySelectorAll('.drawer-view').forEach(v => {
    v.classList.remove('active');
    if (v.id.toLowerCase() === `drawer${drawerKey.toLowerCase()}`) {
      v.classList.add('active');
    }
  });
  setTimeout(fitCanvasToStage, 120);
}

/* ============================================================================
   HORIZONTAL & VERTICAL PIXEL RULERS
   ============================================================================ */
function drawRulers() {
  if (!canvaCanvas) return;
  const zoom = canvaCanvas.getZoom() || 1;
  const wPx = canvaCanvas._logicalWidth || 1536;
  const hPx = canvaCanvas._logicalHeight || 512;

  const rTop = document.getElementById('rulerTopCanvas');
  const rLeft = document.getElementById('rulerLeftCanvas');
  const stage = document.getElementById('canvaStageWrapper');
  const art = document.getElementById('canvaArtboardContainer');
  if (!rTop || !rLeft || !stage || !art) return;

  const artRect = art.getBoundingClientRect();
  const stageRect = stage.getBoundingClientRect();
  const offsetX = Math.round(artRect.left - stageRect.left);
  const offsetY = Math.round(artRect.top - stageRect.top);

  // Top Ruler
  rTop.width = Math.max(300, stage.clientWidth);
  rTop.height = 22;
  const ctxX = rTop.getContext('2d');
  ctxX.clearRect(0, 0, rTop.width, 22);
  ctxX.fillStyle = '#68736D';
  ctxX.font = '600 9.5px Inter, sans-serif';
  ctxX.strokeStyle = '#CBD3D6';
  ctxX.lineWidth = 1;

  const step = zoom < 0.45 ? 250 : zoom < 0.9 ? 100 : 50;
  for (let val = 0; val <= wPx; val += step) {
    const x = Math.round(offsetX + val * zoom) + 0.5;
    if (x < 0 || x > rTop.width) continue;
    ctxX.beginPath();
    ctxX.moveTo(x, 14);
    ctxX.lineTo(x, 22);
    ctxX.stroke();
    ctxX.fillText(String(val), x + 3, 11);
  }

  // Left Ruler
  rLeft.width = 22;
  rLeft.height = Math.max(200, stage.clientHeight);
  const ctxY = rLeft.getContext('2d');
  ctxY.clearRect(0, 0, 22, rLeft.height);
  ctxY.fillStyle = '#68736D';
  ctxY.font = '600 9.5px Inter, sans-serif';
  ctxY.strokeStyle = '#CBD3D6';
  ctxY.lineWidth = 1;

  for (let val = 0; val <= hPx; val += step) {
    const y = Math.round(offsetY + val * zoom) + 0.5;
    if (y < 0 || y > rLeft.height) continue;
    ctxY.beginPath();
    ctxY.moveTo(14, y);
    ctxY.lineTo(22, y);
    ctxY.stroke();
    ctxY.save();
    ctxY.translate(10, y + 14);
    ctxY.rotate(-Math.PI / 2);
    ctxY.fillText(String(val), 0, 0);
    ctxY.restore();
  }
}

/* ============================================================================
   FIT ARTWORK & ARTBOARD READOUTS
   ============================================================================ */
function fitCanvasToStage() {
  const stageWrapper = document.getElementById('canvaStageWrapper');
  const container = document.getElementById('canvaArtboardContainer');
  if (!stageWrapper || !container || !canvaCanvas) return;

  const logicalW = canvaCanvas._logicalWidth || 1536;
  const logicalH = canvaCanvas._logicalHeight || 512;
  const availableW = Math.max(240, stageWrapper.clientWidth - 64);
  const availableH = Math.max(180, stageWrapper.clientHeight - 64);
  const scale = Math.min(availableW / logicalW, availableH / logicalH, 0.92);

  container.style.width = `${Math.round(logicalW * scale)}px`;
  container.style.height = `${Math.round(logicalH * scale)}px`;
  canvaCanvas.setDimensions({ width: Math.round(logicalW * scale), height: Math.round(logicalH * scale) });
  canvaCanvas.setZoom(scale);
  updateZoomReadout(scale);
  drawRulers();
}

function updateZoomReadout(scale) {
  const pct = `${Math.round(scale * 100)}%`;
  const el = document.getElementById('canvaZoomVal');
  if (el) el.textContent = pct;
}

function updateCanvasDimensionReadout() {
  if (!canvaCanvas) return;
  const w = canvaCanvas._logicalWidth || 1536;
  const h = canvaCanvas._logicalHeight || 512;
  const ratio = (w / h);
  let ratioText = `${ratio.toFixed(2)}:1`;
  if (Math.abs(ratio - 3.0) < 0.15) ratioText = '3:1 (Wrap Label)';
  else if (Math.abs(ratio - 1.0) < 0.08) ratioText = '1:1 (Square)';
  else if (Math.abs(ratio - 4.0) < 0.15) ratioText = '4:1 (Wide Tub)';
  else if (Math.abs(ratio - 16 / 9) < 0.1) ratioText = '16:9';
  else if (Math.abs(ratio - 2 / 3) < 0.08) ratioText = '2:3 (Pouch)';
  else if (Math.abs(ratio - 7 / 11) < 0.08) ratioText = '7:11 (Sachet)';

  const botDims = document.getElementById('bottomCanvasDimsLabel');
  if (botDims) botDims.textContent = `${w} × ${h} px  |  ${ratioText}`;
}

function resizeLogicalArtboard(newW, newH, ratioLabel = '') {
  if (!canvaCanvas) return;
  canvaCanvas._logicalWidth = Math.max(100, Math.round(newW));
  canvaCanvas._logicalHeight = Math.max(100, Math.round(newH));
  if (studioArtboards[activeArtboardIdx]) {
    studioArtboards[activeArtboardIdx].width = canvaCanvas._logicalWidth;
    studioArtboards[activeArtboardIdx].height = canvaCanvas._logicalHeight;
    if (ratioLabel) studioArtboards[activeArtboardIdx].ratio = ratioLabel;
  }
  fitCanvasToStage();
  updateCanvasDimensionReadout();
}

/* ============================================================================
   MAIN STUDIO INITIALIZER
   ============================================================================ */
function initGomziStudio() {
  refreshLucideIcons();

  // Sidebar clicks
  document.querySelectorAll('.sidebar-item[data-view]').forEach(item => {
    item.addEventListener('click', () => switchMainView(item.getAttribute('data-view')));
  });

  // Top sidebar collapse toggle
  document.getElementById('topSidebarToggleBtn')?.addEventListener('click', () => {
    document.getElementById('mainAppSidebar')?.classList.toggle('collapsed');
    setTimeout(() => { fitCanvasToStage(); if (typeof resizeThreeViewport === 'function') resizeThreeViewport(); }, 220);
  });

  // Rail clicks
  document.querySelectorAll('.rail-btn[data-drawer]').forEach(btn => {
    btn.addEventListener('click', () => switchStudioDrawer(btn.getAttribute('data-drawer')));
  });

  // Drawer collapse buttons
  document.querySelectorAll('.drawer-collapse-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('studioLeftPanel')?.classList.toggle('collapsed');
      setTimeout(fitCanvasToStage, 220);
    });
  });

  const canvasEl = document.getElementById('canvaMainCanvas');
  if (!canvasEl) return;

  canvaCanvas = new fabric.Canvas('canvaMainCanvas', {
    width: 1536,
    height: 512,
    backgroundColor: '#FAF8F1',
    preserveObjectStacking: true,
    selection: true,
  });
  canvaCanvas._logicalWidth = 1536;
  canvaCanvas._logicalHeight = 512;

  window.addEventListener('resize', () => {
    fitCanvasToStage();
    if (typeof resizeThreeViewport === 'function') resizeThreeViewport();
  });
  document.getElementById('canvaStageWrapper')?.addEventListener('scroll', drawRulers);

  // Load default GOMZI Whey template matching the reference
  loadGomziWheyTemplate();
  fitCanvasToStage();
  updateCanvasDimensionReadout();
  setSaveStatus('unsaved');

  // Canvas event hooks
  let textureDebounce = null;
  function onCanvasMutated() {
    if (isHistoryLocked) return;
    pushCanvasHistory();
    refreshLayersList();
    setSaveStatus('unsaved');
    clearTimeout(textureDebounce);
    textureDebounce = setTimeout(() => {
      if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
    }, 90);
  }

  canvaCanvas.on('object:added', onCanvasMutated);
  canvaCanvas.on('object:modified', onCanvasMutated);
  canvaCanvas.on('object:removed', onCanvasMutated);
  canvaCanvas.on('text:changed', onCanvasMutated);

  // Center Snapping Guide during move
  canvaCanvas.on('object:moving', (e) => {
    if (!isSnapEnabled || !e.target) return;
    const obj = e.target;
    const cw = canvaCanvas._logicalWidth || 1536;
    const ch = canvaCanvas._logicalHeight || 512;
    const objCenter = obj.getCenterPoint();
    if (Math.abs(objCenter.x - cw / 2) < 12) {
      obj.setPositionByOrigin(new fabric.Point(cw / 2, objCenter.y), 'center', 'center');
    }
    if (Math.abs(objCenter.y - ch / 2) < 12) {
      obj.setPositionByOrigin(new fabric.Point(obj.getCenterPoint().x, ch / 2), 'center', 'center');
    }
  });

  // Hand / Pan drag events
  canvaCanvas.on('mouse:down', (opt) => {
    if (!isHandPanMode) return;
    isPanDragging = true;
    panLastPos = { x: opt.e.clientX, y: opt.e.clientY };
  });
  canvaCanvas.on('mouse:move', (opt) => {
    if (!isHandPanMode || !isPanDragging) return;
    const stage = document.getElementById('canvaStageWrapper');
    if (stage) {
      stage.scrollLeft -= (opt.e.clientX - panLastPos.x);
      stage.scrollTop -= (opt.e.clientY - panLastPos.y);
    }
    panLastPos = { x: opt.e.clientX, y: opt.e.clientY };
  });
  canvaCanvas.on('mouse:up', () => { isPanDragging = false; });

  canvaCanvas.on('selection:created', onCanvasSelectionChange);
  canvaCanvas.on('selection:updated', onCanvasSelectionChange);
  canvaCanvas.on('selection:cleared', onCanvasSelectionCleared);

  // Initialize subsystems
  initToolbarAndContextControls();
  initFullLabelUploadEngine();
  initUniversalImportEngine();
  initBrandKitDrawerControls();
  initDrawerToolBindings();
  initExportControls();
  initArtboardBar();

  if (typeof initThreePackagingEngine === 'function') initThreePackagingEngine();
  if (typeof initAiStudioEngine === 'function') initAiStudioEngine();
  if (typeof loadDashboardStats === 'function') loadDashboardStats();
}

/* ============================================================================
   DEFAULT REFERENCE TEMPLATE: GOMZI NUTRITION WHEY PROTEIN 1KG
   Soft Cream & Forest Green theme matching reference screenshot cleanly.
   ============================================================================ */
function loadGomziWheyTemplate() {
  if (!canvaCanvas) return;
  isHistoryLocked = true;
  canvaCanvas.clear();
  canvaCanvas._logicalWidth = 1536;
  canvaCanvas._logicalHeight = 512;
  canvaCanvas.backgroundColor = '#FAF8F1';

  // Soft decorative sage wave ribbons matching reference
  const waveTopLeft = new fabric.Polygon(
    [{ x: 0, y: 0 }, { x: 520, y: 0 }, { x: 240, y: 120 }, { x: 0, y: 160 }],
    { fill: '#889C4E', opacity: 0.22, selectable: true, assetType: 'decorative_graphic', name: 'Sage Ribbon Top-Left' }
  );
  const waveTopRight = new fabric.Polygon(
    [{ x: 1020, y: 0 }, { x: 1536, y: 0 }, { x: 1536, y: 210 }, { x: 1240, y: 90 }],
    { fill: '#74883D', opacity: 0.72, selectable: true, assetType: 'decorative_graphic', name: 'Olive Curve Right' }
  );
  const waveBottomRight = new fabric.Polygon(
    [{ x: 1120, y: 512 }, { x: 1536, y: 290 }, { x: 1536, y: 512 }],
    { fill: '#5F7130', opacity: 0.90, selectable: true, assetType: 'decorative_graphic', name: 'Olive Corner Bottom' }
  );
  canvaCanvas.add(waveTopLeft, waveTopRight, waveBottomRight);

  // Left Nutrition Panel Card
  const nutHeaderBar = new fabric.Rect({
    left: 42, top: 86, width: 390, height: 42, rx: 4, ry: 4,
    fill: '#5F7130', selectable: true, assetType: 'table_box', name: 'Nutrition Header Bar'
  });
  const nutCard = new fabric.Rect({
    left: 42, top: 128, width: 390, height: 280, rx: 4, ry: 4,
    fill: '#FFFFFF', stroke: '#D6DCD0', strokeWidth: 1.5, selectable: true, assetType: 'table_box', name: 'Nutrition Card'
  });
  const nutTitle = new fabric.Textbox('NUTRITIONAL INFORMATION\nServing Size: 1 Scoop (33g) | Servings: 30', {
    left: 54, top: 93, width: 368, fontSize: 13.5, fontFamily: 'Montserrat', fontWeight: '800',
    fill: '#FFFFFF', textAlign: 'left', selectable: true, assetType: 'editable_text', name: 'Nutrition Header'
  });
  const nutRows = new fabric.Textbox(
    'Energy                                     130 kcal\nProtein                                         24.0 g\nCarbohydrate                               3.2 g\n  Total Sugars                                 1.2 g\n  Added Sugars                               0.0 g\nTotal Fat                                        1.5 g\nBCAA (Leucine, Isoleucine, Valine)  5.5 g\nGlutamic Acid                               4.2 g',
    {
      left: 56, top: 142, width: 364, fontSize: 13.5, fontFamily: 'Inter', fontWeight: '600',
      fill: '#202820', lineHeight: 1.75, selectable: true, assetType: 'editable_text', name: 'Nutrition Rows'
    }
  );
  const netWtLeft = new fabric.Textbox('Net Wt. 1 kg (2.2 lbs)', {
    left: 220, top: 432, width: 220, fontSize: 15, fontFamily: 'Montserrat', fontWeight: '800',
    fill: '#202820', textAlign: 'center', selectable: true, assetType: 'editable_text', name: 'Net Weight Left'
  });
  canvaCanvas.add(nutCard, nutHeaderBar, nutTitle, nutRows, netWtLeft);

  // Center Hero Panel: Official GOMZI Logo + WHEY PROTEIN + Flavour Banner
  fabric.loadSVGFromURL('/static/assets/gomzi_logo.svg', (objects, options) => {
    let logo;
    if (objects && objects.length) {
      logo = fabric.util.groupSVGElements(objects, options);
      logo.set({ left: 668, top: 36, scaleX: 0.62, scaleY: 0.62 });
    } else {
      logo = new fabric.Textbox('GOMZI\nNUTRITION', {
        left: 668, top: 36, width: 240, fontSize: 32, fontFamily: 'Montserrat',
        fontWeight: '900', fontStyle: 'italic', fill: '#74883D', textAlign: 'center', lineHeight: 0.92
      });
    }
    logo.set({ selectable: true, assetType: 'brand_logo', isBrandLogo: true, name: 'GOMZI NUTRITION Logo' });
    brandLogoObject = logo;
    canvaCanvas.add(logo);
    canvaCanvas.renderAll();
    if (typeof syncBrandSliders === 'function') syncBrandSliders(logo);
    if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
  });

  const mainTitle = new fabric.Textbox('WHEY\nPROTEIN', {
    left: 530, top: 122, width: 510, fontSize: 78, fontFamily: 'Bebas Neue', fontWeight: '900',
    fill: '#181E1A', textAlign: 'center', lineHeight: 0.88, letterSpacing: 2, selectable: true,
    assetType: 'editable_text', name: 'Main Product Title'
  });
  const subTag = new fabric.Textbox('PREMIUM ULTRA-FILTERED WHEY', {
    left: 530, top: 274, width: 510, fontSize: 15, fontFamily: 'Montserrat', fontWeight: '800',
    fill: '#25372A', textAlign: 'center', letterSpacing: 1.8, selectable: true,
    assetType: 'editable_text', name: 'Product Tagline'
  });
  const statsRow = new fabric.Textbox('24g PROTEIN   |   5.5g BCAAs   |   4.2g GLUTAMIC ACID   |   0g ADDED SUGAR', {
    left: 500, top: 318, width: 570, fontSize: 13.5, fontFamily: 'Montserrat', fontWeight: '800',
    fill: '#202820', textAlign: 'center', selectable: true, assetType: 'editable_text', name: 'Macro Strip'
  });
  const flavourPill = new fabric.Rect({
    left: 615, top: 374, width: 340, height: 52, rx: 10, ry: 10,
    fill: '#6E4427', selectable: true, assetType: 'decorative_graphic', name: 'Flavour Pill'
  });
  const flavourText = new fabric.Textbox('BELGIAN CHOCOLATE\nFLAVOUR', {
    left: 615, top: 382, width: 340, fontSize: 15.5, fontFamily: 'Montserrat', fontWeight: '800',
    fill: '#FFFFFF', textAlign: 'center', lineHeight: 1.15, selectable: true,
    assetType: 'editable_text', name: 'Flavour Text'
  });
  canvaCanvas.add(mainTitle, subTag, statsRow, flavourPill, flavourText);

  // Right Highlights & Weight Panel
  const highlights = new fabric.Textbox(
    '✓  Premium Whey Protein\n\n✓  Fast Absorption\n\n✓  Muscle Recovery\n\n✓  Supports Lean Muscle',
    {
      left: 1130, top: 106, width: 320, fontSize: 17, fontFamily: 'Inter', fontWeight: '700',
      fill: '#202820', lineHeight: 1.35, selectable: true, assetType: 'editable_text', name: 'Key Benefits'
    }
  );
  const vegBorder = new fabric.Rect({
    left: 1338, top: 365, width: 30, height: 30, rx: 4, ry: 4,
    fill: '#FFFFFF', stroke: '#459568', strokeWidth: 2.5, selectable: true, assetType: 'seal_graphic', name: 'Veg Mark Border'
  });
  const vegDot = new fabric.Circle({
    left: 1346, top: 373, radius: 7, fill: '#459568', selectable: true, assetType: 'seal_graphic', name: 'Veg Mark Dot'
  });
  const weightRight = new fabric.Textbox('1 kg\nNET WEIGHT', {
    left: 1280, top: 410, width: 150, fontSize: 22, fontFamily: 'Montserrat', fontWeight: '900',
    fill: '#FFFFFF', textAlign: 'center', lineHeight: 1.0, selectable: true,
    assetType: 'editable_text', name: 'Spec Subtitle'
  });
  canvaCanvas.add(highlights, vegBorder, vegDot, weightRight);

  canvaCanvas.renderAll();
  isHistoryLocked = false;
  canvasHistory = [];
  historyIndex = -1;
  pushCanvasHistory();
  refreshLayersList();
  fitCanvasToStage();
  updateCanvasDimensionReadout();
}

/* ============================================================================
   SELECTION & CONTEXTUAL ARTWORK TOOLBAR
   ============================================================================ */
function onCanvasSelectionChange(e) {
  const act = e?.selected ? e.selected[0] : canvaCanvas?.getActiveObject();
  if (!act) return;
  const textStrip = document.getElementById('textFormatStrip');
  const isText = act.type === 'textbox' || act.type === 'i-text' || act.type === 'text';

  document.querySelectorAll('#textFormatStrip button, #textFormatStrip select, #textFormatStrip input').forEach(el => {
    el.disabled = !isText;
  });
  if (textStrip) textStrip.style.opacity = isText ? '1' : '0.45';

  if (isText) {
    const ff = document.getElementById('canvaFontFamily');
    const fs = document.getElementById('canvaFontSize');
    const tc = document.getElementById('canvaTextColor');
    if (ff && act.fontFamily) ff.value = act.fontFamily;
    if (fs && act.fontSize) fs.value = Math.round(act.fontSize);
    if (tc && typeof act.fill === 'string' && act.fill.startsWith('#')) tc.value = act.fill;
  }
  if ((act.assetType === 'brand_logo' || act.isBrandLogo) && typeof syncBrandSliders === 'function') {
    syncBrandSliders(act);
  }
  refreshLayersList();
}

function onCanvasSelectionCleared() {
  const textStrip = document.getElementById('textFormatStrip');
  document.querySelectorAll('#textFormatStrip button, #textFormatStrip select, #textFormatStrip input').forEach(el => {
    el.disabled = true;
  });
  if (textStrip) textStrip.style.opacity = '0.45';
  refreshLayersList();
}

function initToolbarAndContextControls() {
  // Pointer vs Hand Pan tool
  const selBtn = document.getElementById('ctxSelectToolBtn');
  const panBtn = document.getElementById('ctxHandToolBtn');
  if (selBtn && panBtn) {
    selBtn.onclick = () => {
      isHandPanMode = false;
      canvaCanvas.selection = true;
      canvaCanvas.defaultCursor = 'default';
      selBtn.classList.add('active');
      panBtn.classList.remove('active');
    };
    panBtn.onclick = () => {
      isHandPanMode = true;
      canvaCanvas.selection = false;
      canvaCanvas.discardActiveObject().renderAll();
      canvaCanvas.defaultCursor = 'grab';
      panBtn.classList.add('active');
      selBtn.classList.remove('active');
    };
  }

  // Fit Artwork & Guides
  document.getElementById('ctxFitArtworkBtn')?.addEventListener('click', () => {
    fitCanvasToStage();
    showToast('Centered and fitted artwork to stage', 'success');
  });
  document.getElementById('canvaPrintGuidesBtn')?.addEventListener('click', () => {
    isBleedGuideVisible = !isBleedGuideVisible;
    document.getElementById('canvaPrintGuidesBtn')?.classList.toggle('active', isBleedGuideVisible);
    togglePrintBleedGuides(isBleedGuideVisible);
  });
  document.getElementById('ctxSnapToggleBtn')?.addEventListener('click', () => {
    isSnapEnabled = !isSnapEnabled;
    document.getElementById('ctxSnapToggleBtn')?.classList.toggle('active', isSnapEnabled);
    showToast(isSnapEnabled ? 'Object & Center Snapping enabled' : 'Snapping disabled', 'info');
  });

  // Rotate / Flip
  document.getElementById('ctxRotate90Btn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (!act) return showToast('Select an object to rotate', 'warn');
    act.rotate((act.angle || 0) + 90);
    canvaCanvas.renderAll();
    canvaCanvas.fire('object:modified', { target: act });
  });
  document.getElementById('ctxFlipHBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (!act) return showToast('Select an object to flip', 'warn');
    act.set('flipX', !act.flipX);
    canvaCanvas.renderAll();
    canvaCanvas.fire('object:modified', { target: act });
  });

  // Object Alignment relative to artboard
  function alignActive(pos) {
    const act = canvaCanvas?.getActiveObject();
    if (!act) return showToast('Select an object first', 'warn');
    const cw = canvaCanvas._logicalWidth || 1536;
    const ch = canvaCanvas._logicalHeight || 512;
    const br = act.getBoundingRect(true, true);
    if (pos === 'left') act.set('left', act.left - br.left);
    if (pos === 'center') act.set('left', act.left + (cw / 2 - (br.left + br.width / 2)));
    if (pos === 'right') act.set('left', act.left + (cw - (br.left + br.width)));
    if (pos === 'top') act.set('top', act.top - br.top);
    if (pos === 'middle') act.set('top', act.top + (ch / 2 - (br.top + br.height / 2)));
    if (pos === 'bottom') act.set('top', act.top + (ch - (br.top + br.height)));
    act.setCoords();
    canvaCanvas.renderAll();
    canvaCanvas.fire('object:modified', { target: act });
  }
  document.getElementById('ctxAlignLeftBtn')?.addEventListener('click', () => alignActive('left'));
  document.getElementById('ctxAlignCenterBtn')?.addEventListener('click', () => alignActive('center'));
  document.getElementById('ctxAlignRightBtn')?.addEventListener('click', () => alignActive('right'));
  document.getElementById('ctxAlignMiddleBtn')?.addEventListener('click', () => alignActive('middle'));

  // Group / Ungroup / Duplicate / Lock / Delete
  document.getElementById('ctxGroupBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (act && act.type === 'activeSelection') {
      act.toGroup();
      canvaCanvas.requestRenderAll();
      refreshLayersList();
      showToast('Grouped selected objects', 'success');
    } else if (act && act.type === 'group') {
      act.toActiveSelection();
      canvaCanvas.requestRenderAll();
      refreshLayersList();
      showToast('Ungrouped objects', 'success');
    } else {
      showToast('Select 2+ objects to group, or a group to ungroup', 'info');
    }
  });
  document.getElementById('canvaDuplicateBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (!act) return;
    act.clone((cl) => {
      cl.set({ left: act.left + 24, top: act.top + 24, name: (act.name || 'Layer') + ' Copy' });
      canvaCanvas.add(cl);
      canvaCanvas.setActiveObject(cl);
      canvaCanvas.renderAll();
    });
  });
  document.getElementById('ctxLockBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (!act) return;
    const locked = !act.lockMovementX;
    act.set({ lockMovementX: locked, lockMovementY: locked, lockScalingX: locked, lockScalingY: locked, lockRotation: locked });
    canvaCanvas.renderAll();
    refreshLayersList();
    showToast(locked ? 'Layer locked' : 'Layer unlocked', 'info');
  });
  document.getElementById('canvaDeleteBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (!act) return;
    canvaCanvas.remove(act);
    canvaCanvas.renderAll();
  });

  // Text formatting controls
  document.getElementById('canvaFontFamily')?.addEventListener('change', (e) => {
    const act = canvaCanvas?.getActiveObject();
    if (act && act.set) { act.set('fontFamily', e.target.value); canvaCanvas.renderAll(); canvaCanvas.fire('text:changed', { target: act }); }
  });
  document.getElementById('canvaFontSize')?.addEventListener('change', (e) => {
    const act = canvaCanvas?.getActiveObject();
    const val = parseInt(e.target.value, 10);
    if (act && val > 5) { act.set('fontSize', val); canvaCanvas.renderAll(); canvaCanvas.fire('text:changed', { target: act }); }
  });
  document.getElementById('canvaTextColor')?.addEventListener('input', (e) => {
    const act = canvaCanvas?.getActiveObject();
    if (act && act.set) { act.set('fill', e.target.value); canvaCanvas.renderAll(); canvaCanvas.fire('text:changed', { target: act }); }
  });
  document.getElementById('canvaBoldBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (act && act.set) {
      act.set('fontWeight', (act.fontWeight === 'bold' || act.fontWeight === '800' || act.fontWeight === '900') ? 'normal' : '800');
      canvaCanvas.renderAll();
      canvaCanvas.fire('text:changed', { target: act });
    }
  });
  document.getElementById('canvaItalicBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (act && act.set) {
      act.set('fontStyle', act.fontStyle === 'italic' ? 'normal' : 'italic');
      canvaCanvas.renderAll();
      canvaCanvas.fire('text:changed', { target: act });
    }
  });
  document.getElementById('canvaUnderlineBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (act && act.set) {
      act.set('underline', !act.underline);
      canvaCanvas.renderAll();
      canvaCanvas.fire('text:changed', { target: act });
    }
  });

  // Topbar Undo / Redo / Zoom / Fullscreen / Save / Share
  document.getElementById('canvaUndoBtn')?.addEventListener('click', undoCanvas);
  document.getElementById('canvaRedoBtn')?.addEventListener('click', redoCanvas);
  document.getElementById('canvaZoomInBtn')?.addEventListener('click', () => {
    if (!canvaCanvas) return;
    const z = Math.min(canvaCanvas.getZoom() * 1.15, 2.5);
    const w = canvaCanvas._logicalWidth || 1536;
    const h = canvaCanvas._logicalHeight || 512;
    const cont = document.getElementById('canvaArtboardContainer');
    if (cont) { cont.style.width = `${Math.round(w * z)}px`; cont.style.height = `${Math.round(h * z)}px`; }
    canvaCanvas.setDimensions({ width: Math.round(w * z), height: Math.round(h * z) });
    canvaCanvas.setZoom(z);
    updateZoomReadout(z);
    drawRulers();
  });
  document.getElementById('canvaZoomOutBtn')?.addEventListener('click', () => {
    if (!canvaCanvas) return;
    const z = Math.max(canvaCanvas.getZoom() * 0.85, 0.2);
    const w = canvaCanvas._logicalWidth || 1536;
    const h = canvaCanvas._logicalHeight || 512;
    const cont = document.getElementById('canvaArtboardContainer');
    if (cont) { cont.style.width = `${Math.round(w * z)}px`; cont.style.height = `${Math.round(h * z)}px`; }
    canvaCanvas.setDimensions({ width: Math.round(w * z), height: Math.round(h * z) });
    canvaCanvas.setZoom(z);
    updateZoomReadout(z);
    drawRulers();
  });
  document.getElementById('topFullscreenBtn')?.addEventListener('click', toggleStudioFullscreen);
  document.getElementById('bottomFullscreenBtn')?.addEventListener('click', toggleStudioFullscreen);
  document.getElementById('studio3dToggleBtn')?.addEventListener('click', () => {
    const p = document.getElementById('canvaLiveJarPanel');
    if (!p) return;
    p.classList.toggle('collapsed');
    document.getElementById('studio3dToggleBtn')?.classList.toggle('active', !p.classList.contains('collapsed'));
    setTimeout(() => { fitCanvasToStage(); if (typeof resizeThreeViewport === 'function') resizeThreeViewport(); }, 220);
  });
  document.getElementById('canvaApplyBtn')?.addEventListener('click', saveCurrentProject);
  document.getElementById('topShareBtn')?.addEventListener('click', () => {
    if (!activeProjectId) {
      saveCurrentProject().then(() => {
        if (activeProjectId) {
          navigator.clipboard?.writeText(window.location.href);
          showToast(`Project saved & link copied (${activeProjectId})`, 'success');
        }
      });
    } else {
      navigator.clipboard?.writeText(window.location.href);
      showToast(`Project reference copied (${activeProjectId})`, 'success');
    }
  });

  // Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    const tag = (e.target && e.target.tagName || '').toLowerCase();
    const editingInput = tag === 'input' || tag === 'textarea' || (canvaCanvas?.getActiveObject()?.isEditing);
    if (e.ctrlKey && e.key.toLowerCase() === 'z' && !editingInput) { e.preventDefault(); undoCanvas(); }
    if (e.ctrlKey && e.key.toLowerCase() === 'y' && !editingInput) { e.preventDefault(); redoCanvas(); }
    if (e.ctrlKey && e.key.toLowerCase() === 's') { e.preventDefault(); saveCurrentProject(); }
    if (e.key === 'Delete' && !editingInput && canvaCanvas) {
      const act = canvaCanvas.getActiveObject();
      if (act) { canvaCanvas.remove(act); canvaCanvas.renderAll(); }
    }
  });
}

function toggleStudioFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.().catch(() => { });
  } else {
    document.exitFullscreen?.().catch(() => { });
  }
}

function togglePrintBleedGuides(show) {
  if (!canvaCanvas) return;
  canvaCanvas.getObjects().filter(o => o.isGuideLine).forEach(o => canvaCanvas.remove(o));
  if (show) {
    const w = canvaCanvas._logicalWidth || 1536;
    const h = canvaCanvas._logicalHeight || 512;
    const safeRect = new fabric.Rect({
      left: 20, top: 20, width: w - 40, height: h - 40, fill: 'transparent',
      stroke: '#D65D5D', strokeWidth: 1.5, strokeDashArray: [6, 4],
      selectable: false, evented: false, isGuideLine: true, excludeFromExport: true, name: '3mm Safe Bleed'
    });
    isHistoryLocked = true;
    canvaCanvas.add(safeRect);
    canvaCanvas.bringToFront(safeRect);
    isHistoryLocked = false;
    showToast('Safe margins & 3mm bleed guide visible', 'info');
  }
  canvaCanvas.renderAll();
}

/* ============================================================================
   UNDO / REDO STACK
   ============================================================================ */
function pushCanvasHistory() {
  if (isHistoryLocked || !canvaCanvas) return;
  const jsonStr = JSON.stringify(canvaCanvas.toDatalessJSON([
    'assetType', 'isBrandLogo', 'isGuideLine', 'isTempOcrBox', 'excludeFromExport', 'name', 'lockMovementX',
    'semanticRole', 'layerCategory', 'ocrConfidence', 'ocrSource', 'needsReview', 'isImportedText', 'editable',
  ]));
  if (historyIndex < canvasHistory.length - 1) {
    canvasHistory = canvasHistory.slice(0, historyIndex + 1);
  }
  canvasHistory.push(jsonStr);
  if (canvasHistory.length > 40) { canvasHistory.shift(); }
  historyIndex = canvasHistory.length - 1;
  updateUndoRedoBtnState();
}

function undoCanvas() {
  if (historyIndex <= 0) return showToast('Nothing earlier to undo', 'info');
  historyIndex--;
  loadHistoryIndex(historyIndex);
}

function redoCanvas() {
  if (historyIndex >= canvasHistory.length - 1) return showToast('Already at latest edit', 'info');
  historyIndex++;
  loadHistoryIndex(historyIndex);
}

function loadHistoryIndex(idx) {
  if (!canvaCanvas || !canvasHistory[idx]) return;
  isHistoryLocked = true;
  canvaCanvas.loadFromJSON(canvasHistory[idx], () => {
    isHistoryLocked = false;
    canvaCanvas.renderAll();
    refreshLayersList();
    updateUndoRedoBtnState();
    if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
  });
}

function updateUndoRedoBtnState() {
  const u = document.getElementById('canvaUndoBtn');
  const r = document.getElementById('canvaRedoBtn');
  if (u) u.disabled = historyIndex <= 0;
  if (r) r.disabled = historyIndex >= canvasHistory.length - 1;
}

/* ============================================================================
   MULTI-ARTBOARD BAR
   ============================================================================ */
function initArtboardBar() {
  const sel = document.getElementById('artboardSelector');
  const addBtn = document.getElementById('btnAddArtboard');
  if (addBtn) {
    addBtn.onclick = () => {
      // Save current artboard JSON
      if (studioArtboards[activeArtboardIdx] && canvaCanvas) {
        studioArtboards[activeArtboardIdx].json = canvaCanvas.toDatalessJSON(['assetType', 'isBrandLogo', 'name']);
      }
      const nextNum = studioArtboards.length + 1;
      const nb = { id: `artboard_${nextNum}`, name: `Artboard ${nextNum}`, width: 1536, height: 512, ratio: '3:1 (Wrap Label)', json: null };
      studioArtboards.push(nb);
      activeArtboardIdx = studioArtboards.length - 1;
      if (sel) {
        const opt = document.createElement('option');
        opt.value = activeArtboardIdx;
        opt.textContent = nb.name;
        opt.selected = true;
        sel.appendChild(opt);
      }
      isHistoryLocked = true;
      canvaCanvas.clear();
      canvaCanvas.backgroundColor = '#FFFFFF';
      canvaCanvas.renderAll();
      isHistoryLocked = false;
      resizeLogicalArtboard(1536, 512);
      refreshLayersList();
      showToast(`Created ${nb.name}`, 'success');
    };
  }
  if (sel) {
    sel.onchange = () => {
      if (studioArtboards[activeArtboardIdx] && canvaCanvas) {
        studioArtboards[activeArtboardIdx].json = canvaCanvas.toDatalessJSON(['assetType', 'isBrandLogo', 'name']);
      }
      activeArtboardIdx = parseInt(sel.value, 10) || 0;
      const ab = studioArtboards[activeArtboardIdx];
      resizeLogicalArtboard(ab.width, ab.height);
      if (ab.json) {
        isHistoryLocked = true;
        canvaCanvas.loadFromJSON(ab.json, () => {
          isHistoryLocked = false;
          canvaCanvas.renderAll();
          refreshLayersList();
          if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
        });
      }
    };
  }
}

/* ============================================================================
   LAYERS PANEL (Search, Visibility, Lock, Reorder, Delete)
   ============================================================================ */
function refreshLayersList() {
  const container = document.getElementById('canvaLayersListContainer');
  const badge = document.getElementById('canvaLayerCountBadge');
  const filterVal = (document.getElementById('layersSearchInput')?.value || '').trim().toLowerCase();
  if (!container || !canvaCanvas) return;

  const objects = canvaCanvas.getObjects().filter(o => !o.isGuideLine && !o.isTempOcrBox);
  if (badge) badge.textContent = objects.length;
  container.innerHTML = '';

  for (let i = objects.length - 1; i >= 0; i--) {
    const obj = objects[i];
    const nameText = obj.name || obj.text || `Layer ${i + 1}`;
    if (filterVal && !nameText.toLowerCase().includes(filterVal)) continue;

    const isSelected = canvaCanvas.getActiveObject() === obj;
    const row = document.createElement('div');
    row.style.cssText = `display:flex;align-items:center;justify-content:space-between;padding:7px 9px;background:${isSelected ? '#EDF1DF' : '#F8FAFC'};border:1px solid ${isSelected ? '#C4D29F' : '#E0E5E7'};border-radius:7px;cursor:pointer;font-size:11.5px;font-weight:600;`;
    const typeLabel = obj.layerCategory
      || (obj.assetType === 'brand_logo' ? 'Logo' : (obj.type === 'textbox' ? 'Text' : (obj.type === 'image' ? 'Image' : 'Vector')));
    row.innerHTML = `
      <div style="display:flex;flex-direction:column;overflow:hidden;max-width:155px;">
        <span style="color:#202820;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${nameText.substring(0, 26)}</span>
        <span style="font-size:9.5px;color:#68736D;font-weight:500;">${typeLabel}${obj.lockMovementX ? ' · Locked' : ''}</span>
      </div>
      <div style="display:flex;align-items:center;gap:5px;">
        <button type="button" class="layer-eye icon-btn" style="width:24px;height:24px;" title="Toggle Visibility">${obj.visible ? '<i data-lucide="eye"></i>' : '<i data-lucide="eye-off"></i>'}</button>
        <button type="button" class="layer-del icon-btn" style="width:24px;height:24px;color:#D65D5D;" title="Delete Layer"><i data-lucide="trash-2"></i></button>
      </div>
    `;
    row.onclick = (e) => {
      if (e.target.closest('.layer-eye')) {
        obj.visible = !obj.visible;
        canvaCanvas.renderAll();
        refreshLayersList();
        if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
        return;
      }
      if (e.target.closest('.layer-del')) {
        canvaCanvas.remove(obj);
        canvaCanvas.renderAll();
        return;
      }
      canvaCanvas.setActiveObject(obj);
      canvaCanvas.renderAll();
      refreshLayersList();
    };
    container.appendChild(row);
  }
  refreshLucideIcons();
}

/* ============================================================================
   FULL LABEL UPLOAD VS STICKER SEPARATION
   ============================================================================ */
function initFullLabelUploadEngine() {
  const fullBtn = document.getElementById('btnUploadFullLabel');
  const fullInput = document.getElementById('inputUploadFullLabel');
  if (fullBtn && fullInput) {
    fullBtn.onclick = () => fullInput.click();
    fullInput.onchange = (e) => {
      if (e.target.files?.[0]) {
        const file = e.target.files[0];
        if (canvaCanvas && canvaCanvas.getObjects().length > 0) {
          if (!confirm(`Replace existing artwork with "${file.name}" and run automatic editable reconstruction?`)) {
            fullInput.value = '';
            return;
          }
        }
        const isTiff = /\.tiff?$/i.test(file.name);
        if (isTiff) {
          runAutoSmartReconstruct(file, file.name);
        } else {
          const reader = new FileReader();
          reader.onload = (f) => {
            openImageAsFullLabel(f.target.result, file.name, { skipConfirm: true });
            runAutoSmartReconstruct(file, file.name);
          };
          reader.readAsDataURL(file);
        }
        fullInput.value = '';
      }
    };
  }

  const stickerBtn = document.getElementById('btnAddSticker');
  const stickerInput = document.getElementById('canvaDrawerUploadInput');
  if (stickerBtn && stickerInput) {
    stickerBtn.onclick = () => stickerInput.click();
    stickerInput.onchange = (e) => {
      if (e.target.files?.[0]) {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (f) => addStickerToCanvas(f.target.result, file.name);
        reader.readAsDataURL(file);
        stickerInput.value = '';
      }
    };
  }
}

function openImageAsFullLabel(dataUrl, fileName = 'Uploaded Product Label', opts = {}) {
  if (!canvaCanvas) return;
  if (!opts.skipConfirm && canvaCanvas.getObjects().length > 0 && !fileName.startsWith('AI Generated')) {
    if (!confirm(`Replace existing artwork with "${fileName}" as full label artwork?`)) return;
  }
  canvaCanvas._originalReferenceUrl = dataUrl;

  const img = new Image();
  img.onload = () => {
    const natW = img.naturalWidth || 1536;
    const natH = img.naturalHeight || 512;
    const aspect = natW / natH;
    const targetW = 1536;
    const targetH = Math.round(targetW / aspect);

    isHistoryLocked = true;
    canvaCanvas.clear();
    canvaCanvas.backgroundColor = '#FFFFFF';
    resizeLogicalArtboard(targetW, targetH);

    fabric.Image.fromURL(dataUrl, (fabImg) => {
      fabImg.set({
        left: 0, top: 0,
        scaleX: targetW / natW,
        scaleY: targetH / natH,
        selectable: true, evented: true,
        assetType: 'full_label_artwork',
        name: `Full Label: ${fileName}`,
      });
      canvaCanvas.add(fabImg);
      canvaCanvas.sendToBack(fabImg);
      canvaCanvas.setActiveObject(fabImg);

      brandLogoObject = null;
      const cleanTitle = fileName.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
      const titleInput = document.getElementById('canvaDocTitleInput');
      if (titleInput) titleInput.value = cleanTitle;

      isHistoryLocked = false;
      pushCanvasHistory();
      refreshLayersList();
      fitCanvasToStage();
      updateCanvasDimensionReadout();
      setSaveStatus('unsaved');

      if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
      if (aspect < 1.65 && typeof select3DCategory === 'function') {
        select3DCategory(aspect < 0.85 ? 'sachet' : 'bottle');
      }
      addAssetToGallery(dataUrl, fileName);
      showToast(`Loaded "${cleanTitle}" as full label artwork`, 'success');
    }, { crossOrigin: 'anonymous' });
  };
  img.src = dataUrl;
}

function addStickerToCanvas(dataUrl, fileName = 'Graphic Layer') {
  if (!canvaCanvas) return;
  fabric.Image.fromURL(dataUrl, (img) => {
    img.scaleToWidth(Math.min(260, (canvaCanvas._logicalWidth || 1536) * 0.25));
    img.set({
      left: (canvaCanvas._logicalWidth || 1536) / 2 - 110,
      top: (canvaCanvas._logicalHeight || 512) / 2 - 110,
      assetType: 'sticker',
      name: fileName,
    });
    canvaCanvas.add(img);
    canvaCanvas.setActiveObject(img);
    canvaCanvas.renderAll();
    addAssetToGallery(dataUrl, fileName);
    showToast(`Added "${fileName}" as layer`, 'success');
  }, { crossOrigin: 'anonymous' });
}

function addAssetToGallery(dataUrl, name) {
  const grid = document.getElementById('uploadsGalleryGrid');
  if (!grid) return;
  const card = document.createElement('div');
  card.style.cssText = 'border:1px solid #E0E5E7;border-radius:8px;padding:8px;background:#fff;display:flex;flex-direction:column;gap:6px;';
  card.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;">
      <img src="${dataUrl}" style="width:52px;height:40px;object-fit:contain;background:#F5F6F8;border-radius:4px;border:1px solid #E0E5E7;" />
      <div style="flex:1;overflow:hidden;">
        <div style="font-size:11px;font-weight:700;color:#202820;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${name}</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
      <button type="button" class="table-action-btn full-btn">Full Label</button>
      <button type="button" class="btn-outline-clean sticker-btn" style="padding:4px 6px;font-size:10.5px;">Add Layer</button>
    </div>
  `;
  card.querySelector('.full-btn').onclick = () => openImageAsFullLabel(dataUrl, name);
  card.querySelector('.sticker-btn').onclick = () => addStickerToCanvas(dataUrl, name);
  grid.prepend(card);
}

/* ============================================================================
   UNIVERSAL DESIGN IMPORT ENGINE (CDR, SVG, PDF, AI, EPS)
   ============================================================================ */
let pendingImportData = null;

function initUniversalImportEngine() {
  const fileInput = document.getElementById('universalDesignFileInput');
  document.getElementById('btnDrawerImportVector')?.addEventListener('click', () => fileInput?.click());
  document.getElementById('studioImportDesignBtn')?.addEventListener('click', () => fileInput?.click());

  if (fileInput) {
    fileInput.onchange = (e) => {
      if (e.target.files?.[0]) processUniversalDesignFile(e.target.files[0]);
      fileInput.value = '';
    };
  }

  document.getElementById('closeImportModalBtn')?.addEventListener('click', () => {
    document.getElementById('designImportPreviewModal').style.display = 'none';
  });
  document.getElementById('cancelImportModalBtn')?.addEventListener('click', () => {
    document.getElementById('designImportPreviewModal').style.display = 'none';
  });
  document.getElementById('applyImportEditableBtn')?.addEventListener('click', () => {
    if (!pendingImportData) return;
    hydrateReconstructedScene(pendingImportData, () => {
      document.getElementById('designImportPreviewModal').style.display = 'none';
      const st = pendingImportData.stats || {};
      showToast(
        `Reconstructed ${st.text_objects || 0} text & ${st.vector_objects || 0} vector layers`,
        'success',
        3800
      );
    });
  });
  document.getElementById('applyImportImageBtn')?.addEventListener('click', () => {
    if (pendingImportData?.preview_url) {
      document.getElementById('designImportPreviewModal').style.display = 'none';
      openImageAsFullLabel(pendingImportData.preview_url, pendingImportData.filename || 'Imported Design');
    }
  });
}

function _buildFabricFill(rawFill, w, h) {
  if (rawFill && typeof rawFill === 'object' && Array.isArray(rawFill.colorStops)) {
    const coords = rawFill.coords || { x1: 0, y1: 0, x2: 1, y2: 0 };
    return new fabric.Gradient({
      type: rawFill.type || 'linear',
      coords: {
        x1: (coords.x1 || 0) * (w || 100),
        y1: (coords.y1 || 0) * (h || 100),
        x2: (coords.x2 !== undefined ? coords.x2 : 1) * (w || 100),
        y2: (coords.y2 || 0) * (h || 100),
      },
      colorStops: rawFill.colorStops,
    });
  }
  return rawFill === undefined ? '#000000' : rawFill;
}

function _hydrateSingleObjectAsync(spec) {
  return new Promise((resolve) => {
    const t = (spec.type || '').toLowerCase();
    const commonProps = {
      left: spec.left ?? 0,
      top: spec.top ?? 0,
      opacity: spec.opacity ?? 1.0,
      visible: spec.visible !== false,
      selectable: spec.selectable !== false,
      evented: spec.evented !== false,
      excludeFromExport: Boolean(spec.excludeFromExport) || spec.assetType === 'original_reference',
      assetType: spec.assetType || 'reconstructed_vector',
      layerCategory: spec.layerCategory || 'Artwork',
      semanticRole: spec.semanticRole || '',
      ocrConfidence: spec.ocrConfidence ?? null,
      needsReview: Boolean(spec.needsReview),
      name: spec.name || 'Layer',
    };

    if (t === 'svg_group_raw' && spec.svg_snippet) {
      fabric.loadSVGFromString(spec.svg_snippet, (objs, opts) => {
        if (!objs || !objs.length) return resolve(null);
        const grp = fabric.util.groupSVGElements(objs, opts);
        if (spec.targetWidth && grp.width > 0) grp.scaleX = spec.targetWidth / grp.width;
        if (spec.targetHeight && grp.height > 0) grp.scaleY = spec.targetHeight / grp.height;
        grp.set(commonProps);
        resolve(grp);
      });
      return;
    }

    if (t === 'svg_path_raw' && spec.svg_d) {
      const f = typeof spec.fill === 'string' ? spec.fill : 'none';
      const s = typeof spec.stroke === 'string' ? spec.stroke : 'none';
      const sw = spec.strokeWidth || 0;
      const miniSvg = `<svg xmlns="http://www.w3.org/2000/svg"><path d="${spec.svg_d.replace(/"/g, '&quot;')}" fill="${f}" stroke="${s}" stroke-width="${sw}" /></svg>`;
      fabric.loadSVGFromString(miniSvg, (objs) => {
        if (!objs || !objs.length) return resolve(null);
        const pObj = objs[0];
        if (typeof spec.fill === 'object' && spec.fill) {
          pObj.set('fill', _buildFabricFill(spec.fill, pObj.width, pObj.height));
        }
        pObj.set({
          ...commonProps,
          left: (spec.offsetX || 0) + (pObj.left || 0) * (spec.scaleX || 1),
          top: (spec.offsetY || 0) + (pObj.top || 0) * (spec.scaleY || 1),
          scaleX: spec.scaleX || 1,
          scaleY: spec.scaleY || 1,
        });
        resolve(pObj);
      });
      return;
    }

    if (t === 'rect') {
      return resolve(new fabric.Rect({
        ...commonProps,
        width: spec.width || 100,
        height: spec.height || 40,
        rx: spec.rx || 0,
        ry: spec.ry || 0,
        fill: _buildFabricFill(spec.fill, spec.width || 100, spec.height || 40),
        stroke: spec.stroke || null,
        strokeWidth: spec.strokeWidth || 0,
      }));
    }

    if (t === 'ellipse') {
      return resolve(new fabric.Ellipse({
        ...commonProps,
        rx: spec.rx || 20,
        ry: spec.ry || 20,
        fill: _buildFabricFill(spec.fill, (spec.rx || 20) * 2, (spec.ry || 20) * 2),
        stroke: spec.stroke || null,
        strokeWidth: spec.strokeWidth || 0,
      }));
    }

    if (t === 'circle') {
      return resolve(new fabric.Circle({
        ...commonProps,
        radius: spec.radius || 20,
        fill: _buildFabricFill(spec.fill, (spec.radius || 20) * 2, (spec.radius || 20) * 2),
        stroke: spec.stroke || null,
        strokeWidth: spec.strokeWidth || 0,
      }));
    }

    if (t === 'textbox' || t === 'i-text' || t === 'text') {
      return resolve(new fabric.Textbox(spec.text || '', {
        ...commonProps,
        width: spec.width || 120,
        fontSize: spec.fontSize || 16,
        fontFamily: spec.fontFamily || 'Montserrat',
        fontWeight: spec.fontWeight || '700',
        fontStyle: spec.fontStyle || 'normal',
        fill: spec.fill || '#111827',
        textAlign: spec.textAlign || 'left',
        lineHeight: spec.lineHeight || 1.14,
        charSpacing: spec.charSpacing || 0,
        editable: true,
        isImportedText: true,
        assetType: 'editable_text',
      }));
    }

    if (t === 'image' && spec.src) {
      fabric.Image.fromURL(spec.src, (img) => {
        if (!img) return resolve(null);
        img.set({
          ...commonProps,
          scaleX: spec.width ? spec.width / (img.width || spec.width) : 1,
          scaleY: spec.height ? spec.height / (img.height || spec.height) : 1,
        });
        resolve(img);
      }, { crossOrigin: 'anonymous' });
      return;
    }

    resolve(null);
  });
}

async function hydrateReconstructedScene(data, onComplete) {
  if (!canvaCanvas || !data) return;
  const rawObjs = data.raw_objects || data.fabric_json?.objects || [];
  const logW = data.canvas_width || data.fabric_json?.width || 1536;
  const logH = data.canvas_height || data.fabric_json?.height || 512;
  const dimsMm = data.dimensions_mm || { width: 160.0, height: Math.round(160.0 * (logH / logW)) };

  isHistoryLocked = true;
  canvaCanvas.clear();
  canvaCanvas.backgroundColor = data.background_color || '#FFFFFF';
  canvaCanvas._physicalWidthMm = dimsMm.width;
  canvaCanvas._physicalHeightMm = dimsMm.height;
  canvaCanvas._artifactId = data.artifact_id || null;
  canvaCanvas._lastReconstructionStats = data.stats || {};
  if (data.original_url) canvaCanvas._originalReferenceUrl = data.original_url;
  resizeLogicalArtboard(logW, logH);

  const hydrated = await Promise.all(rawObjs.map(o => _hydrateSingleObjectAsync(o)));
  hydrated.forEach((fObj) => {
    if (fObj) canvaCanvas.add(fObj);
  });

  // Preserve non-destructive hidden & locked Original Reference layer
  if (data.original_url && !canvaCanvas.getObjects().some(o => o.assetType === 'original_reference')) {
    await new Promise((resRef) => {
      fabric.Image.fromURL(data.original_url, (refImg) => {
        if (refImg) {
          refImg.set({
            left: 0, top: 0,
            scaleX: logW / (refImg.width || logW),
            scaleY: logH / (refImg.height || logH),
            visible: false,
            selectable: false,
            evented: false,
            excludeFromExport: true,
            assetType: 'original_reference',
            layerCategory: 'Reference',
            name: 'Original Reference (Locked)',
          });
          canvaCanvas.add(refImg);
          canvaCanvas.sendToBack(refImg);
        }
        resRef();
      }, { crossOrigin: 'anonymous' });
    });
  }

  brandLogoObject = canvaCanvas.getObjects().find(o => o.isBrandLogo || o.assetType === 'brand_logo') || null;
  const cleanTitle = (data.filename || 'Reconstructed Label').replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
  const titleInput = document.getElementById('canvaDocTitleInput');
  if (titleInput) titleInput.value = cleanTitle;

  isHistoryLocked = false;
  canvaCanvas.renderAll();
  pushCanvasHistory();
  refreshLayersList();
  fitCanvasToStage();
  updateCanvasDimensionReadout();
  setSaveStatus('unsaved');
  if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();

  // Optional non-blocking fidelity SSIM evaluation for raster imports
  if (data.artifact_id) {
    try {
      const renderedUrl = getCleanCanvasDataURL(1);
      fetch('/api/canva/evaluate-fidelity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ artifact_id: data.artifact_id, rendered_data_url: renderedUrl, stats: data.stats }),
      }).then(r => r.json()).then(fid => {
        if (fid?.fidelity) canvaCanvas._lastFidelity = fid.fidelity;
      }).catch(() => { });
    } catch (_) { }
  }
  if (typeof onComplete === 'function') onComplete();
}

let _activeSmartReconJobId = null;

async function _safeJsonResponse(res) {
  const ct = (res.headers.get('content-type') || '').toLowerCase();
  const text = await res.text();
  if (!ct.includes('application/json') && text.trim().startsWith('<')) {
    throw new Error(`Server returned HTTP ${res.status} HTML instead of JSON`);
  }
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`Invalid JSON (HTTP ${res.status}): ${err.message}`);
  }
}

async function runAutoSmartReconstruct(fileOrBlob, fileName = 'label.png') {
  const pill = document.getElementById('smartReconProgressPill');
  const pctEl = document.getElementById('smartReconPct');
  const stageEl = document.getElementById('smartReconStage');
  const cancelBtn = document.getElementById('smartReconCancelBtn');

  const setProgress = (pct, msg) => {
    if (pill) pill.style.display = 'flex';
    if (pctEl) pctEl.textContent = `${Math.round(pct)}%`;
    if (stageEl) stageEl.textContent = msg;
  };
  const hideProgress = () => {
    if (pill) pill.style.display = 'none';
    _activeSmartReconJobId = null;
  };

  setProgress(5, `Uploading ${fileName}...`);
  const formData = new FormData();
  formData.append('file', fileOrBlob, fileName);

  try {
    const jobRes = await fetch('/api/canva/import-design/async', { method: 'POST', body: formData });
    const jobInit = await _safeJsonResponse(jobRes);
    let data = null;

    if (jobInit.success && jobInit.job_id) {
      _activeSmartReconJobId = jobInit.job_id;
      if (cancelBtn) {
        cancelBtn.onclick = async () => {
          const jid = _activeSmartReconJobId;
          hideProgress();
          if (jid) {
            await fetch(`/api/canva/import-design/cancel/${jid}`, { method: 'POST' }).catch(() => { });
          }
          showToast('Smart reconstruction cancelled; original artwork preserved.', 'info');
        };
      }
      for (let attempt = 0; attempt < 360; attempt++) {
        if (_activeSmartReconJobId !== jobInit.job_id) return;
        await new Promise(r => setTimeout(r, 500));
        const stRes = await fetch(`/api/canva/import-design/status/${jobInit.job_id}`);
        const stJson = await _safeJsonResponse(stRes);
        setProgress(stJson.progress || 15, stJson.stage || 'Analyzing layout & detecting text...');
        if (stJson.status === 'completed' && stJson.result) {
          data = stJson.result;
          break;
        }
        if (stJson.status === 'failed' || stJson.status === 'cancelled') {
          hideProgress();
          showToast(`Smart reconstruction failed (${stJson.error || stJson.status}); original artwork preserved.`, 'error', 5500);
          return;
        }
      }
    } else {
      const syncForm = new FormData();
      syncForm.append('file', fileOrBlob, fileName);
      setProgress(45, 'Detecting text & reconstructing editable layers...');
      const res = await fetch('/api/canva/import-design', { method: 'POST', body: syncForm });
      data = await _safeJsonResponse(res);
    }

    if (!data?.success) {
      hideProgress();
      showToast(`Smart reconstruction unavailable (${data?.error || 'Error'}); original artwork preserved.`, 'error', 5500);
      return;
    }

    setProgress(95, 'Building editable layers & synchronizing 3D preview...');
    await hydrateReconstructedScene(data, () => {
      hideProgress();
      const st = data.stats || {};
      showToast(
        `Smart Import ready: ${st.text_objects || 0} editable text & ${st.vector_objects || 0} vector layers`,
        'success',
        4500
      );
    });
  } catch (e) {
    hideProgress();
    showToast(`Smart reconstruction error (${e.message}); original artwork preserved.`, 'error', 5500);
  }
}

async function runAutoSmartReconstructFromUrl(imgUrl, fileName = 'ai_generated_label.png') {
  try {
    const resp = await fetch(imgUrl);
    const blob = await resp.blob();
    await runAutoSmartReconstruct(blob, fileName);
  } catch (e) {
    showToast(`Could not auto-reconstruct AI artwork: ${e.message}`, 'error', 4500);
  }
}

function restoreOriginalArtwork() {
  if (!canvaCanvas) return;
  const refObj = canvaCanvas.getObjects().find(o => o.assetType === 'original_reference');
  const refUrl = refObj?.getSrc?.() || canvaCanvas._originalReferenceUrl;
  if (!refUrl) {
    return showToast('No original reference artwork available for this canvas.', 'info');
  }
  openImageAsFullLabel(refUrl, 'Restored Original Artwork', { skipConfirm: true });
  showToast('Restored original uploaded artwork cleanly.', 'success');
}

async function processUniversalDesignFile(file) {
  showToast(`Analyzing & reconstructing ${file.name}...`, 'info', 8000);
  const formData = new FormData();
  formData.append('file', file);
  try {
    // Submit to async background worker queue so UI stays responsive on CPU laptops
    const jobRes = await fetch('/api/canva/import-design/async', { method: 'POST', body: formData });
    const jobInit = await jobRes.json();
    let data = null;

    if (jobInit.success && jobInit.job_id) {
      for (let attempt = 0; attempt < 360; attempt++) {
        await new Promise(r => setTimeout(r, 500));
        const stRes = await fetch(`/api/canva/import-design/status/${jobInit.job_id}`);
        const stJson = await stRes.json();
        if (stJson.status === 'completed' && stJson.result) {
          data = stJson.result;
          break;
        }
        if (stJson.status === 'failed' || stJson.status === 'cancelled') {
          return showToast(`Import error: ${stJson.error || stJson.status}`, 'error', 4500);
        }
      }
      if (!data) {
        return showToast('Reconstruction timed out after 120s; please try again.', 'error', 4500);
      }
    } else {
      const syncForm = new FormData();
      syncForm.append('file', file);
      const res = await fetch('/api/canva/import-design', { method: 'POST', body: syncForm });
      data = await _safeJsonResponse(res);
    }
    if (!data?.success) return showToast(`Import error: ${data?.error || 'Failed'}`, 'error', 4500);

    pendingImportData = data;
    const st = data.stats || {};
    document.getElementById('importModalTitle').textContent = `Reconstructed ${data.format?.toUpperCase()} Design: ${file.name}`;
    document.getElementById('importModalPreviewImg').src = data.preview_url || (data.format === 'svg' && data.svg_content ? 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(data.svg_content) : '');
    document.getElementById('importModalDims').textContent = data.dimensions_mm ? `${data.dimensions_mm.width} × ${data.dimensions_mm.height} mm` : 'Detected';
    document.getElementById('importModalTotalObjs').textContent = st.total_objects || '1';
    document.getElementById('importModalTextObjs').textContent = st.text_objects || '0';
    document.getElementById('importModalVectorObjs').textContent = `${st.vector_objects || 0} (${st.illustrations_vectorized || 0} illust., ${st.icons_vectorized || 0} icons, ${st.retained_rasters || 0} raster)`;
    const warnEl = document.getElementById('importModalWarning');
    const warnMsgs = [...(data.warnings || [])];
    if (data.vision_provider) warnMsgs.unshift(`Engine: Hybrid Tiled OCR + ${data.vision_provider} + VTracer`);
    if (warnMsgs.length) {
      warnEl.textContent = warnMsgs.join(' · ');
      warnEl.style.display = 'block';
    } else {
      warnEl.style.display = 'none';
    }
    document.getElementById('designImportPreviewModal').style.display = 'flex';
  } catch (e) {
    showToast(`Import failed: ${e.message}`, 'error');
  }
}

/* ============================================================================
   BRAND KIT DRAWER, SHAPES, BACKGROUND & NUTRITION TOOLS
   ============================================================================ */
function initBrandKitDrawerControls() {
  const posXSlider = document.getElementById('canvaBrandLogoPosXSlider');
  const posYSlider = document.getElementById('canvaBrandLogoPosYSlider');
  const sizeSlider = document.getElementById('canvaBrandLogoSizeSlider');
  const rotSlider = document.getElementById('canvaBrandLogoRotSlider');

  document.getElementById('canvaInsertBrandNameBtn')?.addEventListener('click', () => {
    const val = (document.getElementById('canvaBrandNameInput')?.value || 'GOMZI NUTRITION').trim();
    const existing = canvaCanvas.getObjects().find(o => o.isBrandNameText);
    if (existing) {
      existing.set('text', val);
    } else {
      const tb = new fabric.Textbox(val, {
        left: 650, top: 96, width: 260, fontSize: 18, fontFamily: 'Montserrat', fontWeight: '900',
        fill: '#74883D', textAlign: 'center', isBrandNameText: true, assetType: 'editable_text', name: 'Brand Name'
      });
      canvaCanvas.add(tb);
      canvaCanvas.setActiveObject(tb);
    }
    canvaCanvas.renderAll();
    showToast(`Brand text "${val}" updated`, 'success');
  });

  if (posXSlider) posXSlider.oninput = () => {
    if (!brandLogoObject) return;
    const x = (parseFloat(posXSlider.value) / 100) * (canvaCanvas._logicalWidth || 1536);
    brandLogoObject.set('left', x);
    document.getElementById('canvaBrandLogoPosXVal').textContent = `${Math.round(x)} px`;
    canvaCanvas.renderAll();
  };
  if (posYSlider) posYSlider.oninput = () => {
    if (!brandLogoObject) return;
    const y = (parseFloat(posYSlider.value) / 100) * (canvaCanvas._logicalHeight || 512);
    brandLogoObject.set('top', y);
    document.getElementById('canvaBrandLogoPosYVal').textContent = `${Math.round(y)} px`;
    canvaCanvas.renderAll();
  };
  if (sizeSlider) sizeSlider.oninput = () => {
    if (!brandLogoObject) return;
    const sz = parseFloat(sizeSlider.value);
    brandLogoObject.scale(sz / (brandLogoObject.width || 200));
    document.getElementById('canvaBrandLogoSizeVal').textContent = `${Math.round(sz)} px`;
    canvaCanvas.renderAll();
  };
  if (rotSlider) rotSlider.oninput = () => {
    if (!brandLogoObject) return;
    const ang = parseFloat(rotSlider.value);
    brandLogoObject.set('angle', ang);
    document.getElementById('canvaBrandLogoRotVal').textContent = `${Math.round(ang)}°`;
    canvaCanvas.renderAll();
  };

  document.getElementById('canvaRestoreFactoryLogoBtn')?.addEventListener('click', () => {
    if (brandLogoObject) canvaCanvas.remove(brandLogoObject);
    fabric.loadSVGFromURL('/static/assets/gomzi_logo.svg', (objects, options) => {
      const logo = fabric.util.groupSVGElements(objects, options);
      logo.set({ left: 668, top: 36, scaleX: 0.62, scaleY: 0.62, selectable: true, assetType: 'brand_logo', isBrandLogo: true, name: 'GOMZI NUTRITION Logo' });
      brandLogoObject = logo;
      canvaCanvas.add(logo);
      canvaCanvas.setActiveObject(logo);
      canvaCanvas.renderAll();
      document.getElementById('brandLogoPreviewImg').src = '/static/assets/gomzi_logo.svg';
      showToast('Restored official GOMZI logo', 'success');
    });
  });

  document.getElementById('canvaUploadBrandLogoInput')?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      fabric.Image.fromURL(ev.target.result, (img) => {
        if (brandLogoObject) canvaCanvas.remove(brandLogoObject);
        img.scaleToWidth(180);
        img.set({ left: 668, top: 36, selectable: true, assetType: 'brand_logo', isBrandLogo: true, name: `Logo: ${file.name}` });
        brandLogoObject = img;
        canvaCanvas.add(img);
        canvaCanvas.setActiveObject(img);
        canvaCanvas.renderAll();
        document.getElementById('brandLogoPreviewImg').src = ev.target.result;
        showToast('Updated brand logo', 'success');
      });
    };
    reader.readAsDataURL(file);
  });
}

function syncBrandSliders(obj) {
  if (!obj || !canvaCanvas) return;
  const cw = canvaCanvas._logicalWidth || 1536;
  const ch = canvaCanvas._logicalHeight || 512;
  const w = Math.round((obj.width || 200) * (obj.scaleX || 1));
  const px = document.getElementById('canvaBrandLogoPosXSlider');
  const py = document.getElementById('canvaBrandLogoPosYSlider');
  const ps = document.getElementById('canvaBrandLogoSizeSlider');
  const pr = document.getElementById('canvaBrandLogoRotSlider');
  if (px) px.value = Math.round((obj.left / cw) * 100);
  if (py) py.value = Math.round((obj.top / ch) * 100);
  if (ps) ps.value = w;
  if (pr) pr.value = Math.round(obj.angle || 0);
}

function initDrawerToolBindings() {
  // Layer ordering & search
  document.getElementById('layerBringForwardBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (act) { canvaCanvas.bringForward(act); canvaCanvas.renderAll(); refreshLayersList(); }
  });
  document.getElementById('layerSendBackwardBtn')?.addEventListener('click', () => {
    const act = canvaCanvas?.getActiveObject();
    if (act) { canvaCanvas.sendBackwards(act); canvaCanvas.renderAll(); refreshLayersList(); }
  });
  document.getElementById('layersSearchInput')?.addEventListener('input', refreshLayersList);

  // Text Drawer buttons
  document.getElementById('canvaAddHeadingBtn')?.addEventListener('click', () => {
    const tb = new fabric.Textbox('ADD HEADING TEXT', { left: 540, top: 180, width: 420, fontSize: 38, fontFamily: 'Montserrat', fontWeight: '800', fill: '#202820', assetType: 'editable_text', name: 'Heading' });
    canvaCanvas.add(tb); canvaCanvas.setActiveObject(tb); canvaCanvas.renderAll();
  });
  document.getElementById('canvaAddSubheadingBtn')?.addEventListener('click', () => {
    const tb = new fabric.Textbox('Add Subheading Text', { left: 540, top: 240, width: 340, fontSize: 22, fontFamily: 'Montserrat', fontWeight: '700', fill: '#304331', assetType: 'editable_text', name: 'Subheading' });
    canvaCanvas.add(tb); canvaCanvas.setActiveObject(tb); canvaCanvas.renderAll();
  });
  document.getElementById('canvaAddBodyBtn')?.addEventListener('click', () => {
    const tb = new fabric.Textbox('Product usage instructions and descriptive details.', { left: 540, top: 290, width: 320, fontSize: 13.5, fontFamily: 'Inter', fontWeight: '500', fill: '#68736D', assetType: 'editable_text', name: 'Body Copy' });
    canvaCanvas.add(tb); canvaCanvas.setActiveObject(tb); canvaCanvas.renderAll();
  });

  // Shapes Drawer
  document.getElementById('shapeAddRectBtn')?.addEventListener('click', () => {
    const r = new fabric.Rect({ left: 650, top: 180, width: 220, height: 110, rx: 10, ry: 10, fill: '#74883D', assetType: 'decorative_graphic', name: 'Rectangle Shape' });
    canvaCanvas.add(r); canvaCanvas.setActiveObject(r); canvaCanvas.renderAll();
  });
  document.getElementById('shapeAddCircleBtn')?.addEventListener('click', () => {
    const c = new fabric.Circle({ left: 680, top: 180, radius: 55, fill: '#25372A', assetType: 'decorative_graphic', name: 'Circle Badge' });
    canvaCanvas.add(c); canvaCanvas.setActiveObject(c); canvaCanvas.renderAll();
  });
  document.getElementById('shapeAddBadgeBtn')?.addEventListener('click', () => {
    const p = new fabric.Rect({ left: 640, top: 220, width: 240, height: 40, rx: 20, ry: 20, fill: '#74883D', assetType: 'decorative_graphic', name: 'Pill Banner' });
    canvaCanvas.add(p); canvaCanvas.setActiveObject(p); canvaCanvas.renderAll();
  });
  document.getElementById('shapeAddDividerBtn')?.addEventListener('click', () => {
    const l = new fabric.Rect({ left: 550, top: 260, width: 380, height: 3, fill: '#74883D', assetType: 'decorative_graphic', name: 'Accent Divider' });
    canvaCanvas.add(l); canvaCanvas.setActiveObject(l); canvaCanvas.renderAll();
  });

  // Background Drawer color swatches & presets
  document.querySelectorAll('.bg-color-btn').forEach(btn => {
    btn.onclick = () => {
      canvaCanvas.setBackgroundColor(btn.getAttribute('data-bg'), () => {
        canvaCanvas.renderAll();
        if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
      });
    };
  });
  document.getElementById('bgStudioPresetSelect')?.addEventListener('change', async (e) => {
    const preset = e.target.value;
    if (!preset) return;
    showToast('Generating studio background...', 'info');
    try {
      const res = await fetch('/api/canva/bg-generator', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset, width: canvaCanvas._logicalWidth || 1536, height: canvaCanvas._logicalHeight || 512 })
      });
      const d = await res.json();
      if (d.image_url) {
        fabric.Image.fromURL(d.image_url, (img) => {
          canvaCanvas.setBackgroundImage(img, () => {
            canvaCanvas.renderAll();
            if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
          });
        });
      }
    } catch (err) {
      showToast(`Background generation error: ${err.message}`, 'error');
    }
  });

  // Quick Barcode Generator into Images drawer
  document.getElementById('btnInsertBarcode')?.addEventListener('click', () => {
    const val = (document.getElementById('barcodeValueInput')?.value || '8901234567890').trim();
    const tmpSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    if (window.JsBarcode) {
      try {
        JsBarcode(tmpSvg, val, { format: 'CODE128', lineColor: '#202820', width: 2, height: 48, displayValue: true });
        const xml = new XMLSerializer().serializeToString(tmpSvg);
        fabric.loadSVGFromString(xml, (objs, opts) => {
          const g = fabric.util.groupSVGElements(objs, opts);
          g.set({ left: 1180, top: 340, name: `Barcode ${val}`, assetType: 'barcode_box' });
          canvaCanvas.add(g);
          canvaCanvas.setActiveObject(g);
          canvaCanvas.renderAll();
          showToast('Inserted vector barcode', 'success');
        });
      } catch (err) { showToast(`Invalid barcode: ${err.message}`, 'error'); }
    }
  });

  // Nutrition Drawer quick insert button
  document.getElementById('canvaAddNutritionTableBtn')?.addEventListener('click', () => {
    const sSize = document.getElementById('nutServingSizeInput')?.value || '1 Scoop (33g)';
    const sCount = document.getElementById('nutServingsInput')?.value || '30';
    const customRows = document.getElementById('nutRowsTextarea')?.value || 'Energy: -- kcal\nProtein: -- g\nCarbohydrate: -- g\nTotal Fat: -- g';
    const txt = `NUTRITIONAL INFORMATION\nServing Size: ${sSize} | Servings: ${sCount}\n\n${customRows}`;
    const tb = new fabric.Textbox(txt, {
      left: 60, top: 90, width: 340, fontSize: 13, fontFamily: 'Inter', fontWeight: '600',
      fill: '#202820', backgroundColor: '#FFFFFF', padding: 12, assetType: 'table_box', name: 'Nutrition Facts Table'
    });
    canvaCanvas.add(tb);
    canvaCanvas.setActiveObject(tb);
    canvaCanvas.renderAll();
    showToast('Added editable Nutrition Facts table', 'success');
  });
  document.getElementById('canvaAddVegBtn')?.addEventListener('click', () => {
    const rect = new fabric.Rect({ left: 1300, top: 360, width: 28, height: 28, rx: 4, ry: 4, fill: '#FFFFFF', stroke: '#459568', strokeWidth: 2 });
    const dot = new fabric.Circle({ left: 1307, top: 367, radius: 7, fill: '#459568' });
    const grp = new fabric.Group([rect, dot], { name: 'Veg Indicator Mark', assetType: 'seal_graphic' });
    canvaCanvas.add(grp);
    canvaCanvas.setActiveObject(grp);
    canvaCanvas.renderAll();
  });
}

/* ============================================================================
   CLEAN CANVAS DATA URL & PROJECT PERSISTENCE & EXPORT
   ============================================================================ */
function getCleanCanvasDataURL(multiplier = 1) {
  if (!canvaCanvas) return null;
  const prevZoom = canvaCanvas.getZoom();
  const prevW = canvaCanvas.width;
  const prevH = canvaCanvas.height;
  const logW = canvaCanvas._logicalWidth || 1536;
  const logH = canvaCanvas._logicalHeight || 512;

  const activeObj = canvaCanvas.getActiveObject();
  canvaCanvas.discardActiveObject();
  const hidden = [];
  canvaCanvas.getObjects().forEach(o => {
    if ((o.isGuideLine || o.isTempOcrBox || o.excludeFromExport) && o.visible !== false) { o.visible = false; hidden.push(o); }
  });

  canvaCanvas.setDimensions({ width: logW, height: logH });
  canvaCanvas.setZoom(1);
  canvaCanvas.renderAll();

  const dataUrl = canvaCanvas.toDataURL({ format: 'png', multiplier: multiplier });

  hidden.forEach(o => { o.visible = true; });
  canvaCanvas.setDimensions({ width: prevW, height: prevH });
  canvaCanvas.setZoom(prevZoom);
  if (activeObj) canvaCanvas.setActiveObject(activeObj);
  canvaCanvas.renderAll();
  return dataUrl;
}

async function saveCurrentProject() {
  if (!canvaCanvas) return;
  setSaveStatus('saving');
  const title = document.getElementById('canvaDocTitleInput')?.value || 'GOMZI Whey Protein 1kg';
  const thumb = getCleanCanvasDataURL(0.4);
  try {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: activeProjectId,
        title,
        product: title,
        container: document.getElementById('bottomCanvasDimsLabel')?.textContent || '1536 × 512 px',
        brand_name: document.getElementById('canvaBrandNameInput')?.value || 'GOMZI NUTRITION',
        container_color: document.getElementById('threeBodyColorPicker')?.value || '#181A1C',
        canvas_json: {
          ...canvaCanvas.toDatalessJSON([
            'assetType', 'isBrandLogo', 'name', 'layerCategory', 'semanticRole',
            'ocrConfidence', 'needsReview', 'editable', 'selectable', 'lockMovementX'
          ]),
          width: canvaCanvas._logicalWidth || 1536,
          height: canvaCanvas._logicalHeight || 512,
          physicalWidthMm: canvaCanvas._physicalWidthMm || 160.0,
          physicalHeightMm: canvaCanvas._physicalHeightMm || 65.0,
          artifactId: canvaCanvas._artifactId || null,
        },
        thumbnail: thumb,
      }),
    });
    const d = await res.json();
    if (!d.success) throw new Error(d.error || 'Save failed');
    activeProjectId = d.project.id;
    const now = new Date();
    const hm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    setSaveStatus('saved', hm);
    showToast('Project saved cleanly', 'success');
  } catch (e) {
    setSaveStatus('unsaved');
    showToast(`Save error: ${e.message}`, 'error');
  }
}

function initExportControls() {
  const btn = document.getElementById('canvaExportMenuBtn');
  const dd = document.getElementById('canvaExportDropdown');
  if (btn && dd) {
    btn.onclick = (e) => { e.stopPropagation(); dd.style.display = dd.style.display === 'flex' ? 'none' : 'flex'; };
    dd.addEventListener('click', (e) => {
      if (e.target && (e.target.tagName === 'SELECT' || e.target.tagName === 'LABEL')) {
        e.stopPropagation();
      }
    });
    document.addEventListener('click', () => { if (dd) dd.style.display = 'none'; });
  }

  // Probe optional Windows CorelDRAW Desktop Bridge status honestly
  const openCorelBtn = document.getElementById('canvaOpenCorelBtn');
  const nativeCdrBtn = document.getElementById('canvaDownloadNativeCdrBtn');
  fetch('/api/coreldraw/status')
    .then(r => r.json())
    .then(status => {
      const available = Boolean(status && status.native_cdr_available);
      const msg = (status && status.message) || 'Requires Windows CorelDRAW Desktop Bridge + licensed CorelDRAW.';
      [openCorelBtn, nativeCdrBtn].forEach((b) => {
        if (!b) return;
        b.disabled = !available;
        b.style.opacity = available ? '1' : '0.55';
        b.style.cursor = available ? 'pointer' : 'not-allowed';
        b.title = available ? `CorelDRAW ${status.coreldraw_version || ''} connected` : msg;
      });
    })
    .catch(() => {
      [openCorelBtn, nativeCdrBtn].forEach((b) => {
        if (!b) return;
        b.disabled = true;
        b.style.opacity = '0.55';
      });
    });

  function dlBlob(blob, filename) {
    const u = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = u;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(u);
  }

  function _getScenePayload(docTitle) {
    return {
      ...canvaCanvas.toDatalessJSON(['assetType', 'isBrandLogo', 'name', 'layerCategory', 'semanticRole', 'editable']),
      width: canvaCanvas._logicalWidth || 1536,
      height: canvaCanvas._logicalHeight || 512,
      physicalWidthMm: canvaCanvas._physicalWidthMm || 160.0,
      physicalHeightMm: canvaCanvas._physicalHeightMm || 65.0,
      title: docTitle,
    };
  }

  async function runExport(fmt) {
    if (!canvaCanvas) return;
    const docTitle = (document.getElementById('canvaDocTitleInput')?.value || 'GOMZI_Label').replace(/[^a-zA-Z0-9_-]/g, '_');

    if (fmt === 'json') {
      const fullJson = {
        ...canvaCanvas.toDatalessJSON(['assetType', 'isBrandLogo', 'name', 'layerCategory', 'semanticRole', 'editable', 'selectable']),
        width: canvaCanvas._logicalWidth || 1536,
        height: canvaCanvas._logicalHeight || 512,
        physicalWidthMm: canvaCanvas._physicalWidthMm || 160.0,
        physicalHeightMm: canvaCanvas._physicalHeightMm || 65.0,
      };
      const jsonBlob = new Blob([JSON.stringify(fullJson, null, 2)], { type: 'application/json' });
      dlBlob(jsonBlob, `${docTitle}_project.json`);
      return showToast('Exported editable project JSON', 'success');
    }
    if (fmt === 'svg' || fmt === 'svg_outlined' || fmt === 'pdf' || fmt === 'cdr') {
      const vecFmtMap = {
        svg: 'svg_editable',
        svg_outlined: 'svg_outlined',
        pdf: 'pdf_vector',
        cdr: 'cdr_exchange',
      };
      const targetVecFmt = vecFmtMap[fmt];
      showToast(`Building CorelDRAW-compatible ${fmt.toUpperCase()} vector export...`, 'info', 4000);
      const sceneJson = _getScenePayload(docTitle);
      try {
        const res = await fetch('/api/canva/export-vector', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fabric_json: sceneJson,
            format: targetVecFmt,
            width_mm: sceneJson.physicalWidthMm,
            height_mm: sceneJson.physicalHeightMm,
            filename: docTitle,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const dlNameMap = {
          svg: `${docTitle}.svg`,
          svg_outlined: `${docTitle}_outlined.svg`,
          pdf: `${docTitle}_vector.pdf`,
          cdr: `${docTitle}_coreldraw_bundle.zip`,
        };
        dlBlob(blob, dlNameMap[fmt]);
        showToast(`Downloaded ${dlNameMap[fmt]} cleanly!`, 'success');
      } catch (e) {
        showToast(`Vector export error: ${e.message}`, 'error');
      }
      return;
    }

    if (fmt === 'open_coreldraw' || fmt === 'native_cdr') {
      const sceneJson = _getScenePayload(docTitle);
      const endpoint = fmt === 'open_coreldraw' ? '/api/coreldraw/open' : '/api/coreldraw/export-cdr';
      showToast(fmt === 'open_coreldraw' ? 'Opening artwork in CorelDRAW...' : 'Exporting native .cdr via CorelDRAW Bridge...', 'info', 5000);
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fabric_json: sceneJson,
            width_mm: sceneJson.physicalWidthMm,
            height_mm: sceneJson.physicalHeightMm,
            filename: docTitle,
          }),
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `HTTP ${res.status}`);
        }
        if (fmt === 'open_coreldraw') {
          const d = await res.json();
          showToast(`Opened in CorelDRAW ${d.coreldraw_version || ''}!`, 'success');
        } else {
          const blob = await res.blob();
          dlBlob(blob, `${docTitle}.cdr`);
          showToast(`Downloaded native ${docTitle}.cdr!`, 'success');
        }
      } catch (e) {
        showToast(`CorelDRAW Bridge: ${e.message}`, 'error', 6000);
      }
      return;
    }

    const dpi = parseInt(document.getElementById('exportPrintDpiSelect')?.value || '300', 10);
    const bleedMm = parseFloat(document.getElementById('exportPrintBleedSelect')?.value || '0');
    const wMm = canvaCanvas._physicalWidthMm || 160.0;
    const hMm = canvaCanvas._physicalHeightMm || 65.0;
    showToast(`Rendering ${fmt.toUpperCase()} (${dpi} DPI, ${bleedMm}mm bleed)...`, 'info', 4000);
    const dataUrl = getCleanCanvasDataURL(2);
    try {
      const res = await fetch('/api/canva/export-print', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_data: dataUrl,
          format: fmt,
          filename: docTitle,
          width_mm: wMm,
          height_mm: hMm,
          dpi,
          bleed_mm: bleedMm,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const ext = fmt === 'png_transparent' ? 'png' : fmt;
      const suffix = fmt === 'png_transparent' ? `_${dpi}dpi_transparent` : `_${dpi}dpi`;
      dlBlob(blob, `${docTitle}${suffix}.${ext}`);
      showToast(`Downloaded ${fmt.toUpperCase()} (${dpi} DPI) print master`, 'success');
    } catch (e) {
      showToast(`Export error: ${e.message}`, 'error');
    }
  }

  document.getElementById('canvaExportPngBtn')?.addEventListener('click', () => runExport('png'));
  document.getElementById('canvaExportPngTransBtn')?.addEventListener('click', () => runExport('png_transparent'));
  document.getElementById('canvaExportJpgBtn')?.addEventListener('click', () => runExport('jpg'));
  document.getElementById('canvaExportTiffBtn')?.addEventListener('click', () => runExport('tiff'));
  document.getElementById('canvaExportSvgBtn')?.addEventListener('click', () => runExport('svg'));
  document.getElementById('canvaExportSvgOutlinedBtn')?.addEventListener('click', () => runExport('svg_outlined'));
  document.getElementById('canvaExportPdfBtn')?.addEventListener('click', () => runExport('pdf'));
  document.getElementById('canvaExportCdrBtn')?.addEventListener('click', () => runExport('cdr'));
  openCorelBtn?.addEventListener('click', () => runExport('open_coreldraw'));
  nativeCdrBtn?.addEventListener('click', () => runExport('native_cdr'));
  document.getElementById('canvaExportJsonBtn')?.addEventListener('click', () => runExport('json'));
}
