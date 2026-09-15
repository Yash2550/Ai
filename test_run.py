import vtracer
import sys
try:
    vtracer.convert_image_to_svg_py('test_tmp.png', 'test_tmp.svg', colormode='color', hierarchical='stacked', mode='spline', filter_speckle=4, color_precision=6, layer_difference=16, corner_threshold=60, length_threshold=4.0, max_iterations=10, splice_threshold=45, path_precision=8)
except Exception:
    sys.exit(1)
