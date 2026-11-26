/* ============================================================================
   studio_modules.js - GOMZI BOB Business Modules:
   Dashboard (Real DB Metrics), My Designs (Grid/List/Filter), Templates,
   Brand Kit, Asset Library, Prompt Library, Nutrition Facts Builder,
   API Management & Settings
   ============================================================================ */

let savedDesignsCache = [];
let myDesignsViewMode = 'grid';

async function loadDashboardStats() {
  try {
    const [statsRes, projRes] = await Promise.all([
      fetch('/api/dashboard/stats'),
      fetch('/api/projects'),
    ]);
    const d = await statsRes.json();
    const pData = await projRes.json();

    const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = String(val); };
    setVal('dashTotalProjects', d.total_projects ?? 0);
    setVal('dashAiGenerated', d.ai_generated_designs ?? 0);
    setVal('dashCompletedJobs', d.completed_jobs ?? 0);
    setVal('dashFailedJobs', d.failed_jobs ?? 0);
    setVal('dashApiCallsTotal', d.api_calls_total ?? 0);
    setVal('dashMonthlyCost', `$${Number(d.ai_cost_month_usd || 0).toFixed(4)}`);
    setVal('dashTodayCost', `Today: $${Number(d.ai_cost_today_usd || 0).toFixed(4)}`);
    setVal('dashActiveProviders', `${d.configured_providers ?? 0} Active (${d.provider_status || 'Check Keys'})`);

    // Recent Projects Table
    const tbody = document.getElementById('dashRecentProjectsTableBody');
    if (tbody) {
      tbody.innerHTML = '';
      const projects = pData.projects || [];
      if (!projects.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#68736D;padding:24px;">No saved designs in database yet. Save a design in Design Studio to see it here.</td></tr>';
      } else {
        projects.slice(0, 6).forEach(p => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong>${p.title}</strong></td>
            <td>${p.container || '1536 × 512 px'}</td>
            <td><span class="badge-soft badge-olive">${p.brand_name || 'GOMZI NUTRITION'}</span></td>
            <td>${p.updated_at || '-'}</td>
            <td><button class="table-action-btn" onclick="openProjectById('${p.id}')">Open</button></td>
          `;
          tbody.appendChild(tr);
        });
      }
    }

    // Recent Activity Table
    const actBody = document.getElementById('dashRecentActivityBody');
    if (actBody) {
      actBody.innerHTML = '';
      const logs = d.recent_activity || [];
      if (!logs.length) {
        actBody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#68736D;padding:18px;">No AI API calls logged in this database yet.</td></tr>';
      } else {
        logs.forEach(l => {
          const badge = l.status === 'success' ? 'badge-success' : 'badge-err';
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong>${l.provider}</strong> (${l.model || '-'})</td>
            <td>${l.mode}</td>
            <td><span class="badge-soft ${badge}">${l.status}</span></td>
            <td>${l.latency_ms} ms · ${l.created_at}</td>
          `;
          actBody.appendChild(tr);
        });
      }
    }
  } catch (e) {
    console.error('Dashboard load error:', e);
  }
}

/* ============================================================================
   MY DESIGNS GALLERY (Grid / List, Search, Sort, Open, Duplicate, Delete)
   ============================================================================ */
async function loadMyDesigns() {
  try {
    const res = await fetch('/api/projects');
    const d = await res.json();
    savedDesignsCache = d.projects || [];
    renderMyDesignsGrid();
  } catch (e) {
    console.error('Load My Designs error:', e);
  }
}

function renderMyDesignsGrid() {
  const grid = document.getElementById('myDesignsGrid');
  if (!grid) return;
  const search = (document.getElementById('myDesignsSearchInput')?.value || '').trim().toLowerCase();
  const sortMode = document.getElementById('myDesignsSortSelect')?.value || 'newest';

  let list = savedDesignsCache.filter(p => !search || (p.title || '').toLowerCase().includes(search) || (p.brand_name || '').toLowerCase().includes(search));
  if (sortMode === 'az') list.sort((a, b) => (a.title || '').localeCompare(b.title || ''));

  grid.style.gridTemplateColumns = myDesignsViewMode === 'list' ? '1fr' : 'repeat(auto-fill, minmax(270px, 1fr))';
  grid.innerHTML = '';

  if (!list.length) {
    grid.innerHTML = '<div class="content-section-card" style="grid-column:1/-1;text-align:center;padding:36px;color:#68736D;">No saved designs match your query. Open Design Studio and save your project to persist it here.</div>';
    return;
  }

  list.forEach(p => {
    const card = document.createElement('div');
    card.className = 'content-section-card';
    const thumb = p.thumbnail
      ? `<img src="${p.thumbnail}" style="width:100%;height:124px;object-fit:contain;background:#F5F6F8;border-radius:6px;border:1px solid #E0E5E7;" />`
      : `<div style="height:124px;background:#EDF1F5;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#68736D;font-weight:600;">No Preview</div>`;

    card.innerHTML = `
      ${thumb}
      <div style="font-size:13.5px;font-weight:700;color:#202820;">${p.title}</div>
      <div style="font-size:11px;color:#68736D;">${p.brand_name || 'GOMZI NUTRITION'} · ${p.updated_at || ''}</div>
      <div style="display:flex;gap:6px;margin-top:4px;">
        <button type="button" class="btn-olive-primary" style="flex:1;padding:5px 8px;font-size:11px;" onclick="openProjectById('${p.id}')">Open Editor</button>
        <button type="button" class="btn-outline-clean" style="padding:5px 8px;font-size:11px;" onclick="duplicateProjectById('${p.id}')">Duplicate</button>
        <button type="button" class="btn-outline-clean" style="padding:5px 8px;font-size:11px;color:#D65D5D;" onclick="deleteProjectById('${p.id}')">Delete</button>
      </div>
    `;
    grid.appendChild(card);
  });
}

async function openProjectById(projId) {
  showToast('Opening project...', 'info');
  try {
    const res = await fetch(`/api/projects/${projId}`);
    const data = await res.json();
    activeProjectId = data.id;
    document.getElementById('canvaDocTitleInput').value = data.title || 'Untitled Project';

    if (data.canvas_json && data.canvas_json.objects) {
      isHistoryLocked = true;
      if (data.canvas_json.width && data.canvas_json.height) {
        resizeLogicalArtboard(data.canvas_json.width, data.canvas_json.height);
      }
      canvaCanvas._physicalWidthMm = data.canvas_json.physicalWidthMm || 160.0;
      canvaCanvas._physicalHeightMm = data.canvas_json.physicalHeightMm || 65.0;
      canvaCanvas._artifactId = data.canvas_json.artifactId || null;
      canvaCanvas.loadFromJSON(data.canvas_json, () => {
        isHistoryLocked = false;
        canvaCanvas.renderAll();
        brandLogoObject = canvaCanvas.getObjects().find(o => o.isBrandLogo || o.assetType === 'brand_logo');
        refreshLayersList();
        fitCanvasToStage();
        setSaveStatus('saved');
        if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
        switchMainView('studio');
        showToast(`Opened "${data.title}"`, 'success');
      });
    } else {
      switchMainView('studio');
    }
  } catch (e) {
    showToast(`Failed to open project: ${e.message}`, 'error');
  }
}

async function duplicateProjectById(projId) {
  const res = await fetch(`/api/projects/${projId}/duplicate`, { method: 'POST' });
  const d = await res.json();
  if (d.success) { showToast('Project duplicated', 'success'); loadMyDesigns(); }
}

async function deleteProjectById(projId) {
  if (!confirm('Delete this saved design permanently?')) return;
  const res = await fetch(`/api/projects/${projId}`, { method: 'DELETE' });
  const d = await res.json();
  if (d.success) { showToast('Project deleted', 'info'); loadMyDesigns(); }
}

/* ============================================================================
   TEMPLATES PAGE
   ============================================================================ */
async function loadTemplatesPage() {
  const grid = document.getElementById('templatesCatalogGrid');
  if (!grid) return;
  const res = await fetch('/api/products');
  const d = await res.json();
  grid.innerHTML = '';

  (d.products || []).forEach(p => {
    const card = document.createElement('div');
    card.className = 'content-section-card';
    card.innerHTML = `
      <span class="badge-soft badge-olive" style="align-self:flex-start;">${p.category}</span>
      <div style="font-size:15px;font-weight:700;color:#202820;">${p.name}</div>
      <div style="font-size:11.5px;color:#68736D;">${p.spec} · Ratio ${p.ratio}</div>
      <button type="button" class="btn-olive-primary" style="margin-top:6px;">Use Template in Studio</button>
    `;
    card.querySelector('button').onclick = () => {
      document.getElementById('canvaDocTitleInput').value = `GOMZI ${p.name}`;
      loadGomziWheyTemplate();
      switchMainView('studio');
      showToast(`Loaded ${p.name} template`, 'success');
    };
    grid.appendChild(card);
  });
}

/* ============================================================================
   BRAND KIT PAGE (SQLite Backed)
   ============================================================================ */
async function loadBrandKitPage() {
  const grid = document.getElementById('brandKitsPageGrid');
  if (!grid) return;
  const res = await fetch('/api/brand-kits');
  const d = await res.json();
  grid.innerHTML = '';

  (d.brand_kits || []).forEach(kit => {
    const card = document.createElement('div');
    card.className = 'content-section-card';
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <strong style="font-size:15px;">${kit.name}</strong>
        ${kit.is_default ? '<span class="badge-soft badge-success">Default Brand</span>' : ''}
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <span style="width:20px;height:20px;border-radius:4px;background:${kit.primary_color};border:1px solid #cbd5e1;"></span>
        <span style="width:20px;height:20px;border-radius:4px;background:${kit.secondary_color};border:1px solid #cbd5e1;"></span>
        <span style="font-size:11.5px;color:#68736D;">Font: ${kit.font_family}</span>
      </div>
      <div style="background:#FAF8F1;border:1px dashed #CBD3D6;border-radius:8px;padding:12px;text-align:center;">
        <img src="${kit.logo_url}" style="max-height:48px;max-width:180px;object-fit:contain;" />
      </div>
      <button type="button" class="btn-outline-clean">Apply Brand to Active Studio</button>
    `;
    card.querySelector('button').onclick = () => {
      const inp = document.getElementById('canvaBrandNameInput');
      if (inp) inp.value = kit.name;
      switchMainView('studio');
      switchStudioDrawer('brand');
      showToast(`Selected Brand Kit: ${kit.name}`, 'success');
    };
    grid.appendChild(card);
  });
}

/* ============================================================================
   ASSET LIBRARY PAGE
   ============================================================================ */
async function loadAssetLibraryPage() {
  const grid = document.getElementById('assetLibraryGrid');
  if (!grid) return;
  const res = await fetch('/api/assets/library');
  const d = await res.json();
  grid.innerHTML = '';
  const assets = d.assets || [];
  if (!assets.length) {
    grid.innerHTML = '<div class="content-section-card" style="grid-column:1/-1;text-align:center;padding:30px;color:#68736D;">No assets uploaded or generated yet.</div>';
    return;
  }
  assets.forEach(a => {
    const card = document.createElement('div');
    card.className = 'content-section-card';
    card.innerHTML = `
      <img src="${a.url}" style="width:100%;height:110px;object-fit:contain;background:#F5F6F8;border-radius:6px;border:1px solid #E0E5E7;" />
      <div style="font-size:12px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${a.name}</div>
      <div style="font-size:10.5px;color:#68736D;">${a.source} · ${a.width}×${a.height}px</div>
      <div style="display:flex;gap:6px;">
        <button type="button" class="btn-olive-primary full-open" style="flex:1;padding:5px;font-size:11px;">Open Full Label</button>
        <button type="button" class="btn-outline-clean add-sticker" style="padding:5px 8px;font-size:11px;">Add Layer</button>
      </div>
    `;
    card.querySelector('.full-open').onclick = () => { switchMainView('studio'); openImageAsFullLabel(a.url, a.name); };
    card.querySelector('.add-sticker').onclick = () => { switchMainView('studio'); addStickerToCanvas(a.url, a.name); };
    grid.appendChild(card);
  });
}

/* ============================================================================
   PROMPT LIBRARY PAGE
   ============================================================================ */
function loadPromptLibraryPage() {
  const listEl = document.getElementById('promptLibraryContainer');
  if (!listEl) return;
  const templates = [
    {
      title: 'GOMZI Whey Protein — Cream & Forest Green (3:1)',
      prompt: 'Create a flat 2D rectangular whey protein label for GOMZI NUTRITION, Belgian Chocolate flavour, 1 kg, soft warm cream and forest green palette, structured nutritional facts panel on left, bold product title center, clean highlights right. Flat artwork only, no 3D jar.'
    },
    {
      title: 'Biotin Capsules Pharmaceutical Label',
      prompt: 'Clean pharmaceutical 2D flat label design for Biotin Capsule 60 Capsules, Unflavoured, crisp white and royal amethyst purple wave footer, left nutritional table and description, right key benefits icons and batch box. Flat print artwork only.'
    },
    {
      title: 'Pre-Workout Sachet (70 × 110 mm)',
      prompt: 'High-energy sports nutrition flat 2D sachet front artwork, bold condensed typography, matte obsidian black and lime accent graphics, 70x110 mm print proportion. Flat artwork only, no pouch mockup.'
    }
  ];

  listEl.innerHTML = '';
  templates.concat(window.aiPromptHistory || []).forEach(item => {
    const card = document.createElement('div');
    card.className = 'content-section-card';
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <strong>${item.title || `Recent Prompt (${item.at || ''})`}</strong>
        <button type="button" class="table-action-btn">Use in AI Assistant</button>
      </div>
      <div style="font-size:12px;color:#68736D;line-height:1.45;">${item.prompt}</div>
    `;
    card.querySelector('button').onclick = () => {
      const ta = document.getElementById('aiPromptInput');
      if (ta) ta.value = item.prompt;
      switchMainView('ai-generator');
      showToast('Loaded prompt into AI Assistant', 'success');
    };
    listEl.appendChild(card);
  });
}

/* ============================================================================
   NUTRITION FACTS BUILDER PAGE
   ============================================================================ */
let nutritionBuilderRows = [
  { name: 'Energy', serving: '', per100g: '', rda: '' },
  { name: 'Protein', serving: '', per100g: '', rda: '' },
  { name: 'Carbohydrate', serving: '', per100g: '', rda: '' },
  { name: 'Total Sugars', serving: '', per100g: '', rda: '' },
  { name: 'Added Sugars', serving: '', per100g: '', rda: '' },
  { name: 'Total Fat', serving: '', per100g: '', rda: '' },
];

function loadNutritionPage() {
  renderNutritionBuilderRows();
}

function renderNutritionBuilderRows() {
  const tbody = document.getElementById('nutBuilderTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';
  nutritionBuilderRows.forEach((row, idx) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input class="studio-input" value="${row.name}" placeholder="Nutrient name" onchange="nutritionBuilderRows[${idx}].name=this.value" /></td>
      <td><input class="studio-input" value="${row.serving}" placeholder="e.g. 24 g" onchange="nutritionBuilderRows[${idx}].serving=this.value" /></td>
      <td><input class="studio-input" value="${row.per100g}" placeholder="e.g. 72.7 g" onchange="nutritionBuilderRows[${idx}].per100g=this.value" /></td>
      <td><input class="studio-input" value="${row.rda}" placeholder="e.g. 40%" onchange="nutritionBuilderRows[${idx}].rda=this.value" /></td>
      <td><button type="button" class="btn-outline-clean" style="color:#D65D5D;" onclick="nutritionBuilderRows.splice(${idx},1);renderNutritionBuilderRows();">Remove</button></td>
    `;
    tbody.appendChild(tr);
  });
}

function generateNutritionTableOnCanvas() {
  const srvSize = document.getElementById('pageNutServingSize')?.value || '1 Scoop';
  const srvCount = document.getElementById('pageNutServingsCount')?.value || '-';
  const lines = nutritionBuilderRows.map(r => `${r.name.padEnd(22, ' ')}  ${(r.serving || '--').padEnd(10, ' ')}  ${(r.per100g || '--').padEnd(10, ' ')}  ${r.rda || '--'}`).join('\n');
  const fullText = `NUTRITIONAL INFORMATION\nServing Size: ${srvSize} | Servings: ${srvCount}\nNutrient                Per Serve   Per 100g   %RDA\n${lines}`;

  const tb = new fabric.Textbox(fullText, {
    left: 54, top: 88, width: 390, fontSize: 12.5, fontFamily: 'Inter', fontWeight: '600',
    fill: '#202820', backgroundColor: '#FFFFFF', padding: 14, assetType: 'table_box', name: 'Nutrition Facts Table'
  });
  switchMainView('studio');
  canvaCanvas.add(tb);
  canvaCanvas.setActiveObject(tb);
  canvaCanvas.renderAll();
  showToast('Inserted formatted Nutrition Facts table on canvas', 'success');
}

/* ============================================================================
   API MANAGEMENT PAGE (Strict Real Backend State & Usage Logs)
   ============================================================================ */
async function loadApiManagementPage() {
  const listEl = document.getElementById('apiMgmtProvidersList');
  if (!listEl) return;
  try {
    const [pRes, uRes] = await Promise.all([fetch('/api/ai/providers'), fetch('/api/ai/usage')]);
    const pData = await pRes.json();
    const uData = await uRes.json();

    const totCalls = document.getElementById('apiMgmtTotalCalls');
    const totFail = document.getElementById('apiMgmtFailedCalls');
    const totCost = document.getElementById('apiMgmtTotalCost');
    if (totCalls) totCalls.textContent = uData.summary?.total_calls ?? 0;
    if (totFail) totFail.textContent = uData.summary?.total_failed ?? 0;
    if (totCost) totCost.textContent = `$${Number(uData.summary?.total_cost_usd || 0).toFixed(4)}`;

    listEl.innerHTML = '';
    (pData.providers || []).forEach(p => {
      const statusBadge = p.is_configured
        ? (p.is_enabled ? '<span class="badge-soft badge-success">Configured & Enabled</span>' : '<span class="badge-soft badge-warn">Disabled</span>')
        : '<span class="badge-soft badge-err">Not Configured</span>';

      const card = document.createElement('div');
      card.className = 'content-section-card';
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
          <div>
            <div style="display:flex;align-items:center;gap:8px;">
              <strong style="font-size:14.5px;">${p.name}</strong>
              ${statusBadge}
              ${p.is_default ? '<span class="badge-soft badge-olive">Default Provider</span>' : ''}
            </div>
            <div style="font-size:11.5px;color:#68736D;margin-top:2px;">${p.description}</div>
            <div style="font-size:11px;color:#68736D;margin-top:4px;">
              Models: ${(p.models || []).map(m => m.id).join(', ')} · Calls: <strong>${p.usage?.calls || 0}</strong> · Failed: <strong>${p.usage?.failed || 0}</strong>
            </div>
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <button type="button" class="btn-outline-clean test-btn">Test Connection</button>
            ${p.id !== 'auto' ? `<button type="button" class="btn-outline-clean toggle-btn">${p.is_enabled ? 'Disable' : 'Enable'}</button>` : ''}
            ${!p.is_default ? '<button type="button" class="table-action-btn def-btn">Set Default</button>' : ''}
          </div>
        </div>
        ${p.env_var_name ? `
        <div style="display:flex;gap:8px;align-items:center;background:#F5F6F8;border-radius:8px;padding:8px 10px;">
          <span style="font-size:11px;font-weight:700;color:#202820;min-width:140px;">${p.env_var_name}</span>
          <span style="font-family:monospace;font-size:11.5px;color:#68736D;flex:1;">${p.masked_key || '(not set)'}</span>
          <input type="password" class="studio-input key-inp" style="width:200px;padding:5px 8px;" placeholder="Enter new API key" />
          <button type="button" class="btn-olive-primary save-key-btn" style="padding:5px 12px;">Save Key</button>
        </div>` : ''}
        <div class="conn-msg" style="display:none;font-size:11.5px;padding:6px 10px;border-radius:6px;"></div>
      `;

      card.querySelector('.test-btn')?.addEventListener('click', async () => {
        const box = card.querySelector('.conn-msg');
        box.style.display = 'block';
        box.style.background = '#EDF1F5';
        box.textContent = `Testing live connection to ${p.name}...`;
        const tr = await fetch('/api/ai/test-connection', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider: p.id }) });
        const td = await tr.json();
        box.style.background = td.success ? '#EAF6EF' : '#FDECEC';
        box.style.color = td.success ? '#2A6241' : '#9B2C2C';
        box.textContent = td.success ? `Connected (${td.latency_ms}ms): ${td.message}` : `Failed: ${td.message}`;
      });

      card.querySelector('.toggle-btn')?.addEventListener('click', async () => {
        await fetch('/api/ai/toggle-provider', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider: p.id, enabled: !p.is_enabled }) });
        loadApiManagementPage();
        if (typeof loadAiProviderCatalog === 'function') loadAiProviderCatalog();
      });

      card.querySelector('.def-btn')?.addEventListener('click', async () => {
        await fetch('/api/ai/save-config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider: p.id, set_default: true }) });
        loadApiManagementPage();
        if (typeof loadAiProviderCatalog === 'function') loadAiProviderCatalog();
        showToast(`${p.name} set as default provider`, 'success');
      });

      card.querySelector('.save-key-btn')?.addEventListener('click', async () => {
        const k = card.querySelector('.key-inp')?.value.trim();
        if (!k) return showToast('Enter a valid key', 'warn');
        await fetch('/api/ai/save-config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider: p.id, api_key: k }) });
        showToast(`Saved ${p.env_var_name} securely on server`, 'success');
        loadApiManagementPage();
        if (typeof loadAiProviderCatalog === 'function') loadAiProviderCatalog();
      });

      listEl.appendChild(card);
    });
  } catch (e) {
    console.error('API Mgmt error:', e);
  }
}

function loadSettingsPage() {
  const btn = document.getElementById('btnSaveWorkspaceSettings');
  if (btn) {
    btn.onclick = () => {
      const qual = document.getElementById('setting3dQuality')?.value || 'high';
      if (typeof threeRenderer !== 'undefined' && threeRenderer) {
        threeRenderer.setPixelRatio(qual === 'low' ? 1 : Math.min(window.devicePixelRatio || 1, 2));
      }
      showToast('Workspace & 3D quality settings updated', 'success');
    };
  }
}
