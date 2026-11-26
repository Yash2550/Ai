# GOMZI BOB — Optional Windows CorelDRAW Desktop Bridge Setup

The **CorelDRAW Desktop Bridge** (`coreldraw_bridge/bridge_server.py`) is an optional, Windows-only localhost companion service that connects GOMZI BOB to a **licensed desktop CorelDRAW installation** via Windows COM automation (`CorelDRAW.Application`).

> **Important:** Without CorelDRAW installed on Windows and this bridge running, GOMZI BOB still exports 100% CorelDRAW-compatible **Editable SVG**, **Outlined Curve SVG**, **Vector PDF**, and **CorelDRAW Interchange ZIP** packages—and never fakes `.cdr` files by renaming SVG/PDF.

## 1. Prerequisites
- **OS:** Windows 10 / 11
- **CorelDRAW:** Licensed CorelDRAW Graphics Suite (X7, 2018–2024+ with COM Automation enabled)
- **Python Package:** `pywin32` (`pip install pywin32`)

## 2. Configure & Start the Bridge
Set a shared secret bearer token and start the bridge on `127.0.0.1:58112`:

```powershell
$env:CORELDRAW_BRIDGE_TOKEN = "replace-with-strong-random-token"
python -m coreldraw_bridge.bridge_server --port 58112
```

## 3. Connect GOMZI BOB Flask Server
In the terminal where you run `python app.py`, set the matching URL and token:

```powershell
$env:CORELDRAW_BRIDGE_URL = "http://127.0.0.1:58112"
$env:CORELDRAW_BRIDGE_TOKEN = "replace-with-strong-random-token"
python app.py
```

## 4. Security Model
- Binds strictly to `127.0.0.1` (loopback only).
- Requires `Authorization: Bearer <CORELDRAW_BRIDGE_TOKEN>` on every request.
- Validates `Origin` headers against `CORELDRAW_BRIDGE_ALLOWED_ORIGINS` (defaults to `http://127.0.0.1:5000,http://localhost:5000`).
- Uses isolated temporary directories for SVG/PDF/CDR interchange.
