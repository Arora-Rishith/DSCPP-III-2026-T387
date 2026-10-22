from pathlib import Path
from vision_model import train_and_save

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models" / "virtual_vehicle_classifier.joblib"

if __name__ == "__main__":
    train_and_save(MODEL, per_class=500)
