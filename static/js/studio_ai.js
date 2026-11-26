/* ============================================================================
   studio_ai.js - GOMZI BOB AI Design Assistant, Dynamic API/Model Selector,
   Multilingual Web Speech Input, Enhance Prompt & Non-Destructive AI Editing
   ============================================================================ */

window.gomziAiProviders = [];
window.currentAiMode = 'generate';
window.currentAiAspectRatio = '3:1';
window.aiReferenceAttachments = [];
window.aiPromptHistory = [];
let gomziSpeechRecognizer = null;
let isVoiceRecording = false;
let pendingAiEditResult = null;

async function initAiStudioEngine() {
  await loadAiProviderCatalog();
  initAiModeSelectors();
  initWebSpeechEngine();
  initPromptAttachments();
  initAiAspectRatioAndPresets();
  initAiComposerAndToolActions();
}

async function loadAiProviderCatalog() {
  try {
    const res = await fetch('/api/ai/providers');
    const data = await res.json();
    if (data.success && data.providers) {
      window.gomziAiProviders = data.providers;
      populateAiProviderDropdown(data.providers);
    }
  } catch (e) {
    console.error('Failed to load AI provider catalog:', e);
  }
}

function populateAiProviderDropdown(providers) {
  const pSelect = document.getElementById('aiProviderSelect');
  if (!pSelect) return;
  const prevVal = pSelect.value;
  pSelect.innerHTML = '';

  providers.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    const statusTag = !p.is_configured ? ' (Not Configured)' : (!p.is_enabled ? ' (Disabled)' : '');
    opt.textContent = `${p.name}${statusTag}`;
    if (prevVal && prevVal === p.id) opt.selected = true;
    else if (!prevVal && p.is_default) opt.selected = true;
    pSelect.appendChild(opt);
  });

  pSelect.onchange = () => updateModelsAndCapabilitiesForProvider(pSelect.value);
  updateModelsAndCapabilitiesForProvider(pSelect.value);
}

function updateModelsAndCapabilitiesForProvider(providerId) {
  const mSelect = document.getElementById('aiModelSelect');
  const qSelect = document.getElementById('aiQualitySelect');
  const oSelect = document.getElementById('aiOutputsSelect');
  const costTag = document.getElementById('aiModelCostTag');

  const provider = window.gomziAiProviders.find(p => p.id === providerId) || window.gomziAiProviders[0];
  if (!mSelect || !provider) return;

  mSelect.innerHTML = '';
  const imageModels = (provider.models || []).filter(m => m.type !== 'text');
  const modelsToShow = imageModels.length ? imageModels : (provider.models || []);

  modelsToShow.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = m.name;
    if (m.recommended || m.id === provider.default_model) opt.selected = true;
    mSelect.appendChild(opt);
  });

  function syncModelConstraints() {
    const m = modelsToShow.find(x => x.id === mSelect.value) || modelsToShow[0];
    if (!m) return;
    if (costTag) costTag.textContent = m.cost || 'Metered';

    if (qSelect && m.quality_options?.length) {
      qSelect.innerHTML = '';
      m.quality_options.forEach(q => {
        const qo = document.createElement('option');
        qo.value = q;
        qo.textContent = q;
        if (q.toLowerCase().includes('high') || q.toLowerCase().includes('ultra')) qo.selected = true;
        qSelect.appendChild(qo);
      });
    }
    if (oSelect) {
      const maxO = m.max_outputs || 1;
      oSelect.innerHTML = '';
      for (let i = 1; i <= maxO; i++) {
        const oo = document.createElement('option');
        oo.value = i;
        oo.textContent = String(i);
        oSelect.appendChild(oo);
      }
      oSelect.disabled = maxO <= 1;
    }

    // Validate aspect ratio options against selected model
    const arSel = document.getElementById('aiAspectRatioSelect');
    if (arSel && m.aspect_ratios?.length && !m.aspect_ratios.includes('custom')) {
      Array.from(arSel.options).forEach(opt => {
        const r = opt.value;
        const ok = r === 'custom' || m.aspect_ratios.includes(r);
        opt.disabled = !ok;
      });
    } else if (arSel) {
      Array.from(arSel.options).forEach(opt => { opt.disabled = false; });
    }
  }

  mSelect.onchange = syncModelConstraints;
  syncModelConstraints();
}

function initAiModeSelectors() {
  const btns = document.querySelectorAll('.ai-mode-btn, .mode-chip-btn');
  const generateSection = document.getElementById('aiGenerateFieldsWrap');
  const editTargetsWrap = document.getElementById('aiEditTargetFieldsWrap');
  const targetInputWrap = document.getElementById('aiEditTargetInputGroup');
  const replaceInputWrap = document.getElementById('aiEditReplaceInputGroup');
  const targetLabel = document.getElementById('aiEditTargetLabel');
  const replaceLabel = document.getElementById('aiEditReplaceLabel');
  const submitBtnLabel = document.getElementById('btnGenerateArtworkLabel');

  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.getAttribute('data-mode');
      window.currentAiMode = mode;
      btns.forEach(b => b.classList.toggle('active', b.getAttribute('data-mode') === mode));

      if (mode === 'generate') {
        if (generateSection) generateSection.style.display = 'flex';
        if (editTargetsWrap) editTargetsWrap.style.display = 'none';
        if (submitBtnLabel) submitBtnLabel.textContent = 'Generate Design';
      } else {
        if (editTargetsWrap) editTargetsWrap.style.display = 'flex';
        if (targetInputWrap) targetInputWrap.style.display = (mode === 'add') ? 'none' : 'block';
        if (replaceInputWrap) replaceInputWrap.style.display = (mode === 'remove') ? 'none' : 'block';

        if (targetLabel) {
          targetLabel.textContent = mode === 'perfect_text' ? 'Original Text on Label' : 'Target Element to ' + (mode === 'remove' ? 'Remove' : 'Modify');
        }
        if (replaceLabel) {
          replaceLabel.textContent = mode === 'perfect_text' ? 'Exact Replacement Text' : (mode === 'add' ? 'New Element to Add' : 'Replacement Instructions');
        }
        if (submitBtnLabel) submitBtnLabel.textContent = `Apply AI ${mode.replace('_', ' ')}`;
      }
    });
  });
}

/* ============================================================================
   MULTILINGUAL WEB SPEECH API (Gujarati, Hindi, Indian/US English)
   ============================================================================ */
function initWebSpeechEngine() {
  const micBtn = document.getElementById('btnVoiceInput');
  const langSelect = document.getElementById('aiLanguageSelect');
  const promptInput = document.getElementById('aiPromptInput');
  const tray = document.getElementById('voiceRecordingTray');
  const interimEl = document.getElementById('interimTranscript');
  const btnStop = document.getElementById('btnStopVoice');
  const btnCancel = document.getElementById('btnCancelVoice');
  const btnClearTranscript = document.getElementById('btnClearTranscript');

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (micBtn) micBtn.onclick = () => showToast('Web Speech API unavailable in this browser. Type your prompt directly.', 'warn');
    return;
  }

  gomziSpeechRecognizer = new SpeechRecognition();
  gomziSpeechRecognizer.continuous = true;
  gomziSpeechRecognizer.interimResults = true;

  gomziSpeechRecognizer.onstart = () => {
    isVoiceRecording = true;
    micBtn?.classList.add('recording');
    if (tray) tray.style.display = 'flex';
    if (interimEl) interimEl.textContent = `Listening (${langSelect?.value || 'gu-IN'})...`;
  };

  gomziSpeechRecognizer.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const txt = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        const prev = promptInput.value.trim();
        promptInput.value = prev ? `${prev} ${txt.trim()}` : txt.trim();
      } else {
        interim += txt;
      }
    }
    if (interimEl) interimEl.textContent = interim || 'Listening...';
  };

  gomziSpeechRecognizer.onerror = (ev) => {
    stopVoiceUi();
    if (ev.error === 'not-allowed') showToast('Microphone permission denied by browser.', 'error');
    else if (ev.error !== 'no-speech' && ev.error !== 'aborted') showToast(`Speech recognition error: ${ev.error}`, 'warn');
  };

  gomziSpeechRecognizer.onend = () => stopVoiceUi();

  function stopVoiceUi() {
    isVoiceRecording = false;
    micBtn?.classList.remove('recording');
    if (tray) tray.style.display = 'none';
  }

  if (micBtn) {
    micBtn.onclick = () => {
      if (isVoiceRecording) {
        gomziSpeechRecognizer.stop();
      } else {
        gomziSpeechRecognizer.lang = langSelect?.value || 'gu-IN';
        try { gomziSpeechRecognizer.start(); } catch (e) { gomziSpeechRecognizer.stop(); }
      }
    };
  }
  btnStop?.addEventListener('click', () => gomziSpeechRecognizer.stop());
  btnCancel?.addEventListener('click', () => { gomziSpeechRecognizer.abort(); stopVoiceUi(); });
  btnClearTranscript?.addEventListener('click', () => {
    if (promptInput) promptInput.value = '';
    if (interimEl) interimEl.textContent = 'Cleared.';
  });
}

/* ============================================================================
   REFERENCE IMAGE ATTACHMENTS
   ============================================================================ */
function initPromptAttachments() {
  const thumbs = document.getElementById('aiAttachmentsThumbnails');
  const fileIn = document.getElementById('aiReferenceFileInput');

  function renderAtts() {
    if (!thumbs) return;
    thumbs.innerHTML = '';
    window.aiReferenceAttachments.forEach((att, idx) => {
      const chip = document.createElement('div');
      chip.style.cssText = 'display:inline-flex;align-items:center;gap:5px;background:#EDF1DF;border:1px solid #C4D29F;border-radius:6px;padding:3px 6px;font-size:10.5px;font-weight:600;color:#202820;';
      chip.innerHTML = `<img src="${att.src}" style="width:18px;height:18px;object-fit:cover;border-radius:3px;" /><span>${att.label}</span><button type="button" style="border:none;background:transparent;color:#D65D5D;cursor:pointer;font-weight:700;">×</button>`;
      chip.querySelector('button').onclick = () => { window.aiReferenceAttachments.splice(idx, 1); renderAtts(); };
      thumbs.appendChild(chip);
    });
  }

  document.getElementById('btnAttachCanvas')?.addEventListener('click', () => {
    if (typeof getCleanCanvasDataURL !== 'function') return;
    window.aiReferenceAttachments.push({ src: getCleanCanvasDataURL(0.5), label: 'Current Canvas' });
    renderAtts();
    showToast('Attached current canvas artwork', 'success');
  });
  document.getElementById('btnAttachLogo')?.addEventListener('click', () => {
    const src = document.getElementById('brandLogoPreviewImg')?.src || '/static/assets/gomzi_logo.svg';
    window.aiReferenceAttachments.push({ src, label: 'Brand Logo' });
    renderAtts();
    showToast('Attached brand logo', 'success');
  });
  document.getElementById('btnAttachUpload')?.addEventListener('click', () => fileIn?.click());
  fileIn?.addEventListener('change', (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) return showToast('Reference image must be under 8 MB', 'warn');
    const r = new FileReader();
    r.onload = (ev) => {
      window.aiReferenceAttachments.push({ src: ev.target.result, label: f.name.slice(0, 12) });
      renderAtts();
    };
    r.readAsDataURL(f);
    fileIn.value = '';
  });
}

/* ============================================================================
   ASPECT RATIO & PACKAGING DIMENSION PRESETS
   ============================================================================ */
function initAiAspectRatioAndPresets() {
  const arSel = document.getElementById('aiAspectRatioSelect');
  const customWrap = document.getElementById('aiCustomDimsWrap');
  const wIn = document.getElementById('aiCustomWidthInput');
  const hIn = document.getElementById('aiCustomHeightInput');
  const uIn = document.getElementById('aiCustomUnitSelect');

  if (arSel) {
    arSel.onchange = () => {
      window.currentAiAspectRatio = arSel.value;
      if (customWrap) customWrap.style.display = (arSel.value === 'custom') ? 'grid' : 'none';
      // Auto-populate custom mm presets
      if (arSel.value === '7:11' && wIn && hIn) { wIn.value = 70; hIn.value = 110; if (uIn) uIn.value = 'mm'; }
      if (arSel.value === '2:3' && wIn && hIn) { wIn.value = 160; hIn.value = 240; if (uIn) uIn.value = 'mm'; }
      if (arSel.value === '3:1' && wIn && hIn) { wIn.value = 315; hIn.value = 110; if (uIn) uIn.value = 'mm'; }
    };
  }
}

/* ============================================================================
   PROMPT ENHANCEMENT, GENERATION, EDITING & PRO TOOLS
   ============================================================================ */
function initAiComposerAndToolActions() {
  const promptInput = document.getElementById('aiPromptInput');
  const btnEnhance = document.getElementById('btnEnhancePrompt');
  const btnGenerate = document.getElementById('btnGenerateArtwork');
  const reviewCard = document.getElementById('aiEnhancedReviewCard');
  const reviewTa = document.getElementById('aiReviewPromptTextarea');

  // Legacy compatibility trigger (#canvaAiPromptInput / #canvaAiPromptBtn)
  const legacyBtn = document.getElementById('canvaAiPromptBtn');
  const legacyIn = document.getElementById('canvaAiPromptInput');
  if (legacyBtn && legacyIn) {
    legacyBtn.onclick = async () => {
      const val = legacyIn.value.trim();
      if (!val) return;
      await fetch('/api/canva/ai-prompt-edit', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: val, width: canvaCanvas?._logicalWidth || 1536, height: canvaCanvas?._logicalHeight || 512 })
      });
    };
  }

  document.getElementById('btnClearPrompt')?.addEventListener('click', () => {
    if (promptInput) promptInput.value = '';
    if (reviewCard) reviewCard.style.display = 'none';
  });
  document.getElementById('btnCopyPrompt')?.addEventListener('click', () => {
    if (promptInput?.value) {
      navigator.clipboard?.writeText(promptInput.value);
      showToast('Prompt copied to clipboard', 'success');
    }
  });

  // Shift+Enter newline, Enter optional
  promptInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      btnGenerate?.click();
    }
  });

  // Enhance Prompt
  btnEnhance?.addEventListener('click', async () => {
    const raw = (promptInput?.value || '').trim();
    if (!raw) return showToast('Enter or speak a prompt first', 'warn');

    btnEnhance.disabled = true;
    showToast('Enhancing prompt for flat 2D print packaging...', 'info', 3500);
    try {
      const res = await fetch('/api/ai/enhance-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: raw,
          language: document.getElementById('aiLanguageSelect')?.value || 'en-US',
          aspect_ratio: window.currentAiAspectRatio || '3:1',
          provider: document.getElementById('aiProviderSelect')?.value || 'auto',
        }),
      });
      const d = await res.json();
      btnEnhance.disabled = false;
      if (d.success && d.enhanced_prompt) {
        if (reviewCard) reviewCard.style.display = 'flex';
        if (reviewTa) reviewTa.value = d.enhanced_prompt;
        const origPreview = document.getElementById('aiOriginalTranscriptPreview');
        if (origPreview) origPreview.textContent = raw;
        const pills = document.getElementById('aiDetectedPills');
        if (pills) {
          pills.innerHTML = [
            d.detected_brand ? `<span class="badge-soft badge-olive">${d.detected_brand}</span>` : '',
            d.detected_product ? `<span class="badge-soft badge-olive">${d.detected_product}</span>` : '',
            d.detected_flavor ? `<span class="badge-soft badge-olive">${d.detected_flavor}</span>` : '',
            d.detected_weight ? `<span class="badge-soft badge-olive">${d.detected_weight}</span>` : '',
          ].join('');
        }
        showToast('Prompt enhanced! Review & apply below.', 'success');
      } else {
        showToast(`Enhance error: ${d.error}`, 'error');
      }
    } catch (e) {
      btnEnhance.disabled = false;
      showToast(`Enhance failed: ${e.message}`, 'error');
    }
  });

  document.getElementById('btnApplyEnhancedPrompt')?.addEventListener('click', () => {
    if (promptInput && reviewTa) {
      promptInput.value = reviewTa.value;
      if (reviewCard) reviewCard.style.display = 'none';
      showToast('Applied enhanced prompt', 'success');
    }
  });
  document.getElementById('btnDismissEnhancedReview')?.addEventListener('click', () => {
    if (reviewCard) reviewCard.style.display = 'none';
  });

  // Primary Generate / Edit Button
  btnGenerate?.addEventListener('click', async () => {
    const mode = window.currentAiMode || 'generate';
    const provider = document.getElementById('aiProviderSelect')?.value || 'auto';
    const model = document.getElementById('aiModelSelect')?.value || null;
    const ratio = document.getElementById('aiAspectRatioSelect')?.value || '3:1';
    const quality = document.getElementById('aiQualitySelect')?.value || 'High';
    const outputCount = parseInt(document.getElementById('aiOutputsSelect')?.value || '1', 10);

    if (mode !== 'generate') {
      return executeNonDestructiveAiEdit(mode, provider);
    }

    const prompt = (promptInput?.value || '').trim();
    if (!prompt) return showToast('Prompt cannot be empty', 'warn');

    // Save to local prompt history
    window.aiPromptHistory.unshift({ prompt, provider, model, at: new Date().toLocaleTimeString() });
    if (window.aiPromptHistory.length > 20) window.aiPromptHistory.pop();

    btnGenerate.disabled = true;
    showToast(`Generating artwork via ${provider} (${model || 'default'})...`, 'info', 15000);

    try {
      const res = await fetch('/api/ai/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          provider,
          model,
          aspect_ratio: ratio === 'custom' ? '3:1' : ratio,
          quality,
          output_count: outputCount,
          reference_images: window.aiReferenceAttachments.map(a => a.src),
        }),
      });
      const d = await res.json();
      btnGenerate.disabled = false;

      if (d.success && (d.image_url || d.saved_asset?.url)) {
        const finalUrl = d.saved_asset?.url || d.image_url;
        showGeneratedResultModal(finalUrl, prompt, d.provider, d.model);
      } else {
        showToast(`Generation failed: ${d.error || 'Provider returned an error'}`, 'error', 6000);
      }
    } catch (e) {
      btnGenerate.disabled = false;
      showToast(`Generation exception: ${e.message}`, 'error', 5000);
    }
  });

  // Canva Pro Quick Actions (Grab Text, Convert to Vector, Grab Object, Background Repair / Clean Plate, Smart Resize)
  document.getElementById('canvaToolGrabTextBtn')?.addEventListener('click', runGrabTextOcr);
  document.getElementById('canvaToolConvertVectorBtn')?.addEventListener('click', runConvertToVector);
  document.getElementById('canvaToolMagicGrabBtn')?.addEventListener('click', runGrabObjectLayer);
  document.getElementById('canvaToolBgRemoverBtn')?.addEventListener('click', runBgRemoverOnSelection);
  document.getElementById('canvaToolMagicEraserBtn')?.addEventListener('click', runCleanPlateRepair);
  document.getElementById('canvaToolCleanPlateBtn')?.addEventListener('click', runCleanPlateRepair);
  document.getElementById('canvaToolUpscaleBtn')?.addEventListener('click', runUpscaleSelection);
  document.getElementById('canvaToolRestoreOriginalBtn')?.addEventListener('click', () => {
    if (typeof restoreOriginalArtwork === 'function') restoreOriginalArtwork();
  });
}

/* Result Workflow Modal (Open in Editor, Regenerate, View in 3D, Download) */
function showGeneratedResultModal(imgUrl, prompt, provider, model) {
  const modal = document.getElementById('aiResultWorkflowModal');
  if (!modal) {
    openImageAsFullLabel(imgUrl, `AI Generated (${provider})`, { skipConfirm: true });
    if (typeof runAutoSmartReconstructFromUrl === 'function') {
      runAutoSmartReconstructFromUrl(imgUrl, `ai_${provider}.png`);
    }
    return;
  }
  document.getElementById('aiResultPreviewImg').src = imgUrl;
  document.getElementById('aiResultMetaText').textContent = `Provider: ${provider} · Model: ${model}`;
  modal.style.display = 'flex';

  document.getElementById('aiResultOpenEditorBtn').onclick = () => {
    modal.style.display = 'none';
    openImageAsFullLabel(imgUrl, `AI Generated ${provider}`, { skipConfirm: true });
    if (typeof runAutoSmartReconstructFromUrl === 'function') {
      runAutoSmartReconstructFromUrl(imgUrl, `ai_${provider}.png`);
    }
  };
  document.getElementById('aiResultDownloadBtn').onclick = () => {
    const a = document.createElement('a');
    a.href = imgUrl;
    a.download = `gomzi_ai_${provider}.png`;
    a.click();
  };
  document.getElementById('aiResultCloseBtn').onclick = () => { modal.style.display = 'none'; };
}

/* Non-Destructive Before/After AI Edit Workflow */
async function executeNonDestructiveAiEdit(mode, provider) {
  const target = document.getElementById('aiEditTargetInput')?.value || '';
  const replacement = document.getElementById('aiEditReplaceInput')?.value || '';
  const prompt = document.getElementById('aiPromptInput')?.value || '';
  const originalUrl = getCleanCanvasDataURL(1);

  showToast(`Running non-destructive AI ${mode}...`, 'info', 8000);
  try {
    const res = await fetch('/api/ai/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, provider, image_data: originalUrl, target, replacement, prompt }),
    });
    const d = await res.json();
    if (!d.success) return showToast(`AI Edit failed: ${d.error}`, 'error', 5000);

    if (d.fabric_json) {
      isHistoryLocked = true;
      canvaCanvas.loadFromJSON(d.fabric_json, () => {
        isHistoryLocked = false;
        canvaCanvas.renderAll();
        refreshLayersList();
        if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
      });
      return showToast('Digitized artwork via REVE into editable layers', 'success');
    }

    pendingAiEditResult = d;
    document.getElementById('beforeAfterOrigImg').src = d.original_data_url;
    document.getElementById('beforeAfterEditedImg').src = d.edited_image_url;
    document.getElementById('aiBeforeAfterModal').style.display = 'flex';

    document.getElementById('btnAcceptAiEdit').onclick = () => {
      document.getElementById('aiBeforeAfterModal').style.display = 'none';
      openImageAsFullLabel(d.edited_image_url, `AI Edited (${mode})`);
    };
    document.getElementById('btnRejectAiEdit').onclick = () => {
      document.getElementById('aiBeforeAfterModal').style.display = 'none';
      showToast('Kept original artwork unchanged', 'info');
    };
  } catch (e) {
    showToast(`AI Edit error: ${e.message}`, 'error');
  }
}

async function runConvertToVector() {
  if (!canvaCanvas) return;
  showToast('Vectorizing artwork into editable shapes, clean plate & text...', 'info', 8000);
  const dataUrl = getCleanCanvasDataURL(1);
  try {
    const res = await fetch('/api/canva/convert-to-vector', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_data: dataUrl,
        width_mm: canvaCanvas._physicalWidthMm || 160.0,
        height_mm: canvaCanvas._physicalHeightMm || 65.0,
        use_vision: false,
      }),
    });
    const d = await res.json();
    if (!d.success || !d.fabric_json) {
      return showToast(`Vectorization failed: ${d.error || 'Unknown error'}`, 'error', 5000);
    }
    if (typeof hydrateReconstructedScene === 'function') {
      hydrateReconstructedScene(d, () => {
        const st = d.stats || {};
        showToast(
          `Converted to ${st.vector_objects || 0} vector & ${st.text_objects || 0} text layers`,
          'success',
          4000
        );
      });
    }
  } catch (e) {
    showToast(`Convert to Vector failed: ${e.message}`, 'error', 5000);
  }
}

async function runGrabTextOcr() {
  if (!canvaCanvas) return;
  showToast('Detecting text regions & repairing Clean Plate underneath...', 'info', 5000);
  const dataUrl = getCleanCanvasDataURL(1);
  try {
    const res = await fetch('/api/canva/grab-text', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: dataUrl })
    });
    const d = await res.json();
    const detected = d.regions || d.text_elements || [];
    if (detected.length && d.clean_background_url) {
      fabric.Image.fromURL(d.clean_background_url, (bgImg) => {
        const logW = canvaCanvas._logicalWidth || 1536;
        const logH = canvaCanvas._logicalHeight || 512;
        const srcW = d.image_width || bgImg.width || logW;
        const srcH = d.image_height || bgImg.height || logH;
        const scX = logW / srcW;
        const scY = logH / srcH;

        isHistoryLocked = true;
        bgImg.set({
          left: 0, top: 0,
          scaleX: logW / (bgImg.width || logW),
          scaleY: logH / (bgImg.height || logH),
          selectable: false, evented: true,
          assetType: 'clean_plate_base',
          layerCategory: 'Background',
          name: 'Clean Plate Background',
        });
        canvaCanvas.clear();
        canvaCanvas.add(bgImg);
        canvaCanvas.sendToBack(bgImg);
        detected.forEach((reg, idx) => {
          const tb = new fabric.Textbox(reg.text || '', {
            left: (reg.left || 40) * scX,
            top: (reg.top || 40) * scY,
            width: Math.max(48, (reg.width || 160) * scX * 1.12),
            fontSize: Math.max(9, Math.round((reg.fontSize || reg.font_size || 20) * scY)),
            fill: reg.color || '#1e293b',
            fontFamily: reg.fontFamily || 'Montserrat',
            fontWeight: reg.fontWeight || reg.font_weight || '700',
            textAlign: reg.align || 'left',
            lineHeight: reg.lineHeight || 1.14,
            editable: true,
            isImportedText: true,
            assetType: 'editable_text',
            layerCategory: reg.role || 'Typography',
            name: `Grab Text: ${(reg.text || '').split('\n')[0].slice(0, 24) || idx + 1}`,
          });
          canvaCanvas.add(tb);
        });
        isHistoryLocked = false;
        canvaCanvas.renderAll();
        pushCanvasHistory();
        refreshLayersList();
        if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
        showToast(`Extracted ${detected.length} editable text layers!`, 'success');
      });
    } else {
      document.getElementById('grabTextReviewBox').style.display = 'flex';
      showToast('Double-click existing vector text on canvas to edit inline.', 'info');
    }
  } catch (e) {
    showToast(`Grab Text error: ${e.message}`, 'error');
  }
}

async function runGrabObjectLayer() {
  if (!canvaCanvas) return;
  showToast('Separating selected object & repairing clean plate...', 'info', 4000);
  const cleanUrl = getCleanCanvasDataURL(1);
  const act = canvaCanvas.getActiveObject();
  let bbox = null;
  if (act) {
    const b = act.getBoundingRect(true, true);
    bbox = { left: Math.round(b.left), top: Math.round(b.top), width: Math.round(b.width), height: Math.round(b.height) };
  }
  try {
    const res = await fetch('/api/canva/grab-object', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: cleanUrl, bbox }),
    });
    const d = await res.json();
    if (!d.success) return showToast(`Grab Object error: ${d.error}`, 'error');

    fabric.Image.fromURL(d.background_data_url, (bgImg) => {
      canvaCanvas.setBackgroundImage(bgImg, () => {
        fabric.Image.fromURL(d.foreground_data_url, (fgImg) => {
          fgImg.set({ left: d.bbox?.left || 100, top: d.bbox?.top || 80, name: 'Extracted Object Layer', selectable: true });
          canvaCanvas.add(fgImg);
          canvaCanvas.setActiveObject(fgImg);
          canvaCanvas.renderAll();
          refreshLayersList();
          if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
          showToast('Extracted object into independent layer!', 'success');
        });
      });
    });
  } catch (e) {
    showToast(`Grab Object error: ${e.message}`, 'error');
  }
}

async function runBgRemoverOnSelection() {
  const act = canvaCanvas?.getActiveObject();
  if (!act || act.type !== 'image') return showToast('Select an image layer on canvas first', 'warn');
  showToast('Removing background...', 'info', 4000);
  try {
    const src = act.toDataURL({ format: 'png' });
    const res = await fetch('/api/canva/bg-remover', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: src }),
    });
    const d = await res.json();
    if (d.result_url) {
      fabric.Image.fromURL(d.result_url, (newImg) => {
        newImg.set({ left: act.left, top: act.top, scaleX: act.scaleX, scaleY: act.scaleY, name: `${act.name || 'Image'} (No BG)` });
        canvaCanvas.remove(act);
        canvaCanvas.add(newImg);
        canvaCanvas.setActiveObject(newImg);
        canvaCanvas.renderAll();
        showToast('Removed image background', 'success');
      });
    }
  } catch (e) {
    showToast(`BG Remover error: ${e.message}`, 'error');
  }
}

async function runCleanPlateRepair() {
  const act = canvaCanvas?.getActiveObject();
  if (!act) return showToast('Select a region or object to repair background underneath', 'warn');
  showToast('Repairing local Clean Plate background...', 'info', 4000);
  const cleanUrl = getCleanCanvasDataURL(1);
  const b = act.getBoundingRect(true, true);
  try {
    const res = await fetch('/api/canva/inpaint-text', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: cleanUrl, regions: [{ left: Math.round(b.left), top: Math.round(b.top), width: Math.round(b.width), height: Math.round(b.height) }] }),
    });
    const d = await res.json();
    if (d.clean_background_url) {
      fabric.Image.fromURL(d.clean_background_url, (bgImg) => {
        canvaCanvas.setBackgroundImage(bgImg, canvaCanvas.renderAll.bind(canvaCanvas));
        if (typeof updateThreeLabelTextureFromCanvas === 'function') updateThreeLabelTextureFromCanvas();
        showToast('Clean Plate background reconstructed', 'success');
      });
    }
  } catch (e) {
    showToast(`Clean Plate error: ${e.message}`, 'error');
  }
}

async function runUpscaleSelection() {
  const act = canvaCanvas?.getActiveObject();
  const targetUrl = (act && act.type === 'image') ? act.toDataURL({ format: 'png' }) : getCleanCanvasDataURL(1);
  showToast('Upscaling artwork clarity 2x...', 'info', 4000);
  try {
    const res = await fetch('/api/canva/upscale', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: targetUrl, scale: 2 }),
    });
    const d = await res.json();
    if (d.result_url) {
      if (act && act.type === 'image') {
        fabric.Image.fromURL(d.result_url, (upImg) => {
          upImg.set({ left: act.left, top: act.top, scaleX: act.scaleX / 2, scaleY: act.scaleY / 2, name: `${act.name || 'Image'} (HD)` });
          canvaCanvas.remove(act);
          canvaCanvas.add(upImg);
          canvaCanvas.renderAll();
        });
      } else {
        openImageAsFullLabel(d.result_url, 'Upscaled Label Master');
      }
      showToast('Super-resolution clarity applied', 'success');
    }
  } catch (e) {
    showToast(`Upscale error: ${e.message}`, 'error');
  }
}
