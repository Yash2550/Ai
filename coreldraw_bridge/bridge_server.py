"""
Optional Windows CorelDRAW Desktop Companion Bridge for GOMZI BOB.

Runs locally on Windows alongside a licensed CorelDRAW desktop installation
and communicates with GOMZI BOB over authenticated localhost HTTP.
Never fakes .cdr files: if CorelDRAW COM automation is unavailable, endpoints
honestly return HTTP 503 with clear diagnostics.
"""
from __future__ import annotations

import argparse
import base64
import hmac
import json
import os
import secrets
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.environ.get("CORELDRAW_BRIDGE_PORT", "58112"))
MAX_PAYLOAD_BYTES = 40 * 1024 * 1024  # 40 MB


def _allowed_origins() -> set[str]:
    raw = os.environ.get(
        "CORELDRAW_BRIDGE_ALLOWED_ORIGINS",
        "http://127.0.0.1:5000,http://localhost:5000",
    )
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


def probe_coreldraw_com() -> Dict[str, Any]:
    """
    Probes Windows COM for an installed CorelDRAW desktop instance.
    Returns honest capability metadata without throwing.
    """
    if os.name != "nt":
        return {
            "os": os.name,
            "pywin32": False,
            "coreldraw_installed": False,
            "coreldraw_version": None,
            "message": "CorelDRAW COM automation is only supported on Windows.",
        }
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception as exc:
        return {
            "os": os.name,
            "pywin32": False,
            "coreldraw_installed": False,
            "coreldraw_version": None,
            "message": f"pywin32 is not available: {exc}",
        }

    pythoncom.CoInitialize()
    try:
        try:
            app = win32com.client.GetActiveObject("CorelDRAW.Application")
        except Exception:
            app = win32com.client.Dispatch("CorelDRAW.Application")
        version = None
        try:
            version = str(getattr(app, "VersionMajor", "")) or str(getattr(app, "Version", ""))
        except Exception:
            version = "Detected"
        return {
            "os": os.name,
            "pywin32": True,
            "coreldraw_installed": True,
            "coreldraw_version": version,
            "message": f"CorelDRAW COM ready (version {version}).",
        }
    except Exception as exc:
        return {
            "os": os.name,
            "pywin32": True,
            "coreldraw_installed": False,
            "coreldraw_version": None,
            "message": f"CorelDRAW desktop application is not installed or registered for COM: {exc}",
        }
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _safe_stem(name: str) -> str:
    cleaned = "".join(c if (c.isalnum() or c in ("_", "-")) else "_" for c in (name or "GOMZI_Label"))
    return cleaned.strip("_") or "GOMZI_Label"


def _com_open_or_export(
    svg_text: Optional[str],
    pdf_b64: Optional[str],
    filename: str,
    save_cdr: bool = False,
    open_visible: bool = True,
) -> Tuple[int, Dict[str, Any]]:
    """
    Imports SVG or Vector PDF into CorelDRAW via Windows COM.
    If save_cdr=True, saves native .cdr and returns base64 bytes.
    """
    probe = probe_coreldraw_com()
    if not probe["coreldraw_installed"]:
        return 503, {"success": False, "error": probe["message"], **probe}

    import pythoncom  # type: ignore
    import win32com.client  # type: ignore

    stem = _safe_stem(filename.rsplit(".", 1)[0])
    pythoncom.CoInitialize()
    try:
        app = win32com.client.Dispatch("CorelDRAW.Application")
        if open_visible:
            app.Visible = True

        work_dir = tempfile.mkdtemp(prefix="gomzi_cdr_")
        src_path = ""
        if svg_text:
            src_path = os.path.join(work_dir, f"{stem}.svg")
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(svg_text)
        elif pdf_b64:
            src_path = os.path.join(work_dir, f"{stem}.pdf")
            with open(src_path, "wb") as f:
                f.write(base64.b64decode(pdf_b64))
        else:
            return 400, {"success": False, "error": "No svg_text or pdf_b64 payload provided."}

        doc = app.CreateDocument()
        doc.ActiveLayer.Import(src_path)

        result: Dict[str, Any] = {
            "success": True,
            "coreldraw_version": probe.get("coreldraw_version"),
            "opened_path": src_path,
        }
        if save_cdr:
            cdr_path = os.path.join(work_dir, f"{stem}.cdr")
            doc.SaveAs(cdr_path)
            with open(cdr_path, "rb") as f:
                result["cdr_b64"] = base64.b64encode(f.read()).decode("ascii")
            result["filename"] = f"{stem}.cdr"
            if not open_visible:
                doc.Close()
        return 200, result
    except Exception as exc:
        return 500, {"success": False, "error": f"CorelDRAW COM operation failed: {exc}"}
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _com_import_cdr(cdr_b64: str, filename: str) -> Tuple[int, Dict[str, Any]]:
    """Opens a binary .cdr file in CorelDRAW COM and exports editable SVG + Vector PDF."""
    probe = probe_coreldraw_com()
    if not probe["coreldraw_installed"]:
        return 503, {"success": False, "error": probe["message"], **probe}

    import pythoncom  # type: ignore
    import win32com.client  # type: ignore

    stem = _safe_stem(filename.rsplit(".", 1)[0])
    pythoncom.CoInitialize()
    try:
        app = win32com.client.Dispatch("CorelDRAW.Application")
        with tempfile.TemporaryDirectory(prefix="gomzi_cdr_in_") as tmpdir:
            cdr_path = os.path.join(tmpdir, f"{stem}.cdr")
            svg_path = os.path.join(tmpdir, f"{stem}.svg")
            pdf_path = os.path.join(tmpdir, f"{stem}.pdf")
            with open(cdr_path, "wb") as f:
                f.write(base64.b64decode(cdr_b64))

            doc = app.OpenDocument(cdr_path)
            # cdrSVG = 1363, cdrPDF = 1318 (CorelDRAW COM filter IDs)
            doc.ExportEx(svg_path, 1363).Finish()
            doc.PublishToPDF(pdf_path)
            doc.Close()

            svg_text = ""
            if os.path.isfile(svg_path):
                with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
                    svg_text = f.read()
            pdf_b64_out = ""
            if os.path.isfile(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_b64_out = base64.b64encode(f.read()).decode("ascii")

            return 200, {
                "success": True,
                "coreldraw_version": probe.get("coreldraw_version"),
                "svg_text": svg_text,
                "pdf_b64": pdf_b64_out,
            }
    except Exception as exc:
        return 500, {"success": False, "error": f"CorelDRAW CDR import failed: {exc}"}
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def make_bridge_handler(token: str, allowed_origins: Optional[set[str]] = None):
    origins = allowed_origins if allowed_origins is not None else _allowed_origins()

    class BridgeHandler(BaseHTTPRequestHandler):
        server_version = "GOMZICorelBridge/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            return  # Keep console clean during tests/daemon runs

        def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _check_security(self) -> Optional[Tuple[int, Dict[str, Any]]]:
            origin = (self.headers.get("Origin") or "").strip().rstrip("/")
            if origin and origin not in origins:
                return 403, {"success": False, "error": f"Origin '{origin}' is not allowed."}
            auth = (self.headers.get("Authorization") or "").strip()
            expected = f"Bearer {token}"
            if not auth or not hmac.compare_digest(auth, expected):
                return 401, {"success": False, "error": "Unauthorized: valid Bearer token required."}
            return None

        def _read_json_body(self) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[int, Dict[str, Any]]]]:
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                return None, (400, {"success": False, "error": "Invalid Content-Length."})
            if length <= 0 or length > MAX_PAYLOAD_BYTES:
                return None, (413, {"success": False, "error": "Payload empty or exceeds 40 MB limit."})
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8")), None
            except Exception:
                return None, (400, {"success": False, "error": "Invalid JSON body."})

        def do_GET(self) -> None:
            err = self._check_security()
            if err:
                return self._send_json(*err)
            if self.path.rstrip("/") == "/bridge/status":
                probe = probe_coreldraw_com()
                return self._send_json(200, {"ok": True, **probe})
            return self._send_json(404, {"success": False, "error": "Unknown bridge endpoint."})

        def do_POST(self) -> None:
            err = self._check_security()
            if err:
                return self._send_json(*err)
            data, body_err = self._read_json_body()
            if body_err:
                return self._send_json(*body_err)
            assert data is not None
            path = self.path.rstrip("/")
            if path == "/bridge/open":
                status, payload = _com_open_or_export(
                    svg_text=data.get("svg_text"),
                    pdf_b64=data.get("pdf_b64"),
                    filename=str(data.get("filename") or "GOMZI_Label"),
                    save_cdr=False,
                    open_visible=True,
                )
                return self._send_json(status, payload)
            if path == "/bridge/export-cdr":
                status, payload = _com_open_or_export(
                    svg_text=data.get("svg_text"),
                    pdf_b64=data.get("pdf_b64"),
                    filename=str(data.get("filename") or "GOMZI_Label"),
                    save_cdr=True,
                    open_visible=False,
                )
                return self._send_json(status, payload)
            if path == "/bridge/import-cdr":
                cdr_b64 = str(data.get("cdr_b64") or "")
                if not cdr_b64:
                    return self._send_json(400, {"success": False, "error": "Missing cdr_b64 payload."})
                status, payload = _com_import_cdr(
                    cdr_b64=cdr_b64,
                    filename=str(data.get("filename") or "design.cdr"),
                )
                return self._send_json(status, payload)
            return self._send_json(404, {"success": False, "error": "Unknown bridge endpoint."})

    return BridgeHandler


def create_bridge_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    token: Optional[str] = None,
    allowed_origins: Optional[set[str]] = None,
) -> Tuple[ThreadingHTTPServer, str]:
    tok = token or os.environ.get("CORELDRAW_BRIDGE_TOKEN") or secrets.token_urlsafe(24)
    handler = make_bridge_handler(tok, allowed_origins=allowed_origins)
    srv = ThreadingHTTPServer((host, port), handler)
    return srv, tok


def main() -> None:
    parser = argparse.ArgumentParser(description="GOMZI BOB Optional Windows CorelDRAW COM Bridge")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token", default=os.environ.get("CORELDRAW_BRIDGE_TOKEN", ""))
    args = parser.parse_args()

    srv, tok = create_bridge_server(host=args.host, port=args.port, token=args.token or None)
    probe = probe_coreldraw_com()
    print(f"[GOMZI CorelDRAW Bridge] Listening on http://{args.host}:{args.port}")
    print(f"[GOMZI CorelDRAW Bridge] Bearer Token: {tok}")
    print(f"[GOMZI CorelDRAW Bridge] CorelDRAW Status: {probe['message']}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[GOMZI CorelDRAW Bridge] Shutting down.")
        srv.shutdown()


if __name__ == "__main__":
    main()
