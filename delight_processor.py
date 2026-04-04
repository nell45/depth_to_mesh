"""
Delighting via illumination division.

Models the image as:

    I(x,y) = R(x,y) * L(x,y)

where R is the reflectance (albedo) and L is the illumination. Solving:

    R(x,y) = I(x,y) / L(x,y)

L is estimated by downsampling the image to a small thumbnail then upsampling
back to the original resolution. The downsample+upsample acts as a very broad
low-pass filter, capturing only large-scale illumination gradients.

All operations use PIL mode "F" (32-bit float) so there is no uint8
quantisation at any stage.
"""

import numpy as np

_THUMB_SIZE = 64
_EPSILON = 1e-3


def _estimate_illumination(channel: np.ndarray) -> np.ndarray:
    from PIL import Image
    """
    Estimate illumination for a single H x W float32 channel in [0, 1].

    Downsample to _THUMB_SIZE x _THUMB_SIZE using PIL mode "F" (float32),
    then upsample back. This acts as a wide low-pass filter with no uint8
    precision loss.
    """
    H, W = channel.shape

    # PIL mode "F" operates entirely in float32
    pil_f = Image.fromarray(channel, mode="F")
    thumb = pil_f.resize((_THUMB_SIZE, _THUMB_SIZE), Image.BILINEAR)
    illumination_pil = thumb.resize((W, H), Image.BILINEAR)

    illumination = np.array(illumination_pil, dtype=np.float32)
    return np.clip(illumination, _EPSILON, 1.0)


def process(image: np.ndarray) -> np.ndarray:
    """
    Remove illumination from an image via per-channel illumination division.

    Args:
        image: H x W x 3 float32 in [0, 1], assumed sRGB

    Returns:
        albedo: H x W x 3 float32 in [0, 1] — reflectance with lighting removed
    """
    albedo = np.empty_like(image)

    for c in range(3):
        channel = image[:, :, c]
        illumination = _estimate_illumination(channel)
        reflectance = channel / illumination

        # Percentile stretch to [0, 1] to handle outliers at bright/dark edges
        p1, p99 = np.percentile(reflectance, 1), np.percentile(reflectance, 99)
        if p99 > p1:
            reflectance = (reflectance - p1) / (p99 - p1)

        albedo[:, :, c] = np.clip(reflectance, 0.0, 1.0)

    return albedo
