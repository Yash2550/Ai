# Label Inpainter — Generative AI Object Removal for Product Labels

A local Flask web application that performs **high-fidelity generative in-painting** on product label images using the **Replicate API** (Stable Diffusion XL + CLIPSeg).

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- A [Replicate](https://replicate.com) account with an API token (~$0.03–$0.07 per image processed)

### 2. Setup

```bash
# Navigate to this folder
cd label-inpainter

# Create and activate a virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Your API Key

```bash
# Copy the example file
copy .env.example .env        # Windows
# or
cp .env.example .env          # macOS/Linux
```

Edit `.env` and replace `r8_your_replicate_api_key_here` with your actual key:

```
REPLICATE_API_KEY=r8_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get your key at: https://replicate.com/account/api-tokens

### 4. Run the Server

```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## 🖼️ How It Works

```
User uploads image + text prompt
        ↓
Flask server receives files
        ↓
Step 1: Image pre-processed (resize to ≤1024px, convert format)
        ↓
Step 2: CLIPSeg model on Replicate
        → Text prompt → binary segmentation mask
        ↓
Step 3: SDXL In-Painting on Replicate
        → image + mask + prompt → reconstructed image
        ↓
Step 4: Result downloaded and served back to browser
```

---

## 📁 Project Structure

```
label-inpainter/
│
├── app.py                  ← Flask server + Replicate API integration
├── requirements.txt        ← Python dependencies
├── .env                    ← Your API keys (NOT committed to git)
├── .env.example            ← Template for environment variables
├── README.md               ← This file
│
├── static/
│   ├── uploads/            ← Temporarily stores uploaded images
│   └── results/            ← Stores inpainted output images
│
└── templates/
    └── index.html          ← Premium UI frontend
```

---

## ⚙️ Models Used

| Model | Provider | Purpose |
|-------|----------|---------|
| `stability-ai/stable-diffusion-inpainting` (SDXL) | Replicate | Generative reconstruction of masked area |
| CLIPSeg | Replicate | Text-guided segmentation mask generation |

---

## 💰 Cost Estimate

| Usage | Estimated Cost |
|-------|----------------|
| Per image (mask + inpaint) | ~$0.03 – $0.07 |
| 100 images/month | ~$3 – $7 |
| 500 images/month | ~$15 – $35 |

---

## 🛡️ Security Notes

- **Never commit your `.env` file** — add it to `.gitignore`
- Uploaded images are stored locally in `static/uploads/` — clean periodically
- The server runs locally; only you have access unless you expose port 5000

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| `Missing API_KEY` error | Create `.env` and set `REPLICATE_API_KEY` |
| `Network error` in browser | Ensure `python app.py` is running |
| Timeout after 120s | Replicate may be under load; try again |
| Poor quality results | Use a more descriptive prompt; try negative prompts |
| Image not changing | The mask may not have found the object; be more specific in your prompt |
