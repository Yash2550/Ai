"""
ai_provider_service.py - GOMZI BOB AI Provider Registry, Dynamic Model Selector & Prompt Enhancer
==================================================================================================
Centralized backend service managing:
  1. Multi-provider registry (Google Gemini, OpenAI, Recraft, REVE, Nano Banana, Eden AI, Auto).
  2. Dynamic per-model capabilities (aspect ratios, quality levels, editing, reference images, output counts).
  3. API connection testing, enable/disable toggle, and .env configuration without exposing full keys.
  4. Real SQLite API usage & cost tracking (never fabricating statistics or balances).
  5. Multilingual Speech / Prompt Enhancement (Gujarati, Hindi, English -> Professional 2D Flat Packaging Prompt).
  6. Strict deterministic dispatch through the user-selected provider without silent switching.
"""

import os
import re
import time
import json
import base64
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)

DEFAULT_BRAND = "GOMZI NUTRITION"

# ---------------------------------------------------------------------------
# Central Provider & Model Registry Specification
# ---------------------------------------------------------------------------

PROVIDER_CATALOG: Dict[str, Dict[str, Any]] = {
    "gemini": {
        "id": "gemini",
        "name": "Google Gemini",
        "badge": "Official Google AI",
        "env_key": "GEMINI_API_KEY",
        "description": "Google Gemini multimodal image and text models directly via generativelanguage API.",
        "default_model": "gemini-2.5-flash-image",
        "models": [
            {
                "id": "gemini-2.5-flash-image",
                "name": "Gemini 2.5 Flash Image",
                "type": "image",
                "aspect_ratios": ["1:1", "3:1", "4:1", "16:9", "9:16", "4:3", "3:4", "2:3"],
                "quality_options": ["Standard", "High"],
                "max_outputs": 1,
                "supports_editing": False,
                "supports_reference": True,
                "max_reference_images": 3,
                "cost": "$0.02 / img",
                "cost_usd": 0.02,
                "speed": "Fast",
                "recommended": True,
            },
            {
                "id": "gemini-3-pro-image",
                "name": "Gemini 3 Pro Image",
                "type": "image",
                "aspect_ratios": ["1:1", "3:1", "4:1", "16:9", "9:16", "4:3", "3:4"],
                "quality_options": ["High", "Ultra HD"],
                "max_outputs": 1,
                "supports_editing": False,
                "supports_reference": True,
                "max_reference_images": 4,
                "cost": "$0.04 / img",
                "cost_usd": 0.04,
                "speed": "Standard",
                "recommended": False,
            },
            {
                "id": "gemini-2.5-flash",
                "name": "Gemini 2.5 Flash (Text & Prompt Enhance)",
                "type": "text",
                "aspect_ratios": [],
                "quality_options": ["Standard"],
                "max_outputs": 1,
                "supports_editing": False,
                "supports_reference": False,
                "capabilities": ["enhance_prompt", "multilingual_translate"],
                "cost": "$0.0001 / call",
                "cost_usd": 0.0001,
                "recommended": False,
            },
        ],
        "supported_modes": ["generate", "enhance_prompt"],
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI",
        "badge": "GPT Image / DALL-E",
        "env_key": "OPENAI_API_KEY",
        "description": "OpenAI GPT-Image 2.5 and DALL-E 3 generators plus GPT-4o-mini prompt director.",
        "default_model": "gpt-image-2.5-sunburst",
        "models": [
            {
                "id": "gpt-image-2.5-sunburst",
                "name": "GPT Image 2.5 Sunburst",
                "type": "image",
                "aspect_ratios": ["1:1", "3:1", "4:1", "16:9", "9:16", "4:3", "2:3"],
                "quality_options": ["Standard", "High"],
                "max_outputs": 4,
                "supports_editing": False,
                "supports_reference": False,
                "max_reference_images": 0,
                "cost": "$0.04 / img",
                "cost_usd": 0.04,
                "speed": "Fast",
                "recommended": True,
            },
            {
                "id": "gpt-image-2",
                "name": "GPT Image 2 Medium",
                "type": "image",
                "aspect_ratios": ["1:1", "3:1", "16:9", "9:16", "4:3"],
                "quality_options": ["Standard", "High"],
                "max_outputs": 4,
                "supports_editing": False,
                "supports_reference": False,
                "max_reference_images": 0,
                "cost": "$0.03 / img",
                "cost_usd": 0.03,
                "speed": "Fast",
                "recommended": False,
            },
            {
                "id": "dall-e-3",
                "name": "DALL-E 3 HD",
                "type": "image",
                "aspect_ratios": ["1:1", "16:9", "9:16", "3:1"],
                "quality_options": ["Standard", "HD"],
                "max_outputs": 1,
                "supports_editing": False,
                "supports_reference": False,
                "max_reference_images": 0,
                "cost": "$0.04 / img",
                "cost_usd": 0.04,
                "speed": "Standard",
                "recommended": False,
            },
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini (Prompt & Translation)",
                "type": "text",
                "aspect_ratios": [],
                "quality_options": ["Standard"],
                "max_outputs": 1,
                "supports_editing": False,
                "supports_reference": False,
                "capabilities": ["enhance_prompt", "multilingual_translate"],
                "cost": "$0.0002 / call",
                "cost_usd": 0.0002,
                "recommended": False,
            },
        ],
        "supported_modes": ["generate", "enhance_prompt"],
    },
    "recraft": {
        "id": "recraft",
        "name": "Recraft AI",
        "badge": "Vector & Print",
        "env_key": "RECRAFT_API_KEY",
        "description": "Recraft V3 commercial print artwork generation and mask-based inpainting.",
        "default_model": "recraftv3",
        "models": [
            {
                "id": "recraftv3",
                "name": "Recraft V3 (Commercial Print)",
                "type": "image",
                "aspect_ratios": ["1:1", "3:1", "4:1", "16:9", "9:16", "7:11", "2:3", "custom"],
                "quality_options": ["Standard", "High"],
                "max_outputs": 2,
                "supports_editing": True,
                "supports_reference": True,
                "max_reference_images": 1,
                "cost": "$0.04 / img",
                "cost_usd": 0.04,
                "speed": "Fast",
                "recommended": True,
            },
        ],
        "supported_modes": ["generate", "edit", "remove", "add", "replace"],
    },
    "reve": {
        "id": "reve",
        "name": "REVE Studio API",
        "badge": "Layout Digitizer",
        "env_key": "REVE_API_KEY",
        "description": "Official REVE layout digitization engine for structured Fabric.js decomposition.",
        "default_model": "reve-digitize",
        "models": [
            {
                "id": "reve-digitize",
                "name": "REVE Layout Digitizer",
                "type": "digitize",
                "aspect_ratios": ["1:1", "3:1", "4:1", "custom"],
                "quality_options": ["Standard"],
                "max_outputs": 1,
                "supports_editing": True,
                "supports_reference": True,
                "max_reference_images": 1,
                "capabilities": ["digitize_to_fabric"],
                "cost": "Metered by plan",
                "cost_usd": 0.0,
                "speed": "Standard",
                "recommended": True,
            },
        ],
        "supported_modes": ["edit"],
    },
    "nanobanana": {
        "id": "nanobanana",
        "name": "Nano Banana (PixAPI / Atlas)",
        "badge": "Edit & Inpaint",
        "env_key": "NANOBANANA_API_KEY",
        "description": "Nano Banana gateway supporting text-to-image generation and mask-based label editing.",
        "default_model": "gpt-image-2.5-flare",
        "models": [
            {
                "id": "gpt-image-2.5-flare",
                "name": "Nano Banana Flare (Generate & Inpaint)",
                "type": "image",
                "aspect_ratios": ["1:1", "3:1", "4:1", "16:9", "9:16", "4:3"],
                "quality_options": ["Low", "Medium", "High"],
                "max_outputs": 2,
                "supports_editing": True,
                "supports_reference": True,
                "max_reference_images": 1,
                "cost": "$0.02 / img",
                "cost_usd": 0.02,
                "speed": "Fast",
                "recommended": True,
            },
            {
                "id": "nano-banana-2-lite",
                "name": "Nano Banana 2 Lite (AtlasCloud)",
                "type": "image",
                "aspect_ratios": ["1:1", "3:1", "4:1", "16:9", "9:16"],
                "quality_options": ["Standard", "1K"],
                "max_outputs": 1,
                "supports_editing": True,
                "supports_reference": True,
                "max_reference_images": 1,
                "cost": "$0.01 / img",
                "cost_usd": 0.01,
                "speed": "Fast",
                "recommended": False,
            },
        ],
        "supported_modes": ["generate", "edit", "remove", "add", "replace", "perfect_text"],
    },
    "edenai": {
        "id": "edenai",
        "name": "Eden AI",
        "badge": "Multi-Engine",
        "env_key": "EDENAI_API_KEY",
        "description": "Eden AI unified image generation gateway.",
        "default_model": "edenai-openai",
        "models": [
            {
                "id": "edenai-openai",
                "name": "Eden AI (OpenAI Route)",
                "type": "image",
                "aspect_ratios": ["1:1", "16:9", "9:16", "4:3"],
                "quality_options": ["Standard"],
                "max_outputs": 1,
                "supports_editing": False,
                "supports_reference": False,
                "cost": "Metered by EdenAI",
                "cost_usd": 0.04,
                "speed": "Standard",
                "recommended": True,
            },
        ],
        "supported_modes": ["generate"],
    },
    "auto": {
        "id": "auto",
        "name": "Auto Select",
        "badge": "Smart Router",
        "env_key": None,
        "description": "Selects the highest-priority enabled and configured provider for the requested operation.",
        "default_model": "auto-optimal",
        "models": [
            {
                "id": "auto-optimal",
                "name": "Auto Select Optimal Model",
                "type": "all",
                "aspect_ratios": ["1:1", "3:1", "4:1", "16:9", "9:16", "7:11", "2:3", "custom"],
                "quality_options": ["Standard", "High", "Ultra HD"],
                "max_outputs": 2,
                "supports_editing": True,
                "supports_reference": True,
                "max_reference_images": 3,
                "cost": "Selected provider rate",
                "cost_usd": 0.02,
                "speed": "Dynamic",
                "recommended": True,
            },
        ],
        "supported_modes": ["generate", "edit", "remove", "add", "replace", "perfect_text", "enhance_prompt"],
    },
}

# Packaging physical & aspect ratio presets
PACKAGING_DIMENSION_PRESETS = [
    {
        "id": "wrap-315x110",
        "name": "Wrap Label (315 × 110 mm)",
        "dimensions": "315 × 110 mm",
        "aspect_ratio": "3:1",
        "pixels": [1536, 512],
        "category": "Protein Jars",
    },
    {
        "id": "wrap-452x142",
        "name": "1kg Muscle Tub Wrap (452 × 142 mm)",
        "dimensions": "452 × 142 mm",
        "aspect_ratio": "3:1",
        "pixels": [1536, 512],
        "category": "Protein Jars",
    },
    {
        "id": "sachet-70x110",
        "name": "Single-Serve Sachet (70 × 110 mm)",
        "dimensions": "70 × 110 mm",
        "aspect_ratio": "7:11",
        "pixels": [700, 1100],
        "category": "Sachets",
    },
    {
        "id": "pouch-160x240",
        "name": "Stand-up Pouch (160 × 240 mm)",
        "dimensions": "160 × 240 mm",
        "aspect_ratio": "2:3",
        "pixels": [1000, 1500],
        "category": "Pouches",
    },
    {
        "id": "square-1x1",
        "name": "Square Box / Front Panel (1:1)",
        "dimensions": "120 × 120 mm",
        "aspect_ratio": "1:1",
        "pixels": [1024, 1024],
        "category": "Boxes",
    },
    {
        "id": "wide-4x1",
        "name": "Ultra-Wide 5kg Tub Wrap (4:1)",
        "dimensions": "750 × 240 mm",
        "aspect_ratio": "4:1",
        "pixels": [2048, 512],
        "category": "Mega Tubs",
    },
    {
        "id": "landscape-16x9",
        "name": "Landscape Label / Header (16:9)",
        "dimensions": "160 × 90 mm",
        "aspect_ratio": "16:9",
        "pixels": [1536, 864],
        "category": "Banners",
    },
    {
        "id": "portrait-9x16",
        "name": "Tall Bottle / Carton (9:16)",
        "dimensions": "90 × 160 mm",
        "aspect_ratio": "9:16",
        "pixels": [864, 1536],
        "category": "Bottles",
    },
]


def mask_key(key: Optional[str]) -> str:
    """Mask API key so only prefix and suffix characters appear."""
    if not key or key.startswith("your_"):
        return ""
    clean = key.strip().strip("'\"")
    if len(clean) <= 8:
        return "••••••••"
    return f"{clean[:4]}••••••••{clean[-4:]}"


def _get_disabled_providers() -> set:
    load_dotenv(override=True)
    raw = os.getenv("GOMZI_DISABLED_PROVIDERS", "")
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def log_api_usage(
    provider: str,
    model: str = "",
    mode: str = "generate",
    status: str = "success",
    latency_ms: int = 0,
    estimated_usd: float = 0.0,
    error_message: str = "",
    prompt_preview: str = "",
) -> None:
    """Persists real API usage telemetry into SQLite if Flask app context is active."""
    try:
        from flask import has_app_context
        from database import db
        from models import ApiUsageLog

        if has_app_context():
            rec = ApiUsageLog(
                provider=provider,
                model=model,
                mode=mode,
                status=status,
                latency_ms=int(latency_ms or 0),
                estimated_usd=float(estimated_usd or 0.0),
                error_message=(error_message or "")[:500],
                prompt_preview=(prompt_preview or "")[:240],
            )
            db.session.add(rec)
            db.session.commit()
    except Exception:
        pass


def get_api_usage_summary() -> Dict[str, Any]:
    """Reads actual per-provider API usage stats from SQLite."""
    summary: Dict[str, Dict[str, Any]] = {}
    total_calls = 0
    total_failed = 0
    total_usd = 0.0
    try:
        from flask import has_app_context
        from models import ApiUsageLog

        if has_app_context():
            logs = ApiUsageLog.query.order_by(ApiUsageLog.created_at.desc()).all()
            for log in logs:
                total_calls += 1
                if log.status != "success":
                    total_failed += 1
                total_usd += float(log.estimated_usd or 0.0)
                p = summary.setdefault(
                    log.provider,
                    {
                        "calls": 0,
                        "failed": 0,
                        "cost_usd": 0.0,
                        "last_status": log.status,
                        "last_latency_ms": log.latency_ms,
                        "last_at": log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else "",
                    },
                )
                p["calls"] += 1
                if log.status != "success":
                    p["failed"] += 1
                p["cost_usd"] = round(p["cost_usd"] + float(log.estimated_usd or 0.0), 4)
    except Exception:
        pass

    return {
        "by_provider": summary,
        "total_calls": total_calls,
        "total_failed": total_failed,
        "total_cost_usd": round(total_usd, 4),
    }


def get_provider_status() -> List[Dict[str, Any]]:
    """Returns real configured status, masked keys, enable state, models, and DB usage stats."""
    load_dotenv(override=True)
    default_provider = os.getenv("GOMZI_DEFAULT_AI_PROVIDER", "gemini").lower()
    disabled = _get_disabled_providers()
    usage = get_api_usage_summary().get("by_provider", {})
    results = []

    for pid, pdata in PROVIDER_CATALOG.items():
        env_var = pdata["env_key"]
        raw_key = os.getenv(env_var, "").strip().strip("'\"") if env_var else ""
        if pid == "auto":
            has_any = any(
                bool(os.getenv(p["env_key"], "").strip().strip("'\""))
                and not os.getenv(p["env_key"], "").startswith("your_")
                and p["id"] not in disabled
                for p in PROVIDER_CATALOG.values()
                if p["env_key"]
            )
            is_configured = has_any
        else:
            is_configured = bool(raw_key and not raw_key.startswith("your_"))

        is_enabled = pid not in disabled
        p_usage = usage.get(pid, {"calls": 0, "failed": 0, "cost_usd": 0.0, "last_status": "not_run", "last_latency_ms": 0})

        results.append({
            "id": pdata["id"],
            "name": pdata["name"],
            "badge": pdata["badge"],
            "description": pdata["description"],
            "is_configured": is_configured,
            "is_enabled": is_enabled,
            "masked_key": mask_key(raw_key),
            "env_var_name": env_var,
            "is_default": (pid == default_provider),
            "default_model": pdata["default_model"],
            "models": pdata["models"],
            "supported_modes": pdata["supported_modes"],
            "usage": p_usage,
        })

    return results


def get_models_for_provider(provider_id: str) -> List[Dict[str, Any]]:
    pdata = PROVIDER_CATALOG.get(provider_id.lower()) or PROVIDER_CATALOG["auto"]
    return pdata.get("models", [])


def test_provider_connection(provider_id: str, test_key: Optional[str] = None) -> Dict[str, Any]:
    """Performs a live HTTP check against the actual provider endpoint. Never leaks full keys."""
    load_dotenv(override=True)
    pid = provider_id.lower()

    if pid == "auto":
        status_list = get_provider_status()
        active = [p["id"] for p in status_list if p["id"] != "auto" and p["is_configured"] and p["is_enabled"]]
        if not active:
            return {"success": False, "provider": "auto", "message": "No enabled providers configured."}
        res = test_provider_connection(active[0])
        res["provider"] = f"auto (via {active[0]})"
        return res

    start = time.time()

    if pid == "gemini":
        key = (test_key or os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")
        if not key:
            return {"success": False, "provider": pid, "message": "GEMINI_API_KEY is not set."}
        try:
            resp = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=6)
            lat = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                models = [m["name"].replace("models/", "") for m in resp.json().get("models", [])]
                return {"success": True, "provider": pid, "latency_ms": lat, "message": f"Connected ({len(models)} models available).", "sample_models": models[:5]}
            return {"success": False, "provider": pid, "latency_ms": lat, "message": f"HTTP {resp.status_code}: {resp.text[:140]}"}
        except Exception as e:
            return {"success": False, "provider": pid, "message": f"Connection error: {e}"}

    if pid == "openai":
        key = (test_key or os.getenv("OPENAI_API_KEY") or "").strip().strip("'\"")
        if not key:
            return {"success": False, "provider": pid, "message": "OPENAI_API_KEY is not set."}
        try:
            resp = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=6)
            lat = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                models = [m["id"] for m in resp.json().get("data", []) if "gpt" in m["id"] or "dall-e" in m["id"]]
                return {"success": True, "provider": pid, "latency_ms": lat, "message": f"Connected ({len(models)} models accessible).", "sample_models": models[:5]}
            return {"success": False, "provider": pid, "latency_ms": lat, "message": f"HTTP {resp.status_code}: {resp.text[:140]}"}
        except Exception as e:
            return {"success": False, "provider": pid, "message": f"Connection error: {e}"}

    if pid == "recraft":
        key = (test_key or os.getenv("RECRAFT_API_KEY") or "").strip().strip("'\"")
        if not key:
            return {"success": False, "provider": pid, "message": "RECRAFT_API_KEY is not set."}
        try:
            resp = requests.get("https://external.api.recraft.ai/v1/users/me", headers={"Authorization": f"Bearer {key}"}, timeout=6)
            lat = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                credits = data.get("credits", "Unknown")
                return {"success": True, "provider": pid, "latency_ms": lat, "message": f"Connected. Credits: {credits}", "credits": str(credits)}
            return {"success": False, "provider": pid, "latency_ms": lat, "message": f"HTTP {resp.status_code}: {resp.text[:140]}"}
        except Exception as e:
            return {"success": False, "provider": pid, "message": f"Connection error: {e}"}

    if pid == "reve":
        key = (test_key or os.getenv("REVE_API_KEY") or "").strip().strip("'\"")
        endpoint = os.getenv("REVE_API_ENDPOINT", "https://api.reve.com/v1/digitize")
        if not key:
            return {"success": False, "provider": pid, "message": "REVE_API_KEY is not set."}
        try:
            resp = requests.options(endpoint, headers={"Authorization": f"Bearer {key}"}, timeout=6)
            lat = int((time.time() - start) * 1000)
            if resp.status_code < 500:
                return {"success": True, "provider": pid, "latency_ms": lat, "message": f"Endpoint reachable (HTTP {resp.status_code})."}
            return {"success": False, "provider": pid, "latency_ms": lat, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "provider": pid, "message": f"Endpoint check failed: {e}"}

    if pid == "nanobanana":
        key = (test_key or os.getenv("NANOBANANA_API_KEY") or os.getenv("ATLASCLOUD_API_KEY") or "").strip().strip("'\"")
        base_url = os.getenv("NANOBANANA_BASE_URL", "https://api.pixapi.ai").strip().strip("'\"")
        if not key:
            return {"success": False, "provider": pid, "message": "NANOBANANA_API_KEY is not set."}
        try:
            resp = requests.get(f"{base_url.rstrip('/')}/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=6)
            lat = int((time.time() - start) * 1000)
            if resp.status_code in (200, 404):
                return {"success": True, "provider": pid, "latency_ms": lat, "message": f"Gateway reachable ({base_url})."}
            return {"success": False, "provider": pid, "latency_ms": lat, "message": f"HTTP {resp.status_code}: {resp.text[:140]}"}
        except Exception as e:
            return {"success": False, "provider": pid, "message": f"Connection error: {e}"}

    if pid == "edenai":
        key = (test_key or os.getenv("EDENAI_API_KEY") or "").strip().strip("'\"")
        if not key:
            return {"success": False, "provider": pid, "message": "EDENAI_API_KEY is not set."}
        try:
            resp = requests.get("https://api.edenai.run/v2/info/providers", headers={"Authorization": f"Bearer {key}"}, timeout=6)
            lat = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                return {"success": True, "provider": pid, "latency_ms": lat, "message": "Eden AI gateway verified."}
            return {"success": False, "provider": pid, "latency_ms": lat, "message": f"HTTP {resp.status_code}: {resp.text[:140]}"}
        except Exception as e:
            return {"success": False, "provider": pid, "message": f"Connection error: {e}"}

    return {"success": False, "provider": provider_id, "message": f"Unknown provider: {provider_id}"}


def _update_env_vars(updates: Dict[str, str]) -> None:
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    lines = []
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

    remaining = dict(updates)
    new_lines = []
    for line in lines:
        stripped = line.strip()
        replaced = False
        for k, v in list(remaining.items()):
            if stripped.startswith(f"{k}="):
                new_lines.append(f'{k}="{v}"\n')
                remaining.pop(k)
                replaced = True
                break
        if not replaced:
            new_lines.append(line)

    for k, v in remaining.items():
        new_lines.append(f'{k}="{v}"\n')

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    load_dotenv(override=True)


def save_provider_config(provider_id: str, api_key: Optional[str] = None, set_default: bool = False) -> Dict[str, Any]:
    pid = provider_id.lower()
    pdata = PROVIDER_CATALOG.get(pid)
    if not pdata and pid != "auto":
        return {"success": False, "message": f"Invalid provider: {provider_id}"}

    updates = {}
    env_var = pdata.get("env_key") if pdata else None
    if env_var and api_key:
        updates[env_var] = api_key.strip()
    if set_default:
        updates["GOMZI_DEFAULT_AI_PROVIDER"] = pid

    if updates:
        _update_env_vars(updates)

    return {
        "success": True,
        "message": f"Configuration updated for {pdata['name'] if pdata else pid}.",
    }


def toggle_provider_enabled(provider_id: str, enabled: bool) -> Dict[str, Any]:
    pid = provider_id.lower()
    if pid == "auto":
        return {"success": False, "message": "Auto Select cannot be disabled."}
    disabled = _get_disabled_providers()
    if enabled:
        disabled.discard(pid)
    else:
        disabled.add(pid)
    _update_env_vars({"GOMZI_DISABLED_PROVIDERS": ",".join(sorted(disabled))})
    return {"success": True, "provider": pid, "is_enabled": enabled}


# ---------------------------------------------------------------------------
# Multilingual Voice-to-Professional-Prompt Transformation Engine
# ---------------------------------------------------------------------------

PACKAGING_PROMPT_SYSTEM_INSTRUCTION = """You are a Senior Packaging & Graphic Design Director at GOMZI BOB.
Convert natural language input (Gujarati, Hindi, English, or mixed) into a studio-grade, print-ready FLAT 2D packaging artwork prompt in English.

STRICT RULES:
1. TARGET IS FLAT 2D PACKAGING ARTWORK:
   - Specify: "flat 2D rectangular packaging label design, unrolled flat vector artwork layout, high-resolution print-safe layout".
   - CRITICAL EXCLUSIONS: "flat artwork only, no jar, no bottle, no 3D packaging mockup, no perspective distortion, preserve readable text".
2. PRESERVE USER SPECIFICATIONS EXACTLY:
   - Preserve user brand name (or default to "GOMZI NUTRITION" if omitted).
   - Preserve product name, net weight, flavour, color palette, design style, physical dimensions, ingredients, and explicit exclusions.
3. DO NOT INVENT CLAIMS OR NUTRITION NUMBERS:
   - Never fabricate nutrition facts numbers, RDA percentages, certifications (like ISO/GMP/FSSAI), or health claims that the user did not supply.
   - If the user did not supply specific nutrition figures, describe structured editable layout placeholders rather than inventing fake values.

OUTPUT VALID JSON ONLY:
{
  "translated_intent": "Clear English summary of user's request",
  "detected_brand": "Brand name extracted or GOMZI NUTRITION",
  "detected_product": "Product name extracted",
  "detected_flavor": "Flavor extracted or empty string",
  "detected_weight": "Weight extracted or empty string",
  "enhanced_prompt": "Professional English flat 2D packaging artwork generation prompt",
  "negative_prompt": "3d jar container mockup, bottle, packaging mockup, perspective distortion, photo on table, wrinkled paper, blurry text, watermark",
  "recommended_aspect_ratio": "3:1"
}
"""


def enhance_prompt_via_rule_compiler(raw_text: str, language: str = "gu-IN", aspect_ratio: str = "3:1") -> Dict[str, Any]:
    """Deterministic packaging prompt compiler preserving user details without inventing claims."""
    text_lower = raw_text.lower()

    brand = DEFAULT_BRAND
    if any(k in raw_text or k in text_lower for k in ["gomzi", "ગોમઝી", "गोमजी"]):
        brand = "GOMZI NUTRITION"
    elif "nx" in text_lower:
        brand = "NX NUTRI LAB"
    elif "hamza" in text_lower:
        brand = "HAMZA NUTRITION"

    product = "Supplement Product"
    if any(k in raw_text or k in text_lower for k in ["whey protein", "વે પ્રોટીન", "व्हे प्रोटीन", "protein"]):
        product = "Whey Protein"
    elif any(k in raw_text or k in text_lower for k in ["mass gainer", "માસ ગેઇનર", "ગેઇનર", "मास गेनर"]):
        product = "Mass Gainer"
    elif any(k in raw_text or k in text_lower for k in ["creatine", "ક્રિએટાઇન", "क्रिएटिन"]):
        product = "Creatine Monohydrate"
    elif any(k in raw_text or k in text_lower for k in ["biotin", "બાયોટિન", "बायोटिन"]):
        product = "Biotin"
    elif any(k in raw_text or k in text_lower for k in ["omega", "ઓમેગા", "ओमेगा"]):
        product = "Omega 3"
    elif "bcaa" in text_lower:
        product = "BCAA"

    flavor = ""
    if any(k in raw_text or k in text_lower for k in ["belgian chocolate", "બેલ્જિયન ચોકલેટ"]):
        flavor = "Belgian Chocolate"
    elif any(k in raw_text or k in text_lower for k in ["chocolate", "ચોકલેટ", "चॉकलेट"]):
        flavor = "Chocolate"
    elif any(k in raw_text or k in text_lower for k in ["mango", "મેંગો", "કેરી", "आम"]):
        flavor = "Mango"
    elif any(k in raw_text or k in text_lower for k in ["strawberry", "સ્ટ્રોબેરી", "स्ट्रॉबेरी"]):
        flavor = "Strawberry"
    elif any(k in raw_text or k in text_lower for k in ["vanilla", "વેનીલા", "वैनिला"]):
        flavor = "Vanilla"
    elif any(k in raw_text or k in text_lower for k in ["unflavoured", "unflavored", "અનફ્લેવર્ડ"]):
        flavor = "Unflavoured"

    weight = ""
    if any(k in raw_text or k in text_lower for k in ["2 kg", "2kg", "બે કિલો", "2 કિલો", "2 किलो", "दो किलो"]):
        weight = "2 kg"
    elif any(k in raw_text or k in text_lower for k in ["5 kg", "5kg", "પાંચ કિલો", "5 કિલો", "5 किलो", "पांच किलो"]):
        weight = "5 kg"
    elif any(k in raw_text or k in text_lower for k in ["500 g", "500g", "૫૦૦ ગ્રામ", "500 ग्राम"]):
        weight = "500 g"
    elif any(k in raw_text or k in text_lower for k in ["1 kg", "1kg", "એક કિલો", "1 કિલો", "1 किलो", "एक किलो"]):
        weight = "1 kg"

    color_parts = []
    if any(k in raw_text or k in text_lower for k in ["cream", "ક્રીમ", "क्रीम"]):
        color_parts.append("soft warm cream")
    if any(k in raw_text or k in text_lower for k in ["green", "લીલા", "ગ્રીન", "લીલો", "हरा"]):
        color_parts.append("olive forest green")
    if any(k in raw_text or k in text_lower for k in ["black", "બ્લેક", "કાળા", "काला"]):
        color_parts.append("matte obsidian black")
    if any(k in raw_text or k in text_lower for k in ["gold", "ગોલ્ડ", "सोना"]):
        color_parts.append("metallic gold accents")
    if any(k in raw_text or k in text_lower for k in ["purple", "જાંબલી", "बैंगनी"]):
        color_parts.append("amethyst purple accents")
    if any(k in raw_text or k in text_lower for k in ["white", "વ્હાઇટ", "સફેદ", "सफेद"]):
        color_parts.append("clean white")
    color_theme = " and ".join(color_parts) if color_parts else "soft cream and olive forest green palette with clean white typography containers"

    flavor_clause = f", {flavor} flavour banner" if flavor else ""
    weight_clause = f", Net Wt. {weight}" if weight else ""

    enhanced_prompt = (
        f"Professional commercial flat 2D rectangular packaging label design for '{brand} {product}'{weight_clause}{flavor_clause}, "
        f"unrolled print-ready artwork layout maintaining {aspect_ratio} aspect ratio. "
        f"Color & style: {color_theme}, crisp legible sans-serif typography, balanced three-panel label hierarchy "
        f"(left structured panel reserved for nutritional information table, bold centered brand and product title with '{brand}' header, "
        f"right panel reserved for product highlights and barcode area). "
        f"Flat artwork only, no jar, no bottle, no 3D packaging mockup, no perspective distortion, print-safe margins, crisp readable text."
    )

    negative_prompt = (
        "3d jar container mockup, bottle, packaging mockup, cylindrical warp, perspective distortion, "
        "photo on desk, shadows, wrinkled paper, blurry text, distorted lettering, watermark"
    )

    return {
        "translated_intent": f"Flat 2D label for {brand} {product}{weight_clause}{flavor_clause} ({color_theme}).",
        "detected_brand": brand,
        "detected_product": product,
        "detected_flavor": flavor,
        "detected_weight": weight,
        "enhanced_prompt": enhanced_prompt,
        "negative_prompt": negative_prompt,
        "recommended_aspect_ratio": aspect_ratio or "3:1",
        "engine": "GOMZI BOB Deterministic Prompt Compiler",
    }


def enhance_prompt_multilingual(
    raw_text: str,
    language: str = "gu-IN",
    aspect_ratio: str = "3:1",
    provider_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Converts voice/manual prompt in Gujarati/Hindi/English into structured flat 2D packaging prompt."""
    if not raw_text or not raw_text.strip():
        return {"error": "Empty prompt text provided."}

    text = raw_text.strip()
    load_dotenv(override=True)
    start = time.time()

    # Prefer configured text-capable API (Gemini Flash or OpenAI GPT-4o-mini)
    gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip().strip("'\"")

    order = ["openai", "gemini"] if provider_id == "openai" else ["gemini", "openai"]
    for eng in order:
        if eng == "gemini" and gemini_key and not gemini_key.startswith("your_"):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{PACKAGING_PROMPT_SYSTEM_INSTRUCTION}\n\nInput Language: {language}\nAspect Ratio: {aspect_ratio}\nUser Input: {text}"}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.25},
                }
                resp = requests.post(url, json=payload, timeout=8)
                if resp.status_code == 200:
                    raw_out = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_out)
                    parsed["engine"] = "Google Gemini 2.5 Flash"
                    log_api_usage("gemini", "gemini-2.5-flash", "enhance_prompt", "success", int((time.time() - start) * 1000), 0.0001, "", text)
                    return parsed
            except Exception:
                pass
        elif eng == "openai" and openai_key and not openai_key.startswith("your_"):
            try:
                resp = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": PACKAGING_PROMPT_SYSTEM_INSTRUCTION},
                            {"role": "user", "content": f"Input Language: {language}\nAspect Ratio: {aspect_ratio}\nUser Input: {text}"},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.25,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    parsed = json.loads(resp.json()["choices"][0]["message"]["content"])
                    parsed["engine"] = "OpenAI GPT-4o Mini"
                    log_api_usage("openai", "gpt-4o-mini", "enhance_prompt", "success", int((time.time() - start) * 1000), 0.0002, "", text)
                    return parsed
            except Exception:
                pass

    return enhance_prompt_via_rule_compiler(text, language=language, aspect_ratio=aspect_ratio)


# ---------------------------------------------------------------------------
# Strict Direct Image Generation Dispatcher (No Silent Provider Switching)
# ---------------------------------------------------------------------------

def generate_packaging_artwork(
    prompt: str,
    provider_id: str = "auto",
    model_id: Optional[str] = None,
    aspect_ratio: str = "3:1",
    quality: str = "High",
    output_count: int = 1,
    negative_prompt: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Executes image generation strictly through the selected provider and model.
    Never silently switches providers when an explicit provider is requested.
    """
    load_dotenv(override=True)
    pid = (provider_id or "auto").lower()
    disabled = _get_disabled_providers()

    if pid != "auto" and pid in disabled:
        raise RuntimeError(f"Provider '{pid}' is currently disabled in API Management.")

    if pid == "auto":
        status_list = get_provider_status()
        active = [p for p in status_list if p["id"] != "auto" and p["is_configured"] and p["is_enabled"]]
        if not active:
            raise RuntimeError("No enabled AI image provider configured. Configure an API key in API Management.")
        order = ["gemini", "openai", "nanobanana", "recraft", "edenai"]
        selected_p = next((p for o in order for p in active if p["id"] == o), active[0])
        pid = selected_p["id"]
        if not model_id or model_id == "auto-optimal":
            model_id = selected_p["default_model"]

    # Validate aspect ratio against selected model capabilities where declared
    models = get_models_for_provider(pid)
    model_meta = next((m for m in models if m["id"] == model_id), models[0] if models else {})
    supported_ratios = model_meta.get("aspect_ratios", [])
    if supported_ratios and "custom" not in supported_ratios and aspect_ratio not in supported_ratios:
        raise RuntimeError(
            f"Aspect ratio '{aspect_ratio}' is not natively supported by {model_meta.get('name', pid)}. "
            f"Supported ratios: {', '.join(supported_ratios)}"
        )

    start = time.time()
    est_cost = float(model_meta.get("cost_usd", 0.02)) * max(1, int(output_count or 1))

    try:
        if pid == "gemini":
            from app import run_gemini_generations
            chosen_model = model_id or "gemini-2.5-flash-image"
            img_data_uri = run_gemini_generations(
                prompt=prompt,
                image_size=aspect_ratio,
                model_id=chosen_model,
                reference_images=reference_images,
            )
            res = {"success": True, "provider": "gemini", "model": chosen_model, "aspect_ratio": aspect_ratio, "image_url": img_data_uri}

        elif pid == "openai":
            from app import run_openai_generations
            chosen_model = model_id or "gpt-image-2.5-sunburst"
            img_data_uri = run_openai_generations(
                prompt=prompt,
                image_size=aspect_ratio,
                model_id=chosen_model,
                quality=quality.lower(),
                n=max(1, min(int(output_count or 1), 4)),
            )
            res = {"success": True, "provider": "openai", "model": chosen_model, "aspect_ratio": aspect_ratio, "image_url": img_data_uri}

        elif pid == "recraft":
            from app import run_recraft_generations
            neg = negative_prompt or "blurry, low quality, 3d jar, distorted text"
            img_url = run_recraft_generations(prompt=prompt, negative_prompt=neg, image_size=aspect_ratio)
            res = {"success": True, "provider": "recraft", "model": model_id or "recraftv3", "aspect_ratio": aspect_ratio, "image_url": img_url}

        elif pid == "nanobanana":
            from app import run_nanobanana_generations
            neg = negative_prompt or "blurry, low quality, 3d jar, distorted text"
            img_url = run_nanobanana_generations(prompt=prompt, negative_prompt=neg, image_size=aspect_ratio)
            res = {"success": True, "provider": "nanobanana", "model": model_id or "gpt-image-2.5-flare", "aspect_ratio": aspect_ratio, "image_url": img_url}

        elif pid == "edenai":
            from app import run_edenai_generations
            img_url = run_edenai_generations(prompt=prompt, image_size=aspect_ratio)
            res = {"success": True, "provider": "edenai", "model": model_id or "edenai-openai", "aspect_ratio": aspect_ratio, "image_url": img_url}

        else:
            raise RuntimeError(f"Provider '{pid}' does not support direct text-to-image generation.")

        lat = int((time.time() - start) * 1000)
        log_api_usage(pid, res["model"], "generate", "success", lat, est_cost, "", prompt)
        return res

    except Exception as e:
        lat = int((time.time() - start) * 1000)
        log_api_usage(pid, model_id or "", "generate", "failed", lat, 0.0, str(e), prompt)
        raise
