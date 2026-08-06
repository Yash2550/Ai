import os
content = open('app.py', 'r', encoding='utf-8').read()

new_route = '''
@app.route("/api/digitize-reve", methods=["POST"])
def digitize_label_reve():
    """Route for sending the label to the official Reve API."""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
        
    try:
        import uuid
        import reve_api
        
        # Save uploaded file
        ext = os.path.splitext(file.filename)[1]
        if not ext:
            ext = ".png"
            
        unique_id = uuid.uuid4().hex[:8]
        filename = f"reve_upload_{unique_id}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Call Official API
        fabric_json = reve_api.digitize_image_via_reve(filepath)
        
        return jsonify({
            "status": "success",
            "fabric_json": fabric_json
        })
    except Exception as e:
        app.logger.error("Reve API Digitizer failed: %s", e)
        return jsonify({"error": str(e)}), 500
'''

if '/api/digitize-reve' not in content:
    content += new_route
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Added /api/digitize-reve to app.py')
else:
    print('Route already exists')
