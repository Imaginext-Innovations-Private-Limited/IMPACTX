
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).parent

MODEL_PATH = BASE_DIR / "runs" / "floater_detection" / "weights" / "best.pt"
IMAGE_PATH = BASE_DIR / "dataset" / "test" / "sample_floater.jpg"

model = YOLO(str(MODEL_PATH))

if not IMAGE_PATH.exists():
    raise FileNotFoundError(f"Test image not found: {IMAGE_PATH}")

results = model.predict(
    source=str(IMAGE_PATH),
    conf=0.25,
    imgsz=416,
    device="cpu",
    save=True
)

for result in results:
    print("\nAquaWatch AI Detection Results")
    print("Total objects detected:", len(result.boxes))

    for box in result.boxes:
        confidence = float(box.conf[0])
        print(
            "Object:", model.names[int(box.cls[0])],
            "| Confidence:", round(confidence * 100, 2), "%"
        )

print("\nDetection completed!")
