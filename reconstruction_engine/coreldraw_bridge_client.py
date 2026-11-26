"""
Flask-side client for the optional Windows CorelDRAW Desktop Companion Bridge.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


def _bridge_config() -> tuple[str, str]:
    url = os.environ.get("CORELDRAW_BRIDGE_URL", "http://127.0.0.1:58112").strip().rstrip("/")
    token = os.environ.get("CORELDRAW_BRIDGE_TOKEN", "").strip()
    return url, token


def _bridge_request(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0,
) -> tuple[int, Dict[str, Any]]:
    url, token = _bridge_config()
    if not token:
        return 503, {
            "success": False,
            "bridge_running": False,
            "coreldraw_installed": False,
            "native_cdr_available": False,
            "error": (
                "CorelDRAW Desktop Bridge token (CORELDRAW_BRIDGE_TOKEN) is not configured. "
                "See coreldraw_bridge/README_BRIDGE_SETUP.md."
            ),
        }

    req_url = f"{url}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(req_url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as he:
        raw = he.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"success": False, "error": raw or str(he)}
        return he.code, data
    except Exception as exc:
        return 503, {
            "success": False,
            "bridge_running": False,
            "coreldraw_installed": False,
            "native_cdr_available": False,
            "error": f"CorelDRAW Desktop Bridge is offline ({exc}).",
        }


def get_coreldraw_bridge_status() -> Dict[str, Any]:
    """Probes the optional local CorelDRAW bridge without raising exceptions."""
    url, token = _bridge_config()
    if not token:
        return {
            "bridge_configured": False,
            "bridge_running": False,
            "coreldraw_installed": False,
            "coreldraw_version": None,
            "native_cdr_available": False,
            "bridge_url": url,
            "message": (
                "Native .cdr export & Open in CorelDRAW require the Windows CorelDRAW "
                "Desktop Bridge + licensed CorelDRAW installation. Use Editable SVG, "
                "Outlined SVG, or Vector PDF in the meantime."
            ),
        }

    status, data = _bridge_request("GET", "/bridge/status", timeout=2.0)
    if status == 200 and data.get("ok"):
        installed = bool(data.get("coreldraw_installed"))
        return {
            "bridge_configured": True,
            "bridge_running": True,
            "coreldraw_installed": installed,
            "coreldraw_version": data.get("coreldraw_version"),
            "native_cdr_available": installed,
            "bridge_url": url,
            "message": data.get("message") or "",
        }
    return {
        "bridge_configured": True,
        "bridge_running": False,
        "coreldraw_installed": False,
        "coreldraw_version": None,
        "native_cdr_available": False,
        "bridge_url": url,
        "message": data.get("error") or "CorelDRAW Desktop Bridge unreachable.",
    }


def bridge_open_in_coreldraw(
    svg_text: str,
    pdf_bytes: Optional[bytes] = None,
    filename: str = "GOMZI_Label",
) -> tuple[int, Dict[str, Any]]:
    payload = {
        "svg_text": svg_text,
        "pdf_b64": base64.b64encode(pdf_bytes).decode("ascii") if pdf_bytes else None,
        "filename": filename,
    }
    return _bridge_request("POST", "/bridge/open", payload=payload, timeout=30.0)


def bridge_export_native_cdr(
    svg_text: str,
    pdf_bytes: Optional[bytes] = None,
    filename: str = "GOMZI_Label",
) -> tuple[int, Dict[str, Any]]:
    payload = {
        "svg_text": svg_text,
        "pdf_b64": base64.b64encode(pdf_bytes).decode("ascii") if pdf_bytes else None,
        "filename": filename,
    }
    return _bridge_request("POST", "/bridge/export-cdr", payload=payload, timeout=45.0)


def bridge_import_native_cdr(
    cdr_bytes: bytes,
    filename: str = "design.cdr",
) -> tuple[int, Dict[str, Any]]:
    payload = {
        "cdr_b64": base64.b64encode(cdr_bytes).decode("ascii"),
        "filename": filename,
    }
    return _bridge_request("POST", "/bridge/import-cdr", payload=payload, timeout=45.0)
