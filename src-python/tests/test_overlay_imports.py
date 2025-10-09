import sys
import time
from PIL import Image

sys.path.append(r"d:\WORKSPACE\WORK\VRChatProject\VRCT\src-python")

from models.overlay import overlay_image, overlay_utils


def test_overlay_image_create():
    oi = overlay_image.OverlayImage()
    img = oi.createOverlayImageSmallLog("hello", "English", [], [])
    assert isinstance(img, Image.Image)


def test_utils_transform():
    import numpy as np
    base = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0]
    ])
    res = overlay_utils.transform_matrix(base, (0, 0, 0), (0, 0, 0))
    assert res.shape == (3, 4)


if __name__ == '__main__':
    test_overlay_image_create()
    test_utils_transform()
    print('tests passed')
