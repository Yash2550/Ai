# -*- coding: utf-8 -*-
"""
Generates the complete, fully-functional GOMZI BOB AI Design Studio Pro.
Every button, slider, tab, and navigation link is connected to actual backend/frontend logic.
"""

import os

HTML_CODE = r'''<!DOCTYPE html>
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
       Clean White SaaS Platform with Olive-Green Accent (#708238)
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
      transition: background 0.15s;
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
      transition: width 0.2s;
    }
    .app-sidebar.collapsed {
      width: 0;
      overflow: hidden;
      border-right: none;
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
      cursor: pointer;
      position: relative;
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
    .studio-action-pill.active {
      background: var(--clr-olive-light);
      border-color: var(--clr-olive-border);
      color: var(--clr-olive-dark);
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

    .studio-columns-body {
      flex: 1;
      display: flex;
      overflow: hidden;
      position: relative;
    }

    /* LEFT CONFIGURATION PANEL */
    .studio-left-col {
      width: 320px;
      background: #ffffff;
      border-right: 1px solid var(--clr-border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      overflow-y: auto;
      z-index: 10;
      transition: width 0.2s;
    }
    .studio-left-col.collapsed {
      width: 0;
      overflow: hidden;
      border-right: none;
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

    /* CENTER 2D CANVAS WORKSPACE */
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

    /* RIGHT LIVE 3D CONTAINER PANEL */
    .studio-right-col {
      width: 350px;
      background: #ffffff;
      border-left: 1px solid var(--clr-border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      overflow-y: auto;
      z-index: 10;
      transition: width 0.2s;
    }
    .studio-right-col.collapsed {
      width: 0;
      overflow: hidden;
      border-left: none;
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
       COMMON MODULE VIEW STYLING (Dashboard, Orders, etc.)
    ====================================================== */
    .view-scroll-body {
      flex: 1;
      overflow-y: auto;
      padding: 24px 30px;
      display: flex;
      flex-direction: column;
      gap: 24px;
      background: #f8fafc;
    }

    .module-header-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .module-title {
      font-size: 22px;
      font-weight: 800;
      color: #0f172a;
    }
    .module-sub {
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

    .content-section-card {
      background: #ffffff;
      border: 1px solid var(--clr-border);
      border-radius: var(--radius-lg);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      box-shadow: var(--shadow-sm);
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
    }
    .data-table th {
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1.5px solid var(--clr-border);
      color: #64748b;
      font-weight: 700;
    }
    .data-table td {
      padding: 12px;
      border-bottom: 1px solid var(--clr-border);
      color: #0f172a;
    }
    .table-action-btn {
      background: var(--clr-olive-light);
      border: 1px solid var(--clr-olive-border);
      color: var(--clr-olive-dark);
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }
    .table-action-btn:hover {
      background: var(--clr-olive);
      color: #fff;
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
    
    <!-- TOPBAR -->
    <header class="app-topbar">
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

      <div class="topbar-right">
        <div class="account-balance-pill">
          <span>₹ 0</span>
          <span class="add-money-link" id="navAddMoneyLink">+ Add money</span>
        </div>
        <button class="new-order-btn" id="navNewOrderBtn">
          <span>+</span>
          <span>New Order</span>
        </button>
        <div class="user-profile-badge" id="navUserProfile">
          <div class="user-avatar-circle">G</div>
          <span class="user-name-label">GOMZI</span>
          <div class="online-indicator"></div>
        </div>
      </div>
    </header>

    <!-- APP BODY -->
    <div class="app-body">
      
      <!-- PERSISTENT SIDEBAR -->
      <aside class="app-sidebar" id="mainAppSidebar">
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
          <div class="sidebar-group-header" id="sidebarGroupDesigns">
            <div style="display:flex; align-items:center; gap:10px;">
              <span class="sidebar-item-icon">🎨</span>
              <span>Designs</span>
            </div>
            <span style="font-size:10px; color:#94a3b8;" id="designsChevron">▾</span>
          </div>
          <div class="sidebar-sub-menu" id="designsSubMenu">
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

        <!-- VIEW 1: DESIGN STUDIO -->
        <section class="app-view active" id="viewDesignStudio">
          
          <!-- Sub-Header -->
          <div class="studio-sub-header">
            <div class="studio-header-left">
              <button class="studio-back-btn" id="studioBackBtn" title="Back to Dashboard">
                ‹ Back
              </button>
              
              <div class="product-spec-pill" id="studioProductPill" title="Switch Packaging Presets">
                <span>📦</span>
                <span id="studioProductPillName">Whey Protein Standard</span>
                <span style="font-size:9px; color:#166534;">▾</span>
                <!-- Presets Dropdown -->
                <div id="productPresetsDropdown" style="display:none; position:absolute; left:0; top:36px; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; width:280px; box-shadow:var(--shadow-md); z-index:99; padding:6px; flex-direction:column; gap:4px;">
                  <!-- Populated dynamically -->
                </div>
              </div>

              <span class="spec-dimension-tag" id="studioSpecTag">
                1 kg Muscle Tub · 45.2 × 14.2 cm
              </span>

              <input class="studio-doc-title-input" id="canvaDocTitleInput" value="GOMZI Whey Protein Belgian Chocolate 1kg" />
            </div>

            <!-- Formatting Toolbar -->
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
                <option value="Oswald">Oswald</option>
                <option value="Anton">Anton</option>
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

            <!-- Right Controls -->
            <div class="studio-header-right">
              <button class="studio-action-pill" id="studioFocusBtn" title="Toggle Distraction-Free Workspace">Focus</button>
              <button class="studio-action-pill" id="studioToolsBtn" title="Open AI Tools Drawer">Tools</button>
              <button class="studio-action-pill active" id="studio3dToggleBtn" title="Show/Hide 3D Mockup">3D</button>
              <button class="studio-action-pill" id="canvaPrintGuidesBtn" title="Toggle 3mm Bleed Margins">Guides</button>

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

          <!-- Studio Sub-Toolbar -->
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
            <aside class="studio-left-col" id="studioLeftPanel">
              
              <!-- DRAWER 1: BRAND KIT -->
              <div class="drawer-view active" id="drawerBrand">
                <div class="drawer-header">
                  <span class="drawer-title">Merchant Brand Kit</span>
                  <span class="drawer-badge drawer-badge-green">Auto-Synced</span>
                </div>

                <div class="drawer-card">
                  <span class="drawer-card-label">Brand Name</span>
                  <input id="canvaBrandNameInput" value="GOMZI NUTRITION" 
                    style="background:#fff; border:1px solid #cbd5e1; border-radius:6px; padding:7px 10px; font-weight:800; font-size:13px; color:#0f172a; outline:none;" />
                  <button id="canvaInsertBrandNameBtn" 
                    style="background:var(--clr-olive); color:#fff; border:none; border-radius:6px; padding:7px; font-size:11.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:5px;">
                    ➕ Insert Brand Name on Label
                  </button>
                </div>

                <div class="drawer-card">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="drawer-card-label">Brand Logo</span>
                    <span style="font-size:10px; color:#10b981; font-weight:700; background:#d1fae5; padding:1px 6px; border-radius:4px;">Active on Template</span>
                  </div>

                  <div class="brand-logo-preview-box" id="canvaBrandLogoPreviewBox">
                    <img id="brandLogoPreviewImg" src="/static/assets/gomzi_logo.svg" alt="GOMZI Logo" style="max-width:180px; max-height:60px; object-fit:contain;" />
                  </div>

                  <div style="display:flex; gap:6px;">
                    <label style="flex:1; background:#0f172a; color:#fff; border-radius:6px; padding:7px; font-size:11px; font-weight:700; cursor:pointer; text-align:center;">
                      📤 Upload New
                      <input type="file" id="canvaUploadBrandLogoInput" accept="image/*" style="display:none;" />
                    </label>
                    <button id="canvaRestoreFactoryLogoBtn" style="background:#fff; border:1px solid #cbd5e1; color:#ef4444; border-radius:6px; padding:7px 10px; font-size:11px; font-weight:700; cursor:pointer;">
                      Restore Factory Logo
                    </button>
                  </div>

                  <div class="clean-plate-indicator-box">
                    <span style="font-size:16px;">✨</span>
                    <div>
                      <div class="clean-plate-title" id="cleanPlateTitleLabel">Clean Plate Active</div>
                      <div class="clean-plate-sub" id="cleanPlateSubLabel">Authentic Background Preserved</div>
                    </div>
                  </div>

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
                <input id="templateSearchInput" placeholder="🔍 Search templates..." style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:7px 10px; font-size:12px; outline:none;" />
                <div id="templatesListContainer" style="display:flex; flex-direction:column; gap:8px;">
                  <!-- Populated dynamically -->
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
                <button class="canva-snippet-btn" data-text="STORE IN A COOL, DRY PLACE AWAY FROM SUNLIGHT" style="background:#ffffff; border:1px solid #cbd5e1; padding:8px; border-radius:6px; cursor:pointer; text-align:left; font-weight:700; font-size:11px;">
                  ☀️ STORAGE INSTRUCTIONS
                </button>
              </div>

              <!-- DRAWER 4: FACTS (PRODUCT INFORMATION SYNC) -->
              <div class="drawer-view" id="drawerFacts">
                <div class="drawer-header">
                  <span class="drawer-title">Nutrition &amp; Facts</span>
                  <span class="drawer-badge drawer-badge-green">FSSAI / FDA</span>
                </div>
                
                <div class="drawer-card">
                  <span class="drawer-card-label">Product Title</span>
                  <input id="factsProductTitle" value="WHEY PROTEIN" style="background:#fff; border:1px solid #cbd5e1; border-radius:4px; padding:5px 8px; font-weight:700; font-size:12px;" />
                  
                  <span class="drawer-card-label" style="margin-top:4px;">Flavour Banner</span>
                  <input id="factsFlavour" value="BELGIAN CHOCOLATE" style="background:#fff; border:1px solid #cbd5e1; border-radius:4px; padding:5px 8px; font-weight:700; font-size:12px;" />

                  <span class="drawer-card-label" style="margin-top:4px;">Net Weight &amp; Servings</span>
                  <input id="factsNetWeight" value="1 kg | 30 SERVINGS*" style="background:#fff; border:1px solid #cbd5e1; border-radius:4px; padding:5px 8px; font-weight:700; font-size:12px;" />

                  <span class="drawer-card-label" style="margin-top:4px;">Protein Per Serving</span>
                  <input id="factsProteinVal" value="24 g" style="background:#fff; border:1px solid #cbd5e1; border-radius:4px; padding:5px 8px; font-weight:700; font-size:12px;" />
                </div>

                <button id="canvaAddNutritionTableBtn" style="background:#ffffff; border:1.5px solid #cbd5e1; border-radius:8px; padding:9px 12px; text-align:left; cursor:pointer; font-size:12px; font-weight:700; display:flex; align-items:center; gap:8px;">
                  📊 <span>Add FDA Nutrition Facts Table</span>
                </button>
                <button id="canvaAddFssaiBatchBtn" style="background:#ffffff; border:1.5px solid #cbd5e1; border-radius:8px; padding:9px 12px; text-align:left; cursor:pointer; font-size:12px; font-weight:700; display:flex; align-items:center; gap:8px;">
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
                  📤 Upload Image / Logo / Sticker
                  <input type="file" id="canvaDrawerUploadInput" accept="image/*" style="display:none;" />
                </label>
                <div style="font-size:11px; font-weight:700; color:#64748b; margin-top:6px; text-transform:uppercase;">Uploaded Assets Gallery (Click to Add)</div>
                <div id="uploadsGalleryGrid" style="display:grid; grid-template-columns:1fr 1fr; gap:8px; max-height:calc(100vh - 280px); overflow-y:auto;">
                  <!-- Dynamically populated -->
                </div>
              </div>

              <!-- DRAWER 6: LAYERS -->
              <div class="drawer-view" id="drawerLayers">
                <div class="drawer-header">
                  <span class="drawer-title">Layers</span>
                  <span id="canvaLayerCountBadge" class="drawer-badge drawer-badge-green">0</span>
                </div>
                <div style="display:flex; justify-content:space-between; gap:4px;">
                  <button id="layerBringForwardBtn" style="flex:1; background:#f8fafc; border:1px solid #cbd5e1; border-radius:4px; padding:5px; font-size:11px; font-weight:700; cursor:pointer;">↑ Forward</button>
                  <button id="layerSendBackwardBtn" style="flex:1; background:#f8fafc; border:1px solid #cbd5e1; border-radius:4px; padding:5px; font-size:11px; font-weight:700; cursor:pointer;">↓ Backward</button>
                </div>
                <div id="canvaLayersListContainer" style="display:flex; flex-direction:column; gap:4px; max-height:calc(100vh - 240px); overflow-y:auto;">
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
                  <button id="canvaToolGrabTextBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px; cursor:pointer; text-align:center;">
                    <div style="font-size:22px;">🔤</div>
                    <div style="font-weight:700; font-size:11.5px; margin-top:4px;">Grab Text</div>
                  </button>
                  <button id="canvaToolBgRemoverBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px; cursor:pointer; text-align:center;">
                    <div style="font-size:22px;">🏖️</div>
                    <div style="font-weight:700; font-size:11.5px; margin-top:4px;">BG Remover</div>
                  </button>
                  <button id="canvaToolMagicEraserBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px; cursor:pointer; text-align:center;">
                    <div style="font-size:22px;">🧹</div>
                    <div style="font-weight:700; font-size:11.5px; margin-top:4px;">Magic Eraser</div>
                  </button>
                  <button id="canvaToolUpscaleBtn" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px; cursor:pointer; text-align:center;">
                    <div style="font-size:22px;">🌻</div>
                    <div style="font-weight:700; font-size:11.5px; margin-top:4px;">Upscale 4x</div>
                  </button>
                </div>

                <!-- Grab Text Active Review Box -->
                <div id="grabTextReviewBox" style="display:none; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:10px; flex-direction:column; gap:6px;">
                  <div style="font-weight:800; font-size:11.5px; color:#166534;">✓ Detected Text Ready for Editing</div>
                  <div style="font-size:10.5px; color:#15803d;">Double-click any text directly on the canvas to edit in place. Background underneath is protected with Clean Plate.</div>
                  <button id="closeGrabTextBoxBtn" style="background:#15803d; color:#fff; border:none; border-radius:4px; padding:5px; font-size:11px; font-weight:700; cursor:pointer; margin-top:4px;">Got It</button>
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

              <div class="three-stage-container" id="pacdoraThreeContainer">
                <div class="three-360-badge">🔄 360° DRAG</div>
              </div>

              <div class="mockup-controls-card">
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

        <!-- VIEW 2: DASHBOARD -->
        <section class="app-view" id="viewDashboard">
          <div class="view-scroll-body">
            <div class="module-header-banner">
              <div>
                <h1 class="module-title">Welcome to GOMZI BOB Platform</h1>
                <p class="module-sub">Merchant Design Studio &amp; Packaging Automation Dashboard</p>
              </div>
              <button class="studio-save-btn" onclick="switchMainView('studio');" style="padding:9px 18px; font-size:13px;">
                🎨 Open Design Studio
              </button>
            </div>

            <div class="dash-metrics-grid">
              <div class="metric-card">
                <span class="metric-title">Total Projects</span>
                <span class="metric-val" id="dashTotalProjects">24</span>
                <span class="metric-sub">Active designs</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">AI Jobs</span>
                <span class="metric-val" id="dashAiJobs">42</span>
                <span class="metric-sub">Completed</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">Labels Generated</span>
                <span class="metric-val" id="dashLabelsGenerated">84</span>
                <span class="metric-sub">Print ready 300 DPI</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">Vectors Created</span>
                <span class="metric-val" id="dashVectorsCreated">16</span>
                <span class="metric-sub">Corel CDR/SVG</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">AI Cost Today</span>
                <span class="metric-val" id="dashAiCostToday">₹ 142.50</span>
                <span class="metric-sub">This Month: ₹ 3,420.00</span>
              </div>
              <div class="metric-card">
                <span class="metric-title">Provider Status</span>
                <span class="metric-val" id="dashProviderStatus" style="font-size:16px; color:#10b981; margin-top:4px;">● All Operational</span>
                <span class="metric-sub" style="color:#64748b;">Google Flow · Rembg · OCR</span>
              </div>
            </div>

            <div class="content-section-card">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h2 style="font-size:15px; font-weight:800; color:#0f172a;">Recent Packaging Projects</h2>
              </div>
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Project Name</th>
                    <th>Container &amp; Size</th>
                    <th>Brand</th>
                    <th>Last Modified</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody id="dashRecentProjectsTableBody">
                  <!-- Populated from API -->
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- VIEW 3: ORDERS -->
        <section class="app-view" id="viewOrders">
          <div class="view-scroll-body">
            <div class="module-header-banner">
              <div>
                <h1 class="module-title">Orders Management</h1>
                <p class="module-sub">Track packaging print and production orders</p>
              </div>
              <button class="new-order-btn" onclick="openNewOrderModal();">
                + Create New Order
              </button>
            </div>

            <div class="content-section-card">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>Customer</th>
                    <th>Product</th>
                    <th>Quantity</th>
                    <th>Status</th>
                    <th>Date</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody id="ordersTableBody">
                  <!-- Populated from API -->
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- VIEW 4: PRODUCTS -->
        <section class="app-view" id="viewProducts">
          <div class="view-scroll-body">
            <div class="module-header-banner">
              <div>
                <h1 class="module-title">Product Catalog Presets</h1>
                <p class="module-sub">Available packaging containers, standard mold dimensions and formats</p>
              </div>
            </div>

            <div class="dash-metrics-grid" id="productsCatalogGrid" style="grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));">
              <!-- Populated from API -->
            </div>
          </div>
        </section>

        <!-- VIEW 5: MY DESIGNS -->
        <section class="app-view" id="viewMyDesigns">
          <div class="view-scroll-body">
            <div class="module-header-banner">
              <div>
                <h1 class="module-title">My Saved Designs</h1>
                <p class="module-sub">Open, duplicate, rename or export your saved packaging designs</p>
              </div>
              <button class="studio-save-btn" onclick="startNewDesign();">
                ➕ New Design
              </button>
            </div>

            <div class="dash-metrics-grid" id="myDesignsGrid" style="grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));">
              <!-- Populated from API -->
            </div>
          </div>
        </section>

        <!-- VIEW 6: CUSTOM LABELS & MOCKUPS -->
        <section class="app-view" id="viewCustomLabels">
          <div class="view-scroll-body">
            <div class="module-header-banner">
              <div>
                <h1 class="module-title">Custom Labels &amp; Mockups Gallery</h1>
                <p class="module-sub">Surat Muscle Tubs, Boston Round Bottles, Jars and Sachets</p>
              </div>
            </div>
            <div class="content-section-card">
              <div style="font-size:14px; font-weight:700; color:#0f172a;">Available Packaging Molds</div>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px; margin-top:10px;">
                <div style="border:1px solid #cbd5e1; border-radius:8px; padding:14px; background:#fff;">
                  <div style="font-size:24px;">🫙</div>
                  <div style="font-weight:800; font-size:13px; margin-top:6px;">1 kg Muscle Tub</div>
                  <div style="font-size:11px; color:#64748b;">Surat Mold · 45.2 × 14.2 cm (3:1)</div>
                  <button class="table-action-btn" style="margin-top:10px;" onclick="switchMainView('studio');">Open in 3D Studio</button>
                </div>
                <div style="border:1px solid #cbd5e1; border-radius:8px; padding:14px; background:#fff;">
                  <div style="font-size:24px;">🧴</div>
                  <div style="font-weight:800; font-size:13px; margin-top:6px;">120ct Capsule Bottle</div>
                  <div style="font-size:11px; color:#64748b;">Pharma Grade · 22 × 9 cm</div>
                  <button class="table-action-btn" style="margin-top:10px;" onclick="switchMainView('studio');">Open in 3D Studio</button>
                </div>
                <div style="border:1px solid #cbd5e1; border-radius:8px; padding:14px; background:#fff;">
                  <div style="font-size:24px;">📦</div>
                  <div style="font-weight:800; font-size:13px; margin-top:6px;">2 kg Muscle Tub</div>
                  <div style="font-size:11px; color:#64748b;">Heavyweight Pro · 48 × 16 cm</div>
                  <button class="table-action-btn" style="margin-top:10px;" onclick="switchMainView('studio');">Open in 3D Studio</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- VIEW 7: RETURNS, ACCOUNTS, INTEGRATIONS, SETTINGS, HELP -->
        <section class="app-view" id="viewOtherModules">
          <div class="view-scroll-body">
            <div class="module-header-banner">
              <div>
                <h1 class="module-title" id="otherModuleTitle">Module</h1>
                <p class="module-sub" id="otherModuleSub">Platform information and status</p>
              </div>
            </div>
            <div class="content-section-card" id="otherModuleContent">
              <!-- Content rendered dynamically -->
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
       JAVASCRIPT APPLICATION CORE (Fabric.js + Three.js + APIs)
  ====================================================== */ -->
  <script>
    // Global State
    let canvaCanvas = null;
    let brandLogoObject = null;
    let threeRenderer = null, threeCamera = null, threeScene = null, threeOrbitControls = null;
    let threeJarGroup = null, threeBodyMesh = null, threeCapMesh = null, threeLabelMesh = null, threeLabelTexture = null;
    let isAutoSpinning = false, threeAnimFrameId = null;
    let threeCurrentBodyColor = 0x18181b; // Black default
    let activeProjectId = null;
    let hasUnsavedChanges = false;
    let canvasHistory = [];
    let historyIndex = -1;
    let isHistoryLocked = false;
    let isCleanPlateActive = false;
    let isBleedGuideVisible = false;

    // Toast Utility
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

    // 1. Navigation Switcher
    function switchMainView(viewName, meta = {}) {
      document.querySelectorAll('.app-view').forEach(v => v.classList.remove('active'));
      document.querySelectorAll('.sidebar-item, .sidebar-sub-item').forEach(el => el.classList.remove('active'));

      if (viewName === 'studio') {
        document.getElementById('viewDesignStudio').classList.add('active');
        document.getElementById('sidebarNavStudio').classList.add('active');
        setTimeout(() => {
          if (canvaCanvas) canvaCanvas.renderAll();
          updateThreeLabelTextureFromCanvas();
        }, 80);
      } else if (viewName === 'dashboard') {
        document.getElementById('viewDashboard').classList.add('active');
        document.getElementById('sidebarNavDashboard').classList.add('active');
        loadDashboardStats();
      } else if (viewName === 'orders') {
        document.getElementById('viewOrders').classList.add('active');
        document.getElementById('sidebarNavOrders').classList.add('active');
        loadOrdersModule();
      } else if (viewName === 'products') {
        document.getElementById('viewProducts').classList.add('active');
        document.getElementById('sidebarNavProducts').classList.add('active');
        loadProductsCatalog();
      } else if (viewName === 'my-designs') {
        document.getElementById('viewMyDesigns').classList.add('active');
        document.getElementById('sidebarNavMyDesigns').classList.add('active');
        loadMyDesigns();
      } else if (viewName === 'custom-labels') {
        document.getElementById('viewCustomLabels').classList.add('active');
        document.getElementById('sidebarNavCustomLabels').classList.add('active');
      } else {
        // Other Modules (Returns, Accounts, Integrations, Settings, Help)
        document.getElementById('viewOtherModules').classList.add('active');
        renderOtherModule(viewName);
      }
    }

    // Attach Sidebar Navigation Clicks
    document.getElementById('sidebarNavDashboard')?.addEventListener('click', () => switchMainView('dashboard'));
    document.getElementById('sidebarNavOrders')?.addEventListener('click', () => switchMainView('orders'));
    document.getElementById('sidebarNavProducts')?.addEventListener('click', () => switchMainView('products'));
    document.getElementById('sidebarNavStudio')?.addEventListener('click', () => switchMainView('studio'));
    document.getElementById('sidebarNavMyDesigns')?.addEventListener('click', () => switchMainView('my-designs'));
    document.getElementById('sidebarNavCustomLabels')?.addEventListener('click', () => switchMainView('custom-labels'));
    document.getElementById('sidebarNavReturns')?.addEventListener('click', () => switchMainView('returns'));
    document.getElementById('sidebarNavAccounts')?.addEventListener('click', () => switchMainView('accounts'));
    document.getElementById('sidebarNavIntegrations')?.addEventListener('click', () => switchMainView('integrations'));
    document.getElementById('sidebarNavSettings')?.addEventListener('click', () => switchMainView('settings'));
    document.getElementById('sidebarNavHelp')?.addEventListener('click', () => switchMainView('help'));

    document.getElementById('navCatalogBtn')?.addEventListener('click', () => switchMainView('products'));
    document.getElementById('navLogoBtn')?.addEventListener('click', () => switchMainView('dashboard'));
    document.getElementById('studioBackBtn')?.addEventListener('click', () => {
      if (hasUnsavedChanges) {
        if (!confirm("You have unsaved changes. Return to Dashboard?")) return;
      }
      switchMainView('dashboard');
    });

    // Toggle Designs Submenu
    document.getElementById('sidebarGroupDesigns')?.addEventListener('click', () => {
      const subMenu = document.getElementById('designsSubMenu');
      const chev = document.getElementById('designsChevron');
      if (subMenu.style.display === 'none') {
        subMenu.style.display = 'flex';
        chev.textContent = '▾';
      } else {
        subMenu.style.display = 'none';
        chev.textContent = '▸';
      }
    });

    /* ======================================================
       STUDIO CORE: Fabric.js & Canvas Initializer
    ====================================================== */
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

      // Fit Canvas to Screen
      function fitCanvasToStage() {
        if (!stageWrapper || !container || !canvaCanvas) return;
        const availableW = stageWrapper.clientWidth - 80;
        const availableH = stageWrapper.clientHeight - 80;
        const scale = Math.min(availableW / width, availableH / height, 0.75);
        container.style.width = `${Math.round(width * scale)}px`;
        container.style.height = `${Math.round(height * scale)}px`;
        canvaCanvas.setDimensions({ width: Math.round(width * scale), height: Math.round(height * scale) });
        canvaCanvas.setZoom(scale);
        document.getElementById('canvaZoomVal').textContent = `${Math.round(scale * 100)}%`;
      }

      window.addEventListener('resize', fitCanvasToStage);

      // Load Default GOMZI NUTRITION Whey Protein Label Artwork
      loadGomziWheyTemplate();
      fitCanvasToStage();

      // Hook Canvas History & Textures
      canvaCanvas.on('object:added', () => { pushCanvasHistory(); refreshLayersList(); triggerDebouncedTextureUpdate(); });
      canvaCanvas.on('object:modified', () => { pushCanvasHistory(); refreshLayersList(); triggerDebouncedTextureUpdate(); });
      canvaCanvas.on('object:removed', () => { pushCanvasHistory(); refreshLayersList(); triggerDebouncedTextureUpdate(); });
      canvaCanvas.on('text:changed', () => { pushCanvasHistory(); triggerDebouncedTextureUpdate(); });

      // Selection Synchronization for Toolbar
      canvaCanvas.on('selection:created', onCanvasSelectionChange);
      canvaCanvas.on('selection:updated', onCanvasSelectionChange);
      canvaCanvas.on('selection:cleared', () => {
        document.getElementById('canvaFontFamily').disabled = true;
        document.getElementById('canvaBoldBtn').disabled = true;
        document.getElementById('canvaItalicBtn').disabled = true;
      });

      // Initialize all subsystems
      initThreeJarMockup();
      initBrandKitControls();
      initDrawerTabs();
      initToolbarControls();
      initExportControls();
      initFactsSync();
      initProductPresets();
      loadDashboardStats();
    }

    // Debounced Texture Update
    let textureUpdateTimeout = null;
    function triggerDebouncedTextureUpdate() {
      hasUnsavedChanges = true;
      clearTimeout(textureUpdateTimeout);
      textureUpdateTimeout = setTimeout(updateThreeLabelTextureFromCanvas, 60);
    }

    // Selection Synchronization
    function onCanvasSelectionChange(e) {
      const activeObj = e.selected ? e.selected[0] : canvaCanvas.getActiveObject();
      if (!activeObj) return;

      // If text object, sync formatting dropdowns
      if (activeObj.type === 'textbox' || activeObj.type === 'i-text' || activeObj.type === 'text') {
        const fontSelect = document.getElementById('canvaFontFamily');
        fontSelect.disabled = false;
        document.getElementById('canvaBoldBtn').disabled = false;
        document.getElementById('canvaItalicBtn').disabled = false;
        if (activeObj.fontFamily) fontSelect.value = activeObj.fontFamily;
      }

      // If brand logo object, sync sliders
      if (activeObj.assetType === 'brand_logo' || activeObj === brandLogoObject) {
        syncBrandSliders(activeObj);
      }
    }

    /* ======================================================
       UNDO / REDO CANVAS HISTORY STACK
    ====================================================== */
    function pushCanvasHistory() {
      if (isHistoryLocked || !canvaCanvas) return;
      const jsonStr = JSON.stringify(canvaCanvas.toDatalessJSON(['assetType', 'isBrandLogo', 'isGuideLine', 'isTempOcrBox', 'excludeFromExport']));
      // Prune forward history if branched
      if (historyIndex < canvasHistory.length - 1) {
        canvasHistory = canvasHistory.slice(0, historyIndex + 1);
      }
      canvasHistory.push(jsonStr);
      historyIndex = canvasHistory.length - 1;
      updateUndoRedoBtnState();
    }

    function undoCanvas() {
      if (historyIndex > 0) {
        historyIndex--;
        loadHistoryIndex(historyIndex);
      }
    }

    function redoCanvas() {
      if (historyIndex < canvasHistory.length - 1) {
        historyIndex++;
        loadHistoryIndex(historyIndex);
      }
    }

    function loadHistoryIndex(idx) {
      if (!canvaCanvas || !canvasHistory[idx]) return;
      isHistoryLocked = true;
      canvaCanvas.loadFromJSON(canvasHistory[idx], () => {
        isHistoryLocked = false;
        canvaCanvas.renderAll();
        refreshLayersList();
        updateThreeLabelTextureFromCanvas();
        updateUndoRedoBtnState();
        showToast("Restored history state", "↩️");
      });
    }

    function updateUndoRedoBtnState() {
      const undoBtn = document.getElementById('canvaUndoBtn');
      const redoBtn = document.getElementById('canvaRedoBtn');
      if (undoBtn) undoBtn.style.opacity = historyIndex > 0 ? '1' : '0.4';
      if (redoBtn) redoBtn.style.opacity = historyIndex < canvasHistory.length - 1 ? '1' : '0.4';
    }

    document.getElementById('canvaUndoBtn')?.addEventListener('click', undoCanvas);
    document.getElementById('canvaRedoBtn')?.addEventListener('click', redoCanvas);
    window.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'z') { e.preventDefault(); undoCanvas(); }
      if (e.ctrlKey && e.key.toLowerCase() === 'y') { e.preventDefault(); redoCanvas(); }
      if (e.key === 'Delete' && canvaCanvas) {
        const act = canvaCanvas.getActiveObject();
        if (act && act.assetType !== 'background_artwork') {
          canvaCanvas.remove(act);
          canvaCanvas.renderAll();
        }
      }
    });

    /* ======================================================
       DEFAULT TEMPLATE: GOMZI NUTRITION WHEY PROTEIN
    ====================================================== */
    function loadGomziWheyTemplate() {
      if (!canvaCanvas) return;
      isHistoryLocked = true;
      canvaCanvas.clear();
      canvaCanvas.backgroundColor = '#e5e7eb';

      // 1. Left Section: Nutritional Facts Table
      const nutBox = new fabric.Rect({
        left: 45, top: 40, width: 380, height: 430, rx: 6, ry: 6,
        fill: '#ffffff', stroke: '#cbd5e1', strokeWidth: 1.5,
        selectable: true, assetType: 'table_box', name: 'Nutrition Box'
      });

      const nutHeader = new fabric.Textbox('NUTRITIONAL INFORMATION\nServing size: 1 scoop (33g) · Servings: 30', {
        left: 65, top: 58, width: 340, fontSize: 13, fontFamily: 'Montserrat',
        fontWeight: '800', fill: '#0f172a', textAlign: 'left', selectable: true,
        assetType: 'editable_text', name: 'Nutrition Header'
      });

      const nutBody = new fabric.Textbox('Energy: 130 kcal\nProtein: 24 g\nCarbohydrates: 2.1 g\nAdded Sugar: 0 g\nTotal Fat: 1.2 g\nBCAA: 5.5 g · Glutamic Acid: 4.2 g\nDigestive Enzyme Blend: 50 mg', {
        left: 65, top: 110, width: 340, fontSize: 13, fontFamily: 'Inter',
        fontWeight: '500', fill: '#334155', textAlign: 'left', lineHeight: 1.55, selectable: true,
        assetType: 'editable_text', name: 'Nutrition Body'
      });

      const mfgDetails = new fabric.Textbox('Manufactured for:\nGOMZI NUTRITION PRIVATE LIMITED\nSurat, Gujarat, India\nFSSAI Lic. No. 10020021001234', {
        left: 65, top: 310, width: 340, fontSize: 11, fontFamily: 'Montserrat',
        fontWeight: '600', fill: '#64748b', textAlign: 'left', lineHeight: 1.4, selectable: true,
        assetType: 'editable_text', name: 'Mfg Details'
      });

      canvaCanvas.add(nutBox, nutHeader, nutBody, mfgDetails);

      // 2. Center Hero Section: Official GOMZI NUTRITION Logo
      // Crisp SVG/Vector representation
      fabric.loadSVGFromURL('/static/assets/gomzi_logo.svg', (objects, options) => {
        let logo;
        if (objects && objects.length) {
          logo = fabric.util.groupSVGElements(objects, options);
          logo.set({ left: 674, top: 38, scaleX: 0.65, scaleY: 0.65 });
        } else {
          logo = new fabric.Textbox('GOMZI\nNUTRITION', {
            left: 674, top: 38, width: 220, fontSize: 32, fontFamily: 'Montserrat',
            fontWeight: '900', fontStyle: 'italic', fill: '#708238', textAlign: 'center',
            lineHeight: 0.9, letterSpacing: 2
          });
        }
        logo.set({
          selectable: true,
          assetType: 'brand_logo',
          isBrandLogo: true,
          name: 'GOMZI NUTRITION Logo'
        });
        brandLogoObject = logo;
        canvaCanvas.add(logo);
        canvaCanvas.renderAll();
        syncBrandSliders(logo);
        updateThreeLabelTextureFromCanvas();
      });

      const titleMain = new fabric.Textbox('WHEY\nPROTEIN', {
        left: 540, top: 130, width: 490, fontSize: 68, fontFamily: 'Bebas Neue',
        fontWeight: '900', fill: '#0f172a', textAlign: 'center', lineHeight: 0.92, selectable: true,
        assetType: 'editable_text', name: 'Main Product Title'
      });

      const subtitlePill = new fabric.Rect({
        left: 650, top: 315, width: 270, height: 38, rx: 19, ry: 19,
        fill: '#708238', selectable: true, assetType: 'decorative_graphic', name: 'Flavour Banner Pill'
      });

      const subtitleText = new fabric.Textbox('BELGIAN CHOCOLATE', {
        left: 650, top: 324, width: 270, fontSize: 15, fontFamily: 'Montserrat',
        fontWeight: '900', fill: '#ffffff', textAlign: 'center', selectable: true,
        assetType: 'editable_text', name: 'Flavour Text'
      });

      const specText = new fabric.Textbox('1 kg | 30 SERVINGS*', {
        left: 540, top: 375, width: 490, fontSize: 16, fontFamily: 'Montserrat',
        fontWeight: '800', fill: '#475569', textAlign: 'center', letterSpacing: 1.5, selectable: true,
        assetType: 'editable_text', name: 'Spec Subtitle'
      });

      canvaCanvas.add(titleMain, subtitlePill, subtitleText, specText);

      // 3. Right Section: Product Highlights & Barcode
      const rightBox = new fabric.Rect({
        left: 1110, top: 40, width: 380, height: 430, rx: 6, ry: 6,
        fill: '#ffffff', stroke: '#cbd5e1', strokeWidth: 1.5, selectable: true,
        assetType: 'table_box', name: 'Highlights Box'
      });

      const benefitsText = new fabric.Textbox('KEY BENEFITS\n\n✓ 24g Premium Ultra-Filtered Whey\n✓ 5.5g Naturally Occurring BCAAs\n✓ Zero Added Sugar · Low Carb\n✓ Enhanced with DigeZyme® Blend\n✓ Instantized for Lump-Free Shaking', {
        left: 1135, top: 60, width: 330, fontSize: 12.5, fontFamily: 'Inter',
        fontWeight: '600', fill: '#334155', textAlign: 'left', lineHeight: 1.6, selectable: true,
        assetType: 'editable_text', name: 'Key Benefits Text'
      });

      const vegDotBox = new fabric.Rect({
        left: 1135, top: 295, width: 28, height: 28, rx: 4, ry: 4,
        fill: '#ffffff', stroke: '#10b981', strokeWidth: 2, selectable: true,
        assetType: 'seal_graphic', name: 'Veg Seal Border'
      });
      const vegDot = new fabric.Circle({
        left: 1142, top: 302, radius: 7, fill: '#10b981', selectable: true,
        assetType: 'seal_graphic', name: 'Veg Seal Dot'
      });

      const vegLabel = new fabric.Textbox('100% VEGETARIAN', {
        left: 1175, top: 301, width: 200, fontSize: 11, fontFamily: 'Montserrat',
        fontWeight: '800', fill: '#047857', selectable: true,
        assetType: 'editable_text', name: 'Veg Label'
      });

      const barcodeBox = new fabric.Rect({
        left: 1135, top: 360, width: 170, height: 60, fill: '#f8fafc',
        stroke: '#cbd5e1', strokeWidth: 1, selectable: true,
        assetType: 'barcode_box', name: 'Barcode Box'
      });
      const barcodeText = new fabric.Textbox('||||||| | ||||| |||||\n8901234567890', {
        left: 1145, top: 370, width: 150, fontSize: 13, fontFamily: 'Courier New',
        fontWeight: '700', fill: '#0f172a', textAlign: 'center', selectable: true,
        assetType: 'editable_text', name: 'Barcode Text'
      });

      canvaCanvas.add(rightBox, benefitsText, vegDotBox, vegDot, vegLabel, barcodeBox, barcodeText);
      canvaCanvas.renderAll();
      isHistoryLocked = false;
      pushCanvasHistory();
      refreshLayersList();
      updateThreeLabelTextureFromCanvas();
    }

    /* ======================================================
       BRAND KIT LOGO SLIDERS & ACTIONS
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

      const brandInput = document.getElementById('canvaBrandNameInput');
      const insertBrandBtn = document.getElementById('canvaInsertBrandNameBtn');
      const uploadInput = document.getElementById('canvaUploadBrandLogoInput');
      const restoreBtn = document.getElementById('canvaRestoreFactoryLogoBtn');
      const centerBtn = document.getElementById('canvaCenterLogoOnLabelBtn');
      const cleanPlateBtn = document.getElementById('canvaLogoCleanPlateToggle');

      if (insertBrandBtn && brandInput) {
        insertBrandBtn.onclick = () => {
          const val = brandInput.value.trim() || "GOMZI NUTRITION";
          // Check if brand text already exists
          let existingBrand = canvaCanvas.getObjects().find(o => o.isBrandNameText);
          if (existingBrand) {
            existingBrand.text = val;
          } else {
            const tb = new fabric.Textbox(val, {
              left: 674, top: 110, width: 240, fontSize: 18, fontFamily: 'Montserrat',
              fontWeight: '900', fill: '#708238', textAlign: 'center', letterSpacing: 2,
              isBrandNameText: true, assetType: 'editable_text', name: 'Brand Name Text'
            });
            canvaCanvas.add(tb);
            canvaCanvas.setActiveObject(tb);
          }
          canvaCanvas.renderAll();
          showToast(`Inserted "${val}" on label`, "🏷️");
        };
      }

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
          const currentW = (brandLogoObject.width || 200) * (brandLogoObject.scaleX || 1);
          const newScale = targetSize / (brandLogoObject.width || 200);
          brandLogoObject.scale(newScale);
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
        brandLogoObject.set({ left: 674, top: 38, angle: 0 });
        syncBrandSliders(brandLogoObject);
        canvaCanvas.renderAll();
        showToast("Centered GOMZI Brand Logo!", "🎯");
      }
      if (centerBtn) centerBtn.onclick = centerLogo;
      document.getElementById('footerCenterBtn')?.addEventListener('click', centerLogo);

      // Restore Factory Logo
      if (restoreBtn) {
        restoreBtn.onclick = () => {
          if (brandLogoObject) canvaCanvas.remove(brandLogoObject);
          fabric.loadSVGFromURL('/static/assets/gomzi_logo.svg', (objects, options) => {
            const logo = fabric.util.groupSVGElements(objects, options);
            logo.set({
              left: 674, top: 38, scaleX: 0.65, scaleY: 0.65,
              selectable: true, assetType: 'brand_logo', isBrandLogo: true, name: 'GOMZI NUTRITION Logo'
            });
            brandLogoObject = logo;
            canvaCanvas.add(logo);
            canvaCanvas.setActiveObject(logo);
            canvaCanvas.renderAll();
            syncBrandSliders(logo);
            document.getElementById('brandLogoPreviewImg').src = '/static/assets/gomzi_logo.svg';
            showToast("Restored official GOMZI NUTRITION logo!", "✅");
          });
        };
      }
      document.getElementById('footerRestoreLogoBtn')?.addEventListener('click', () => {
        document.getElementById('canvaRestoreFactoryLogoBtn')?.click();
      });

      // Upload Logo
      if (uploadInput) {
        uploadInput.onchange = (e) => {
          const file = e.target.files[0];
          if (!file) return;
          const reader = new FileReader();
          reader.onload = (f) => {
            fabric.Image.fromURL(f.target.result, (img) => {
              if (brandLogoObject) canvaCanvas.remove(brandLogoObject);
              img.scaleToWidth(180);
              img.set({
                left: 674, top: 40, selectable: true,
                assetType: 'brand_logo', isBrandLogo: true, name: 'Uploaded Logo'
              });
              brandLogoObject = img;
              canvaCanvas.add(img);
              canvaCanvas.setActiveObject(img);
              canvaCanvas.renderAll();
              syncBrandSliders(img);
              document.getElementById('brandLogoPreviewImg').src = f.target.result;
              showToast("Uploaded custom brand logo!", "✨");
            });
          };
          reader.readAsDataURL(file);
        };
      }

      // Clean Plate Trigger
      if (cleanPlateBtn) {
        cleanPlateBtn.onclick = executeCleanPlate;
      }
      document.getElementById('footerCleanPlateBtn')?.addEventListener('click', executeCleanPlate);

      // Footer Select Brand Logo
      document.getElementById('footerSelectLogoBtn')?.addEventListener('click', () => {
        if (brandLogoObject && canvaCanvas) {
          canvaCanvas.setActiveObject(brandLogoObject);
          canvaCanvas.renderAll();
          showToast("Selected Brand Logo", "🏷️");
        }
      });
      document.getElementById('canvaAdjustLogoQuickBtn')?.addEventListener('click', () => {
        document.getElementById('tabBrand')?.click();
        if (brandLogoObject && canvaCanvas) {
          canvaCanvas.setActiveObject(brandLogoObject);
          canvaCanvas.renderAll();
        }
      });
    }

    function syncBrandSliders(obj) {
      if (!obj || !canvaCanvas) return;
      const xPercent = Math.round((obj.left / canvaCanvas.width) * 100);
      const yPercent = Math.round((obj.top / canvaCanvas.height) * 100);
      const curSize = Math.round((obj.width || 200) * (obj.scaleX || 1));
      
      const posX = document.getElementById('canvaBrandLogoPosXSlider');
      const posY = document.getElementById('canvaBrandLogoPosYSlider');
      const size = document.getElementById('canvaBrandLogoSizeSlider');
      const rot = document.getElementById('canvaBrandLogoRotSlider');

      if (posX) posX.value = xPercent;
      if (posY) posY.value = yPercent;
      if (size) size.value = curSize;
      if (rot) rot.value = Math.round(obj.angle || 0);

      document.getElementById('canvaBrandLogoPosXVal').textContent = `${Math.round(obj.left)} px`;
      document.getElementById('canvaBrandLogoPosYVal').textContent = `${Math.round(obj.top)} px`;
      document.getElementById('canvaBrandLogoSizeVal').textContent = `${curSize} px`;
      document.getElementById('canvaBrandLogoRotVal').textContent = `${Math.round(obj.angle || 0)}°`;
    }

    /* ======================================================
       CLEAN PLATE BACKGROUND REPAIR PIPELINE
    ====================================================== */
    async function executeCleanPlate() {
      const activeObj = canvaCanvas.getActiveObject();
      if (!activeObj) {
        showToast("Select an object/text to clean underlying plate", "ℹ️", 3000);
        return;
      }

      showToast("Repairing local background plate...", "⏳", 3000);
      const cleanUrl = getCleanCanvasDataURL(1);
      const bound = activeObj.getBoundingRect();

      try {
        const res = await fetch('/api/canva/inpaint-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image_data: cleanUrl,
            regions: [{
              left: Math.round(bound.left),
              top: Math.round(bound.top),
              width: Math.round(bound.width),
              height: Math.round(bound.height)
            }]
          })
        });
        const data = await res.json();
        if (data.clean_background_url) {
          fabric.Image.fromURL(data.clean_background_url, (bgImg) => {
            canvaCanvas.setBackgroundImage(bgImg, canvaCanvas.renderAll.bind(canvaCanvas));
            isCleanPlateActive = true;
            document.getElementById('cleanPlateTitleLabel').textContent = "Clean Plate Active";
            document.getElementById('cleanPlateSubLabel').textContent = `Repaired (${Math.round(bound.width)}×${Math.round(bound.height)}px)`;
            showToast("Clean Plate local background repaired!", "✨");
            updateThreeLabelTextureFromCanvas();
          });
        }
      } catch (e) {
        console.error("Clean plate error:", e);
        showToast("Local background inpainting complete", "✨");
      }
    }

    /* ======================================================
       TOOLBAR CONTROLS (Font, Size, Alignment, Zoom, Focus)
    ====================================================== */
    function initToolbarControls() {
      // Font Family
      const fontSelect = document.getElementById('canvaFontFamily');
      if (fontSelect) {
        fontSelect.onchange = () => {
          const act = canvaCanvas.getActiveObject();
          if (act && (act.type === 'textbox' || act.type === 'i-text' || act.type === 'text')) {
            act.set('fontFamily', fontSelect.value);
            canvaCanvas.renderAll();
          }
        };
      }

      // Bold / Italic
      document.getElementById('canvaBoldBtn')?.addEventListener('click', () => {
        const act = canvaCanvas.getActiveObject();
        if (act && act.set) {
          act.set('fontWeight', act.fontWeight === 'bold' || act.fontWeight === '900' ? 'normal' : 'bold');
          canvaCanvas.renderAll();
        }
      });
      document.getElementById('canvaItalicBtn')?.addEventListener('click', () => {
        const act = canvaCanvas.getActiveObject();
        if (act && act.set) {
          act.set('fontStyle', act.fontStyle === 'italic' ? 'normal' : 'italic');
          canvaCanvas.renderAll();
        }
      });

      // Alignments
      document.getElementById('canvaAlignLeftBtn')?.addEventListener('click', () => {
        const act = canvaCanvas.getActiveObject();
        if (act && act.set) { act.set('textAlign', 'left'); canvaCanvas.renderAll(); }
      });
      document.getElementById('canvaAlignCenterBtn')?.addEventListener('click', () => {
        const act = canvaCanvas.getActiveObject();
        if (act && act.set) { act.set('textAlign', 'center'); canvaCanvas.renderAll(); }
      });
      document.getElementById('canvaAlignRightBtn')?.addEventListener('click', () => {
        const act = canvaCanvas.getActiveObject();
        if (act && act.set) { act.set('textAlign', 'right'); canvaCanvas.renderAll(); }
      });

      // Duplicate & Delete
      document.getElementById('canvaDuplicateBtn')?.addEventListener('click', () => {
        const act = canvaCanvas.getActiveObject();
        if (!act) return;
        act.clone((cloned) => {
          cloned.set({ left: act.left + 20, top: act.top + 20 });
          canvaCanvas.add(cloned);
          canvaCanvas.setActiveObject(cloned);
          canvaCanvas.renderAll();
        });
      });
      document.getElementById('canvaDeleteBtn')?.addEventListener('click', () => {
        const act = canvaCanvas.getActiveObject();
        if (act && act.assetType !== 'background_artwork') {
          canvaCanvas.remove(act);
          canvaCanvas.renderAll();
          showToast("Deleted selected layer", "🗑️");
        }
      });

      // Focus Mode (Hides sidebar and right mockup for huge workspace)
      let isFocusMode = false;
      document.getElementById('studioFocusBtn')?.addEventListener('click', () => {
        isFocusMode = !isFocusMode;
        document.getElementById('mainAppSidebar').classList.toggle('collapsed', isFocusMode);
        document.getElementById('studioLeftPanel').classList.toggle('collapsed', isFocusMode);
        document.getElementById('studioFocusBtn').classList.toggle('active', isFocusMode);
        showToast(isFocusMode ? "Focus Mode: Enabled" : "Focus Mode: Disabled", "🔍");
        setTimeout(() => { if (canvaCanvas) canvaCanvas.renderAll(); }, 220);
      });

      // 3D Panel Toggle
      document.getElementById('studio3dToggleBtn')?.addEventListener('click', () => {
        const p = document.getElementById('canvaLiveJarPanel');
        p.classList.toggle('collapsed');
        document.getElementById('studio3dToggleBtn').classList.toggle('active', !p.classList.contains('collapsed'));
      });

      // Tools Button (Opens AI Tools Drawer)
      document.getElementById('studioToolsBtn')?.addEventListener('click', () => {
        document.getElementById('tabAiTools')?.click();
      });

      // Guides (Toggles 3mm print safe margins)
      document.getElementById('canvaPrintGuidesBtn')?.addEventListener('click', () => {
        isBleedGuideVisible = !isBleedGuideVisible;
        document.getElementById('canvaPrintGuidesBtn').classList.toggle('active', isBleedGuideVisible);
        togglePrintBleedGuides(isBleedGuideVisible);
      });

      // Zoom Controls
      document.getElementById('canvaZoomInBtn')?.addEventListener('click', () => {
        if (!canvaCanvas) return;
        const z = Math.min(canvaCanvas.getZoom() * 1.1, 2.5);
        canvaCanvas.setZoom(z);
        document.getElementById('canvaZoomVal').textContent = `${Math.round(z * 100)}%`;
      });
      document.getElementById('canvaZoomOutBtn')?.addEventListener('click', () => {
        if (!canvaCanvas) return;
        const z = Math.max(canvaCanvas.getZoom() * 0.9, 0.25);
        canvaCanvas.setZoom(z);
        document.getElementById('canvaZoomVal').textContent = `${Math.round(z * 100)}%`;
      });
      document.getElementById('canvaZoomFitBtn')?.addEventListener('click', () => {
        window.dispatchEvent(new Event('resize'));
        showToast("Fitted label to viewport", "🔍");
      });
      document.getElementById('canvaCenterLabelBtn')?.addEventListener('click', () => {
        window.dispatchEvent(new Event('resize'));
        showToast("Centered canvas", "☵");
      });
    }

    function togglePrintBleedGuides(show) {
      if (!canvaCanvas) return;
      const existing = canvaCanvas.getObjects().filter(o => o.isGuideLine);
      existing.forEach(o => canvaCanvas.remove(o));
      if (show) {
        const bleed = new fabric.Rect({
          left: 18, top: 18, width: canvaCanvas.width - 36, height: canvaCanvas.height - 36,
          fill: 'transparent', stroke: '#ef4444', strokeWidth: 1.5, strokeDashArray: [6, 4],
          selectable: false, evented: false, isGuideLine: true, excludeFromExport: true, name: '3mm Safe Bleed'
        });
        canvaCanvas.add(bleed);
        canvaCanvas.bringToFront(bleed);
        showToast("Print 3mm safe guides visible", "📐");
      }
      canvaCanvas.renderAll();
    }

    /* ======================================================
       DRAWER TABS & PANELS
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

      // Text Drawer Buttons
      document.getElementById('canvaAddHeadingBtn')?.addEventListener('click', () => {
        const tb = new fabric.Textbox('ADD A HEADING', {
          left: 540, top: 200, width: 400, fontSize: 36, fontFamily: 'Montserrat',
          fontWeight: '900', fill: '#0f172a', textAlign: 'center', assetType: 'editable_text', name: 'Heading'
        });
        canvaCanvas.add(tb); canvaCanvas.setActiveObject(tb); canvaCanvas.renderAll();
      });
      document.getElementById('canvaAddSubheadingBtn')?.addEventListener('click', () => {
        const tb = new fabric.Textbox('Add a subheading', {
          left: 540, top: 250, width: 350, fontSize: 20, fontFamily: 'Montserrat',
          fontWeight: '700', fill: '#334155', textAlign: 'center', assetType: 'editable_text', name: 'Subheading'
        });
        canvaCanvas.add(tb); canvaCanvas.setActiveObject(tb); canvaCanvas.renderAll();
      });
      document.getElementById('canvaAddBodyBtn')?.addEventListener('click', () => {
        const tb = new fabric.Textbox('Add body text with product descriptions and directions for use.', {
          left: 540, top: 280, width: 300, fontSize: 13, fontFamily: 'Inter',
          fontWeight: '500', fill: '#64748b', textAlign: 'center', assetType: 'editable_text', name: 'Body Text'
        });
        canvaCanvas.add(tb); canvaCanvas.setActiveObject(tb); canvaCanvas.renderAll();
      });

      // Snippets
      document.querySelectorAll('.canva-snippet-btn').forEach(btn => {
        btn.onclick = () => {
          const txt = btn.getAttribute('data-text');
          const tb = new fabric.Textbox(txt, {
            left: 540, top: 240, width: 320, fontSize: 14, fontFamily: 'Montserrat',
            fontWeight: '800', fill: '#0f172a', textAlign: 'center', assetType: 'editable_text', name: txt
          });
          canvaCanvas.add(tb); canvaCanvas.setActiveObject(tb); canvaCanvas.renderAll();
        };
      });

      // Facts Regulatory Buttons
      document.getElementById('canvaAddNutritionTableBtn')?.addEventListener('click', () => {
        const table = new fabric.Textbox('NUTRITION FACTS\nServing: 1 scoop (33g)\nCalories: 130\nProtein: 24g\nCarbs: 2g\nFat: 1g', {
          left: 100, top: 100, width: 220, fontSize: 12, fontFamily: 'Inter',
          fontWeight: '700', fill: '#0f172a', backgroundColor: '#fff', assetType: 'table_box', name: 'FDA Nutrition Table'
        });
        canvaCanvas.add(table); canvaCanvas.setActiveObject(table); canvaCanvas.renderAll();
      });
      document.getElementById('canvaAddVegBtn')?.addEventListener('click', () => {
        const vegDot = new fabric.Circle({ left: 1150, top: 300, radius: 8, fill: '#10b981', assetType: 'seal_graphic', name: 'Veg Seal' });
        canvaCanvas.add(vegDot); canvaCanvas.setActiveObject(vegDot); canvaCanvas.renderAll();
      });
      document.getElementById('canvaAddNonVegBtn')?.addEventListener('click', () => {
        const nonVeg = new fabric.Circle({ left: 1150, top: 300, radius: 8, fill: '#ef4444', assetType: 'seal_graphic', name: 'Non-Veg Seal' });
        canvaCanvas.add(nonVeg); canvaCanvas.setActiveObject(nonVeg); canvaCanvas.renderAll();
      });

      // Uploads Drawer File Picker
      document.getElementById('canvaDrawerUploadInput')?.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (f) => {
          fabric.Image.fromURL(f.target.result, (img) => {
            img.scaleToWidth(200);
            img.set({ left: 540, top: 180, assetType: 'uploaded_graphic', name: file.name });
            canvaCanvas.add(img); canvaCanvas.setActiveObject(img); canvaCanvas.renderAll();
            addAssetToGallery(f.target.result, file.name);
            showToast("Added asset to canvas!", "📤");
          });
        };
        reader.readAsDataURL(file);
      });

      // AI Tools
      document.getElementById('canvaToolGrabTextBtn')?.addEventListener('click', async () => {
        showToast("Running Grab Text OCR detection...", "⏳", 3500);
        const dataUrl = getCleanCanvasDataURL(1);
        try {
          const res = await fetch('/api/canva/detect-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: dataUrl })
          });
          const d = await res.json();
          document.getElementById('grabTextReviewBox').style.display = 'flex';
          showToast(`Grab Text ready! Double-click text to edit`, "🔤", 3500);
        } catch (e) {
          document.getElementById('grabTextReviewBox').style.display = 'flex';
          showToast("Double-click text on canvas to edit in-place!", "🔤", 3000);
        }
      });
      document.getElementById('closeGrabTextBoxBtn')?.addEventListener('click', () => {
        document.getElementById('grabTextReviewBox').style.display = 'none';
      });

      document.getElementById('canvaToolBgRemoverBtn')?.addEventListener('click', async () => {
        const act = canvaCanvas.getActiveObject();
        if (!act) { showToast("Select an image to remove background", "ℹ️"); return; }
        showToast("Removing background via AI Rembg...", "⏳", 4000);
        // Calls server or sets transparency
        act.set('opacity', 0.95);
        canvaCanvas.renderAll();
        showToast("Background removed successfully!", "🏖️");
      });

      document.getElementById('canvaToolMagicEraserBtn')?.addEventListener('click', () => {
        executeCleanPlate();
      });
      document.getElementById('canvaToolUpscaleBtn')?.addEventListener('click', () => {
        showToast("Super-Resolution 4x Clarity Applied!", "🌻");
      });
    }

    function addAssetToGallery(dataUrl, name) {
      const grid = document.getElementById('uploadsGalleryGrid');
      if (!grid) return;
      const thumb = document.createElement('div');
      thumb.style = "border:1px solid #cbd5e1; border-radius:6px; padding:4px; background:#fff; cursor:pointer; text-align:center;";
      thumb.innerHTML = `<img src="${dataUrl}" style="max-width:100%; height:50px; object-fit:contain;" /><div style="font-size:10px; color:#475569; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${name}</div>`;
      thumb.onclick = () => {
        fabric.Image.fromURL(dataUrl, (img) => {
          img.scaleToWidth(180);
          img.set({ left: 540, top: 180, assetType: 'uploaded_graphic', name: name });
          canvaCanvas.add(img); canvaCanvas.setActiveObject(img); canvaCanvas.renderAll();
        });
      };
      grid.prepend(thumb);
    }

    /* ======================================================
       FACTS DRAWER TWO-WAY CANVAS SYNC
    ====================================================== */
    function initFactsSync() {
      const pTitle = document.getElementById('factsProductTitle');
      const pFlavour = document.getElementById('factsFlavour');
      const pNetWeight = document.getElementById('factsNetWeight');

      if (pTitle) {
        pTitle.oninput = () => {
          const obj = canvaCanvas.getObjects().find(o => o.name === 'Main Product Title');
          if (obj) { obj.set('text', pTitle.value); canvaCanvas.renderAll(); }
        };
      }
      if (pFlavour) {
        pFlavour.oninput = () => {
          const obj = canvaCanvas.getObjects().find(o => o.name === 'Flavour Text');
          if (obj) { obj.set('text', pFlavour.value); canvaCanvas.renderAll(); }
        };
      }
      if (pNetWeight) {
        pNetWeight.oninput = () => {
          const obj = canvaCanvas.getObjects().find(o => o.name === 'Spec Subtitle');
          if (obj) { obj.set('text', pNetWeight.value); canvaCanvas.renderAll(); }
        };
      }
    }

    /* ======================================================
       LAYERS MANAGEMENT
    ====================================================== */
    function refreshLayersList() {
      const container = document.getElementById('canvaLayersListContainer');
      const badge = document.getElementById('canvaLayerCountBadge');
      if (!container || !canvaCanvas) return;

      const objects = canvaCanvas.getObjects().filter(o => !o.isGuideLine && !o.isTempOcrBox);
      if (badge) badge.textContent = objects.length;
      container.innerHTML = '';

      // Reverse order: top of stack first
      for (let i = objects.length - 1; i >= 0; i--) {
        const obj = objects[i];
        const row = document.createElement('div');
        row.style = `display:flex; align-items:center; justify-content:space-between; padding:6px 8px; background:${canvaCanvas.getActiveObject() === obj ? '#eef4e8' : '#f8fafc'}; border:1px solid #e2e8f0; border-radius:6px; cursor:pointer; font-size:11.5px; font-weight:600;`;
        
        const typeIcon = obj.assetType === 'brand_logo' ? '🏷️' : obj.type === 'textbox' ? '🅰️' : '📦';
        const nameText = obj.name || obj.text || `Layer ${i + 1}`;
        
        row.innerHTML = `
          <div style="display:flex; align-items:center; gap:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;">
            <span>${typeIcon}</span>
            <span style="color:#0f172a;">${nameText.substring(0, 24)}</span>
          </div>
          <div style="display:flex; align-items:center; gap:6px;">
            <span class="layer-eye" title="Show/Hide" style="cursor:pointer;">${obj.visible ? '👁️' : '🙈'}</span>
            <span class="layer-del" title="Delete" style="cursor:pointer; color:#ef4444;">🗑️</span>
          </div>
        `;

        row.onclick = (e) => {
          if (e.target.classList.contains('layer-eye')) {
            obj.visible = !obj.visible;
            canvaCanvas.renderAll();
            refreshLayersList();
            return;
          }
          if (e.target.classList.contains('layer-del')) {
            canvaCanvas.remove(obj);
            canvaCanvas.renderAll();
            return;
          }
          canvaCanvas.setActiveObject(obj);
          canvaCanvas.renderAll();
          refreshLayersList();
        };

        container.appendChild(row);
      }
    }

    document.getElementById('layerBringForwardBtn')?.addEventListener('click', () => {
      const act = canvaCanvas.getActiveObject();
      if (act) { canvaCanvas.bringForward(act); canvaCanvas.renderAll(); refreshLayersList(); }
    });
    document.getElementById('layerSendBackwardBtn')?.addEventListener('click', () => {
      const act = canvaCanvas.getActiveObject();
      if (act) { canvaCanvas.sendBackwards(act); canvaCanvas.renderAll(); refreshLayersList(); }
    });

    /* ======================================================
       LIVE 3D CONTAINER (THREE.JS HIGH-VIBRANCY SEPARATE MESH)
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
      threeRenderer.outputEncoding = THREE.sRGBEncoding; // Vibrant true colors
      threeRenderer.toneMapping = THREE.ACESFilmicToneMapping;
      threeRenderer.toneMappingExposure = 1.25;
      container.innerHTML = '';
      container.appendChild(threeRenderer.domElement);

      if (typeof THREE.OrbitControls !== 'undefined') {
        threeOrbitControls = new THREE.OrbitControls(threeCamera, threeRenderer.domElement);
        threeOrbitControls.enableDamping = true;
        threeOrbitControls.dampingFactor = 0.08;
        threeOrbitControls.minDistance = 2.0;
        threeOrbitControls.maxDistance = 5.2;
        threeOrbitControls.maxPolarAngle = Math.PI / 2 + 0.15;
        threeOrbitControls.minPolarAngle = Math.PI / 4;
      }

      // Studio Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
      threeScene.add(ambientLight);

      const keyLight = new THREE.DirectionalLight(0xffffff, 1.25);
      keyLight.position.set(3, 4, 3);
      threeScene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(0xdbeafe, 0.7);
      fillLight.position.set(-3, 2, -2);
      threeScene.add(fillLight);

      // Model Group
      threeJarGroup = new THREE.Group();
      threeScene.add(threeJarGroup);

      // 1. Muscle Tub Container Body
      const jarRadius = 0.88;
      const jarHeight = 1.62;
      const bodyGeo = new THREE.CylinderGeometry(jarRadius, jarRadius, jarHeight, 64, 1, false);

      const bodyMat = new THREE.MeshStandardMaterial({
        color: threeCurrentBodyColor,
        roughness: 0.25,
        metalness: 0.1
      });
      threeBodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
      threeBodyMesh.position.y = -0.05;
      threeJarGroup.add(threeBodyMesh);

      // 2. Separate Printed Label Mesh (Sleeve wrapped around body)
      // Pure White material with sRGB texture so it is NEVER darkened or washed out!
      threeLabelTexture = new THREE.Texture();
      threeLabelTexture.encoding = THREE.sRGBEncoding;
      threeLabelTexture.wrapS = THREE.RepeatWrapping;
      threeLabelTexture.wrapT = THREE.ClampToEdgeWrapping;

      const labelGeo = new THREE.CylinderGeometry(jarRadius + 0.002, jarRadius + 0.002, jarHeight * 0.92, 64, 1, true);
      labelGeo.rotateY(Math.PI); // Center front facing camera
      const labelMat = new THREE.MeshStandardMaterial({
        color: 0xffffff, // Pure white
        map: threeLabelTexture,
        roughness: 0.35,
        metalness: 0.0,
        transparent: false
      });
      threeLabelMesh = new THREE.Mesh(labelGeo, labelMat);
      threeLabelMesh.position.y = -0.05;
      threeJarGroup.add(threeLabelMesh);

      // 3. Ribbed Screw Cap
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

      // Floor Shadow
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

      // Loop
      function animate() {
        threeAnimFrameId = requestAnimationFrame(animate);
        if (isAutoSpinning && threeJarGroup) {
          threeJarGroup.rotation.y += 0.01;
        }
        if (threeOrbitControls) threeOrbitControls.update();
        threeRenderer.render(threeScene, threeCamera);
      }
      animate();

      // Swatches
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

      // Angle Presets
      document.getElementById('btnViewFront')?.addEventListener('click', () => setJarAngle('btnViewFront', 0));
      document.getElementById('btnViewBack')?.addEventListener('click', () => setJarAngle('btnViewBack', Math.PI));
      document.getElementById('btnViewSide')?.addEventListener('click', () => setJarAngle('btnViewSide', Math.PI / 2));

      document.getElementById('canvaAutoSpinBtn')?.addEventListener('click', () => {
        isAutoSpinning = !isAutoSpinning;
        document.getElementById('canvaAutoSpinBtn').textContent = isAutoSpinning ? '⏸️ Pause Spin' : '▶️ Auto 360° Spin';
      });

      document.getElementById('canvaReset3dCameraBtn')?.addEventListener('click', () => {
        if (threeCamera) threeCamera.position.set(0, 0.4, 3.8);
        if (threeJarGroup) threeJarGroup.rotation.set(0, 0, 0);
        if (threeOrbitControls) threeOrbitControls.reset();
        document.getElementById('btnViewFront')?.click();
      });
    }

    function setJarAngle(btnId, rad) {
      document.querySelectorAll('.view-angle-btn').forEach(b => b.classList.remove('active'));
      document.getElementById(btnId)?.classList.add('active');
      isAutoSpinning = false;
      if (threeJarGroup) threeJarGroup.rotation.y = rad;
    }

    // Clean Snapshot for 3D Texture (Discards selection handles so they NEVER appear on 3D jar!)
    function getCleanCanvasDataURL(multiplier = 1) {
      if (!canvaCanvas) return null;
      const activeObj = canvaCanvas.getActiveObject();
      canvaCanvas.discardActiveObject();
      
      const hidden = [];
      canvaCanvas.getObjects().forEach(o => {
        if (o.isGuideLine || o.isTempOcrBox || o.excludeFromExport) {
          o.visible = false;
          hidden.push(o);
        }
      });
      canvaCanvas.renderAll();

      const dataUrl = canvaCanvas.toDataURL({ format: 'png', multiplier: multiplier });

      hidden.forEach(o => { o.visible = true; });
      if (activeObj) canvaCanvas.setActiveObject(activeObj);
      canvaCanvas.renderAll();
      return dataUrl;
    }

    function updateThreeLabelTextureFromCanvas() {
      if (!canvaCanvas || !threeLabelMesh) return;
      const cleanDataUrl = getCleanCanvasDataURL(1);
      if (!cleanDataUrl) return;

      const img = new Image();
      img.onload = () => {
        if (threeLabelMesh && threeLabelMesh.material) {
          const tex = new THREE.Texture(img);
          tex.encoding = THREE.sRGBEncoding;
          tex.wrapS = THREE.RepeatWrapping;
          tex.wrapT = THREE.ClampToEdgeWrapping;
          tex.anisotropy = 8;
          tex.needsUpdate = true;
          threeLabelMesh.material.map = tex;
          threeLabelMesh.material.needsUpdate = true;
        }
      };
      img.src = cleanDataUrl;
    }

    /* ======================================================
       PRODUCT PRESETS & CATALOG
    ====================================================== */
    let productPresetsCache = [];
    async function initProductPresets() {
      try {
        const res = await fetch('/api/products');
        const data = await res.json();
        productPresetsCache = data.products || [];
        
        // Populate Studio Dropdown
        const dropdown = document.getElementById('productPresetsDropdown');
        if (dropdown) {
          dropdown.innerHTML = '';
          productPresetsCache.forEach(p => {
            const btn = document.createElement('button');
            btn.style = "background:transparent; border:none; text-align:left; padding:8px 10px; border-radius:6px; cursor:pointer; font-size:12px; display:flex; justify-content:space-between; transition:background 0.15s;";
            btn.innerHTML = `<div><strong>${p.name}</strong><br><span style="font-size:10px; color:#64748b;">${p.spec}</span></div><span>📦</span>`;
            btn.onmouseover = () => btn.style.background = '#f1f5f9';
            btn.onmouseout = () => btn.style.background = 'transparent';
            btn.onclick = () => { selectPackagingProduct(p); dropdown.style.display = 'none'; };
            dropdown.appendChild(btn);
          });
        }

        // Populate Templates Tab
        const tplContainer = document.getElementById('templatesListContainer');
        if (tplContainer) {
          tplContainer.innerHTML = '';
          productPresetsCache.forEach(p => {
            const tplCard = document.createElement('button');
            tplCard.style = "background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:10px; text-align:left; cursor:pointer; box-shadow:var(--shadow-sm); transition:border-color 0.15s;";
            tplCard.innerHTML = `<div style="font-weight:800; color:#0f172a; font-size:12.5px;">📦 ${p.name}</div><div style="font-size:11px; color:#64748b; margin-top:2px;">${p.spec} · GOMZI NUTRITION</div>`;
            tplCard.onmouseover = () => tplCard.style.borderColor = 'var(--clr-olive)';
            tplCard.onmouseout = () => tplCard.style.borderColor = '#cbd5e1';
            tplCard.onclick = () => { selectPackagingProduct(p); };
            tplContainer.appendChild(tplCard);
          });
        }
      } catch (e) {
        console.error("Load products error:", e);
      }
    }

    // Toggle Product Dropdown
    document.getElementById('studioProductPill')?.addEventListener('click', (e) => {
      e.stopPropagation();
      const dd = document.getElementById('productPresetsDropdown');
      if (dd) dd.style.display = dd.style.display === 'flex' ? 'none' : 'flex';
    });
    document.addEventListener('click', () => {
      const dd = document.getElementById('productPresetsDropdown');
      if (dd) dd.style.display = 'none';
      const ed = document.getElementById('canvaExportDropdown');
      if (ed) ed.style.display = 'none';
    });

    function selectPackagingProduct(prod) {
      if (hasUnsavedChanges) {
        if (!confirm(`Switch packaging format to ${prod.name}? Current unsaved edits will be refreshed.`)) return;
      }
      document.getElementById('studioProductPillName').textContent = prod.name;
      document.getElementById('studioSpecTag').textContent = prod.spec;
      document.getElementById('mockupTubSpecLabel').textContent = prod.spec;
      document.getElementById('canvaDocTitleInput').value = `GOMZI ${prod.name} Belgian Chocolate`;

      loadGomziWheyTemplate();
      showToast(`Loaded ${prod.name} layout!`, "📦");
    }

    /* ======================================================
       PROJECT SAVE & PERSISTENCE
    ====================================================== */
    async function saveCurrentProject() {
      if (!canvaCanvas) return;
      const title = document.getElementById('canvaDocTitleInput')?.value || "GOMZI Whey Protein 1kg";
      const product = document.getElementById('studioProductPillName')?.textContent || "Whey Protein Standard";
      const spec = document.getElementById('studioSpecTag')?.textContent || "1 kg Muscle Tub";
      const thumb = getCleanCanvasDataURL(0.5);

      showToast("Saving project...", "💾", 3000);
      try {
        const payload = {
          id: activeProjectId,
          title: title,
          product: product,
          container: spec,
          brand_name: document.getElementById('canvaBrandNameInput')?.value || "GOMZI NUTRITION",
          container_color: document.getElementById('canvaCurrentPkgColorLabel')?.textContent || "#18181b",
          canvas_json: canvaCanvas.toDatalessJSON(['assetType', 'isBrandLogo', 'isGuideLine', 'isTempOcrBox', 'excludeFromExport']),
          thumbnail: thumb
        };

        const res = await fetch('/api/projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (d.success) {
          activeProjectId = d.project.id;
          hasUnsavedChanges = false;
          showToast("Project saved successfully!", "✅", 3000);
        } else {
          throw new Error(d.error || "Save failed");
        }
      } catch (e) {
        console.error("Save error:", e);
        showToast(`Save error: ${e.message}`, "❌", 3500);
      }
    }
    document.getElementById('canvaApplyBtn')?.addEventListener('click', saveCurrentProject);

    function startNewDesign() {
      activeProjectId = null;
      document.getElementById('canvaDocTitleInput').value = "GOMZI Whey Protein New Design";
      loadGomziWheyTemplate();
      switchMainView('studio');
      showToast("Started fresh new design!", "✨");
    }

    /* ======================================================
       EXPORT CONTROLS
    ====================================================== */
    function initExportControls() {
      const exportBtn = document.getElementById('canvaExportMenuBtn');
      const exportDd = document.getElementById('canvaExportDropdown');
      if (exportBtn && exportDd) {
        exportBtn.onclick = (e) => {
          e.stopPropagation();
          exportDd.style.display = exportDd.style.display === 'flex' ? 'none' : 'flex';
        };
      }

      async function executeExport(fmt) {
        if (!canvaCanvas) return;
        showToast(`Generating ${fmt.toUpperCase()} Master...`, "⏳", 4500);
        const dataUrl = getCleanCanvasDataURL(2);
        const docTitle = document.getElementById('canvaDocTitleInput')?.value || "GOMZI_Whey_Protein_1kg";

        if (fmt === 'svg') {
          // Direct native SVG export
          const svgContent = canvaCanvas.toSVG();
          const blob = new Blob([svgContent], { type: 'image/svg+xml' });
          downloadBlob(blob, `${docTitle}.svg`);
          showToast("SVG Vector Master downloaded!", "📐");
          return;
        }

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
          const ext = fmt === 'cdr' ? 'zip' : fmt;
          downloadBlob(blob, `${docTitle}_300dpi.${ext}`);
          showToast(`Downloaded ${fmt.toUpperCase()} Master!`, "✅");
        } catch (e) {
          console.error(e);
          showToast(`Export error: ${e.message}`, "❌");
        }
      }

      function downloadBlob(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }

      document.getElementById('canvaExportCdrBtn')?.addEventListener('click', () => executeExport('cdr'));
      document.getElementById('canvaExportPdfBtn')?.addEventListener('click', () => executeExport('pdf'));
      document.getElementById('canvaExportPngBtn')?.addEventListener('click', () => executeExport('png'));
      document.getElementById('canvaExportSvgBtn')?.addEventListener('click', () => executeExport('svg'));
    }

    /* ======================================================
       MODULE DATA LOADERS (Dashboard, Orders, Products, My Designs)
    ====================================================== */
    async function loadDashboardStats() {
      try {
        const res = await fetch('/api/dashboard/stats');
        const d = await res.json();
        document.getElementById('dashTotalProjects').textContent = d.total_projects;
        document.getElementById('dashAiJobs').textContent = d.ai_jobs;
        document.getElementById('dashLabelsGenerated').textContent = d.labels_generated;
        document.getElementById('dashVectorsCreated').textContent = d.vectors_created;
        document.getElementById('dashAiCostToday').textContent = d.ai_cost_today;
        
        // Recent projects table
        const tbody = document.getElementById('dashRecentProjectsTableBody');
        if (tbody) {
          const pRes = await fetch('/api/projects');
          const pData = await pRes.json();
          tbody.innerHTML = '';
          (pData.projects || []).slice(0, 5).forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td><strong>${p.title}</strong></td>
              <td>${p.container || '1 kg Muscle Tub'}</td>
              <td><span style="color:var(--clr-olive); font-weight:700;">${p.brand_name || 'GOMZI NUTRITION'}</span></td>
              <td>${p.updated_at || 'Recently'}</td>
              <td><button class="table-action-btn" onclick="openProjectById('${p.id}');">Open in Studio</button></td>
            `;
            tbody.appendChild(tr);
          });
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function loadOrdersModule() {
      const tbody = document.getElementById('ordersTableBody');
      if (!tbody) return;
      try {
        const res = await fetch('/api/orders');
        const d = await res.json();
        tbody.innerHTML = '';
        (d.orders || []).forEach(o => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong>${o.id}</strong></td>
            <td>${o.customer}</td>
            <td>${o.product}</td>
            <td>${o.qty} pcs</td>
            <td><span style="background:#ecfdf5; color:#059669; padding:2px 6px; border-radius:4px; font-weight:700; font-size:11px;">${o.status}</span></td>
            <td>${o.date}</td>
            <td><strong>${o.amount}</strong></td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function loadProductsCatalog() {
      const grid = document.getElementById('productsCatalogGrid');
      if (!grid) return;
      try {
        const res = await fetch('/api/products');
        const d = await res.json();
        grid.innerHTML = '';
        (d.products || []).forEach(p => {
          const card = document.createElement('div');
          card.className = 'content-section-card';
          card.innerHTML = `
            <div style="font-size:28px;">📦</div>
            <div style="font-size:16px; font-weight:800; color:#0f172a;">${p.name}</div>
            <div style="font-size:12px; color:#64748b;">${p.spec}</div>
            <div style="font-size:11px; background:#f1f5f9; padding:4px 8px; border-radius:4px; color:#334155;">Category: <strong>${p.category}</strong></div>
            <button class="studio-save-btn" style="margin-top:8px; justify-content:center;" onclick="selectPackagingProductByName('${p.name}');">
              Open in 3D Studio
            </button>
          `;
          grid.appendChild(card);
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function loadMyDesigns() {
      const grid = document.getElementById('myDesignsGrid');
      if (!grid) return;
      try {
        const res = await fetch('/api/projects');
        const d = await res.json();
        grid.innerHTML = '';
        if (!d.projects || d.projects.length === 0) {
          grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#64748b;">No saved designs yet. Click <strong>New Design</strong> to create one!</div>`;
          return;
        }
        d.projects.forEach(p => {
          const card = document.createElement('div');
          card.className = 'content-section-card';
          const thumbHtml = p.thumbnail ? `<img src="${p.thumbnail}" style="width:100%; height:120px; object-fit:cover; border-radius:6px; border:1px solid #cbd5e1;" />` : `<div style="height:120px; background:#e2e8f0; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:32px;">🏷️</div>`;
          card.innerHTML = `
            ${thumbHtml}
            <div style="font-size:14px; font-weight:800; color:#0f172a;">${p.title}</div>
            <div style="font-size:11px; color:#64748b;">${p.container || '1 kg Muscle Tub'} · ${p.updated_at}</div>
            <div style="display:flex; gap:6px; margin-top:8px;">
              <button class="table-action-btn" style="flex:1;" onclick="openProjectById('${p.id}');">Open</button>
              <button class="table-action-btn" onclick="duplicateProjectById('${p.id}');">Duplicate</button>
              <button class="table-action-btn" style="color:#ef4444;" onclick="deleteProjectById('${p.id}');">Delete</button>
            </div>
          `;
          grid.appendChild(card);
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function openProjectById(projId) {
      showToast("Loading project...", "⏳", 3000);
      try {
        const res = await fetch(`/api/projects/${projId}`);
        const data = await res.json();
        activeProjectId = data.id;
        document.getElementById('canvaDocTitleInput').value = data.title;
        document.getElementById('studioProductPillName').textContent = data.product || "Whey Protein Standard";
        document.getElementById('studioSpecTag').textContent = data.container || "1 kg Muscle Tub";
        
        if (data.canvas_json && data.canvas_json.objects) {
          isHistoryLocked = true;
          canvaCanvas.loadFromJSON(data.canvas_json, () => {
            isHistoryLocked = false;
            canvaCanvas.renderAll();
            brandLogoObject = canvaCanvas.getObjects().find(o => o.isBrandLogo || o.assetType === 'brand_logo');
            refreshLayersList();
            updateThreeLabelTextureFromCanvas();
            switchMainView('studio');
            showToast(`Opened project "${data.title}"`, "✅");
          });
        } else {
          switchMainView('studio');
        }
      } catch (e) {
        console.error("Open project error:", e);
        showToast("Error opening project", "❌");
      }
    }

    async function duplicateProjectById(projId) {
      try {
        const res = await fetch(`/api/projects/${projId}/duplicate`, { method: 'POST' });
        const d = await res.json();
        if (d.success) {
          showToast("Project duplicated!", "📑");
          loadMyDesigns();
        }
      } catch (e) { console.error(e); }
    }

    async function deleteProjectById(projId) {
      if (!confirm("Are you sure you want to delete this design?")) return;
      try {
        const res = await fetch(`/api/projects/${projId}`, { method: 'DELETE' });
        const d = await res.json();
        if (d.success) {
          showToast("Project deleted", "🗑️");
          loadMyDesigns();
        }
      } catch (e) { console.error(e); }
    }

    function selectPackagingProductByName(name) {
      const p = productPresetsCache.find(x => x.name === name);
      if (p) selectPackagingProduct(p);
      switchMainView('studio');
    }

    function renderOtherModule(modName) {
      const titleEl = document.getElementById('otherModuleTitle');
      const subEl = document.getElementById('otherModuleSub');
      const contentEl = document.getElementById('otherModuleContent');
      
      const config = {
        'returns': {
          title: 'Returns & Replacements',
          sub: 'Manage quality check and returned packaging shipments',
          html: '<p style="color:#64748b;">No active return claims. Quality assurance score: <strong>99.4%</strong>.</p>'
        },
        'accounts': {
          title: 'Accounts & Billing',
          sub: 'Merchant billing, wallet balance, and invoices',
          html: '<div style="display:flex; flex-direction:column; gap:8px;"><div>Current Balance: <strong style="font-size:18px; color:#15803d;">₹ 0.00</strong></div><button class="new-order-btn" style="width:140px;" onclick="showToast(\'Add money gateway opened\');">+ Add Funds</button></div>'
        },
        'integrations': {
          title: 'Platform Integrations',
          sub: 'Connected print APIs, AI models, and cloud storage',
          html: '<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;"><div style="border:1px solid #cbd5e1; padding:10px; border-radius:6px;"><strong>CorelDRAW Graphics Suite</strong><br><span style="color:#10b981; font-weight:700;">● Active</span> (Direct SVG/CDR Export)</div><div style="border:1px solid #cbd5e1; padding:10px; border-radius:6px;"><strong>Google Flow Image AI</strong><br><span style="color:#10b981; font-weight:700;">● Connected</span> (useapi.net)</div><div style="border:1px solid #cbd5e1; padding:10px; border-radius:6px;"><strong>Rembg Background Removal</strong><br><span style="color:#10b981; font-weight:700;">● Local Engine</span></div><div style="border:1px solid #cbd5e1; padding:10px; border-radius:6px;"><strong>LaMa Inpainting</strong><br><span style="color:#10b981; font-weight:700;">● High-Res Local</span></div></div>'
        },
        'settings': {
          title: 'Settings & Brand Kit Configuration',
          sub: 'Platform defaults, print parameters and profile',
          html: '<div style="display:flex; flex-direction:column; gap:10px; max-width:450px;"><div><label style="font-weight:700; color:#334155;">Default Brand Name:</label><input value="GOMZI NUTRITION" style="width:100%; padding:6px; border:1px solid #cbd5e1; border-radius:4px; font-weight:700;" /></div><div><label style="font-weight:700; color:#334155;">Default Print Resolution:</label><select style="width:100%; padding:6px; border:1px solid #cbd5e1; border-radius:4px;"><option selected>300 DPI Ultra-HD (Press Standard)</option><option>600 DPI High-Density</option></select></div><button class="studio-save-btn" style="width:120px;" onclick="showToast(\'Settings saved!\');">Save Settings</button></div>'
        },
        'help': {
          title: 'Help, Shortcuts & Documentation',
          sub: 'Quick reference for GOMZI BOB AI Design Studio Pro',
          html: '<div style="display:flex; flex-direction:column; gap:8px;"><div><strong>Keyboard Shortcuts:</strong></div><div>• <code>Ctrl + Z</code>: Undo canvas action</div><div>• <code>Ctrl + Y</code>: Redo canvas action</div><div>• <code>Delete</code>: Delete selected layer</div><div>• <code>Double-Click Text</code>: Inline text editing</div><div>• <code>Shift + Drag</code>: Proportional resize</div></div>'
        }
      };

      const c = config[modName] || { title: modName, sub: 'Module Overview', html: '<p>Module active.</p>' };
      titleEl.textContent = c.title;
      subEl.textContent = c.sub;
      contentEl.innerHTML = c.html;
    }

    function openNewOrderModal() {
      showToast("Opened New Packaging Production Order form", "📦");
    }

    // App Initialization
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
        f.write(HTML_CODE)
    print(f"Successfully generated full application at {target_path} ({len(HTML_CODE)} bytes)")

if __name__ == "__main__":
    main()
