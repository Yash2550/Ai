with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = 'if __name__ == "__main__":'
if '/api/ai/providers' in content:
    print('Routes already exist!')
else:
    new_code = '''
# ---------------------------------------------------------------------------
# GOMZI BOB Advanced AI API Selector & Multilingual Prompt Composer Routes
# ---------------------------------------------------------------------------
import ai_provider_service

@app.route("/api/ai/providers", methods=["GET"])
def api_ai_providers():
    """Returns the centralized AI provider catalog with status and configured models."""
    try:
        providers = ai_provider_service.get_provider_status()
        return jsonify({
            "success": True,
            "providers": providers,
            "count": len(providers)
        })
    except Exception as e:
        app.logger.error(f"Error fetching AI providers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai/presets", methods=["GET"])
def api_ai_presets():
    """Returns the standard packaging dimension and aspect ratio presets."""
    return jsonify({
        "success": True,
        "presets": ai_provider_service.PACKAGING_DIMENSION_PRESETS
    })


@app.route("/api/ai/test-connection", methods=["POST"])
def api_ai_test_connection():
    """
    Tests network connection to the selected AI provider.
    Never exposes complete API keys to client.
    """
    data = request.get_json(silent=True) or {}
    provider_id = data.get("provider", "auto")
    test_key = data.get("api_key")  # Optional key tested before saving
    
    try:
        res = ai_provider_service.test_provider_connection(provider_id, test_key=test_key)
        return jsonify(res)
    except Exception as e:
        app.logger.error(f"Test connection error: {e}")
        return jsonify({"success": False, "provider": provider_id, "message": str(e)}), 500


@app.route("/api/ai/save-config", methods=["POST"])
def api_ai_save_config():
    """Saves updated API key and default provider to .env securely on backend."""
    data = request.get_json(silent=True) or {}
    provider_id = data.get("provider")
    api_key = data.get("api_key")
    set_default = bool(data.get("set_default", False))
    
    if not provider_id:
        return jsonify({"success": False, "error": "Provider ID required"}), 400
        
    try:
        res = ai_provider_service.save_provider_config(provider_id, api_key=api_key, set_default=set_default)
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai/enhance-prompt", methods=["POST"])
def api_ai_enhance_prompt():
    """
    Converts conversational voice or manual text (Gujarati, Hindi, English)
    into a professional, print-ready, flat 2D packaging artwork prompt.
    """
    data = request.get_json(silent=True) or {}
    raw_prompt = data.get("prompt", "").strip()
    language = data.get("language", "gu-IN")
    aspect_ratio = data.get("aspect_ratio", "3:1")
    provider_id = data.get("provider", "auto")
    
    if not raw_prompt:
        return jsonify({"success": False, "error": "Prompt cannot be empty"}), 400
        
    try:
        result = ai_provider_service.enhance_prompt_multilingual(
            raw_text=raw_prompt,
            language=language,
            aspect_ratio=aspect_ratio,
            provider_id=provider_id
        )
        result["success"] = True
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error enhancing prompt: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai/generate", methods=["POST"])
def api_ai_generate_artwork():
    """
    Directly generates packaging artwork using the strictly selected AI provider and model.
    Opens the resulting label as full artwork rather than a small sticker.
    """
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    provider_id = data.get("provider", "auto")
    model_id = data.get("model")
    aspect_ratio = data.get("aspect_ratio", "3:1")
    negative_prompt = data.get("negative_prompt")
    
    if not prompt:
        return jsonify({"success": False, "error": "A prompt is required for generation."}), 400
        
    try:
        res = ai_provider_service.generate_packaging_artwork(
            prompt=prompt,
            provider_id=provider_id,
            model_id=model_id,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt
        )
        
        # Save a copy to results/ and create UploadedImage record for gallery persistence
        img_url = res.get("image_url", "")
        if img_url:
            unique_stem = str(uuid.uuid4())[:8]
            out_filename = f"ai_gen_{provider_id}_{unique_stem}.png"
            out_path = os.path.join(app.config["RESULTS_FOLDER"], out_filename)
            
            if img_url.startswith("data:image"):
                b64_data = img_url.split(",", 1)[1]
                img_bytes = base64.b64decode(b64_data)
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
            else:
                r_img = requests.get(img_url, timeout=30)
                if r_img.status_code == 200:
                    with open(out_path, "wb") as f:
                        f.write(r_img.content)
                        
            # Register in DB if file exists
            if os.path.exists(out_path):
                try:
                    with Image.open(out_path) as pimg:
                        pw, ph = pimg.size
                    db_image = UploadedImage(
                        filename=out_filename,
                        original_name=f"AI Generated {provider_id} Label",
                        file_path=out_path,
                        description=prompt[:200],
                        width=pw,
                        height=ph
                    )
                    db.session.add(db_image)
                    db.session.commit()
                    res["saved_asset"] = {
                        "id": db_image.id,
                        "filename": out_filename,
                        "url": f"/static/results/{out_filename}",
                        "width": pw,
                        "height": ph
                    }
                    res["image_url"] = f"/static/results/{out_filename}"
                except Exception as dbe:
                    app.logger.warning(f"Could not persist generated asset in DB: {dbe}")

        return jsonify(res)
    except Exception as e:
        app.logger.error(f"AI Generation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

'''
    updated = content.replace(target, new_code + "\n\n" + target)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(updated)
    print('Successfully inserted AI API routes into app.py!')
