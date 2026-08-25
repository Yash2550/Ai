import app
import traceback
import sys

try:
    app._build_svg_from_image('test_small.png')
    print('SUCCESS')
    sys.exit(0)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
