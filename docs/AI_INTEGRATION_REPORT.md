# GOMZI BOB — AI Provider Integration, Voice Prompt & Editing Report

**Core Backend Module:** [`ai_provider_service.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/ai_provider_service.py)  
**Frontend Controller:** [`static/js/studio_ai.js`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/js/studio_ai.js)  
**API Blueprint / App Integration:** [`app.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/app.py)

---

## 1. Configured AI Provider & Model Catalog

Providers are dynamically discovered from server environment variables (`.env`) via `PROVIDER_CATALOG` and exposed via `GET /api/ai/providers`:

| Provider ID | Display Name | Env Variable | Configured Models |
| :--- | :--- | :--- | :--- |
| `gemini` | Google Gemini | `GEMINI_API_KEY` | `gemini-2.5-flash-image`, `gemini-3-pro-image`, `gemini-2.5-flash` |
| `openai` | OpenAI | `OPENAI_API_KEY` | `gpt-image-2.5-sunburst`, `gpt-image-2`, `dall-e-3`, `gpt-4o-mini` |
| `recraft` | Recraft AI | `RECRAFT_API_KEY` | `recraftv3` |
| `reve` | REVE Studio API | `REVE_API_KEY` | `reve-digitize` |
| `nanobanana` | Nano Banana (PixAPI / Atlas) | `NANOBANANA_API_KEY` | `gpt-image-2.5-flare`, `nano-banana-2-lite` |
| `edenai` | Eden AI | `EDENAI_API_KEY` | `edenai-openai` |
| `auto` | Auto Select | *(derived from active keys)* | `auto-optimal` |

- **Strict Selected Provider Execution:** Choosing a provider (e.g., `gemini` or `openai`) routes `POST /api/ai/generate` and `POST /api/ai/edit` exclusively to that provider without silently switching to another API.
- **No-Fabrication Guarantee:** Only `auto` selects an active configured provider when explicitly chosen by the user. Unconfigured or disabled providers cannot be executed silently.
- **API Management Controls:** Users can ping live provider endpoints (`POST /api/ai/test-connection`), update `.env` API keys (`POST /api/ai/save-config`), enable/disable providers (`POST /api/ai/toggle-provider`), and audit real usage counts & estimated costs stored in `ApiUsageLog` (`GET /api/ai/usage`).

---

## 2. Dynamic Model Capabilities & Prompt Composer

When changing **API Provider** or **AI Model**, `updateModelsAndCapabilitiesForProvider()` dynamically updates:
- Available **Aspect Ratios** (e.g., `3:1 (Wrap Label · 315×110 mm)`, `1:1`, `4:5`, `16:9`, etc.)
- Supported **Quality Options** and **Outputs Count**
- Per-image estimated cost indicator (e.g., `$0.02 / img`)

### Prompt Enhancement & Non-Fabrication Rules (`POST /api/ai/enhance-prompt`)
- Accepts English, **Gujarati (`gu-IN`)**, and **Hindi (`hi-IN`)** natural-language input.
- Extracts user-specified brand, product type, net weight, flavor, and color theme (verified on Gujarati test input producing `"detected_flavor": "Chocolate"` and Hindi `"detected_weight": "2 kg"` without inventing unstated `"Belgian"` or `"60 Servings"` claims).
- Displays extracted metadata badges alongside the enhanced flat 2D print-ready prompt with `Keep Original` and `Apply Prompt` controls.

### Multilingual Voice-to-Prompt (`initWebSpeechEngine()`)
- Integrated browser **Web Speech API** (`SpeechRecognition` / `webkitSpeechRecognition`) supporting `Gujarati (gu-IN)`, `Hindi (hi-IN)`, and `English (en-IN / en-US)` with visual microphone pulse feedback.

---

## 3. Non-Destructive AI Editing & Layer Extraction

- **Generate Modes:** `Add` / `Replace` / `Perfect Text`
- **Edit & Remove Tools (`POST /api/ai/edit`, `/api/canva/ai-prompt-edit`):**
  - Displays side-by-side **Review AI Edit (Non-Destructive Before / After)** modal (`#aiBeforeAfterModal`) comparing Original Artwork vs Edited Preview before applying to the Fabric.js stage (`Reject & Keep Original` vs `Apply Edited Artwork`).
- **Extraction & Clean Plate Tools:**
  - `Grab Text` (`/api/canva/grab-text` — EasyOCR + Telea background repair + editable Fabric `Textbox`)
  - `Grab Object` (`/api/canva/grab-object`)
  - `Background Repair` / Clean Plate (`/api/canva/inpaint-text`)
  - `BG Remover` (`/api/canva/bg-remover`)
  - `Magic Eraser` (`/api/canva/magic-eraser`)
  - `Upscale 2x` (`/api/canva/upscale`)

---

## 4. Known Unconfigured Integrations

- `CANVA_CLIENT_ID` / Canva Connect OAuth REST export jobs require merchant OAuth credentials in `.env` before `/api/canva/official/import-design` can execute against live Canva cloud workspaces.
- `GOOGLE_FLOW_API_TOKEN` is optional and not configured in `.env` unless explicitly added by the user.
