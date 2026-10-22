"""Synthetic visual ML model for classifying vehicles rendered from SUMO.

Detection is pixel-based: OpenCV proposes candidate vehicle regions from the rendered
camera frame; a scikit-learn RandomForest classifies each crop. The model never reads
SUMO vehicle IDs or type labels at prediction time.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable

import cv2
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

CLASSES = ["normal_car", "bus", "truck", "emergency_vehicle"]
ROAD_BGR = (58, 61, 64)
TARGET_SIZE = (32, 20)  # width, height

# Bright and saturated normal-car paint colors, BGR order.
NORMAL_PALETTE = [
    (220, 120, 40), (180, 155, 35), (40, 170, 225), (50, 185, 65),
    (180, 85, 175), (210, 180, 65), (45, 135, 210), (130, 185, 35),
]


def _points(center: tuple[float, float], forward: tuple[float, float], side: tuple[float, float],
            along_half: float, side_half: float, along_offset: float = 0.0) -> np.ndarray:
    cx, cy = center
    fx, fy = forward
    sx, sy = side
    c = (cx + fx * along_offset, cy + fy * along_offset)
    return np.array([
        [round(c[0] + fx * along_half + sx * side_half), round(c[1] + fy * along_half + sy * side_half)],
        [round(c[0] + fx * along_half - sx * side_half), round(c[1] + fy * along_half - sy * side_half)],
        [round(c[0] - fx * along_half - sx * side_half), round(c[1] - fy * along_half - sy * side_half)],
        [round(c[0] - fx * along_half + sx * side_half), round(c[1] - fy * along_half + sy * side_half)],
    ], dtype=np.int32)


def draw_vehicle_sprite(image: np.ndarray, center: tuple[float, float], angle: float,
                        kind: str, scale: float = 1.0,
                        color: tuple[int, int, int] | None = None,
                        rng: random.Random | None = None) -> tuple[int, int, int, int]:
    """Draw one recognizable top-down vehicle sprite; angle follows SUMO convention."""
    rng = rng or random
    kind = kind if kind in CLASSES else "normal_car"
    if color is None:
        color = rng.choice(NORMAL_PALETTE)

    theta = np.deg2rad(float(angle))
    # SUMO: 0 points north; image y grows downwards.
    forward = (float(np.sin(theta)), float(-np.cos(theta)))
    side = (float(np.cos(theta)), float(np.sin(theta)))

    if kind == "bus":
        length_m, width_m = rng.uniform(10.0, 12.0), rng.uniform(2.25, 2.75)
    elif kind == "truck":
        length_m, width_m = rng.uniform(7.0, 9.0), rng.uniform(2.2, 2.7)
    elif kind == "emergency_vehicle":
        length_m, width_m = rng.uniform(5.0, 6.0), rng.uniform(1.8, 2.15)
    else:
        length_m, width_m = rng.uniform(4.2, 5.5), rng.uniform(1.65, 2.05)

    length_px = max(17.0, length_m * scale)
    width_px = max(7.0, width_m * scale)
    lh, wh = length_px / 2.0, width_px / 2.0

    body_color = (238, 238, 238) if kind == "emergency_vehicle" else color
    # Body and outline remain one connected high-contrast silhouette.
    body = _points(center, forward, side, lh, wh)
    cv2.fillPoly(image, [body], body_color, lineType=cv2.LINE_AA)
    cv2.polylines(image, [body], True, (20, 22, 24), max(1, round(scale * 0.30)), lineType=cv2.LINE_AA)

    def local_shape(along_half: float, side_half: float, along_offset: float,
                    fill: tuple[int, int, int], outline: tuple[int, int, int] | None = None) -> None:
        poly = _points(center, forward, side, along_half, side_half, along_offset)
        cv2.fillPoly(image, [poly], fill, lineType=cv2.LINE_AA)
        if outline is not None:
            cv2.polylines(image, [poly], True, outline, 1, lineType=cv2.LINE_AA)

    glass = (78, 92, 104)
    if kind == "bus":
        # Row of dark windows on each side; the bright body remains visible around them.
        count = 5
        for i in range(count):
            frac = -0.28 + i * 0.14
            local_shape(length_px * 0.055, width_px * 0.20, lh * frac, glass)
        local_shape(length_px * 0.10, width_px * 0.34, lh * 0.72, (35, 45, 50))
    elif kind == "truck":
        # Cargo box and a distinct cab at the forward end.
        local_shape(length_px * 0.24, width_px * 0.42, -lh * 0.18,
                    (166, 176, 184), (35, 38, 42))
        local_shape(length_px * 0.11, width_px * 0.34, lh * 0.62, glass)
    else:
        local_shape(length_px * 0.18, width_px * 0.34, -lh * 0.18, glass)
        local_shape(length_px * 0.12, width_px * 0.30, lh * 0.54, glass)

    if kind == "emergency_vehicle":
        # White ambulance body, red side stripe/cross and alternating light bar.
        local_shape(length_px * 0.32, max(1.0, width_px * 0.13), -lh * 0.02, (35, 35, 230))
        local_shape(length_px * 0.085, width_px * 0.22, -lh * 0.18, (35, 35, 230))
        local_shape(length_px * 0.055, width_px * 0.22, -lh * 0.18, (245, 245, 245))
        local_shape(length_px * 0.07, width_px * 0.33, lh * 0.74, (30, 40, 235))
        # Blue segment on one side of the roof light bar.
        local_shape(length_px * 0.045, width_px * 0.20, lh * 0.74, (235, 110, 25))
    else:
        # Tiny tail/front lamps vary by orientation but do not dominate the crop.
        local_shape(max(1.0, length_px * 0.025), width_px * 0.12, lh * 0.88, (40, 40, 225))

    # Return a geometry box for training data only; runtime detection uses image contours.
    xs = body[:, 0]
    ys = body[:, 1]
    x1, x2 = int(xs.min()), int(xs.max()) + 1
    y1, y2 = int(ys.min()), int(ys.max()) + 1
    return x1, y1, x2, y2


def vehicle_mask(frame: np.ndarray, view_width: int | None = None) -> np.ndarray:
    """Propose vehicle regions from image pixels, without vehicle IDs or type metadata."""
    if view_width is None:
        view_width = frame.shape[1]
    view = frame[:, :view_width]
    hsv = cv2.cvtColor(view, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    chromatic = cv2.inRange(saturation, 65, 255)
    bright = cv2.inRange(value, 218, 255)
    # The dark outline is deliberately part of each sprite; using it helps bridge window gaps.
    dark_outline = cv2.inRange(value, 0, 38)
    mask = cv2.bitwise_or(cv2.bitwise_or(chromatic, bright), dark_outline)
    # Close small dark gaps caused by windows and outlines; remove isolated tiny details.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return mask


def candidate_boxes(frame: np.ndarray, view_width: int | None = None) -> list[tuple[int, int, int, int]]:
    """Extract candidate boxes using OpenCV contours; no SUMO state is consulted."""
    if view_width is None:
        view_width = frame.shape[1]
    mask = vehicle_mask(frame, view_width)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h_frame, w_frame = frame.shape[:2]
    boxes: list[tuple[int, int, int, int]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        long_side, short_side = max(w, h), max(1, min(w, h))
        aspect = long_side / short_side
        if area < 80 or w < 9 or h < 7:
            continue
        if long_side > 115 or short_side > 28:
            continue
        if aspect < 1.45 or aspect > 8.5:
            continue
        if x < 8 or y < 8 or x + w >= min(view_width, w_frame) - 5 or y + h >= h_frame - 5:
            continue
        boxes.append((x, y, x + w, y + h))

    # Merge boxes which represent different bright details from the same vehicle.
    boxes = _merge_overlapping_boxes(boxes)
    return boxes


def _merge_overlapping_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    merged: list[tuple[int, int, int, int]] = []
    for box in boxes:
        x1, y1, x2, y2 = box
        found = False
        for i, old in enumerate(merged):
            a1, b1, a2, b2 = old
            ix = max(0, min(x2, a2) - max(x1, a1))
            iy = max(0, min(y2, b2) - max(y1, b1))
            union = (x2-x1)*(y2-y1) + (a2-a1)*(b2-b1) - ix*iy
            iou = ix*iy/max(1, union)
            # Touching pieces with aligned centers are likely windows/lights on one sprite.
            centers_close = abs((x1+x2-a1-a2)/2) < 10 and abs((y1+y2-b1-b2)/2) < 10
            if iou > 0.08 or centers_close:
                merged[i] = (min(x1,a1), min(y1,b1), max(x2,a2), max(y2,b2))
                found = True
                break
        if not found:
            merged.append(box)
    return merged


def image_features(crop: np.ndarray) -> np.ndarray:
    """Fixed-size visual features for the RandomForest classifier."""
    if crop.size == 0:
        crop = np.full((20, 32, 3), ROAD_BGR, dtype=np.uint8)
    resized = cv2.resize(crop, TARGET_SIZE, interpolation=cv2.INTER_AREA)
    pixels = resized.astype(np.float32).reshape(-1) / 255.0
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    hist_parts = []
    for channel, bins, max_value in [(0, 8, 180), (1, 8, 256), (2, 8, 256)]:
        hist = cv2.calcHist([hsv], [channel], None, [bins], [0, max_value]).reshape(-1)
        hist = hist / max(1.0, hist.sum())
        hist_parts.append(hist.astype(np.float32))
    return np.concatenate([pixels, *hist_parts])


def synthetic_training_examples(per_class: int = 500, seed: int = 24017) -> tuple[np.ndarray, np.ndarray]:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    features: list[np.ndarray] = []
    labels: list[str] = []
    angles = [0, 90, 180, 270]
    # Larger training canvases; vehicle proposals are cropped using the same image mask
    # as live detection, so the classifier learns from candidate pixels rather than IDs.
    for label in CLASSES:
        for _ in range(per_class):
            canvas = np.empty((100, 100, 3), dtype=np.uint8)
            base = int(rng.randint(-4, 4))
            canvas[:] = tuple(max(0, min(255, c + base)) for c in ROAD_BGR)
            # Mild sensor noise and tiny illumination variations help generalization.
            noise = np_rng.normal(0, 1.4, canvas.shape).astype(np.int16)
            canvas[:] = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            center = (50 + rng.randint(-3, 3), 50 + rng.randint(-3, 3))
            scale = rng.uniform(4.4, 6.4)
            color = rng.choice(NORMAL_PALETTE)
            draw_vehicle_sprite(canvas, center, rng.choice(angles), label, scale, color, rng)
            boxes = candidate_boxes(canvas, 100)
            if boxes:
                # Prefer the candidate closest to the canvas center.
                box = min(boxes, key=lambda b: (0.5*(b[0]+b[2])-50)**2 + (0.5*(b[1]+b[3])-50)**2)
                x1, y1, x2, y2 = box
                crop = canvas[max(0,y1-2):min(100,y2+2), max(0,x1-2):min(100,x2+2)]
            else:
                # Fallback is only used if contour settings are changed too strictly.
                x1, y1, x2, y2 = draw_vehicle_sprite(canvas, center, 0, label, scale, color, rng)
                crop = canvas[max(0,y1-2):min(100,y2+2), max(0,x1-2):min(100,x2+2)]
            features.append(image_features(crop))
            labels.append(label)
    return np.asarray(features, dtype=np.float32), np.asarray(labels)


def train_and_save(model_path: str | Path, per_class: int = 500, seed: int = 24017,
                   verbose: bool = True) -> RandomForestClassifier:
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    X, y = synthetic_training_examples(per_class=per_class, seed=seed)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.22, random_state=seed, stratify=y
    )
    model = RandomForestClassifier(
        n_estimators=140, max_depth=18, min_samples_leaf=1,
        max_features="sqrt", class_weight="balanced", n_jobs=-1,
        random_state=seed,
    )
    model.fit(X_train, y_train)
    score = accuracy_score(y_test, model.predict(X_test))
    joblib.dump(model, model_path)
    if verbose:
        print(f"Saved visual vehicle classifier: {model_path}")
        print(f"Synthetic held-out crop accuracy: {score:.3f}")
        print(classification_report(y_test, model.predict(X_test), labels=CLASSES, zero_division=0))
        print("Note: this score is on synthetic rendered crops, not real-world traffic footage.")
    return model


def load_or_train(model_path: str | Path) -> RandomForestClassifier:
    model_path = Path(model_path)
    if model_path.exists():
        try:
            return joblib.load(model_path)
        except Exception as exc:
            print(f"Saved model could not be loaded ({exc}). Retraining for this Python environment...")
    else:
        print("No saved ML model found. Training the virtual-vehicle visual classifier...")
    return train_and_save(model_path)


def classify_frame(frame: np.ndarray, model: RandomForestClassifier,
                   view_width: int | None = None,
                   min_confidence: float = 0.56) -> list[dict[str, object]]:
    detections: list[dict[str, object]] = []
    for x1, y1, x2, y2 in candidate_boxes(frame, view_width):
        pad = 2
        crop = frame[max(0, y1-pad):min(frame.shape[0], y2+pad),
                      max(0, x1-pad):min(frame.shape[1], x2+pad)]
        probs = model.predict_proba(image_features(crop).reshape(1, -1))[0]
        idx = int(np.argmax(probs))
        label = str(model.classes_[idx])
        confidence = float(probs[idx])
        if confidence < min_confidence:
            label = "unknown"
        detections.append({"box": (x1, y1, x2, y2), "label": label, "confidence": confidence})
    return detections
