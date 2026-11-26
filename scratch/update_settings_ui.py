# -*- coding: utf-8 -*-
import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Locate renderOtherModule
target_code = """      const c = config[modName] || { title: modName, sub: 'Module Overview', html: '<p>Module active.</p>' };
      titleEl.textContent = c.title;
      subEl.textContent = c.sub;
      contentEl.innerHTML = c.html;"""

if target_code not in html:
    print("Could not find target_code in html!")
    sys.exit(1)

replacement_code = """      const c = config[modName] || { title: modName, sub: 'Module Overview', html: '<p>Module active.</p>' };
      titleEl.textContent = c.title;
      subEl.textContent = c.sub;
      contentEl.innerHTML = c.html;

      if (modName === 'settings') {
        renderAiSettingsModule(contentEl);
      }"""

html = html.replace(target_code, replacement_code, 1)

# Now define renderAiSettingsModule function before renderOtherModule
settings_func_code = """
    async function renderAiSettingsModule(containerEl) {
      const wrapper = document.createElement('div');
      wrapper.style.cssText = 'margin-top:20px; border-top:1.5px solid #e2e8f0; padding-top:16px; max-width:680px;';
      wrapper.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <div>
            <h3 style="font-size:14px; font-weight:800; color:#0f172a; display:flex; align-items:center; gap:6px;">
              <span>⚡</span> AI API Providers & Credentials Management
            </h3>
            <p style="font-size:11px; color:#64748b; margin-top:2px;">
              Manage and verify real AI providers securely. Keys are stored server-side and never exposed.
            </p>
          </div>
          <button id="btnRefreshAiSettings" style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:11px; font-weight:700; color:#334155; cursor:pointer;">
            🔄 Refresh Status
          </button>
        </div>
        <div id="aiProvidersSettingsList" style="display:flex; flex-direction:column; gap:10px;">
          <div style="font-size:11px; color:#64748b;">Loading provider status...</div>
        </div>
      `;
      containerEl.appendChild(wrapper);

      async function loadSettingsList() {
        const listEl = document.getElementById('aiProvidersSettingsList');
        if (!listEl) return;
        try {
          const res = await fetch('/api/ai/providers');
          const data = await res.json();
          if (!data.success || !data.providers) return;

          listEl.innerHTML = '';
          data.providers.forEach(p => {
            const card = document.createElement('div');
            card.style.cssText = 'background:#ffffff; border:1.5px solid #e2e8f0; border-radius:8px; padding:12px; display:flex; flex-direction:column; gap:8px;';

            const statusColor = p.is_configured ? '#15803d' : '#b45309';
            const statusBg = p.is_configured ? '#dcfce7' : '#fef3c7';
            const statusText = p.is_configured ? '● Configured' : '○ Missing Key';

            card.innerHTML = `
              <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                  <div style="display:flex; align-items:center; gap:6px;">
                    <span style="font-size:16px;">${p.icon || '🤖'}</span>
                    <strong style="font-size:13px; color:#0f172a;">${p.name}</strong>
                    <span style="font-size:10px; background:${statusBg}; color:${statusColor}; padding:1px 6px; border-radius:10px; font-weight:800;">
                      ${statusText}
                    </span>
                    ${p.is_default ? '<span style="font-size:10px; background:#eff6ff; color:#2563eb; padding:1px 6px; border-radius:10px; font-weight:800;">DEFAULT</span>' : ''}
                  </div>
                  <div style="font-size:11px; color:#64748b; margin-top:2px;">
                    ${p.description || ''}
                  </div>
                </div>

                <div style="display:flex; gap:6px;">
                  <button class="test-conn-btn" data-pid="${p.id}" style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:11px; font-weight:700; color:#1e293b; cursor:pointer;">
                    Test Connection
                  </button>
                  ${p.id !== 'auto' && !p.is_default ? `<button class="set-default-btn" data-pid="${p.id}" style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:4px; padding:4px 8px; font-size:11px; font-weight:700; color:#1e293b; cursor:pointer;">Set Default</button>` : ''}
                </div>
              </div>

              ${p.env_var_name ? `
              <div style="display:flex; gap:6px; align-items:center; background:#f8fafc; border-radius:6px; padding:6px 8px;">
                <span style="font-size:10px; font-weight:800; color:#475569; width:130px;">
                  ${p.env_var_name}:
                </span>
                <span style="font-size:11px; font-family:monospace; color:#334155; flex:1;">
                  ${p.masked_key || '<span style="color:#94a3b8;">(not set)</span>'}
                </span>
                <input type="password" placeholder="Enter new API key" class="new-key-input" data-pid="${p.id}" style="border:1px solid #cbd5e1; border-radius:4px; padding:3px 6px; font-size:11px; width:160px;" />
                <button class="save-key-btn" data-pid="${p.id}" style="background:#0f172a; color:#fff; border:none; border-radius:4px; padding:3px 8px; font-size:11px; font-weight:700; cursor:pointer;">
                  Update
                </button>
              </div>
              ` : ''}

              <div class="conn-result-box" id="connResult_${p.id}" style="display:none; font-size:10.5px; border-radius:4px; padding:6px 8px;"></div>
            `;

            // Test Connection handler
            card.querySelector('.test-conn-btn')?.addEventListener('click', async () => {
              const resBox = card.querySelector(`#connResult_${p.id}`);
              resBox.style.display = 'block';
              resBox.style.background = '#f8fafc';
              resBox.style.color = '#334155';
              resBox.textContent = `Testing connection to ${p.name}...`;

              try {
                const tr = await fetch('/api/ai/test-connection', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ provider: p.id })
                });
                const td = await tr.json();
                if (td.success) {
                  resBox.style.background = '#dcfce7';
                  resBox.style.color = '#15803d';
                  resBox.textContent = `✓ ${td.message} (${td.latency_ms || 0}ms)`;
                } else {
                  resBox.style.background = '#fee2e2';
                  resBox.style.color = '#991b1b';
                  resBox.textContent = `✕ ${td.message || 'Connection failed'}`;
                }
              } catch (err) {
                resBox.style.background = '#fee2e2';
                resBox.style.color = '#991b1b';
                resBox.textContent = `✕ Connection error: ${err.message}`;
              }
            });

            // Update Key handler
            card.querySelector('.save-key-btn')?.addEventListener('click', async () => {
              const input = card.querySelector(`.new-key-input[data-pid="${p.id}"]`);
              const newKey = input ? input.value.trim() : '';
              if (!newKey) {
                showToast("Please enter an API key", "⚠️");
                return;
              }
              showToast("Saving API key...", "⏳");
              try {
                const sr = await fetch('/api/ai/save-config', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ provider: p.id, api_key: newKey })
                });
                const sd = await sr.json();
                if (sd.success) {
                  showToast(`Updated key for ${p.name}!`, "✓");
                  input.value = '';
                  loadSettingsList();
                  loadAiProviderCatalog();
                } else {
                  showToast(`Error saving key: ${sd.error}`, "❌");
                }
              } catch (err) {
                showToast(`Error: ${err.message}`, "❌");
              }
            });

            // Set Default handler
            card.querySelector('.set-default-btn')?.addEventListener('click', async () => {
              showToast(`Setting ${p.name} as default...`, "⏳");
              try {
                const sr = await fetch('/api/ai/save-config', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ provider: p.id, set_default: true })
                });
                const sd = await sr.json();
                if (sd.success) {
                  showToast(`${p.name} is now the default provider!`, "✓");
                  loadSettingsList();
                  loadAiProviderCatalog();
                }
              } catch (err) {
                showToast(`Error: ${err.message}`, "❌");
              }
            });

            listEl.appendChild(card);
          });
        } catch (e) {
          console.error("Error loading AI settings:", e);
        }
      }

      document.getElementById('btnRefreshAiSettings')?.addEventListener('click', () => {
        loadSettingsList();
        showToast("Refreshed AI provider statuses", "🔄");
      });

      loadSettingsList();
    }
"""

target_module_def = "function renderOtherModule(modName) {"
if target_module_def in html:
    html = html.replace(target_module_def, settings_func_code + "\n\n    " + target_module_def)
    print("Successfully added renderAiSettingsModule function!")
else:
    print("Could not find renderOtherModule definition!")
    sys.exit(1)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Saved updated index.html with Settings UI!")
