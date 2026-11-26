# -*- coding: utf-8 -*-
import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Target drawer 7
old_drawer_start = '<!-- DRAWER 7: AI TOOLS -->'
old_drawer_end = '<!-- COLUMN 2: CENTER 2D CANVAS WORKSPACE -->'

start_idx = html.find(old_drawer_start)
end_idx = html.find(old_drawer_end)

if start_idx == -1 or end_idx == -1:
    print(f"Error: could not find Drawer 7 boundaries. start={start_idx}, end={end_idx}")
    sys.exit(1)

new_drawer_html = '''<!-- DRAWER 7: ADVANCED AI GENERATION & PROMPT STUDIO -->
              <div class="drawer-view" id="drawerAiTools" style="display:flex; flex-direction:column; gap:12px;">
                <div class="drawer-header" style="margin-bottom:0;">
                  <div style="display:flex; align-items:center; gap:6px;">
                    <span style="font-size:16px;">✨</span>
                    <span class="drawer-title" style="font-size:13px; font-weight:800; color:#0f172a;">AI Prompt & Generation Studio</span>
                  </div>
                  <span class="drawer-badge drawer-badge-green" id="aiProviderStatusBadge">PRO MULTILINGUAL</span>
                </div>

                <!-- 1. AI Provider & Model Dynamic Selector -->
                <div style="background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:8px; padding:10px; display:flex; flex-direction:column; gap:8px;">
                  <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                    <div>
                      <label style="font-size:10px; font-weight:800; color:#475569; text-transform:uppercase; display:block; margin-bottom:3px;">
                        AI Provider
                      </label>
                      <select id="aiProviderSelect" style="width:100%; background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:5px 6px; font-size:11px; font-weight:700; color:#1e293b; cursor:pointer;">
                        <option value="auto">✨ Auto Select (Optimal)</option>
                        <option value="gemini">⚡ Google Gemini</option>
                        <option value="openai">🧠 OpenAI GPT-Image 2.5</option>
                        <option value="recraft">📐 Recraft / REVE</option>
                        <option value="nanobanana">🍌 Nano Banana / Flow</option>
                      </select>
                    </div>

                    <div>
                      <label style="font-size:10px; font-weight:800; color:#475569; text-transform:uppercase; display:block; margin-bottom:3px;">
                        Model
                      </label>
                      <select id="aiModelSelect" style="width:100%; background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; padding:5px 6px; font-size:11px; font-weight:700; color:#1e293b; cursor:pointer;">
                        <option value="auto-optimal">Auto Optimal Model</option>
                      </select>
                    </div>
                  </div>

                  <!-- Model metadata strip -->
                  <div id="aiModelMetaStrip" style="display:flex; justify-content:space-between; align-items:center; font-size:10px; color:#64748b; border-top:1px dashed #cbd5e1; padding-top:6px;">
                    <span id="aiModelQualityTag">⚡ Ultra HD · Vector/Raster</span>
                    <span id="aiModelCostTag" style="font-weight:700; color:#15803d;">Best Price</span>
                  </div>
                </div>

                <!-- 2. Generation & Editing Mode Switcher -->
                <div style="display:flex; flex-direction:column; gap:4px;">
                  <label style="font-size:10px; font-weight:800; color:#64748b; text-transform:uppercase;">Generation Mode</label>
                  <div style="display:flex; gap:4px; overflow-x:auto; padding-bottom:2px;" id="aiModeButtonsContainer">
                    <button class="ai-mode-btn active" data-mode="generate" style="background:#0f172a; color:#fff; border:none; border-radius:6px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">🎨 Generate Design</button>
                    <button class="ai-mode-btn" data-mode="remove" style="background:#ffffff; color:#334155; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">🧹 Remove Element</button>
                    <button class="ai-mode-btn" data-mode="replace" style="background:#ffffff; color:#334155; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">🔄 Replace Element</button>
                    <button class="ai-mode-btn" data-mode="perfect_text" style="background:#ffffff; color:#334155; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">🔤 Perfect Text</button>
                  </div>
                </div>

                <!-- 3. Professional ChatGPT-Style Prompt Composer Container -->
                <div id="aiPromptComposerContainer" style="background:#ffffff; border:1.5px solid #cbd5e1; border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                  
                  <!-- Language Selector & Mic Status Header -->
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:6px;">
                      <span style="font-size:10px; font-weight:800; color:#334155;">SPEECH & INPUT:</span>
                      <select id="aiLanguageSelect" style="border:1px solid #cbd5e1; border-radius:4px; font-size:10.5px; padding:2px 4px; font-weight:700; color:#1e293b; background:#f8fafc;">
                        <option value="gu-IN" selected>🇮🇳 ગુજરાતી (Gujarati)</option>
                        <option value="hi-IN">🇮🇳 हिंदी (Hindi)</option>
                        <option value="en-IN">🇮🇳 Indian English</option>
                        <option value="en-US">🇺🇸 US English</option>
                      </select>
                    </div>

                    <div id="micStatusIndicator" style="display:flex; align-items:center; gap:4px; font-size:10px; font-weight:700; color:#64748b;">
                      <span id="micDot" style="width:6px; height:6px; border-radius:50%; background:#10b981; display:inline-block;"></span>
                      <span id="micStatusText">Mic Ready</span>
                    </div>
                  </div>

                  <!-- Multiline Textarea with Embedded Microphone Button -->
                  <div style="position:relative;">
                    <textarea id="aiPromptInput" rows="3" placeholder="Speak in Gujarati/Hindi/English or describe packaging... e.g. મારે ગોમઝીનું 1kg વે પ્રોટીન બ્લેક અને ગોલ્ડ કલરમાં બનાવવું છે, ચોકલેટ ફ્લેવર..." style="width:100%; border:1px solid #cbd5e1; border-radius:6px; padding:8px 36px 8px 8px; font-size:11.5px; font-family:inherit; color:#0f172a; resize:vertical; min-height:64px; line-height:1.4; outline:none; background:#fafafa;"></textarea>
                    
                    <button id="btnVoiceInput" type="button" title="Click to Speak in Gujarati, Hindi or English" style="position:absolute; right:6px; bottom:8px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:50%; width:28px; height:28px; display:flex; align-items:center; justify-content:center; cursor:pointer; color:#2563eb; font-size:13px; transition:all 0.2s;">
                      🎙️
                    </button>
                  </div>

                  <!-- Live Voice Recording Tray (Hidden by default, shown while recording) -->
                  <div id="voiceRecordingTray" style="display:none; background:#fef2f2; border:1.5px solid #fecaca; border-radius:6px; padding:8px; flex-direction:column; gap:6px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                      <div style="display:flex; align-items:center; gap:6px;">
                        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#ef4444;"></span>
                        <span style="font-size:11px; font-weight:800; color:#b91c1c;">Listening... Speak now</span>
                      </div>
                      <div style="display:flex; gap:4px;">
                        <button id="btnStopVoice" type="button" style="background:#b91c1c; color:#fff; border:none; border-radius:4px; padding:2px 8px; font-size:10px; font-weight:700; cursor:pointer;">Stop</button>
                        <button id="btnCancelVoice" type="button" style="background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; border-radius:4px; padding:2px 6px; font-size:10px; font-weight:700; cursor:pointer;">Cancel</button>
                      </div>
                    </div>
                    <div id="interimTranscript" style="font-size:11px; color:#475569; font-style:italic; min-height:18px;">Listening for speech...</div>
                  </div>

                  <!-- Reference Attachments Container -->
                  <div style="display:flex; flex-direction:column; gap:4px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                      <div style="display:flex; gap:4px;">
                        <button id="btnAttachCanvas" type="button" title="Attach Current Canvas Screenshot as Reference" style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; padding:3px 7px; font-size:10px; font-weight:700; color:#334155; cursor:pointer; display:flex; align-items:center; gap:4px;">
                          <span>🖼️</span> Canvas
                        </button>
                        <button id="btnAttachLogo" type="button" title="Attach Brand Logo" style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; padding:3px 7px; font-size:10px; font-weight:700; color:#334155; cursor:pointer; display:flex; align-items:center; gap:4px;">
                          <span>⭐</span> Logo
                        </button>
                        <button id="btnAttachUpload" type="button" title="Upload Reference File" style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; padding:3px 7px; font-size:10px; font-weight:700; color:#334155; cursor:pointer; display:flex; align-items:center; gap:4px;">
                          <span>📁</span> Upload
                        </button>
                        <input type="file" id="aiReferenceFileInput" accept="image/*" style="display:none;" />
                      </div>
                      
                      <div style="display:flex; gap:4px;">
                        <button id="btnClearPrompt" type="button" title="Clear Prompt" style="background:transparent; border:none; font-size:10.5px; color:#94a3b8; cursor:pointer;">Clear</button>
                      </div>
                    </div>

                    <!-- Thumbnails row -->
                    <div id="aiAttachmentsThumbnails" style="display:flex; gap:6px; flex-wrap:wrap;"></div>
                  </div>

                  <!-- Actions Bar: Enhance & Generate Buttons -->
                  <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:2px;">
                    <button id="btnEnhancePrompt" type="button" style="background:#f3f4f6; color:#1e293b; border:1.5px solid #d1d5db; border-radius:6px; padding:8px 10px; font-size:11px; font-weight:800; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px; transition:all 0.2s;">
                      <span>⚡</span> Enhance Prompt
                    </button>
                    <button id="btnGenerateArtwork" type="button" style="background:var(--clr-olive, #556b2f); color:#ffffff; border:none; border-radius:6px; padding:8px 10px; font-size:11px; font-weight:800; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                      <span>🚀</span> Generate Artwork
                    </button>
                  </div>

                  <!-- AI Enhanced Review Card (Hidden by default, shown when Enhance is clicked) -->
                  <div id="aiEnhancedReviewCard" style="display:none; background:#f0fdf4; border:1.5px solid #86efac; border-radius:8px; padding:10px; flex-direction:column; gap:6px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                      <span style="font-size:11px; font-weight:800; color:#166534; display:flex; align-items:center; gap:4px;">
                        <span>✓</span> Enhanced Flat 2D Artwork Prompt
                      </span>
                      <span id="aiEnhanceEngineBadge" style="font-size:9.5px; background:#dcfce7; color:#15803d; padding:1px 6px; border-radius:10px; font-weight:700;">GOMZI Director</span>
                    </div>

                    <!-- Detected Product Pills -->
                    <div id="aiDetectedPills" style="display:flex; gap:4px; flex-wrap:wrap; font-size:10px;"></div>

                    <!-- Review Textarea -->
                    <textarea id="aiReviewPromptTextarea" rows="4" style="width:100%; font-size:11px; border:1px solid #bbf7d0; border-radius:4px; padding:6px; font-family:inherit; color:#14532d; background:#ffffff; resize:vertical; line-height:1.35;"></textarea>
                    
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:2px;">
                      <span style="font-size:9.5px; color:#16a34a; font-weight:700;">🔒 Non-mockup flat vector constraint applied</span>
                      <div style="display:flex; gap:4px;">
                        <button id="btnApplyEnhancedPrompt" type="button" style="background:#16a34a; color:#fff; border:none; border-radius:4px; padding:4px 10px; font-size:10.5px; font-weight:800; cursor:pointer;">Use Prompt</button>
                        <button id="btnDismissEnhancedReview" type="button" style="background:#dcfce7; color:#15803d; border:1px solid #86efac; border-radius:4px; padding:4px 8px; font-size:10.5px; font-weight:700; cursor:pointer;">Dismiss</button>
                      </div>
                    </div>
                  </div>

                </div>

                <!-- 4. Aspect Ratio & Dimensions Bar -->
                <div style="display:flex; flex-direction:column; gap:4px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <label style="font-size:10px; font-weight:800; color:#64748b; text-transform:uppercase;">Artwork Aspect Ratio</label>
                    <span id="aiSelectedPresetDesc" style="font-size:10px; color:#15803d; font-weight:700;">3:1 Wrap Label (452×142mm)</span>
                  </div>
                  <div style="display:flex; gap:4px; overflow-x:auto; padding-bottom:2px;" id="aiAspectRatioContainer">
                    <button class="ai-aspect-btn active" data-ratio="3:1" type="button" style="background:#0f172a; color:#fff; border:none; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">3:1 Wrap</button>
                    <button class="ai-aspect-btn" data-ratio="1:1" type="button" style="background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">1:1 Box</button>
                    <button class="ai-aspect-btn" data-ratio="4:1" type="button" style="background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">4:1 Tub</button>
                    <button class="ai-aspect-btn" data-ratio="16:9" type="button" style="background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">16:9 Banner</button>
                    <button class="ai-aspect-btn" data-ratio="9:16" type="button" style="background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">9:16 Tall</button>
                    <button class="ai-aspect-btn" data-ratio="7:11" type="button" style="background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">Sachet</button>
                    <button class="ai-aspect-btn" data-ratio="2:3" type="button" style="background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; white-space:nowrap;">Pouch</button>
                  </div>
                </div>

                <!-- 5. Canva Pro Quick Tools Grid -->
                <div style="display:flex; flex-direction:column; gap:4px; margin-top:4px;">
                  <label style="font-size:10px; font-weight:800; color:#64748b; text-transform:uppercase;">Canva Pro Studio Tools</label>
                  <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
                    <button id="canvaToolMagicGrabBtn" type="button" style="background:#ffffff; border:1.5px solid #c084fc; border-radius:8px; padding:10px; cursor:pointer; text-align:center; position:relative;">
                      <span style="position:absolute; top:3px; right:3px; background:#9333ea; color:#fff; font-size:8px; padding:1px 4px; border-radius:6px; font-weight:800;">PRO</span>
                      <div style="font-size:20px;">🎈</div>
                      <div style="font-weight:700; font-size:11px; margin-top:2px; color:#7e22ce;">Magic Grab</div>
                    </button>

                    <button id="canvaToolGrabTextBtn" type="button" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                      <div style="font-size:20px;">🔤</div>
                      <div style="font-weight:700; font-size:11px; margin-top:2px;">Grab Text</div>
                    </button>
                    <button id="canvaToolBgRemoverBtn" type="button" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                      <div style="font-size:20px;">🏖️</div>
                      <div style="font-weight:700; font-size:11px; margin-top:2px;">BG Remover</div>
                    </button>
                    <button id="canvaToolMagicEraserBtn" type="button" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                      <div style="font-size:20px;">🧹</div>
                      <div style="font-weight:700; font-size:11px; margin-top:2px;">Magic Eraser</div>
                    </button>
                    <button id="canvaToolUpscaleBtn" type="button" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                      <div style="font-size:20px;">🌻</div>
                      <div style="font-weight:700; font-size:11px; margin-top:2px;">Upscale 4x</div>
                    </button>
                    <button id="canvaToolCleanPlateBtn" type="button" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                      <div style="font-size:20px;">🛡️</div>
                      <div style="font-weight:700; font-size:11px; margin-top:2px;">Clean Plate</div>
                    </button>
                  </div>
                </div>

                <!-- Grab Text Active Review Box -->
                <div id="grabTextReviewBox" style="display:none; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:10px; flex-direction:column; gap:6px;">
                  <div style="font-weight:800; font-size:11.5px; color:#166534;">✓ Detected Text Ready for Editing</div>
                  <div style="font-size:10.5px; color:#15803d;">Double-click any text directly on the canvas to edit in place. Background underneath is protected with Clean Plate.</div>
                  <button id="closeGrabTextBoxBtn" type="button" style="background:#15803d; color:#fff; border:none; border-radius:4px; padding:5px; font-size:11px; font-weight:700; cursor:pointer; margin-top:4px;">Got It</button>
                </div>
              </div>

            </aside>

            '''

html = html[:start_idx] + new_drawer_html + html[end_idx:]
print("Replaced Drawer 7 successfully!")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Saved updated Drawer 7 in index.html")
