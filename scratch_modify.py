import os
import re

app_file = r"d:\NEWWWW - Copy - Copy\app.py"

# Read content
try:
    with open(app_file, "r", encoding="utf-8") as f:
        content = f.read()
    write_encoding = "utf-8"
except UnicodeDecodeError:
    with open(app_file, "r", encoding="utf-16") as f:
        content = f.read()
    write_encoding = "utf-16"

# 1. Inject API Keys
api_key_injection = """
NANOBANANA_BASE_URL = (os.getenv("ATLASCLOUD_BASE_URL") or os.getenv("NANOBANANA_BASE_URL") or "https://api.pixapi.ai").rstrip("/")
if "pixapi.ai" in NANOBANANA_BASE_URL and "api.pixapi.ai" not in NANOBANANA_BASE_URL:
    NANOBANANA_BASE_URL = NANOBANANA_BASE_URL.replace("pixapi.ai", "api.pixapi.ai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY: OPENAI_API_KEY = OPENAI_API_KEY.strip("'\\\"")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY: GEMINI_API_KEY = GEMINI_API_KEY.strip("'\\\"")
"""

target = """NANOBANANA_BASE_URL = (os.getenv("ATLASCLOUD_BASE_URL") or os.getenv("NANOBANANA_BASE_URL") or "https://api.pixapi.ai").rstrip("/")
if "pixapi.ai" in NANOBANANA_BASE_URL and "api.pixapi.ai" not in NANOBANANA_BASE_URL:
    NANOBANANA_BASE_URL = NANOBANANA_BASE_URL.replace("pixapi.ai", "api.pixapi.ai")"""

if target in content:
    content = content.replace(target, api_key_injection)
else:
    print("Could not find target for API key injection.")

# 2. Add Generator Functions
generator_funcs = """
def run_openai_generations(prompt: str, image_size: str = "1:1") -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    size_map = {
        "1:1": "1024x1024", "16:9": "1792x1024", "9:16": "1024x1792",
        "4:3": "1792x1024", "3:4": "1024x1792", "3:1": "1792x1024"
    }
    size_str = size_map.get(image_size, "1024x1024")
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": size_str,
        "response_format": "b64_json"
    }
    import requests
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    b64 = resp.json()["data"][0]["b64_json"]
    return f"data:image/png;base64,{b64}"

def run_gemini_generations(prompt: str, image_size: str = "1:1") -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={GEMINI_API_KEY}"
    size_map = {
        "1:1": "1:1", "16:9": "16:9", "9:16": "9:16",
        "4:3": "4:3", "3:4": "3:4"
    }
    aspect_ratio = size_map.get(image_size, "1:1")
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "outputOptions": {"mimeType": "image/jpeg"}
        }
    }
    headers = {"Content-Type": "application/json"}
    import requests
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    b64 = resp.json()["predictions"][0]["bytesBase64Encoded"]
    return f"data:image/jpeg;base64,{b64}"

def run_openai_inpainting(*args, **kwargs):
    raise RuntimeError("OpenAI (DALL-E 3) does not support inpainting. Please use Recraft or Nano Banana.")

def run_gemini_inpainting(*args, **kwargs):
    raise RuntimeError("Google Gemini (Imagen 3) does not support inpainting. Please use Recraft or Nano Banana.")

"""

# Insert before @app.route("/")
if '@app.route("/")' in content:
    content = content.replace('@app.route("/")', generator_funcs + '\n@app.route("/")')
else:
    print("Could not find @app.route(\"/\")")


# 3. Update routing in /process
import re
pattern_process = re.compile(
    r'(if api_provider == "recraft":\s+b64 = run_recraft_inpainting\(image_path, mask_path, prompt, negative_prompt\)\s+elif api_provider == "nanobanana":\s+b64 = run_nanobanana_inpainting\(image_path, mask_path, prompt, negative_prompt\))'
)
new_process = """if api_provider == "recraft":
        b64 = run_recraft_inpainting(image_path, mask_path, prompt, negative_prompt)
    elif api_provider == "nanobanana":
        b64 = run_nanobanana_inpainting(image_path, mask_path, prompt, negative_prompt)
    elif api_provider == "openai":
        b64 = run_openai_inpainting(image_path, mask_path, prompt, negative_prompt)
    elif api_provider == "gemini":
        b64 = run_gemini_inpainting(image_path, mask_path, prompt, negative_prompt)"""

if pattern_process.search(content):
    content = pattern_process.sub(new_process, content)
else:
    print("Could not find /process routing logic.")


# 4. Update routing in /smart-process
pattern_smart_gen = re.compile(
    r'(if api_provider == "recraft":\s+b64 = run_recraft_generations\(prompt, negative_prompt, image_size\)\s+else:\s+b64 = run_nanobanana_generations\(prompt, negative_prompt, image_size\))'
)
new_smart_gen = """if api_provider == "recraft":
            b64 = run_recraft_generations(prompt, negative_prompt, image_size)
        elif api_provider == "openai":
            b64 = run_openai_generations(prompt, image_size)
        elif api_provider == "gemini":
            b64 = run_gemini_generations(prompt, image_size)
        else:
            b64 = run_nanobanana_generations(prompt, negative_prompt, image_size)"""
if pattern_smart_gen.search(content):
    content = pattern_smart_gen.sub(new_smart_gen, content)
else:
    print("Could not find /smart-process generation routing logic.")

pattern_smart_inp = re.compile(
    r'(if api_provider == "recraft":\s+b64 = run_recraft_inpainting\(tmp_img_path, tmp_mask_path, prompt, negative_prompt\)\s+else:\s+b64 = run_nanobanana_inpainting\(tmp_img_path, tmp_mask_path, prompt, negative_prompt\))'
)
new_smart_inp = """if api_provider == "recraft":
            b64 = run_recraft_inpainting(tmp_img_path, tmp_mask_path, prompt, negative_prompt)
        elif api_provider == "openai":
            b64 = run_openai_inpainting(tmp_img_path, tmp_mask_path, prompt, negative_prompt)
        elif api_provider == "gemini":
            b64 = run_gemini_inpainting(tmp_img_path, tmp_mask_path, prompt, negative_prompt)
        else:
            b64 = run_nanobanana_inpainting(tmp_img_path, tmp_mask_path, prompt, negative_prompt)"""

if pattern_smart_inp.search(content):
    content = pattern_smart_inp.sub(new_smart_inp, content)
else:
    print("Could not find /smart-process inpainting routing logic.")

with open(app_file, "w", encoding=write_encoding) as f:
    f.write(content)

print("Modification complete.")
