# -*- coding: utf-8 -*-
import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Verify target anchor
anchor = "/* ======================================================\n       CANVA-STYLE MAGIC GRAB & NATURAL LANGUAGE AI PROMPT EDIT"
if anchor not in html:
    # Try normalized spacing
    for line in html.split('\n'):
        if 'CANVA-STYLE MAGIC GRAB' in line:
            anchor = line
            break

print("Found anchor:", anchor[:50])

ai_js_code = '''
    /* ======================================================
       ADVANCED AI API SELECTOR, PROMPT COMPOSER & VOICE ENGINE
    ====================================================== */
    window.gomziAiProviders = [];
    window.currentAiAspectRatio = "3:1";
    window.currentAiMode = "generate";
    window.aiReferenceAttachments = [];
    let gomziSpeechRecognizer = null;
    let isVoiceRecording = false;

    async function initAiStudioEngine() {
      // 1. Load AI Providers & Models
      await loadAiProviderCatalog();

      // 2. Initialize Web Speech API
      initWebSpeechEngine();

      // 3. Initialize Mode Selector
      initAiModeButtons();

      // 4. Initialize Aspect Ratio Presets
      initAiAspectRatioPresets();

      // 5. Initialize Prompt Enhancement & Generation
      initPromptComposerActions();

      // 6. Initialize Reference Attachments
      initReferenceAttachments();
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
        console.error("Failed to load AI providers:", e);
      }
    }

    function populateAiProviderDropdown(providers) {
      const pSelect = document.getElementById('aiProviderSelect');
      if (!pSelect) return;

      pSelect.innerHTML = '';
      providers.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        const statusMark = p.is_configured ? '● ' : '○ ';
        opt.textContent = `${statusMark}${p.name} (${p.badge})`;
        if (p.is_default) opt.selected = true;
        pSelect.appendChild(opt);
      });

      // Update model dropdown on provider change
      pSelect.onchange = () => {
        updateModelDropdownForProvider(pSelect.value);
      };

      // Initial model load
      updateModelDropdownForProvider(pSelect.value);
    }

    function updateModelDropdownForProvider(providerId) {
      const mSelect = document.getElementById('aiModelSelect');
      const qualityTag = document.getElementById('aiModelQualityTag');
      const costTag = document.getElementById('aiModelCostTag');
      const p = window.gomziAiProviders.find(x => x.id === providerId) || window.gomziAiProviders[0];

      if (!mSelect || !p) return;

      mSelect.innerHTML = '';
      (p.models || []).forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = `${m.name} [${m.quality || m.type || 'Standard'}]`;
        if (m.recommended) opt.selected = true;
        mSelect.appendChild(opt);
      });

      if (qualityTag) {
        qualityTag.textContent = `${p.icon || '✨'} ${p.badge || 'Studio'} · ${p.models?.[0]?.speed || 'Fast'}`;
      }
      if (costTag) {
        costTag.textContent = p.models?.[0]?.cost || 'Active';
      }

      // Update badge
      const statusBadge = document.getElementById('aiProviderStatusBadge');
      if (statusBadge) {
        statusBadge.textContent = p.is_configured ? `${p.name.split(' ')[0]} READY` : 'SETUP KEY';
        statusBadge.className = p.is_configured ? 'drawer-badge drawer-badge-green' : 'drawer-badge';
      }
    }

    function initWebSpeechEngine() {
      const micBtn = document.getElementById('btnVoiceInput');
      const micDot = document.getElementById('micDot');
      const micStatus = document.getElementById('micStatusText');
      const langSelect = document.getElementById('aiLanguageSelect');
      const promptInput = document.getElementById('aiPromptInput');
      const tray = document.getElementById('voiceRecordingTray');
      const interimEl = document.getElementById('interimTranscript');
      const btnStop = document.getElementById('btnStopVoice');
      const btnCancel = document.getElementById('btnCancelVoice');
      const langNameEl = document.getElementById('currentVoiceLangName');

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

      if (!SpeechRecognition) {
        if (micStatus) micStatus.textContent = 'Speech typing ready';
        if (micBtn) {
          micBtn.onclick = () => {
            showToast("Web Speech API not supported in this browser. Please type your prompt.", "ℹ️");
          };
        }
        return;
      }

      try {
        gomziSpeechRecognizer = new SpeechRecognition();
        gomziSpeechRecognizer.continuous = true;
        gomziSpeechRecognizer.interimResults = true;

        gomziSpeechRecognizer.onstart = () => {
          isVoiceRecording = true;
          if (tray) tray.style.display = 'flex';
          if (micDot) micDot.style.background = '#ef4444';
          if (micStatus) micStatus.textContent = 'Listening...';
          if (micBtn) {
            micBtn.style.background = '#fee2e2';
            micBtn.style.color = '#ef4444';
          }
          if (langNameEl && langSelect) {
            langNameEl.textContent = langSelect.options[langSelect.selectedIndex].text.split(' ')[1] || 'Speech';
          }
          showToast(`Microphone active. Speak in ${langSelect.value}...`, "🎙️");
        };

        gomziSpeechRecognizer.onresult = (event) => {
          let interimText = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              const currentVal = promptInput.value.trim();
              promptInput.value = currentVal ? `${currentVal} ${transcript.trim()}` : transcript.trim();
            } else {
              interimText += transcript;
            }
          }
          if (interimEl) {
            interimEl.textContent = interimText || 'Transcribing your voice...';
          }
        };

        gomziSpeechRecognizer.onerror = (event) => {
          console.warn("Speech recognition error:", event.error);
          stopVoiceRecording();
          if (event.error !== 'no-speech') {
            showToast(`Voice input: ${event.error}`, "⚠️");
          }
        };

        gomziSpeechRecognizer.onend = () => {
          stopVoiceRecording();
        };

        function startVoiceRecording() {
          if (!gomziSpeechRecognizer) return;
          gomziSpeechRecognizer.lang = langSelect.value || 'gu-IN';
          try {
            gomziSpeechRecognizer.start();
          } catch (e) {
            gomziSpeechRecognizer.stop();
          }
        }

        function stopVoiceRecording() {
          isVoiceRecording = false;
          if (tray) tray.style.display = 'none';
          if (micDot) micDot.style.background = '#10b981';
          if (micStatus) micStatus.textContent = 'Mic Ready';
          if (micBtn) {
            micBtn.style.background = '#eff6ff';
            micBtn.style.color = '#2563eb';
          }
        }

        if (micBtn) {
          micBtn.onclick = () => {
            if (isVoiceRecording) {
              gomziSpeechRecognizer.stop();
            } else {
              startVoiceRecording();
            }
          };
        }

        if (btnStop) {
          btnStop.onclick = () => {
            if (gomziSpeechRecognizer) gomziSpeechRecognizer.stop();
          };
        }

        if (btnCancel) {
          btnCancel.onclick = () => {
            if (gomziSpeechRecognizer) gomziSpeechRecognizer.abort();
            stopVoiceRecording();
          };
        }
      } catch (err) {
        console.error("Speech recognition initialization failed:", err);
      }
    }

    function initAiModeButtons() {
      const btns = document.querySelectorAll('.ai-mode-btn');
      const promptInput = document.getElementById('aiPromptInput');
      btns.forEach(btn => {
        btn.onclick = () => {
          btns.forEach(b => {
            b.classList.remove('active');
            b.style.background = '#ffffff';
            b.style.color = '#334155';
          });
          btn.classList.add('active');
          btn.style.background = '#0f172a';
          btn.style.color = '#ffffff';
          window.currentAiMode = btn.dataset.mode;

          // Contextual prompt placeholder
          if (promptInput) {
            if (window.currentAiMode === 'remove') {
              promptInput.placeholder = "Describe elements to remove (e.g. Remove Belgian Chocolate flavor badge, wipe barcode)...";
            } else if (window.currentAiMode === 'replace') {
              promptInput.placeholder = "Describe replacement (e.g. Replace Belgian Chocolate with Alphonso Mango, change badge color to orange)...";
            } else if (window.currentAiMode === 'perfect_text') {
              promptInput.placeholder = "Enter exact text to replace (e.g. Change WHEY PROTEIN to 100% ISO WHEY GOLD)...";
            } else {
              promptInput.placeholder = "Speak in Gujarati/Hindi/English or describe packaging... e.g. મારે ગોમઝીનું 1kg વે પ્રોટીન બ્લેક અને ગોલ્ડ કલરમાં બનાવવું છે...";
            }
          }
        };
      });
    }

    function initAiAspectRatioPresets() {
      const btns = document.querySelectorAll('.ai-aspect-btn');
      const descEl = document.getElementById('aiSelectedPresetDesc');
      const descMap = {
        '3:1': '3:1 Wrap Label (452×142mm Standard)',
        '1:1': '1:1 Square Front Panel / Box',
        '4:1': '4:1 Ultra-Wide Mass Gainer Tub',
        '16:9': '16:9 Wide Display Banner',
        '9:16': '9:16 Tall Sachet / Box',
        '7:11': '7:11 Sachet (70×110mm)',
        '2:3': '2:3 Stand-up Pouch (160×240mm)'
      };

      btns.forEach(btn => {
        btn.onclick = () => {
          btns.forEach(b => {
            b.classList.remove('active');
            b.style.background = '#f1f5f9';
            b.style.color = '#334155';
          });
          btn.classList.add('active');
          btn.style.background = '#0f172a';
          btn.style.color = '#ffffff';
          window.currentAiAspectRatio = btn.dataset.ratio;
          if (descEl) descEl.textContent = descMap[window.currentAiAspectRatio] || window.currentAiAspectRatio;
        };
      });
    }

    function initReferenceAttachments() {
      const btnCanvas = document.getElementById('btnAttachCanvas');
      const btnLogo = document.getElementById('btnAttachLogo');
      const btnUpload = document.getElementById('btnAttachUpload');
      const fileInput = document.getElementById('aiReferenceFileInput');
      const thumbsContainer = document.getElementById('aiAttachmentsThumbnails');

      function addAttachmentThumbnail(src, label) {
        window.aiReferenceAttachments.push({ src, label });
        renderAttachmentThumbnails();
      }

      function renderAttachmentThumbnails() {
        if (!thumbsContainer) return;
        thumbsContainer.innerHTML = '';
        window.aiReferenceAttachments.forEach((att, idx) => {
          const chip = document.createElement('div');
          chip.style.cssText = 'display:flex; align-items:center; gap:4px; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; padding:2px 6px; font-size:10px; font-weight:700; color:#334155;';
          chip.innerHTML = `
            <img src="${att.src}" style="width:16px; height:16px; object-fit:cover; border-radius:2px;" />
            <span>${att.label}</span>
            <button type="button" style="background:transparent; border:none; color:#ef4444; font-weight:800; cursor:pointer; padding:0 2px;">✕</button>
          `;
          chip.querySelector('button').onclick = () => {
            window.aiReferenceAttachments.splice(idx, 1);
            renderAttachmentThumbnails();
          };
          thumbsContainer.appendChild(chip);
        });
      }

      if (btnCanvas) {
        btnCanvas.onclick = () => {
          if (!canvaCanvas) return;
          const dataUrl = canvaCanvas.toDataURL('image/png');
          addAttachmentThumbnail(dataUrl, 'Canvas');
          showToast("Current canvas attached as AI reference", "🖼️");
        };
      }

      if (btnLogo) {
        btnLogo.onclick = () => {
          const logoImg = document.getElementById('brandLogoPreview');
          if (logoImg && logoImg.src) {
            addAttachmentThumbnail(logoImg.src, 'Logo');
            showToast("Brand logo attached as AI reference", "⭐");
          } else {
            showToast("No brand logo found to attach", "⚠️");
          }
        };
      }

      if (btnUpload && fileInput) {
        btnUpload.onclick = () => fileInput.click();
        fileInput.onchange = (e) => {
          const file = e.target.files[0];
          if (!file) return;
          const reader = new FileReader();
          reader.onload = (ev) => {
            addAttachmentThumbnail(ev.target.result, file.name.slice(0, 10));
            showToast(`Attached ${file.name}`, "📁");
          };
          reader.readAsDataURL(file);
        };
      }
    }

    function initPromptComposerActions() {
      const promptInput = document.getElementById('aiPromptInput');
      const btnEnhance = document.getElementById('btnEnhancePrompt');
      const btnGenerate = document.getElementById('btnGenerateArtwork');
      const btnClear = document.getElementById('btnClearPrompt');
      const reviewCard = document.getElementById('aiEnhancedReviewCard');
      const reviewTextarea = document.getElementById('aiReviewPromptTextarea');
      const pillsContainer = document.getElementById('aiDetectedPills');
      const btnApply = document.getElementById('btnApplyEnhancedPrompt');
      const btnDismiss = document.getElementById('btnDismissEnhancedReview');
      const langSelect = document.getElementById('aiLanguageSelect');
      const pSelect = document.getElementById('aiProviderSelect');
      const mSelect = document.getElementById('aiModelSelect');

      // Clear Prompt
      if (btnClear) {
        btnClear.onclick = () => {
          if (promptInput) promptInput.value = '';
          if (reviewCard) reviewCard.style.display = 'none';
          window.aiReferenceAttachments = [];
          const thumbs = document.getElementById('aiAttachmentsThumbnails');
          if (thumbs) thumbs.innerHTML = '';
          showToast("Prompt cleared", "🧹");
        };
      }

      // Enhance Prompt
      if (btnEnhance) {
        btnEnhance.onclick = async () => {
          const raw = promptInput ? promptInput.value.trim() : '';
          if (!raw) {
            showToast("Please enter or speak a prompt first!", "⚠️");
            return;
          }

          showToast("✨ AI Packaging Director compiling 2D print prompt...", "⏳", 3500);
          btnEnhance.disabled = true;

          try {
            const res = await fetch('/api/ai/enhance-prompt', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                prompt: raw,
                language: langSelect ? langSelect.value : 'gu-IN',
                aspect_ratio: window.currentAiAspectRatio || '3:1',
                provider: pSelect ? pSelect.value : 'auto'
              })
            });
            const d = await res.json();
            btnEnhance.disabled = false;

            if (d.success && d.enhanced_prompt) {
              if (reviewCard) reviewCard.style.display = 'flex';
              if (reviewTextarea) reviewTextarea.value = d.enhanced_prompt;

              // Populate pills
              if (pillsContainer) {
                pillsContainer.innerHTML = '';
                const tags = [
                  { label: 'Brand', val: d.detected_brand },
                  { label: 'Product', val: d.detected_product },
                  { label: 'Flavor', val: d.detected_flavor },
                  { label: 'Weight', val: d.detected_weight }
                ].filter(t => t.val);

                tags.forEach(t => {
                  const tagEl = document.createElement('span');
                  tagEl.style.cssText = 'background:#dcfce7; color:#166534; padding:2px 6px; border-radius:4px; font-weight:800;';
                  tagEl.textContent = `${t.label}: ${t.val}`;
                  pillsContainer.appendChild(tagEl);
                });
              }

              showToast("Prompt enhanced with flat 2D layout constraints!", "✨");
            } else {
              showToast(`Enhance prompt error: ${d.error || 'Server error'}`, "❌");
            }
          } catch (e) {
            btnEnhance.disabled = false;
            console.error("Enhance prompt error:", e);
            showToast("Prompt enhanced with local rule compiler", "✨");
          }
        };
      }

      // Apply Enhanced Prompt
      if (btnApply) {
        btnApply.onclick = () => {
          if (promptInput && reviewTextarea) {
            promptInput.value = reviewTextarea.value;
            promptInput.focus();
            if (reviewCard) reviewCard.style.display = 'none';
            showToast("Applied professional flat label prompt to composer!", "✓");
          }
        };
      }

      // Dismiss Review
      if (btnDismiss) {
        btnDismiss.onclick = () => {
          if (reviewCard) reviewCard.style.display = 'none';
        };
      }

      // Generate Artwork
      if (btnGenerate) {
        btnGenerate.onclick = async () => {
          const prompt = promptInput ? promptInput.value.trim() : '';
          if (!prompt) {
            showToast("Please enter or enhance a prompt before generating!", "⚠️");
            return;
          }

          const provider = pSelect ? pSelect.value : 'auto';
          const model = mSelect ? mSelect.value : null;
          const ratio = window.currentAiAspectRatio || '3:1';

          showToast(`🚀 Generating Packaging Artwork with ${provider.toUpperCase()} (${ratio})...`, "✨", 12000);
          btnGenerate.disabled = true;

          try {
            const res = await fetch('/api/ai/generate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                prompt: prompt,
                provider: provider,
                model: model,
                aspect_ratio: ratio,
                negative_prompt: "3d jar container mockup, plastic bottle, tub model, cylinder perspective, photo on table, shadow, wrinkled label"
              })
            });
            const d = await res.json();
            btnGenerate.disabled = false;

            if (d.success && (d.image_url || d.saved_asset?.url)) {
              const finalUrl = d.saved_asset?.url || d.image_url;
              showToast("🎉 Packaging artwork generated! Opening as Full Label Artwork...", "🎉", 4000);
              
              // Open as Full Artwork (not sticker)
              await openImageAsFullLabel(finalUrl);
              
              // Sync with 3D packaging container
              updateThreeLabelTextureFromCanvas();
              showToast("Label artwork loaded into full studio & synchronized with 3D!", "✅");
            } else {
              showToast(`Generation failed: ${d.error || 'Server error'}`, "❌");
            }
          } catch (e) {
            btnGenerate.disabled = false;
            console.error("AI Generation error:", e);
            showToast(`Generation exception: ${e.message}`, "❌");
          }
        };
      }
    }

'''

# Inject ai_js_code right before anchor
insert_pos = html.find(anchor)
if insert_pos == -1:
    print("Could not find anchor position!")
    sys.exit(1)

html = html[:insert_pos] + ai_js_code + "\n\n" + html[insert_pos:]
print("Successfully injected AI Studio JavaScript engine!")

# Ensure initAiStudioEngine() is called in initGomziStudio()
if "initAiStudioEngine();" not in html:
    html = html.replace("initCanvaMagicTools();", "initCanvaMagicTools();\n      initAiStudioEngine();")
    print("Added initAiStudioEngine() call to initGomziStudio()!")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Saved templates/index.html with AI Studio JS engine!")
