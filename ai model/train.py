
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).parent
DATA_YAML = BASE_DIR / "data.yaml"
RUNS_DIR = BASE_DIR / "runs"

def train_model():
    print("Starting AquaWatch YOLO training...")
    print("Training device: CPU")

    model = YOLO("yolo11n.pt")

    model.train(
        data=str(DATA_YAML),
        epochs=5,          # Initial test training
        imgsz=416,
        batch=2,
        device="cpu",
        workers=0,
        cache=False,
        project=str(RUNS_DIR),
        name="floater_detection",
        exist_ok=True
    )

    print("Initial training completed!")

if __name__ == "__main__":
    train_model()
