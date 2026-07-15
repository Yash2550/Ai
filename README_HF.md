---
title: Label Editor AI
emoji: 🎨
colorFrom: purple
colorTo: cyan
sdk: gradio
sdk_version: "5.16.1"
app_file: gradio_app.py
pinned: false
license: mit
---

# 🎨 Label Editor AI

AI-powered product label editor — Remove, Add, Replace, or Generate label designs using **Recraft.ai** and **Nano Banana (Gemini)** APIs.

## Features
- **Remove** — erase any element from a label (logo, text, graphic)
- **Add / Replace** — inpaint new elements or swap existing ones
- **Text Replace** — precisely replace brand name / text using CLIPSeg + PIL rendering
- **Generate** — create a full label from a text prompt (no image needed)
- **Download** in PNG, JPG, PDF, SVG, CDR, CDRx, GMS, CGS formats

## Setup — Secrets required

Add these in your Space **Settings → Secrets**:

| Secret | Description |
|--------|-------------|
| `RECRAFT_API_KEY` | From your [Recraft.ai](https://recraft.ai) profile |
| `NANOBANANA_API_KEY` | From your [Nano Banana](https://nanobananaapi.dev) dashboard |

At least one key is required. Both can coexist — you pick the provider per request.

## CorelDRAW format guide

| Format | How to use |
|--------|-----------|
| CDR | Open directly via File → Import in CorelDRAW 2019+ |
| CDRx | ZIP package — extract and open `document.svg` in CorelDRAW |
| GMS | Tools → Macros → Run Macro (embeds image directly) |
| CGS | Object Styles panel → Import Styles |
| SVG | Universal vector — CorelDRAW, Illustrator, Inkscape |
| PDF | Print-ready 300 DPI — any CorelDRAW version |
