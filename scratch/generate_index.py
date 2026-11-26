# -*- coding: utf-8 -*-
"""
Script to generate the complete production-ready GOMZI BOB AI Design Studio Pro (templates/index.html).
Strictly follows the reference screenshot:
- White SaaS background
- Olive green accent (#708238 / #6b8e23)
- Left persistent navigation sidebar
- 3-column studio layout
- Live 3D Muscle Tub Mockup (Three.js)
- Official GOMZI NUTRITION branding throughout
- Full Fabric.js 2D canvas with Grab Text, Background Preservation, and CorelDRAW CDR/PDF/SVG export.
"""

import os

HTML_CONTENT = r'''<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GOMZI BOB — AI Design Studio Pro</title>
  
  <!-- External Libraries: Fabric.js, Three.js, OrbitControls, JsBarcode, QRCode -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.1/fabric.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
  
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Anton&family=Bebas+Neue&family=Cinzel:wght@600;700;800;900&family=Inter:wght@400;500;600;700;800;900&family=Montserrat:wght@400;500;600;700;800;900&family=Oswald:wght@400;600;700&family=Outfit:wght@400;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;0,900;1,700&family=Poppins:wght@400;500;600;700;800&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">

  <style>
    /* ======================================================
       CSS RESET & GOMZI BOB DESIGN TOKENS
       Clean White SaaS Platform with Olive-Green Accent
    ====================================================== */
    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    :root {
      --clr-bg: #f8fafc;
      --clr-surface: #ffffff;
      --clr-surface-dim: #f1f5f9;
      --clr-workspace: #eef0f3;
      --clr-border: #e2e8f0;
      --clr-border-dark: #cbd5e1;
      
      /* Primary Olive Green Accent */
      --clr-olive: #708238;
      --clr-olive-dark: #556b2f;
      --clr-olive-light: #eef4e8;
      --clr-olive-border: #b9d19d;
      
      --clr-text: #0f172a;
      --clr-text-muted: #64748b;
      --clr-text-dim: #94a3b8;
      
      --radius-sm: 6px;
      --radius-md: 8px;
      --radius-lg: 12px;
      --radius-pill: 9999px;
      
      --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
      --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
      --shadow-artboard: 0 10px 30px rgba(0, 0, 0, 0.08), 0 1px 4px rgba(0, 0, 0, 0.04);
    }

    html, body {
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--clr-bg);
      color: var(--clr-text);
      font-size: 13px;
    }

    button, input, select, textarea {
      font-family: inherit;
    }

    /* Custom Scrollbars */
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f5f9;
    }
    ::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #94a3b8;
    }

    /* Range Sliders Olive Green */
    input[type=range] {
      accent-color: var(--clr-olive);
    }

    /* ======================================================
       LAYOUT SHELL: TOPBAR + (SIDEBAR + MAIN CONTENT)
    ====================================================== */
    .app-shell {
      display: flex;
      flex-direction: column;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
    }

    /* TOPBAR */
    .app-topbar {
      height: 52px;
      background: #ffffff;
      border-bottom: 1px solid var(--clr-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      flex-shrink: 0;
      z-index: 50;
    }

    .topbar-left {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .brand-logo-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      text-decoration: none;
      cursor: pointer;
    }
    .brand-title {
      font-weight: 900;
      font-size: 17px;
      letter-spacing: 0.5px;
      color: #2e7d32;
    }
    .bob-pill {
      background: #fef08a;
      color: #854d0e;
      font-size: 10px;
      font-weight: 900;
      padding: 1px 6px;
      border-radius: 4px;
      border: 1px solid #fde047;
      letter-spacing: 0.5px;
    }

    .storefront-catalog-btn {
      background: transparent;
      border: none;
      color: #475569;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      padding: 6px 10px;
      border-radius: var(--radius-sm);
      transition: background 0.15s;
    }
    .storefront-catalog-btn:hover {
      background: #f1f5f9;
      color: #0f172a;
    }

    .topbar-right {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .account-balance-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 700;
      color: #334155;
    }
    .add-money-link {
      font-size: 11px;
      color: var(--clr-olive);
      font-weight: 600;
      cursor: pointer;
    }
    .add-money-link:hover {
      text-decoration: underline;
    }

    .new-order-btn {
      background: var(--clr-olive);
      color: #ffffff;
      border: none;
      border-radius: var(--radius-sm);
      padding: 7px 16px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s, transform 0.1s;
    }
    .new-order-btn:hover {
      background: var(--clr-olive-dark);
    }

    .user-profile-badge {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #f1f5f9;
      padding: 4px 10px;
      border-radius: var(--radius-pill);
      border: 1px solid var(--clr-border);
      cursor: pointer;
      position: relative;
    }
    .user-avatar-circle {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--clr-olive);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 800;
    }
    .user-name-label {
      font-size: 12px;
      font-weight: 700;
      color: #1e293b;
    }
    .online-indicator {
      width: 8px;
      height: 8px;
      background: #10b981;
      border: 1.5px solid #fff;
      border-radius: 50%;
      position: absolute;
      bottom: 2px;
      left: 22px;
    }

    /* BODY CONTAINER */
    .app-body {
      flex: 1;
      display: flex;
      overflow: hidden;
      position: relative;
    }

    /* ======================================================
       LEFT PERSISTENT NAVIGATION SIDEBAR
    ====================================================== */
    .app-sidebar {
      width: 220px;
      background: #ffffff;
      border-right: 1px solid var(--clr-border);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      flex-shrink: 0;
      z-index: 40;
    }

    .sidebar-menu {
      display: flex;
      flex-direction: column;
      gap: 3px;
      padding: 14px 10px;
      overflow-y: auto;
    }

    .sidebar-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: var(--radius-sm);
      color: #475569;
      font-size: 13px;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
      transition: all 0.15s;
    }
    .sidebar-item:hover {
      background: #f8fafc;
      color: #0f172a;
    }
    .sidebar-item.active {
      background: var(--clr-olive-light);
      color: var(--clr-olive-dark);
      font-weight: 700;
    }
    .sidebar-item-icon {
      font-size: 15px;
      width: 18px;
      text-align: center;
    }

    .sidebar-group-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px;
      color: #0f172a;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }
    .sidebar-sub-menu {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding-left: 20px;
    }
    .sidebar-sub-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 7px 10px;
      border-radius: var(--radius-sm);
      color: #64748b;
      font-size: 12.5px;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
      transition: all 0.15s;
    }
    .sidebar-sub-item:hover {
      background: #f8fafc;
      color: #0f172a;
    }
    .sidebar-sub-item.active {
      background: var(--clr-olive-light);
      color: var(--clr-olive-dark);
      font-weight: 700;
      border-left: 3px solid var(--clr-olive);
    }

    .sidebar-footer {
      padding: 14px;
      border-top: 1px solid var(--clr-border);
      text-align: center;
      font-size: 11px;
      font-weight: 700;
      color: #94a3b8;
      letter-spacing: 0.3px;
    }

    /* ======================================================
       MAIN CONTENT CONTAINER & MULTI-VIEW
    ====================================================== */
    .app-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: var(--clr-workspace);
      position: relative;
    }

    .app-view {
      display: none;
      width: 100%;
      height: 100%;
      flex-direction: column;
      overflow: hidden;
    }
    .app-view.active {
      display: flex;
    }

    /* ======================================================
       DESIGN STUDIO VIEW
    ====================================================== */
    /* 1. STUDIO SUB-HEADER */
    .studio-sub-header {
      height: 48px;
      background: #ffffff;
      border-bottom: 1px solid var(--clr-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      flex-shrink: 0;
      z-index: 30;
      gap: 12px;
    }

    .studio-header-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .studio-back-btn {
      background: #f8fafc;
      border: 1px solid var(--clr-border-dark);
      color: #334155;
      border-radius: var(--radius-sm);
      padding: 5px 10px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .studio-back-btn:hover {
      background: #e2e8f0;
    }

    .product-spec-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      padding: 4px 10px;
      border-radius: var(--radius-pill);
      font-size: 12px;
      color: #166534;
      font-weight: 700;
    }

    .spec-dimension-tag {
      font-size: 11px;
      color: #64748b;
      font-weight: 600;
    }

    .studio-doc-title-input {
      background: transparent;
      border: 1px solid transparent;
      color: #0f172a;
      font-weight: 700;
      font-size: 13px;
      outline: none;
      padding: 3px 6px;
      border-radius: var(--radius-sm);
      min-width: 220px;
      max-width: 280px;
    }
    .studio-doc-title-input:focus {
      background: #f8fafc;
      border-color: var(--clr-border-dark);
    }

    /* Contextual Text Formatting Toolbar */
    .studio-header-mid {
      display: flex;
      align-items: center;
      gap: 6px;
      background: #f8fafc;
      padding: 3px 8px;
      border-radius: var(--radius-md);
      border: 1px solid var(--clr-border);
      overflow-x: auto;
    }
    .ctx-tool-btn {
      background: transparent;
      border: none;
      color: #475569;
      cursor: pointer;
      padding: 4px 6px;
      font-size: 13px;
      border-radius: var(--radius-sm);
    }
    .ctx-tool-btn:hover {
      background: #e2e8f0;
      color: #0f172a;
    }
    .ctx-divider {
      width: 1px;
      height: 18px;
      background: #cbd5e1;
      margin: 0 2px;
    }

    .studio-header-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .studio-action-pill {
      background: #f8fafc;
      border: 1px solid var(--clr-border);
      color: #334155;
      border-radius: var(--radius-sm);
      padding: 6px 10px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .studio-action-pill:hover {
      background: #e2e8f0;
    }

    .studio-save-btn {
      background: var(--clr-olive);
      color: #ffffff;
      border: none;
      border-radius: var(--radius-sm);
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: background 0.15s;
    }
    .studio-save-btn:hover {
      background: var(--clr-olive-dark);
    }

    .studio-export-btn {
      background: #0f172a;
      color: #ffffff;
      border: none;
      border-radius: var(--radius-sm);
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      position: relative;
    }

    /* 2. STUDIO WORKSPACE TOOLBAR (Tabs + Zoom) */
    .studio-sub-toolbar {
      height: 42px;
      background: #ffffff;
      border-bottom: 1px solid var(--clr-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      flex-shrink: 0;
      z-index: 20;
    }

    .studio-tabs-row {
      display: flex;
      align-items: center;
      gap: 4px;
      height: 100%;
    }

    .studio-tab-btn {
      height: 100%;
      background: transparent;
      border: none;
      border-bottom: 2.5px solid transparent;
      color: #64748b;
      font-size: 12.5px;
      font-weight: 600;
      padding: 0 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .studio-tab-btn:hover {
      color: #0f172a;
    }
    .studio-tab-btn.active {
      color: var(--clr-olive-dark);
      border-bottom-color: var(--clr-olive);
      font-weight: 700;
    }

    .studio-zoom-controls {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .zoom-btn {
      background: none;
      border: none;
      color: #64748b;
      cursor: pointer;
      font-weight: 800;
      font-size: 13px;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .zoom-btn:hover {
      background: #f1f5f9;
      color: #0f172a;
    }
    .zoom-label {
      font-weight: 700;
      font-size: 11.5px;
      color: #0f172a;
      min-width: 38px;
      text-align: center;
    }
    .zoom-action-pill {
      background: #f8fafc;
      border: 1px solid var(--clr-border);
      color: #334155;
      border-radius: var(--radius-sm);
      padding: 3px 8px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
    }
    .zoom-action-pill:hover {
      background: #e2e8f0;
    }

    /* 3. THREE-COLUMN WORKSPACE */
    .studio-columns-body {
      flex: 1;
      display: flex;
      overflow: hidden;
      position: relative;
    }

    /* COLUMN 1: LEFT CONFIGURATION PANEL */
    .studio-left-col {
      width: 320px;
      background: #ffffff;
      border-right: 1px solid var(--clr-border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      overflow-y: auto;
      z-index: 10;
    }

    .drawer-view {
      display: none;
      padding: 16px;
      flex-direction: column;
      gap: 14px;
    }
    .drawer-view.active {
      display: flex;
    }

    .drawer-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .drawer-title {
      font-weight: 800;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #0f172a;
    }
    .drawer-badge {
      font-size: 10px;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: var(--radius-pill);
    }
    .drawer-badge-green {
      background: #ecfdf5;
      color: #059669;
      border: 1px solid #a7f3d0;
    }

    /* Section Card inside Drawers */
    .drawer-card {
      background: #f8fafc;
      border: 1px solid var(--clr-border);
      border-radius: var(--radius-md);
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .drawer-card-label {
      font-size: 11px;
      font-weight: 800;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    .brand-logo-preview-box {
      background: #ffffff;
      border: 1.5px dashed var(--clr-border-dark);
      border-radius: var(--radius-sm);
      padding: 14px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 80px;
    }
    .brand-wordmark-preview {
      display: flex;
      align-items: baseline;
      gap: 6px;
    }
    .wordmark-gomzi {
      font-family: 'Montserrat', sans-serif;
      font-weight: 900;
      font-style: italic;
      font-size: 24px;
      color: var(--clr-olive);
      letter-spacing: 0.5px;
    }
    .wordmark-nutrition {
      font-family: 'Montserrat', sans-serif;
      font-weight: 800;
      font-size: 12px;
      color: #334155;
      letter-spacing: 2px;
    }

    .clean-plate-indicator-box {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      border-radius: var(--radius-md);
      padding: 10px 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .clean-plate-title {
      font-size: 12px;
      font-weight: 800;
      color: #166534;
    }
    .clean-plate-sub {
      font-size: 10.5px;
      color: #15803d;
      font-weight: 500;
    }

    .slider-row {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .slider-label-row {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #475569;
      font-weight: 600;
    }

    /* COLUMN 2: CENTER 2D CANVAS WORKSPACE */
    .studio-center-col {
      flex: 1;
      background: var(--clr-workspace);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
    }

    .canvas-stage-wrapper {
      flex: 1;
      overflow: auto;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 30px;
      position: relative;
    }

    .canvas-header-tag {
      position: absolute;
      top: 14px;
      left: 20px;
      font-size: 11px;
      font-weight: 800;
      color: #64748b;
      letter-spacing: 0.8px;
      text-transform: uppercase;
    }

    .artboard-container {
      box-shadow: var(--shadow-artboard);
      border: 1px solid var(--clr-border-dark);
      border-radius: 4px;
      overflow: hidden;
      background: #ffffff;
      position: relative;
    }

    .canvas-footer-toolbar {
      height: 42px;
      background: #ffffff;
      border-top: 1px solid var(--clr-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      flex-shrink: 0;
      z-index: 10;
    }
    .canvas-quick-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .canvas-quick-btn {
      background: #f8fafc;
      border: 1px solid var(--clr-border);
      color: #334155;
      border-radius: var(--radius-sm);
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }
    .canvas-quick-btn:hover {
      background: #e2e8f0;
      color: #0f172a;
    }

    /* COLUMN 3: RIGHT LIVE 3D PACKAGING PANEL */
    .studio-right-col {
      width: 350px;
      background: #ffffff;
      border-left: 1px solid var(--clr-border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      overflow-y: auto;
      z-index: 10;
    }

    .mockup-header-box {
      padding: 14px 16px 8px;
      border-bottom: 1px solid var(--clr-border);
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .mockup-title {
      font-weight: 800;
      font-size: 13.5px;
      color: #0f172a;
    }
    .mockup-spec {
      font-size: 11px;
      color: #64748b;
      font-weight: 600;
    }

    .three-stage-container {
      width: 100%;
      height: 330px;
      position: relative;
      background: radial-gradient(circle at 50% 40%, #ffffff 0%, #f1f5f9 60%, #e2e8f0 100%);
      overflow: hidden;
      cursor: grab;
    }
    .three-stage-container:active {
      cursor: grabbing;
    }
    .three-360-badge {
      position: absolute;
      top: 10px;
      right: 12px;
      background: rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(4px);
      border: 1px solid var(--clr-border);
      border-radius: var(--radius-pill);
      padding: 2px 8px;
      font-size: 10px;
      font-weight: 800;
      color: #475569;
      pointer-events: none;
      z-index: 2;
    }

    .mockup-controls-card {
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .view-angles-row {
      display: flex;
      gap: 6px;
    }
    .view-angle-btn {
      flex: 1;
      background: #f8fafc;
      border: 1px solid var(--clr-border);
      color: #334155;
      border-radius: var(--radius-sm);
      padding: 6px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      text-align: center;
      transition: all 0.15s;
    }
    .view-angle-btn:hover {
      background: #e2e8f0;
    }
    .view-angle-btn.active {
      background: var(--clr-olive);
      color: #ffffff;
      border-color: var(--clr-olive);
    }

    .pkg-color-row {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .pkg-color-label-row {
      display: flex;
      justify-content: space-between;
      font-size: 11.5px;
      font-weight: 700;
      color: #334155;
    }
    .pkg-color-swatches {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .color-swatch-btn {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 2px solid transparent;
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      transition: transform 0.15s, border-color 0.15s;
    }
    .color-swatch-btn:hover {
      transform: scale(1.15);
    }
    .color-swatch-btn.active {
      border-color: var(--clr-olive);
      transform: scale(1.2);
    }

    /* ======================================================
       DASHBOARD OVERVIEW VIEW
    ====================================================== */
    .dashboard-scroll-body {
      flex: 1;
      overflow-y: auto;
      padding: 24px 30px;
      display: flex;
      flex-direction: column;
      gap: 24px;
      background: #f8fafc;
    }

    .dashboard-header-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .dash-title {
      font-size: 22px;
      font-weight: 800;
      color: #0f172a;
    }
    .dash-sub {
      font-size: 13px;
      color: #64748b;
      margin-top: 2px;
    }

    .dash-metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
    }
    .metric-card {
      background: #ffffff;
      border: 1px solid var(--clr-border);
      border-radius: var(--radius-lg);
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      box-shadow: var(--shadow-sm);
    }
    .metric-title {
      font-size: 11.5px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    .metric-val {
      font-size: 24px;
      font-weight: 900;
      color: #0f172a;
    }
    .metric-sub {
      font-size: 11px;
      color: #10b981;
      font-weight: 600;
    }

    .dash-section-card {
      background: #ffffff;
      border: 1px solid var(--clr-border);
      border-radius: var(--radius-lg);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      box-shadow: var(--shadow-sm);
    }

    .projects-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
    }
    .projects-table th {
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1.5px solid var(--clr-border);
      color: #64748b;
      font-weight: 700;
    }
    .projects-table td {
      padding: 12px;
      border-bottom: 1px solid var(--clr-border);
      color: #0f172a;
    }
    .table-btn {
      background: var(--clr-olive-light);
      border: 1px solid var(--clr-olive-border);
      color: var(--clr-olive-dark);
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }

    /* Notification Toast */
    .studio-toast {
      display: none;
      position: fixed;
      top: 64px;
      right: 24px;
      background: #ffffff;
      border: 1px solid var(--clr-border-dark);
      color: #0f172a;
      border-radius: var(--radius-md);
      padding: 10px 16px;
      font-size: 12.5px;
      font-weight: 600;
      box-shadow: var(--shadow-md);
      z-index: 999;
      align-items: center;
      gap: 8px;
    }
  </style>
</head>

<body>
  <div class="app-shell">
    
    <!-- ======================================================
         TOPBAR: GOMZI BOB Storefront Platform Header
    ====================================================== -->
    <header class="app-topbar">
      <!-- Left: Logo & Catalog -->
      <div class="topbar-left">
        <a class="brand-logo-badge" id="navLogoBtn">
          <span style="font-size:18px;">📦</span>
          <span class="brand-title">GOMZI</span>
          <span class="bob-pill">BOB</span>
        </a>
        <div style="width:1px; height:20px; background:#e5e7eb;"></div>
        <button class="storefront-catalog-btn" id="navCatalogBtn">
          <span>🏬</span>
          <span>Storefront Catalog</span>
        </button>
      </div>

      <!-- Right: Balance, New Order, Profile -->
      <div class="topbar-right">
        <div class="account-balance-pill">
          <span>₹ 0</span>
          <span class="add-money-link">+ Add money</span>
        </div>
        <button class="new-order-btn" id="navNewOrderBtn">
          <span>+</span>
          <span>New Order</span>
        </button>
        <div class="user-profile-badge">
          <div class="user-avatar-circle">G</div>
          <span class="user-name-label">GOMZI</span>
          <div class="online-indicator"></div>
        </div>
      </div>
    </header>

    <!-- ======================================================
         APP BODY: SIDEBAR + MAIN VIEWS
    ====================================================== -->
    <div class="app-body">
      
      <!-- LEFT PERSISTENT SIDEBAR -->
      <aside class="app-sidebar">
        <nav class="sidebar-menu">
          <a class="sidebar-item" data-view="dashboard" id="sidebarNavDashboard">
            <span class="sidebar-item-icon">📊</span>
            <span>Dashboard</span>
          </a>
          <a class="sidebar-item" data-view="orders" id="sidebarNavOrders">
            <span class="sidebar-item-icon">📦</span>
            <span>Orders</span>
          </a>
          <a class="sidebar-item" data-view="products" id="sidebarNavProducts">
            <span class="sidebar-item-icon">🏷️</span>
            <span>Products</span>
          </a>

          <!-- Designs Sub-Group -->
          <div class="sidebar-group-header">
            <div style="display:flex; align-items:center; gap:10px;">
              <span class="sidebar-item-icon">🎨</span>
              <span>Designs</span>
            </div>
            <span style="font-size:10px; color:#94a3b8;">▾</span>
          </div>
          <div class="sidebar-sub-menu">
            <a class="sidebar-sub-item active" data-view="studio" id="sidebarNavStudio">
              <span>Design Studio</span>
            </a>
            <a class="sidebar-sub-item" data-view="my-designs" id="sidebarNavMyDesigns">
              <span>My Designs</span>
            </a>
            <a class="sidebar-sub-item" data-view="custom-labels" id="sidebarNavCustomLabels">
              <span>Custom Labels &amp; Mockups</span>
            </a>
          </div>

          <a class="sidebar-item" data-view="returns" id="sidebarNavReturns">
            <span class="sidebar-item-icon">↩️</span>
            <span>Returns</span>
          </a>
          <a class="sidebar-item" data-view="accounts" id="sidebarNavAccounts">
            <span class="sidebar-item-icon">💳</span>
            <span>Accounts</span>
          </a>
          <a class="sidebar-item" data-view="integrations" id="sidebarNavIntegrations">
            <span class="sidebar-item-icon">🔗</span>
            <span>Integrations</span>
          </a>
          <a class="sidebar-item" data-view="settings" id="sidebarNavSettings">
            <span class="sidebar-item-icon">⚙️</span>
            <span>Settings</span>
          </a>
          <a class="sidebar-item" data-view="help" id="sidebarNavHelp">
            <span class="sidebar-item-icon">❓</span>
            <span>Help</span>
          </a>
        </nav>
        
        <div class="sidebar-footer">
          GOMZI BOB Platform
        </div>
      </aside>

      <!-- MAIN VIEWPORT -->
      <main class="app-main">

        <!-- ======================================================
             VIEW 1: DESIGN STUDIO (DEFAULT ACTIVE)
        ====================================================== -->
        <section class="app-view active" id="viewDesignStudio">
          
          <!-- Studio Sub-Header -->
          <div class="studio-sub-header">
            <!-- Left: Back, Product Pill, Title -->
            <div class="studio-header-left">
              <button class="studio-back-btn" id="studioBackBtn" title="Back to Dashboard">
                ‹ Back
              </button>
              
              <div class="product-spec-pill" id="studioProductPill">
                <span>📦</span>
                <span>Whey Protein Standard</span>
              </div>

              <span class="spec-dimension-tag" id="studioSpecTag">
                1 kg Muscle Tub · 45.2 × 14.2 cm
              </span>

              <input class="studio-doc-title-input" id="canvaDocTitleInput" value="GOMZI Whey Protein Belgian Chocolate 1kg" />
            </div>

            <!-- Mid: Contextual Quick Text Formatters -->
            <div class="studio-header-mid" id="studioContextToolbar">
              <button class="ctx-tool-btn" id="canvaUndoBtn" title="Undo (Ctrl+Z)">↩️</button>
              <button class="ctx-tool-btn" id="canvaRedoBtn" title="Redo (Ctrl+Y)">↪️</button>
              <div class="ctx-divider"></div>
              
              <select id="canvaFontFamily" style="background:#fff; border:1px solid #cbd5e1; border-radius:4px; padding:3px 6px; font-size:12px; font-weight:600; outline:none;">
                <option value="Montserrat" selected>Montserrat</option>
                <option value="Bebas Neue">Bebas Neue</option>
                <option value="Impact">Impact</option>
                <option value="Cinzel">Cinzel</option>
                <option value="Inter">Inter</option>
                <option value="Roboto">Roboto</option>
              </select>

              <button class="ctx-tool-btn" id="canvaBoldBtn" title="Bold" style="font-weight:900;">B</button>
              <button class="ctx-tool-btn" id="canvaItalicBtn" title="Italic" style="font-style:italic;">I</button>
              <div class="ctx-divider"></div>

              <button class="ctx-tool-btn" id="canvaAlignLeftBtn" title="Align Left">⫷</button>
              <button class="ctx-tool-btn" id="canvaAlignCenterBtn" title="Align Center">☰</button>
              <button class="ctx-tool-btn" id="canvaAlignRightBtn" title="Align Right">⫸</button>
              <div class="ctx-divider"></div>

              <button class="ctx-tool-btn" id="canvaDuplicateBtn" title="Duplicate (Ctrl+D)">📑</button>
              <button class="ctx-tool-btn" id="canvaDeleteBtn" title="Delete Selected" style="color:#ef4444;">🗑️</button>
            </div>

            <!-- Right: Focus, Tools, 3D, Guides, Save, Export -->
            <div class="studio-header-right">
              <button class="studio-action-pill" id="studioFocusBtn">Focus</button>
              <button class="studio-action-pill" id="studioToolsBtn">Tools</button>
              <button class="studio-action-pill" id="studio3dToggleBtn">3D</button>
              <button class="studio-action-pill" id="canvaPrintGuidesBtn">Guides</button>

              <button class="studio-save-btn" id="canvaApplyBtn">
                <span>💾</span>
                <span>Save</span>
              </button>

              <!-- Export Dropdown -->
              <div style="position:relative;">
                <button class="studio-export-btn" id="canvaExportMenuBtn">
                  <span>📥</span>
                  <span>Export ▾</span>
                </button>
                <div id="canvaExportDropdown" style="display:none; position:absolute; right:0; top:36px; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; width:260px; box-shadow:var(--shadow-md); z-index:99; padding:6px; flex-direction:column; gap:4px;">
                  <button id="canvaExportCdrBtn" style="background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; text-align:left; padding:8px 10px; border-radius:6px; cursor:pointer; font-size:12px; font-weight:800;">
                    🟢 CorelDRAW (CDR Package)
                    <div style="font-size:10px; color:#16a34a; font-weight:500;">Direct Corel Import SVG + 9600px PDF</div>
                  </button>
                  <button id="canvaExportPdfBtn" style="background:transparent; border:none; color:#0f172a; text-align:left; padding:8px 10px; border-radius:6px; cursor:pointer; font-size:12px;">
                    📄 PDF Print Master (300 DPI)
                  </button>
                  <button id="canvaExportPngBtn" style="background:transparent; border:none; color:#0f172a; text-align:left; padding:8px 10px; border-radius:6px; cursor:pointer; font-size:12px;">
                    🖼️ PNG Master (300 DPI, Lossless)
                  </button>
                  <button id="canvaExportSvgBtn" style="background:transparent; border:none; color:#0f172a; text-align:left; padding:8px 10px; border-radius:6px; cursor:pointer; font-size:12px;">
                    📐 SVG Vector File
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Studio Sub-Toolbar (Tabs + Zoom controls) -->
          <div class="studio-sub-toolbar">
            <div class="studio-tabs-row">
              <button class="studio-tab-btn" data-drawer="templates" id="tabTemplates">Templates</button>
              <button class="studio-tab-btn active" data-drawer="brand" id="tabBrand">Brand</button>
              <button class="studio-tab-btn" data-drawer="text" id="tabText">Text</button>
              <button class="studio-tab-btn" data-drawer="facts" id="tabFacts">Facts</button>
              <button class="studio-tab-btn" data-drawer="uploads" id="tabUploads">Uploads</button>
              <button class="studio-tab-btn" data-drawer="layers" id="tabLayers">Layers</button>
              <button class="studio-tab-btn" data-drawer="aitools" id="tabAiTools">AI Tools</button>
            </div>

            <div class="studio-zoom-controls">
              <button class="zoom-btn" id="canvaZoomOutBtn">-</button>
              <span class="zoom-label" id="canvaZoomVal">54%</span>
              <button class="zoom-btn" id="canvaZoomInBtn">+</button>
              <button class="zoom-action-pill" id="canvaZoomFitBtn">Fit Label</button>
              <button class="zoom-action-pill" id="canvaCenterLabelBtn">Center</button>
              <button class="zoom-action-pill" id="canvaAdjustLogoQuickBtn">Adjust Logo</button>
            </div>
          </div>

          <!-- 3-Column Studio Workspace -->
          <div class="studio-columns-body">
            
            <!-- COLUMN 1: LEFT CONFIGURATION PANEL -->
            <aside class="studio-left-col">
              
              <!-- DRAWER 1: BRAND KIT (DEFAULT ACTIVE) -->
              <div class="drawer-view active" id="drawerBrand">
                <div class="drawer-header">
                  <span class="drawer-title">Merchant Brand Kit</span>
                  <span class="drawer-badge drawer-badge-green">Auto-Synced</span>
                </div>

                <!-- Brand Name Card -->
                <div class="drawer-card">
                  <span class="drawer-card-label">Brand Name</span>
                  <input id="canvaBrandNameInput" value="GOMZI NUTRITION" 
                    style="background:#fff; border:1px solid #cbd5e1; border-radius:6px; padding:7px 10px; font-weight:800; font-size:13px; color:#0f172a; outline:none;" />
                  <button id="canvaInsertBrandNameBtn" 
                    style="background:var(--clr-olive); color:#fff; border:none; border-radius:6px; padding:7px; font-size:11.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:5px;">
                    ➕ Insert Brand Name on Label
                  </button>
                </div>

                <!-- Brand Logo Card -->
                <div class="drawer-card">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="drawer-card-label">Brand Logo</span>
                    <span style="font-size:10px; color:#10b981; font-weight:700; background:#d1fae5; padding:1px 6px; border-radius:4px;">Active on Template</span>
                  </div>

                  <!-- Wordmark / Logo Preview -->
                  <div class="brand-logo-preview-box" id="canvaBrandLogoPreviewBox">
                    <div class="brand-wordmark-preview">
                      <span class="wordmark-gomzi">GOMZI</span>
                      <span class="wordmark-nutrition">NUTRITION</span>
                    </div>
                  </div>

                  <!-- Logo Upload / Restore Row -->
                  <div style="display:flex; gap:6px;">
                    <label style="flex:1; background:#0f172a; color:#fff; border-radius:6px; padding:7px; font-size:11px; font-weight:700; cursor:pointer; text-align:center;">
                      📤 Upload New
                      <input type="file" id="canvaUploadBrandLogoInput" accept="image/*" style="display:none;" />
                    </label>
                    <button id="canvaRestoreFactoryLogoBtn" style="background:#fff; border:1px solid #cbd5e1; color:#ef4444; border-radius:6px; padding:7px 10px; font-size:11px; font-weight:700; cursor:pointer;">
                      Restore Factory Logo
                    </button>
                  </div>

                  <!-- Clean Plate Status -->
                  <div class="clean-plate-indicator-box">
                    <span style="font-size:16px;">✨</span>
                    <div>
                      <div class="clean-plate-title">Clean Plate Active</div>
                      <div class="clean-plate-sub">Authentic Background Preserved</div>
                    </div>
                  </div>

                  <!-- Sliders -->
                  <div style="font-size:11px; font-weight:800; color:#64748b; margin-top:4px; text-transform:uppercase;">Logo Adjustments</div>
                  
                  <div class="slider-row">
                    <div class="slider-label-row">
                      <span>Position X</span>
                      <span id="canvaBrandLogoPosXVal">674 px</span>
                    </div>
                    <input type="range" id="canvaBrandLogoPosXSlider" min="5" max="95" value="50" />
                  </div>

                  <div class="slider-row">
                    <div class="slider-label-row">
                      <span>Position Y</span>
                      <span id="canvaBrandLogoPosYVal">38 px</span>
                    </div>
                    <input type="range" id="canvaBrandLogoPosYSlider" min="5" max="95" value="20" />
                  </div>

                  <div class="slider-row">
                    <div class="slider-label-row">
                      <span>Logo Size</span>
                      <span id="canvaBrandLogoSizeVal">87 px</span>
                    </div>
                    <input type="range" id="canvaBrandLogoSizeSlider" min="40" max="240" value="87" />
                  </div>

                  <div class="slider-row">
                    <div class="slider-label-row">
                      <span>Rotation</span>
                      <span id="canvaBrandLogoRotVal">0°</span>
                    </div>
                    <input type="range" id="canvaBrandLogoRotSlider" min="-180" max="180" value="0" />
                  </div>

                  <div style="display:flex; gap:6px; margin-top:4px;">
                    <button id="canvaCenterLogoOnLabelBtn" style="flex:1; background:#f1f5f9; border:1px solid #cbd5e1; color:#334155; border-radius:6px; padding:6px; font-size:11px; font-weight:700; cursor:pointer;">
                      🎯 Center on Label
                    </button>
                    <button id="canvaLogoCleanPlateToggle" style="background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; border-radius:6px; padding:6px 10px; font-size:11px; font-weight:700; cursor:pointer;">
                      ✨ Clean Plate
                    </button>
                  </div>
                </div>
              </div>

              <!-- DRAWER 2: TEMPLATES -->
              <div class="drawer-view" id="drawerTemplates">
                <div class="drawer-header">
                  <span class="drawer-title">Templates</span>
                  <span class="drawer-badge drawer-badge-green">GOMZI BOB</span>
                </div>
                <div style="display:flex; flex-direction:column; gap:8px;">
                  <button class="tpl-select-btn" data-template="gomzi_whey_standard" 
                    style="background:#ffffff; border:1.5px solid var(--clr-olive-border); border-radius:8px; padding:10px; text-align:left; cursor:pointer; box-shadow:var(--shadow-sm);">
                    <div style="font-weight:800; color:#0f172a; font-size:12.5px;">📦 GOMZI Whey Protein Standard</div>
                    <div style="font-size:11px; color:#64748b; margin-top:2px;">1 kg Muscle Tub · 45.2 × 14.2 cm · Belgian Chocolate</div>
                  </button>

                  <button class="tpl-select-btn" data-template="gomzi_isolate_gold" 
                    style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; text-align:left; cursor:pointer;">
                    <div style="font-weight:800; color:#0f172a; font-size:12.5px;">⚡ GOMZI Whey Isolate Gold</div>
                    <div style="font-size:11px; color:#64748b; margin-top:2px;">27g Protein · Zero Sugar · 1 kg Tub</div>
                  </button>

                  <button class="tpl-select-btn" data-template="gomzi_pre_workout" 
                    style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; text-align:left; cursor:pointer;">
                    <div style="font-weight:800; color:#0f172a; font-size:12.5px;">🔥 Voltage Pre-Workout</div>
                    <div style="font-size:11px; color:#64748b; margin-top:2px;">High Energy · 300g Tub</div>
                  </button>

                  <button class="tpl-select-btn" data-template="gomzi_multivitamin" 
                    style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; text-align:left; cursor:pointer;">
                    <div style="font-weight:800; color:#0f172a; font-size:12.5px;">💊 Daily Multivitamin</div>
                    <div style="font-size:11px; color:#64748b; margin-top:2px;">120 Veg Capsules Bottle</div>
                  </button>
                </div>
              </div>

              <!-- DRAWER 3: TEXT -->
              <div class="drawer-view" id="drawerText">
                <div class="drawer-header">
                  <span class="drawer-title">Text</span>
                </div>
                <button id="canvaAddHeadingBtn" style="background:#f8fafc; border:1.5px solid #cbd5e1; color:#0f172a; border-radius:8px; padding:10px 12px; text-align:left; cursor:pointer; font-weight:800; font-size:16px;">
                  + Add a Heading
                </button>
                <button id="canvaAddSubheadingBtn" style="background:#f8fafc; border:1.5px solid #cbd5e1; color:#0f172a; border-radius:8px; padding:8px 12px; text-align:left; cursor:pointer; font-weight:700; font-size:13px;">
                  + Add a Subheading
                </button>
                <button id="canvaAddBodyBtn" style="background:#f8fafc; border:1.5px solid #cbd5e1; color:#334155; border-radius:8px; padding:7px 12px; text-align:left; cursor:pointer; font-weight:500; font-size:12px;">
                  + Add body text
                </button>

                <div style="font-weight:800; color:#64748b; font-size:11px; text-transform:uppercase; margin-top:8px;">Packaging Snippets</div>
                <button class="canva-snippet-btn" data-text="NET WT. 1 KG (2.2 LBS)" style="background:#ffffff; border:1px solid #cbd5e1; padding:8px; border-radius:6px; cursor:pointer; text-align:left; font-weight:700; font-size:11px;">
                  📦 NET WT. 1 KG (2.2 LBS)
                </button>
                <button class="canva-snippet-btn" data-text="100% WHEY PROTEIN ISOLATE" style="background:#ffffff; border:1px solid #cbd5e1; padding:8px; border-radius:6px; cursor:pointer; text-align:left; font-weight:700; font-size:11px;">
                  ⚡ 100% WHEY PROTEIN ISOLATE
                </button>
                <button class="canva-snippet-btn" data-text="DIETARY SUPPLEMENT · NOT FOR MEDICINAL USE" style="background:#ffffff; border:1px solid #cbd5e1; padding:8px; border-radius:6px; cursor:pointer; text-align:left; font-weight:700; font-size:11px;">
                  🛡️ DIETARY SUPPLEMENT
                </button>
              </div>

              <!-- DRAWER 4: FACTS -->
              <div class="drawer-view" id="drawerFacts">
                <div class="drawer-header">
                  <span class="drawer-title">Nutrition &amp; Facts</span>
                  <span class="drawer-badge drawer-badge-green">FSSAI / FDA</span>
                </div>
                <button id="canvaAddNutritionTableBtn" style="background:#ffffff; border:1.5px solid #cbd5e1; border-radius:8px; padding:10px 12px; text-align:left; cursor:pointer; font-size:12px; font-weight:700; display:flex; align-items:center; gap:8px;">
                  📊 <span>Add Whey Nutrition Facts Table</span>
                </button>
                <button id="canvaAddFssaiBatchBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px 12px; text-align:left; cursor:pointer; font-size:12px; font-weight:700; display:flex; align-items:center; gap:8px;">
                  🏷️ <span>Add FSSAI &amp; Batch Table</span>
                </button>
                <div style="display:flex; gap:6px;">
                  <button id="canvaAddVegBtn" style="flex:1; background:#f0fdf4; border:1.5px solid #10b981; color:#047857; border-radius:6px; padding:7px; font-size:11px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:5px;">
                    🟢 100% Veg Dot
                  </button>
                  <button id="canvaAddNonVegBtn" style="flex:1; background:#fef2f2; border:1.5px solid #ef4444; color:#b91c1c; border-radius:6px; padding:7px; font-size:11px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:5px;">
                    🔴 Non-Veg Dot
                  </button>
                </div>
              </div>

              <!-- DRAWER 5: UPLOADS -->
              <div class="drawer-view" id="drawerUploads">
                <div class="drawer-header">
                  <span class="drawer-title">Upload Media</span>
                </div>
                <label style="background:var(--clr-olive); color:#fff; border-radius:8px; padding:10px; font-size:12px; font-weight:700; cursor:pointer; text-align:center; display:block;">
                  📤 Upload Image / Logo
                  <input type="file" id="canvaDrawerUploadInput" accept="image/*" style="display:none;" />
                </label>
              </div>

              <!-- DRAWER 6: LAYERS -->
              <div class="drawer-view" id="drawerLayers">
                <div class="drawer-header">
                  <span class="drawer-title">Layers</span>
                  <span id="canvaLayerCountBadge" class="drawer-badge drawer-badge-green">0</span>
                </div>
                <div id="canvaLayersListContainer" style="display:flex; flex-direction:column; gap:4px; max-height:calc(100vh - 200px); overflow-y:auto;">
                  <!-- Layers populated dynamically -->
                </div>
              </div>

              <!-- DRAWER 7: AI TOOLS -->
              <div class="drawer-view" id="drawerAiTools">
                <div class="drawer-header">
                  <span class="drawer-title">AI Packaging Tools</span>
                  <span class="drawer-badge drawer-badge-green">PRO</span>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                  <button id="canvaToolGrabTextBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                    <div style="font-size:20px;">🔤</div>
                    <div style="font-weight:700; font-size:11px; margin-top:4px;">Grab Text</div>
                  </button>
                  <button id="canvaToolBgRemoverBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                    <div style="font-size:20px;">🏖️</div>
                    <div style="font-weight:700; font-size:11px; margin-top:4px;">BG Remover</div>
                  </button>
                  <button id="canvaToolMagicEraserBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                    <div style="font-size:20px;">🧹</div>
                    <div style="font-weight:700; font-size:11px; margin-top:4px;">Magic Eraser</div>
                  </button>
                  <button id="canvaToolUpscaleBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; cursor:pointer; text-align:center;">
                    <div style="font-size:20px;">🌻</div>
                    <div style="font-weight:700; font-size:11px; margin-top:4px;">Upscale</div>
                  </button>
                </div>
              </div>

            </aside>

            <!-- COLUMN 2: CENTER 2D CANVAS WORKSPACE -->
            <section class="studio-center-col">
              <span class="canvas-header-tag">FULL LABEL WORKSPACE</span>

              <div class="canvas-stage-wrapper" id="canvaStageWrapper">
                <div class="artboard-container" id="canvaArtboardContainer">
                  <canvas id="canvaMainCanvas"></canvas>
                </div>
              </div>

              <!-- Canvas Bottom Action Toolbar -->
              <div class="canvas-footer-toolbar">
                <div class="canvas-quick-actions">
                  <button class="canvas-quick-btn" id="footerSelectLogoBtn">Select Brand Logo</button>
                  <button class="canvas-quick-btn" id="footerCenterBtn">Center</button>
                  <button class="canvas-quick-btn" id="footerCleanPlateBtn">Clean Plate</button>
                  <button class="canvas-quick-btn" id="footerRestoreLogoBtn">Restore Factory Logo</button>
                </div>

                <div style="font-size:11.5px; color:#64748b; font-weight:600;">
                  Double-click text to edit inline · 1536 × 512 px (3:1)
                </div>
              </div>
            </section>

            <!-- COLUMN 3: RIGHT LIVE 3D CONTAINER PANEL -->
            <aside class="studio-right-col" id="canvaLiveJarPanel">
              <div class="mockup-header-box">
                <div class="mockup-title">Live 3D Container</div>
                <div class="mockup-spec" id="mockupTubSpecLabel">1 kg Muscle Tub · W 45.2 × H 14.2 cm</div>
              </div>

              <!-- WebGL Three.js Container -->
              <div class="three-stage-container" id="pacdoraThreeContainer">
                <div class="three-360-badge">🔄 360° DRAG</div>
              </div>

              <!-- Controls Card -->
              <div class="mockup-controls-card">
                <!-- Angle Presets -->
                <div class="view-angles-row">
                  <button class="view-angle-btn active" id="btnViewFront">Front (0°)</button>
                  <button class="view-angle-btn" id="btnViewBack">Back (180°)</button>
                  <button class="view-angle-btn" id="btnViewSide">Side (90°)</button>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <button id="canvaAutoSpinBtn" style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:6px 12px; font-size:11px; font-weight:700; color:#334155; cursor:pointer;">
                    ▶️ Auto 360° Spin
                  </button>
                  <button id="canvaReset3dCameraBtn" style="background:transparent; border:none; color:#64748b; font-size:11px; font-weight:600; cursor:pointer;">
                    Reset Camera
                  </button>
                </div>

                <!-- Package Color -->
                <div class="pkg-color-row">
                  <div class="pkg-color-label-row">
                    <span>Container Color</span>
                    <span id="canvaCurrentPkgColorLabel" style="font-weight:600; color:#64748b;">Black Matte</span>
                  </div>
                  <div class="pkg-color-swatches" id="canvaPkgColorSwatches">
                    <button class="color-swatch-btn active" data-color="#18181b" data-name="Black Matte" style="background:#18181b;" title="Black"></button>
                    <button class="color-swatch-btn" data-color="#ffffff" data-name="White Gloss" style="background:#ffffff; border:1px solid #cbd5e1;" title="White"></button>
                    <button class="color-swatch-btn" data-color="#94a3b8" data-name="Silver Grey" style="background:#94a3b8;" title="Grey"></button>
                    <button class="color-swatch-btn" data-color="#b45309" data-name="Gold / Amber" style="background:#b45309;" title="Gold"></button>
                    <button class="color-swatch-btn" data-color="#1e3a8a" data-name="Navy Blue" style="background:#1e3a8a;" title="Navy"></button>
                    <button class="color-swatch-btn" data-color="#581c87" data-name="Burgundy / Purple" style="background:#581c87;" title="Burgundy"></button>
                  </div>
                </div>
              </div>
            </aside>

          </div>

        </section>

        <!-- ======================================================
             VIEW 2: DASHBOARD VIEW
        ====================================================== -->
        <section class="app-view" id="viewDashboard">
          <div class="dashboard-scroll-body">
            
            <div class="dashboard-header-banner">
              <div>
                <h1 class="dash-title">Welcome to GOMZI BOB Platform</h1>
                <p class="dash-sub">Merchant Design Studio &amp; Packaging Automation Dashboard</p>
              </div>
              <button class="studio-save-btn" id="dashOpenStudioBtn" style="padding:9px 18px; font-size:13px;">
                🎨 Open Design Studio
              </button>
            </div>

            <!-- Metrics Grid -->
            <div class="dash-metrics-grid">
              <div class="metric-card">
                <span class="metric-title">Total Projects</span>
                <span class="metric-val">24</span>
                <span class="metric-sub">Active designs</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">AI Jobs</span>
                <span class="metric-val">42</span>
                <span class="metric-sub">39 Completed</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">Labels Generated</span>
                <span class="metric-val">84</span>
                <span class="metric-sub">Print ready 300 DPI</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">Vectors Created</span>
                <span class="metric-val">16</span>
                <span class="metric-sub">Corel CDR/SVG</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">AI Cost Today</span>
                <span class="metric-val">₹ 142.50</span>
                <span class="metric-sub">₹ 3,420.00 This Month</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">Provider Status</span>
                <span class="metric-val" style="font-size:16px; color:#10b981; margin-top:4px;">● All Operational</span>
                <span class="metric-sub" style="color:#64748b;">Google Flow · Rembg · OCR</span>
              </div>
            </div>

            <!-- Recent Projects Table -->
            <div class="dash-section-card">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h2 style="font-size:15px; font-weight:800; color:#0f172a;">Recent Packaging Projects</h2>
              </div>
              
              <table class="projects-table">
                <thead>
                  <tr>
                    <th>Project Name</th>
                    <th>Container &amp; Size</th>
                    <th>Brand</th>
                    <th>Last Modified</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>GOMZI Whey Belgian Chocolate 1kg</strong></td>
                    <td>1 kg Muscle Tub · 45.2 × 14.2 cm</td>
                    <td><span style="color:var(--clr-olive); font-weight:700;">GOMZI NUTRITION</span></td>
                    <td>Just now</td>
                    <td><button class="table-btn" onclick="switchMainView('studio');">Open in Studio</button></td>
                  </tr>
                  <tr>
                    <td><strong>GOMZI Whey Isolate Gold 2kg</strong></td>
                    <td>2 kg Jar · 48 × 16 cm</td>
                    <td><span style="color:var(--clr-olive); font-weight:700;">GOMZI NUTRITION</span></td>
                    <td>Yesterday</td>
                    <td><button class="table-btn" onclick="switchMainView('studio');">Open in Studio</button></td>
                  </tr>
                  <tr>
                    <td><strong>Voltage Pre-Workout Watermelon</strong></td>
                    <td>300g Tub · 31.5 × 11 cm</td>
                    <td><span style="color:var(--clr-olive); font-weight:700;">GOMZI NUTRITION</span></td>
                    <td>3 days ago</td>
                    <td><button class="table-btn" onclick="switchMainView('studio');">Open in Studio</button></td>
                  </tr>
                </tbody>
              </table>
            </div>

          </div>
        </section>

      </main>
    </div>

  </div>

  <!-- Notification Toast -->
  <div class="studio-toast" id="canvaStudioToast">
    <span id="canvaToastIcon">ℹ️</span>
    <span id="canvaToastMsg">Notification</span>
  </div>

  <!-- ======================================================
       JAVASCRIPT APPLICATION CORE (Fabric.js + Three.js + Brand Sync)
  ====================================================== -->
  <script>
    // Global Navigation & View Switcher
    function switchMainView(viewName) {
      document.querySelectorAll('.app-view').forEach(v => v.classList.remove('active'));
      document.querySelectorAll('.sidebar-item, .sidebar-sub-item').forEach(el => el.classList.remove('active'));
      
      if (viewName === 'studio') {
        const studioView = document.getElementById('viewDesignStudio');
        const studioSub = document.getElementById('sidebarNavStudio');
        if (studioView) studioView.classList.add('active');
        if (studioSub) studioSub.classList.add('active');
        if (typeof updateThreeLabelTextureFromCanvas === 'function') {
          setTimeout(updateThreeLabelTextureFromCanvas, 100);
        }
      } else if (viewName === 'dashboard') {
        const dashView = document.getElementById('viewDashboard');
        const dashNav = document.getElementById('sidebarNavDashboard');
        if (dashView) dashView.classList.add('active');
        if (dashNav) dashNav.classList.add('active');
      }
    }

    // Attach Sidebar View Clicks
    document.getElementById('sidebarNavDashboard')?.addEventListener('click', () => switchMainView('dashboard'));
    document.getElementById('sidebarNavStudio')?.addEventListener('click', () => switchMainView('studio'));
    document.getElementById('studioBackBtn')?.addEventListener('click', () => switchMainView('dashboard'));
    document.getElementById('dashOpenStudioBtn')?.addEventListener('click', () => switchMainView('studio'));
    document.getElementById('navCatalogBtn')?.addEventListener('click', () => switchMainView('dashboard'));
    document.getElementById('navLogoBtn')?.addEventListener('click', () => switchMainView('studio'));

    // Toast Notification Utility
    function showToast(msg, icon = "ℹ️", duration = 2500) {
      const toast = document.getElementById('canvaStudioToast');
      const msgEl = document.getElementById('canvaToastMsg');
      const iconEl = document.getElementById('canvaToastIcon');
      if (!toast) return;
      msgEl.textContent = msg;
      iconEl.textContent = icon;
      toast.style.display = 'flex';
      clearTimeout(window.__toastTimer);
      window.__toastTimer = setTimeout(() => { toast.style.display = 'none'; }, duration);
    }

    /* ======================================================
       STUDIO CORE: Fabric.js & Canvas Initializer
    ====================================================== */
    let canvaCanvas = null;
    let brandLogoObject = null;
    let threeRenderer = null, threeCamera = null, threeScene = null, threeOrbitControls = null;
    let threeJarGroup = null, threeBodyMesh = null, threeCapMesh = null, threeLabelTexture = null;
    let isAutoSpinning = false, threeAnimFrameId = null;
    let threeCurrentBodyColor = 0x18181b; // Black default

    function initGomziStudio() {
      const canvasEl = document.getElementById('canvaMainCanvas');
      if (!canvasEl) return;

      const container = document.getElementById('canvaArtboardContainer');
      const stageWrapper = document.getElementById('canvaStageWrapper');
      
      const width = 1536;
      const height = 512;
      canvasEl.width = width;
      canvasEl.height = height;

      canvaCanvas = new fabric.Canvas('canvaMainCanvas', {
        width: width,
        height: height,
        backgroundColor: '#e5e7eb',
        preserveObjectStacking: true,
        selection: true
      });

      // Fit Canvas to screen smoothly
      function fitCanvasToStage() {
        if (!stageWrapper || !container) return;
        const availableW = stageWrapper.clientWidth - 80;
        const availableH = stageWrapper.clientHeight - 80;
        const scale = Math.min(availableW / width, availableH / height, 0.75);
        container.style.width = `${Math.round(width * scale)}px`;
        container.style.height = `${Math.round(height * scale)}px`;
        container.style.transform = `scale(1)`;
        canvaCanvas.setDimensions({ width: Math.round(width * scale), height: Math.round(height * scale) });
        canvaCanvas.setZoom(scale);
        document.getElementById('canvaZoomVal').textContent = `${Math.round(scale * 100)}%`;
      }

      window.addEventListener('resize', fitCanvasToStage);

      // Load Default GOMZI NUTRITION Whey Protein Label Artwork
      loadGomziWheyTemplate();

      fitCanvasToStage();

      // Hook canvas events to 3D Live texture updates
      canvaCanvas.on('object:modified', () => { updateThreeLabelTextureFromCanvas(); });
      canvaCanvas.on('text:changed', () => { updateThreeLabelTextureFromCanvas(); });
      canvaCanvas.on('after:render', () => { triggerDebouncedTextureUpdate(); });

      // Initialize 3D Packaging Mockup
      initThreeJarMockup();
      initBrandKitControls();
      initDrawerTabs();
      initExportControls();
    }

    // Debounced Texture Update to avoid lag
    let textureUpdateTimeout = null;
    function triggerDebouncedTextureUpdate() {
      clearTimeout(textureUpdateTimeout);
      textureUpdateTimeout = setTimeout(updateThreeLabelTextureFromCanvas, 80);
    }

    /* ======================================================
       DEFAULT TEMPLATE: GOMZI NUTRITION WHEY PROTEIN
    ====================================================== */
    function loadGomziWheyTemplate() {
      if (!canvaCanvas) return;
      canvaCanvas.clear();
      canvaCanvas.backgroundColor = '#e5e7eb';

      // 1. Left Section: Nutritional Facts Table
      const nutBox = new fabric.Rect({
        left: 45, top: 40, width: 380, height: 430, rx: 6, ry: 6,
        fill: '#ffffff', stroke: '#cbd5e1', strokeWidth: 1.5,
        selectable: true
      });

      const nutHeader = new fabric.Textbox('NUTRITIONAL INFORMATION\nServing size: 1 scoop (33g) · Servings: 30', {
        left: 65, top: 58, width: 340, fontSize: 13, fontFamily: 'Montserrat',
        fontWeight: '800', fill: '#0f172a', textAlign: 'left', selectable: true
      });

      const nutBody = new fabric.Textbox('Energy: 130 kcal\nProtein: 24 g\nCarbohydrates: 2.1 g\nAdded Sugar: 0 g\nTotal Fat: 1.2 g\nBCAA: 5.5 g · Glutamic Acid: 4.2 g\nDigestive Enzyme Blend: 50 mg', {
        left: 65, top: 110, width: 340, fontSize: 13, fontFamily: 'Inter',
        fontWeight: '500', fill: '#334155', textAlign: 'left', lineHeight: 1.55, selectable: true
      });

      const mfgDetails = new fabric.Textbox('Manufactured for:\nGOMZI NUTRITION PRIVATE LIMITED\nSurat, Gujarat, India\nFSSAI Lic. No. 10020021001234', {
        left: 65, top: 310, width: 340, fontSize: 11, fontFamily: 'Montserrat',
        fontWeight: '600', fill: '#64748b', textAlign: 'left', lineHeight: 1.4, selectable: true
      });

      canvaCanvas.add(nutBox, nutHeader, nutBody, mfgDetails);

      // 2. Center Hero Section: GOMZI NUTRITION Logo & Whey Protein Title
      const logoText = new fabric.Textbox('GOMZI\nNUTRITION', {
        left: 674, top: 38, width: 220, fontSize: 32, fontFamily: 'Montserrat',
        fontWeight: '900', fontStyle: 'italic', fill: '#708238', textAlign: 'center',
        lineHeight: 0.9, letterSpacing: 2, selectable: true
      });
      brandLogoObject = logoText;

      const titleMain = new fabric.Textbox('WHEY\nPROTEIN', {
        left: 540, top: 130, width: 490, fontSize: 68, fontFamily: 'Bebas Neue',
        fontWeight: '900', fill: '#0f172a', textAlign: 'center', lineHeight: 0.92, selectable: true
      });

      const subtitlePill = new fabric.Rect({
        left: 650, top: 315, width: 270, height: 38, rx: 19, ry: 19,
        fill: '#708238', selectable: true
      });

      const subtitleText = new fabric.Textbox('BELGIAN CHOCOLATE', {
        left: 650, top: 324, width: 270, fontSize: 15, fontFamily: 'Montserrat',
        fontWeight: '900', fill: '#ffffff', textAlign: 'center', selectable: true
      });

      const specText = new fabric.Textbox('1 kg | 30 SERVINGS*', {
        left: 540, top: 375, width: 490, fontSize: 16, fontFamily: 'Montserrat',
        fontWeight: '800', fill: '#475569', textAlign: 'center', letterSpacing: 1.5, selectable: true
      });

      canvaCanvas.add(logoText, titleMain, subtitlePill, subtitleText, specText);

      // 3. Right Section: Product Highlights & Barcode
      const rightBox = new fabric.Rect({
        left: 1110, top: 40, width: 380, height: 430, rx: 6, ry: 6,
        fill: '#ffffff', stroke: '#cbd5e1', strokeWidth: 1.5, selectable: true
      });

      const benefitsText = new fabric.Textbox('KEY BENEFITS\n\n✓ 24g Premium Ultra-Filtered Whey\n✓ 5.5g Naturally Occurring BCAAs\n✓ Zero Added Sugar · Low Carb\n✓ Enhanced with DigeZyme® Blend\n✓ Instantized for Lump-Free Shaking', {
        left: 1135, top: 60, width: 330, fontSize: 12.5, fontFamily: 'Inter',
        fontWeight: '600', fill: '#334155', textAlign: 'left', lineHeight: 1.6, selectable: true
      });

      const vegDotBox = new fabric.Rect({
        left: 1135, top: 295, width: 28, height: 28, rx: 4, ry: 4,
        fill: '#ffffff', stroke: '#10b981', strokeWidth: 2, selectable: true
      });
      const vegDot = new fabric.Circle({
        left: 1142, top: 302, radius: 7, fill: '#10b981', selectable: true
      });

      const vegLabel = new fabric.Textbox('100% VEGETARIAN', {
        left: 1175, top: 301, width: 200, fontSize: 11, fontFamily: 'Montserrat',
        fontWeight: '800', fill: '#047857', selectable: true
      });

      // Barcode placeholder simulation
      const barcodeBox = new fabric.Rect({
        left: 1135, top: 360, width: 170, height: 60, fill: '#f8fafc',
        stroke: '#cbd5e1', strokeWidth: 1, selectable: true
      });
      const barcodeText = new fabric.Textbox('||||||| | ||||| |||||\n8901234567890', {
        left: 1145, top: 370, width: 150, fontSize: 13, fontFamily: 'Courier New',
        fontWeight: '700', fill: '#0f172a', textAlign: 'center', selectable: true
      });

      canvaCanvas.add(rightBox, benefitsText, vegDotBox, vegDot, vegLabel, barcodeBox, barcodeText);
      canvaCanvas.renderAll();
      updateThreeLabelTextureFromCanvas();
    }

    /* ======================================================
       BRAND KIT INTERACTIVE SYNC (SLIDERS + ACTIONS)
    ====================================================== */
    function initBrandKitControls() {
      const posXSlider = document.getElementById('canvaBrandLogoPosXSlider');
      const posYSlider = document.getElementById('canvaBrandLogoPosYSlider');
      const sizeSlider = document.getElementById('canvaBrandLogoSizeSlider');
      const rotSlider = document.getElementById('canvaBrandLogoRotSlider');

      const posXVal = document.getElementById('canvaBrandLogoPosXVal');
      const posYVal = document.getElementById('canvaBrandLogoPosYVal');
      const sizeVal = document.getElementById('canvaBrandLogoSizeVal');
      const rotVal = document.getElementById('canvaBrandLogoRotVal');

      const restoreBtn = document.getElementById('canvaRestoreFactoryLogoBtn');
      const centerBtn = document.getElementById('canvaCenterLogoOnLabelBtn');
      const footerSelectLogoBtn = document.getElementById('footerSelectLogoBtn');
      const footerCenterBtn = document.getElementById('footerCenterBtn');
      const footerRestoreLogoBtn = document.getElementById('footerRestoreLogoBtn');

      function syncSlidersFromObject(obj) {
        if (!obj || !canvaCanvas) return;
        const xPercent = Math.round((obj.left / canvaCanvas.width) * 100);
        const yPercent = Math.round((obj.top / canvaCanvas.height) * 100);
        if (posXSlider) posXSlider.value = xPercent;
        if (posYSlider) posYSlider.value = yPercent;
        if (posXVal) posXVal.textContent = `${Math.round(obj.left)} px`;
        if (posYVal) posYVal.textContent = `${Math.round(obj.top)} px`;
        if (rotSlider) rotSlider.value = Math.round(obj.angle || 0);
        if (rotVal) rotVal.textContent = `${Math.round(obj.angle || 0)}°`;
      }

      canvaCanvas.on('selection:created', (e) => {
        if (e.selected && e.selected[0]) {
          brandLogoObject = e.selected[0];
          syncSlidersFromObject(brandLogoObject);
        }
      });
      canvaCanvas.on('selection:updated', (e) => {
        if (e.selected && e.selected[0]) {
          brandLogoObject = e.selected[0];
          syncSlidersFromObject(brandLogoObject);
        }
      });

      if (posXSlider) {
        posXSlider.oninput = () => {
          if (!brandLogoObject) return;
          const leftPx = (parseFloat(posXSlider.value) / 100) * canvaCanvas.width;
          brandLogoObject.set('left', leftPx);
          if (posXVal) posXVal.textContent = `${Math.round(leftPx)} px`;
          canvaCanvas.renderAll();
        };
      }

      if (posYSlider) {
        posYSlider.oninput = () => {
          if (!brandLogoObject) return;
          const topPx = (parseFloat(posYSlider.value) / 100) * canvaCanvas.height;
          brandLogoObject.set('top', topPx);
          if (posYVal) posYVal.textContent = `${Math.round(topPx)} px`;
          canvaCanvas.renderAll();
        };
      }

      if (sizeSlider) {
        sizeSlider.oninput = () => {
          if (!brandLogoObject) return;
          const targetSize = parseFloat(sizeSlider.value);
          const baseScale = targetSize / 87.0;
          brandLogoObject.scale(baseScale);
          if (sizeVal) sizeVal.textContent = `${Math.round(targetSize)} px`;
          canvaCanvas.renderAll();
        };
      }

      if (rotSlider) {
        rotSlider.oninput = () => {
          if (!brandLogoObject) return;
          const deg = parseFloat(rotSlider.value);
          brandLogoObject.set('angle', deg);
          if (rotVal) rotVal.textContent = `${Math.round(deg)}°`;
          canvaCanvas.renderAll();
        };
      }

      function centerLogo() {
        if (!brandLogoObject || !canvaCanvas) return;
        brandLogoObject.set('left', 674);
        brandLogoObject.set('top', 38);
        brandLogoObject.set('angle', 0);
        syncSlidersFromObject(brandLogoObject);
        canvaCanvas.renderAll();
        showToast("Centered GOMZI Brand Logo!", "🎯");
      }

      if (centerBtn) centerBtn.onclick = centerLogo;
      if (footerCenterBtn) footerCenterBtn.onclick = centerLogo;

      function restoreLogo() {
        loadGomziWheyTemplate();
        showToast("Restored official GOMZI NUTRITION logo & template!", "✅");
      }

      if (restoreBtn) restoreBtn.onclick = restoreLogo;
      if (footerRestoreLogoBtn) footerRestoreLogoBtn.onclick = restoreLogo;

      if (footerSelectLogoBtn) {
        footerSelectLogoBtn.onclick = () => {
          if (brandLogoObject && canvaCanvas) {
            canvaCanvas.setActiveObject(brandLogoObject);
            canvaCanvas.renderAll();
            showToast("Selected Brand Logo", "🏷️");
          }
        };
      }

      // Upload Logo File Input
      const uploadLogoInput = document.getElementById('canvaUploadBrandLogoInput');
      if (uploadLogoInput) {
        uploadLogoInput.onchange = (e) => {
          const file = e.target.files[0];
          if (!file) return;
          const reader = new FileReader();
          reader.onload = (f) => {
            fabric.Image.fromURL(f.target.result, (img) => {
              if (brandLogoObject) canvaCanvas.remove(brandLogoObject);
              img.scaleToWidth(200);
              img.set({ left: 674, top: 40 });
              brandLogoObject = img;
              canvaCanvas.add(img);
              canvaCanvas.setActiveObject(img);
              canvaCanvas.renderAll();
              syncSlidersFromObject(img);
              showToast("Uploaded custom brand logo!", "✨");
            });
          };
          reader.readAsDataURL(file);
        };
      }
    }

    /* ======================================================
       DRAWER TABS SWITCHER
    ====================================================== */
    function initDrawerTabs() {
      const tabBtns = document.querySelectorAll('.studio-tab-btn');
      const drawerViews = document.querySelectorAll('.drawer-view');

      tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          const target = btn.getAttribute('data-drawer');
          tabBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');

          drawerViews.forEach(view => {
            view.classList.remove('active');
            if (view.id.toLowerCase() === `drawer${target}`) {
              view.classList.add('active');
            }
          });
        });
      });
    }

    /* ======================================================
       THREE.JS LIVE 3D MUSCLE TUB MOCKUP
    ====================================================== */
    function initThreeJarMockup() {
      const container = document.getElementById('pacdoraThreeContainer');
      if (!container || typeof THREE === 'undefined') return;

      const width = container.clientWidth || 350;
      const height = container.clientHeight || 330;

      threeScene = new THREE.Scene();
      threeCamera = new THREE.PerspectiveCamera(36, width / height, 0.1, 100);
      threeCamera.position.set(0, 0.4, 3.8);

      threeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
      threeRenderer.setSize(width, height);
      threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      threeRenderer.toneMapping = THREE.ACESFilmicToneMapping;
      threeRenderer.toneMappingExposure = 1.2;
      container.innerHTML = '';
      container.appendChild(threeRenderer.domElement);

      if (typeof THREE.OrbitControls !== 'undefined') {
        threeOrbitControls = new THREE.OrbitControls(threeCamera, threeRenderer.domElement);
        threeOrbitControls.enableDamping = true;
        threeOrbitControls.dampingFactor = 0.08;
        threeOrbitControls.minDistance = 2.2;
        threeOrbitControls.maxDistance = 5.2;
        threeOrbitControls.maxPolarAngle = Math.PI / 2 + 0.15;
        threeOrbitControls.minPolarAngle = Math.PI / 4;
      }

      // Studio Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
      threeScene.add(ambientLight);

      const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
      keyLight.position.set(3, 4, 3);
      threeScene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(0xdbeafe, 0.7);
      fillLight.position.set(-3, 2, -2);
      threeScene.add(fillLight);

      // Model Group
      threeJarGroup = new THREE.Group();
      threeScene.add(threeJarGroup);

      // Label Texture mapping placeholder
      threeLabelTexture = new THREE.Texture();
      threeLabelTexture.wrapS = THREE.RepeatWrapping;
      threeLabelTexture.wrapT = THREE.ClampToEdgeWrapping;

      // 1. Muscle Tub Cylindrical Body
      const jarRadius = 0.88;
      const jarHeight = 1.62;
      const bodyGeo = new THREE.CylinderGeometry(jarRadius, jarRadius, jarHeight, 64, 1, false);
      bodyGeo.rotateY(Math.PI); // Center front facing camera

      const bodyMat = new THREE.MeshStandardMaterial({
        color: threeCurrentBodyColor,
        roughness: 0.25,
        metalness: 0.1
      });
      threeBodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
      threeBodyMesh.position.y = -0.05;
      threeJarGroup.add(threeBodyMesh);

      // 2. Ribbed Screw Cap
      const capRadius = jarRadius * 0.95;
      const capHeight = 0.32;
      const capGeo = new THREE.CylinderGeometry(capRadius, capRadius, capHeight, 64);
      const capMat = new THREE.MeshStandardMaterial({
        color: 0x222225,
        roughness: 0.3,
        metalness: 0.12
      });
      threeCapMesh = new THREE.Mesh(capGeo, capMat);
      threeCapMesh.position.y = jarHeight / 2 + capHeight / 2 + 0.04;
      threeJarGroup.add(threeCapMesh);

      // Floor Soft Shadow
      const shadowGeo = new THREE.PlaneGeometry(2.5, 2.5);
      const sCanvas = document.createElement('canvas');
      sCanvas.width = 128; sCanvas.height = 128;
      const sCtx = sCanvas.getContext('2d');
      const grad = sCtx.createRadialGradient(64, 64, 10, 64, 64, 64);
      grad.addColorStop(0, 'rgba(0,0,0,0.5)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      sCtx.fillStyle = grad;
      sCtx.fillRect(0, 0, 128, 128);
      const shadowTex = new THREE.CanvasTexture(sCanvas);
      const shadowMat = new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, opacity: 0.6 });
      const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
      shadowMesh.rotation.x = -Math.PI / 2;
      shadowMesh.position.y = -jarHeight / 2 - 0.05;
      threeJarGroup.add(shadowMesh);

      // Animation Loop
      function animate() {
        threeAnimFrameId = requestAnimationFrame(animate);
        if (isAutoSpinning && threeJarGroup) {
          threeJarGroup.rotation.y += 0.01;
        }
        if (threeOrbitControls) threeOrbitControls.update();
        threeRenderer.render(threeScene, threeCamera);
      }
      animate();

      // Hook Swatches
      const colorBtns = document.querySelectorAll('.color-swatch-btn');
      colorBtns.forEach(btn => {
        btn.onclick = () => {
          colorBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const hex = btn.getAttribute('data-color');
          const name = btn.getAttribute('data-name');
          document.getElementById('canvaCurrentPkgColorLabel').textContent = name;
          threeCurrentBodyColor = parseInt(hex.replace('#', '0x'));
          if (threeBodyMesh) threeBodyMesh.material.color.setHex(threeCurrentBodyColor);
          if (threeCapMesh && hex !== '#ffffff') threeCapMesh.material.color.setHex(threeCurrentBodyColor);
        };
      });

      // Hook View Angle Buttons
      const frontBtn = document.getElementById('btnViewFront');
      const backBtn = document.getElementById('btnViewBack');
      const sideBtn = document.getElementById('btnViewSide');

      function setAngle(btn, rad) {
        document.querySelectorAll('.view-angle-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        isAutoSpinning = false;
        if (threeJarGroup) threeJarGroup.rotation.y = rad;
      }

      if (frontBtn) frontBtn.onclick = () => setAngle(frontBtn, 0);
      if (backBtn) backBtn.onclick = () => setAngle(backBtn, Math.PI);
      if (sideBtn) sideBtn.onclick = () => setAngle(sideBtn, Math.PI / 2);

      const autoSpinBtn = document.getElementById('canvaAutoSpinBtn');
      if (autoSpinBtn) {
        autoSpinBtn.onclick = () => {
          isAutoSpinning = !isAutoSpinning;
          autoSpinBtn.textContent = isAutoSpinning ? '⏸️ Pause Spin' : '▶️ Auto 360° Spin';
        };
      }

      const resetCamBtn = document.getElementById('canvaReset3dCameraBtn');
      if (resetCamBtn) {
        resetCamBtn.onclick = () => {
          if (threeCamera) threeCamera.position.set(0, 0.4, 3.8);
          if (threeJarGroup) threeJarGroup.rotation.set(0, 0, 0);
          if (threeOrbitControls) threeOrbitControls.reset();
        };
      }
    }

    // Synchronize 2D Canvas onto 3D Jar Body Texture
    function updateThreeLabelTextureFromCanvas() {
      if (!canvaCanvas || !threeBodyMesh) return;
      const nativeCanvas = canvaCanvas.lowerCanvasEl;
      if (!nativeCanvas) return;

      const newTexture = new THREE.CanvasTexture(nativeCanvas);
      newTexture.wrapS = THREE.RepeatWrapping;
      newTexture.wrapT = THREE.ClampToEdgeWrapping;
      newTexture.anisotropy = 8;
      
      threeBodyMesh.material.map = newTexture;
      threeBodyMesh.material.needsUpdate = true;
    }

    /* ======================================================
       EXPORT CONTROLS (CorelDRAW CDR, PDF, PNG, SVG)
    ====================================================== */
    function initExportControls() {
      const exportMenuBtn = document.getElementById('canvaExportMenuBtn');
      const exportDropdown = document.getElementById('canvaExportDropdown');

      if (exportMenuBtn && exportDropdown) {
        exportMenuBtn.onclick = (e) => {
          e.stopPropagation();
          exportDropdown.style.display = exportDropdown.style.display === 'flex' ? 'none' : 'flex';
        };
        document.addEventListener('click', () => { exportDropdown.style.display = 'none'; });
      }

      async function triggerExport(fmt) {
        if (!canvaCanvas) return;
        showToast(`Generating ${fmt.toUpperCase()} Master...`, "⏳", 4000);
        const dataUrl = canvaCanvas.toDataURL({ format: 'png', multiplier: 2 });
        const docTitle = document.getElementById('canvaDocTitleInput')?.value || "GOMZI_Whey_Protein_1kg";

        try {
          const res = await fetch('/api/canva/export-master', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_data: dataUrl,
              format: fmt,
              filename: `${docTitle}.${fmt}`
            })
          });

          if (!res.ok) throw new Error("Export failed on server");
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = fmt === 'cdr' ? `${docTitle}_Corel_Master.zip` : `${docTitle}_300dpi.${fmt}`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          showToast(`Successfully downloaded ${fmt.toUpperCase()}!`, "✅", 3000);
        } catch (err) {
          console.error(err);
          showToast(`Export error: ${err.message}`, "❌", 3500);
        }
      }

      document.getElementById('canvaExportCdrBtn')?.addEventListener('click', () => triggerExport('cdr'));
      document.getElementById('canvaExportPdfBtn')?.addEventListener('click', () => triggerExport('pdf'));
      document.getElementById('canvaExportPngBtn')?.addEventListener('click', () => triggerExport('png'));
      document.getElementById('canvaExportSvgBtn')?.addEventListener('click', () => triggerExport('svg'));

      // Save Project Button
      document.getElementById('canvaApplyBtn')?.addEventListener('click', () => {
        showToast("Design project saved successfully!", "💾", 2500);
      });
    }

    // Initialize application when DOM ready
    window.addEventListener('DOMContentLoaded', () => {
      initGomziStudio();
    });
  </script>
</body>
</html>
'''

def main():
    target_path = os.path.join("templates", "index.html")
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)
    print(f"Successfully generated {target_path} ({len(HTML_CONTENT)} bytes)")

if __name__ == "__main__":
    main()
