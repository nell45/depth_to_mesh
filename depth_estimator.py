"""
Depth estimation backends.

All backends share the same interface:
    infer(image: np.ndarray) -> np.ndarray
        image : H x W x 3  float32  [0, 1]
        returns H x W      float32  [0, 1]  (higher value = closer to camera)
"""

import numpy as np


class AlgorithmicDepthEstimator:
    """
    Estimates a pseudo-depth map using local sharpness (variance of Laplacian).
    Sharper regions are treated as closer. Works without any model download.

    Used as a fallback when the ML model is not yet downloaded.
    """

    def __init__(self, smooth_radius: float = 24.0):
        self._smooth_radius = smooth_radius

    def infer(self, image: np.ndarray) -> np.ndarray:
        from PIL import Image, ImageFilter

        luma = (
            0.2126 * image[:, :, 0]
            + 0.7152 * image[:, :, 1]
            + 0.0722 * image[:, :, 2]
        )
        gray_u8 = (np.clip(luma, 0.0, 1.0) * 255).astype(np.uint8)
        pil_gray = Image.fromarray(gray_u8, mode="L")

        tight_blur = pil_gray.filter(ImageFilter.GaussianBlur(radius=2))
        lap = np.abs(
            np.array(pil_gray, dtype=np.float32)
            - np.array(tight_blur, dtype=np.float32)
        )

        lap_pil = Image.fromarray(np.clip(lap, 0, 255).astype(np.uint8), mode="L")
        depth_pil = lap_pil.filter(ImageFilter.GaussianBlur(radius=self._smooth_radius))
        depth = np.array(depth_pil, dtype=np.float32)

        p1, p99 = np.percentile(depth, 1), np.percentile(depth, 99)
        if p99 > p1:
            depth = (depth - p1) / (p99 - p1)
        return np.clip(depth, 0.0, 1.0)


class DepthAnythingV2Estimator:
    """
    Monocular depth estimation using Depth Anything V2 Small via
    transformers.pipeline("depth-estimation").

    The model weights (~100 MB) are downloaded on first use and cached in
    `cache_dir`. All subsequent runs are fully offline.
    """

    MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"

    def __init__(self, cache_dir: str, progress_callback=None):
        self._cache_dir = cache_dir
        self._progress = progress_callback or (lambda msg: None)
        self._pipe = None

    def load(self) -> None:
        """Download (if needed) and load the model. Call before infer()."""
        import os
        os.makedirs(self._cache_dir, exist_ok=True)

        self._progress("Loading Depth Anything V2 Small...")

        from transformers import pipeline
        import torch

        device = 0 if torch.cuda.is_available() else -1

        self._pipe = pipeline(
            task="depth-estimation",
            model=self.MODEL_ID,
            device=device,
            model_kwargs={"cache_dir": self._cache_dir},
        )
        self._progress("Model loaded.")

    def infer(self, image: np.ndarray) -> np.ndarray:
        if self._pipe is None:
            raise RuntimeError("Call load() before infer().")

        self._progress("Estimating depth...")

        from PIL import Image
        pil_img = Image.fromarray((np.clip(image, 0, 1) * 255).astype(np.uint8))
        result = self._pipe(pil_img)

        depth_pil = result["depth"]
        depth = np.array(depth_pil, dtype=np.float32)

        p1, p99 = np.percentile(depth, 1), np.percentile(depth, 99)
        if p99 > p1:
            depth = (depth - p1) / (p99 - p1)
        return np.clip(depth, 0.0, 1.0)
