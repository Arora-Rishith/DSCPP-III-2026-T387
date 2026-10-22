"""Preflight test for the image-based classifier; does not require SUMO to be installed."""
from pathlib import Path

import cv2
from run_virtual_sim import (
    MODEL_FILE, VIEW_W, annotate_detections, empty_ml_counts, render_scene,
)
from vision_model import classify_frame, load_or_train

ROOT = Path(__file__).resolve().parent
MODEL = load_or_train(MODEL_FILE)
scene = [
    # Two opposing vertical approaches and two opposing horizontal approaches.
    {"id": "test-car-north", "x": -1.6, "y": 44, "angle": 180, "render_kind": "normal_car"},
    {"id": "test-bus-south", "x": 1.6, "y": -33, "angle": 0, "render_kind": "bus"},
    {"id": "test-truck-west", "x": -36, "y": -1.6, "angle": 90, "render_kind": "truck"},
    {"id": "test-ambulance-east", "x": 36, "y": 1.6, "angle": 270, "render_kind": "emergency_vehicle"},
]
frame = render_scene(scene, 3, "balanced", 12.4, True, False)
detections = classify_frame(frame, MODEL, view_width=VIEW_W, min_confidence=0.50)
labels = [str(d["label"]) for d in detections]
required = {"normal_car", "bus", "truck", "emergency_vehicle"}
missing = required - set(labels)
counts = empty_ml_counts()
# The preflight checks whether the four rendered vehicle appearances are recognizable.
preview = annotate_detections(frame, detections, counts, 3 if "emergency_vehicle" in labels else 0)
out = ROOT / "assets" / "vision_test_preview.png"
out.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(out), preview)
print(f"Candidate boxes found: {len(detections)}")
print("Predicted classes:", ", ".join(labels))
print("Preview saved to:", out)
if missing:
    raise SystemExit("Preflight failed; missing visual predictions: " + ", ".join(sorted(missing)))
print("Preflight passed: car, bus, truck, and emergency-vehicle crops were classified from pixels.")
