# image_metrics.py
import os
from PIL import Image, ImageFilter, ImageChops, ImageStat
import math

# Optional: try OpenCV for face detection / better blur detection
try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False

def image_dimensions_and_size(path):
    try:
        with Image.open(path) as im:
            w, h = im.size
        size_bytes = os.path.getsize(path)
        return {"width": w, "height": h, "size_bytes": size_bytes, "size_mb": round(size_bytes / (1024*1024), 2)}
    except Exception:
        return {"width": None, "height": None, "size_bytes": None, "size_mb": None}

def blur_score_laplacian(path):
    """Simple sharpness score: variance of Laplacian via cv2 if available, else PIL-based edge energy."""
    try:
        if _HAS_CV2:
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if img is None:
                return None
            lap = cv2.Laplacian(img, cv2.CV_64F)
            var = float(lap.var())
            # normalize roughly to 0..100
            score = max(0.0, min(100.0, var / 10.0))
            return round(score, 2)
        else:
            # PIL fallback: use RMS of high-pass (approx)
            with Image.open(path).convert("L") as im:
                # create simple high-pass by subtracting a blurred version
                blurred = im.filter(ImageFilter.GaussianBlur(2))
                hp = ImageChops.difference(im, blurred)
                stat = ImageStat.Stat(hp)
                rms = stat.rms[0] if stat.rms else 0
                score = max(0.0, min(100.0, rms / 2.0))
                return round(score, 2)
    except Exception:
        return None

def face_count(path):
    """Return count of faces using OpenCV cascade if available, else None."""
    if not _HAS_CV2:
        return None
    try:
        img = cv2.imdecode(__import__("numpy").fromfile(path, dtype=__import__("numpy").uint8), cv2.IMREAD_GRAYSCALE)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if img is None:
            return None
        faces = face_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return int(len(faces))
    except Exception:
        return None

def get_image_metrics(path):
    dims = image_dimensions_and_size(path)
    quality = blur_score_laplacian(path)
    faces = face_count(path)
    return {
        "width": dims.get("width"),
        "height": dims.get("height"),
        "size_mb": dims.get("size_mb"),
        "size_bytes": dims.get("size_bytes"),
        "quality_score": quality,
        "faces": faces
    }
