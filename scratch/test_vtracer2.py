import vtracer

print("Testing vtracer WITHOUT kwargs...", flush=True)
try:
    vtracer.convert_image_to_svg_py(
        "static/uploads/7148a5c7_new_Isolate_Chocolate_1kg.jpg.jpeg",
        "test3.svg"
    )
    print("SUCCESS", flush=True)
except Exception as e:
    print(f"Exception: {e}", flush=True)
