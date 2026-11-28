import json
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from model_architecture import build_model_b


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_DIR = Path(r"D:\FINAL DFDT")

CHECKPOINT_PATH = (
    PROJECT_DIR
    / "experiment_v3_degradation_aware"
    / "checkpoints"
    / "model_B_v3_best.pth"
)

NORMALIZATION_PATH = (
    PROJECT_DIR
    / "SELECTED_DATASET"
    / "degradation_features_160"
    / "descriptor_normalization_160.json"
)

IMAGE_SIZE = 160

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# --------------------------------------------------
# IMAGE TRANSFORM
# --------------------------------------------------

image_transform = transforms.Compose([
    transforms.Resize(
        (IMAGE_SIZE, IMAGE_SIZE),
        interpolation=transforms.InterpolationMode.BILINEAR
    ),
    transforms.ToTensor()
])


# --------------------------------------------------
# LOAD NORMALIZATION VALUES
# --------------------------------------------------

def load_normalization():

    if not NORMALIZATION_PATH.exists():
        raise FileNotFoundError(
            f"Normalization file not found: {NORMALIZATION_PATH}"
        )

    with open(NORMALIZATION_PATH, "r", encoding="utf-8") as file:
        normalization = json.load(file)

    if normalization.get("image_size") != IMAGE_SIZE:
        raise ValueError("Unexpected image size in normalization file.")

    if normalization.get("normalization_method") != "z-score":
        raise ValueError("Unexpected descriptor normalization method.")

    if normalization.get("fitted_on") != "train":
        raise ValueError("Normalization values must be fitted on training data.")

    return normalization


# --------------------------------------------------
# EXTRACT DEGRADATION DESCRIPTORS
# --------------------------------------------------

def extract_degradation_descriptors(image_path, normalization):

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    image = cv2.resize(
        image,
        (IMAGE_SIZE, IMAGE_SIZE),
        interpolation=cv2.INTER_LINEAR
    )

    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gray_float = gray.astype(np.float32) / 255.0

    # Brightness, contrast and sharpness
    brightness = float(np.mean(gray_float))
    contrast = float(np.std(gray_float))
    sharpness = float(
        cv2.Laplacian(gray_float, cv2.CV_32F).var()
    )

    # Residual descriptors
    blurred = cv2.GaussianBlur(gray_float, (5, 5), 0)
    residual = gray_float - blurred

    residual_energy = float(np.mean(residual ** 2))
    absolute_residual = float(np.mean(np.abs(residual)))

    # FFT frequency descriptors
    fft = np.fft.fftshift(np.fft.fft2(gray_float))
    magnitude = np.abs(fft) ** 2

    height, width = gray_float.shape
    center_y = height // 2
    center_x = width // 2

    y, x = np.ogrid[:height, :width]

    distance = np.sqrt(
        (y - center_y) ** 2 +
        (x - center_x) ** 2
    )

    max_distance = np.sqrt(center_y ** 2 + center_x ** 2)
    normalized_distance = distance / max_distance

    low_mask = normalized_distance < 0.15
    mid_mask = (
        (normalized_distance >= 0.15) &
        (normalized_distance < 0.50)
    )
    high_mask = normalized_distance >= 0.50

    total_energy = np.sum(magnitude) + 1e-8

    low_frequency_energy = float(
        np.sum(magnitude[low_mask]) / total_energy
    )

    mid_frequency_energy = float(
        np.sum(magnitude[mid_mask]) / total_energy
    )

    high_frequency_energy = float(
        np.sum(magnitude[high_mask]) / total_energy
    )

    descriptor_values = {
        "brightness": brightness,
        "contrast": contrast,
        "sharpness": sharpness,
        "residual_energy": residual_energy,
        "absolute_residual": absolute_residual,
        "fft_low": low_frequency_energy,
        "fft_mid": mid_frequency_energy,
        "fft_high": high_frequency_energy
    }

    descriptor_names = normalization["descriptor_names"]

    raw_features = np.array(
        [descriptor_values[name] for name in descriptor_names],
        dtype=np.float32
    )

    means = np.array(
        [normalization["mean"][name] for name in descriptor_names],
        dtype=np.float32
    )

    stds = np.array(
        [normalization["std"][name] for name in descriptor_names],
        dtype=np.float32
    )

    normalized_features = (raw_features - means) / stds

    return torch.tensor(
        normalized_features,
        dtype=torch.float32
    ).unsqueeze(0)


# --------------------------------------------------
# LOAD TRAINED MODEL
# --------------------------------------------------

def load_model():

    if not CHECKPOINT_PATH.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {CHECKPOINT_PATH}"
        )

    model = build_model_b()

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location=DEVICE,
        weights_only=False
    )

    if "model_state_dict" not in checkpoint:
        raise KeyError("model_state_dict not found in checkpoint.")

    model.load_state_dict(
        checkpoint["model_state_dict"],
        strict=True
    )

    model.to(DEVICE)
    model.eval()

    return model


# --------------------------------------------------
# LOAD MODEL AND NORMALIZATION
# --------------------------------------------------

normalization = load_normalization()
model = load_model()


# --------------------------------------------------
# PREDICTION FUNCTION
# --------------------------------------------------

def predict_image(image_path):

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # RGB image preprocessing
    image = Image.open(image_path).convert("RGB")
    image_tensor = image_transform(image).unsqueeze(0)

    # Degradation descriptors
    descriptor_tensor = extract_degradation_descriptors(
        image_path,
        normalization
    )

    image_tensor = image_tensor.to(DEVICE)
    descriptor_tensor = descriptor_tensor.to(DEVICE)

    with torch.inference_mode():

        output = model(
            image_tensor,
            descriptor_tensor
        )

        probabilities = torch.softmax(
            output["logits"],
            dim=1
        )[0]

    real_probability = float(probabilities[0].item())
    fake_probability = float(probabilities[1].item())

    predicted_class = (
        "FAKE" if fake_probability >= real_probability else "REAL"
    )

    confidence = max(real_probability, fake_probability) * 100

    return {
        "prediction": predicted_class,
        "confidence": round(confidence, 2),
        "real_probability": round(real_probability * 100, 2),
        "fake_probability": round(fake_probability * 100, 2)
    }


print("AMSF-GNet V3 inference pipeline loaded successfully.")
print("Device:", DEVICE)
print("Checkpoint:", CHECKPOINT_PATH.name)
print("Model: Model B V3")
