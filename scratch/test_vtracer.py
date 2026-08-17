import vtracer
import sys

print("Testing vtracer with kwargs...", flush=True)
try:
    vtracer.convert_image_to_svg_py(
        "static/uploads/7148a5c7_new_Isolate_Chocolate_1kg.jpg.jpeg",
        "test2.svg",
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=8
    )
    print("SUCCESS", flush=True)
except Exception as e:
    print(f"Exception: {e}", flush=True)
