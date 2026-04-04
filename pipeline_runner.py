"""
Pipeline orchestrator.

Free of bpy imports — runs safely on a background thread.
All scene mutations happen in operators.py after this module returns.
"""

import os

import numpy as np

from . import delight_processor
from .depth_estimator import AlgorithmicDepthEstimator, DepthAnythingV2Estimator

_SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
_SUPPORTED_EXR_EXTS = {".exr"}
ALL_SUPPORTED_EXTS = _SUPPORTED_IMAGE_EXTS | _SUPPORTED_EXR_EXTS


def run(
    input_path: str,
    cache_dir: str,
    use_ml_depth: bool = True,
    use_delight: bool = True,
    delight_strength: float = 0.5,
    progress_callback=None,
    preloaded_image: np.ndarray = None,
) -> tuple:
    """
    Load an image, estimate depth, and return both as float32 arrays.

    Args:
        input_path:        Absolute path to the input image file.
        cache_dir:         Directory for HuggingFace model cache.
        use_ml_depth:      Use Depth Anything V2 when True, algorithmic when False.
        use_delight:       Apply Multi-Scale Retinex delighting when True.
        delight_strength:  Blend factor between original and delighted image.
        progress_callback: Optional callable(str) for status messages.
        preloaded_image:   Optional H x W x 3 float32 array. When provided
                           (e.g. for EXR files loaded via bpy on the main thread),
                           file loading is skipped entirely.

    Returns:
        (albedo, depth) where:
            albedo : H x W x 3  float32  [0, 1]
            depth  : H x W      float32  [0, 1]  higher = closer

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the file extension is not in the supported set.
    """
    progress = progress_callback or (lambda msg: None)

    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    if ext not in ALL_SUPPORTED_EXTS:
        raise ValueError(
            f"Unsupported format '{ext}'. "
            f"Supported: {', '.join(sorted(ALL_SUPPORTED_EXTS))}"
        )

    if preloaded_image is not None:
        progress("Using pre-loaded image...")
        albedo = preloaded_image
    else:
        progress("Loading image...")
        from PIL import Image
        pil_img = Image.open(input_path).convert("RGB")
        albedo = np.array(pil_img, dtype=np.float32) / 255.0

    if use_ml_depth:
        estimator = DepthAnythingV2Estimator(
            cache_dir=cache_dir,
            progress_callback=progress,
        )
        estimator.load()
    else:
        progress("Using algorithmic depth estimator...")
        estimator = AlgorithmicDepthEstimator()

    depth = estimator.infer(albedo)
    progress("Depth estimation complete.")

    if use_delight:
        progress("Delighting...")
        original = albedo
        delighted = delight_processor.process(albedo)
        albedo = original * (1.0 - delight_strength) + delighted * delight_strength
        progress("Delighting complete.")

    return albedo, depth
