from __future__ import annotations

import cv2
import numpy as np

_INFERENCE_MAX_WIDTH = 960


def downscale_for_inference(frame: np.ndarray, max_width: int = _INFERENCE_MAX_WIDTH) -> np.ndarray:
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    scale = max_width / width
    new_height = max(1, int(height * scale))
    return cv2.resize(frame, (max_width, new_height), interpolation=cv2.INTER_AREA)
