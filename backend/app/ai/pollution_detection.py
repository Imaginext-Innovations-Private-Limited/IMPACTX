
from pathlib import Path
from ultralytics import YOLO

# Locate the custom-trained AquaWatch model
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "best.pt"

# Load model once when the application starts
model = YOLO(str(MODEL_PATH))


def detect_pollution(image_path: str):
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    results = model.predict(
        source=str(image_path),
        conf=0.25,
        imgsz=416,
        device="cpu",
        verbose=False
    )

    detections = []

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detections.append({
                "object": model.names[class_id],
                "confidence": round(confidence, 3),
                "bounding_box": {
                    "x1": round(x1, 2),
                    "y1": round(y1, 2),
                    "x2": round(x2, 2),
                    "y2": round(y2, 2)
                }
            })

    return {
        "model": "AquaWatch Custom YOLO11n",
        "total_detections": len(detections),
        "detections": detections
    }
