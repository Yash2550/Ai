# Goal: Voice Input, Logo Extraction, and Advanced Features

The user wants to add voice typing for prompts, a feature to extract logos from uploaded reference photos (e.g., gym photos) and apply them to generated labels, and suggestions for other high-value features.

## User Review Required

Please review the proposed approaches below. Since your server runs on Render's Free Tier (which has very limited memory), we have to be smart about how we implement heavy AI tasks like Logo Extraction.

### 1. Voice Input (Speech-to-Text)
**Approach:** I will integrate the **Web Speech API** directly into your frontend (`index.html`). 
- **Benefits:** It is completely free, runs directly in the user's browser (Chrome/Edge/Safari), and supports Hindi, Gujarati, and English automatically! 
- **UI:** A microphone icon will be added to the input boxes.

### 2. Logo Detection from Reference Photos
Extracting a clean logo from a complex, real-world photo (like a gym photo) requires heavy AI object detection. Since we cannot run heavy models locally on Render, I propose the following pipeline using your existing APIs:
**Approach (Vision AI + Prompt Injection):**
1. We add an "Upload Reference Photo" button next to the prompt.
2. When a photo is uploaded, we send it to **Google Gemini Vision 1.5 Pro** (since you already have the Gemini API key).
3. Gemini will analyze the photo, extract the exact Brand Name, Brand Colors, and Logo Design Style.
4. We automatically inject these brand details into the generation prompt so the new label matches the gym's branding perfectly.

*(Note: Physically extracting a transparent PNG of the logo from a messy photo requires advanced background removal and cropping AI, which is difficult on a free server. Using Gemini Vision to "read" the logo and recreate it is the most reliable cloud-based approach).*

### 3. Suggested High-Value Features
Based on my research, here are the best features you could add to make this project incredibly useful:
- **Brand Kits:** Allow users to save their Company Logo, Brand Colors, and Fonts. Every time they generate a label, the AI automatically applies their specific Brand Kit.
- **Auto 3D Mockups:** After the flat label is generated, automatically wrap it around a 3D Protein Jar or Bottle using CSS or an external API so the user can see what the final product looks like.
- **Auto QR Code / Barcode Generator:** Real product labels need barcodes. The app could automatically generate a scannable QR code (linking to their website) and place it on the label.

## Open Questions

> [!IMPORTANT]
> **Question 1:** For the Voice Input, do you want the microphone to automatically detect the language (Hindi/Gujarati/English), or should we add a small dropdown for the user to select their language before speaking?
> 
> **Question 2:** For the Logo Detection, are you okay with using Google Gemini Vision to analyze the photo and recreate the branding, or do you specifically want to overlay the *exact physical pixels* of the logo from the photo?
> 
> **Question 3:** Out of the suggested features (Brand Kits, 3D Mockups, QR Codes), which one would you like me to build first?

## Proposed Changes

### Frontend (`index.html`)
- [MODIFY] `templates/index.html`
  - Add Microphone `<i>` buttons inside the prompt input fields.
  - Add JavaScript using `window.SpeechRecognition` to capture voice, convert it to text, and fill the input box.
  - Add an "Upload Reference Image" button for the Smart Prompt section.

### Backend (`app.py`)
- [MODIFY] `app.py`
  - Create a new endpoint `/analyze-reference` that accepts an image, sends it to Gemini Vision API, and returns the extracted brand guidelines (Colors, Text, Style).
