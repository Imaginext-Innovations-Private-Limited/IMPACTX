"""
KisanVaani — PyTorch Transfer-Learning & Prototype Calibration Script
=====================================================================
Allows fine-tuning or extending the local 38-class MobileNetV2 Leaf Disease CNN
on custom Indian crop leaf folders (e.g., Coffee Rust, Paddy Blast, Arecanut, Chilli).

Usage:
  1. Fine-tune on a custom ImageFolder dataset (dataset/<class_name>/*.jpg):
       python scripts/train_leaf_model.py --data-dir path/to/dataset --epochs 8 --lr 3e-4

  2. Calibrate 1280-dim MobileNetV2 deep feature prototypes for Indian plantation samples:
       python scripts/train_leaf_model.py --calibrate-indian-prototypes
"""

import argparse
import json
import os
import sys
from typing import Dict, List

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageEnhance, ImageOps
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms
from transformers import AutoModelForImageClassification, MobileNetV2ImageProcessor

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, "models", "leaf_disease_cnn")
PROTOTYPES_PATH = os.path.join(MODEL_DIR, "indian_crop_prototypes.pt")


def extract_backbone_embedding(model: nn.Module, pixel_values: torch.Tensor) -> torch.Tensor:
    """Extract L2-normalized 1280-dim pooled MobileNetV2 feature vector from image tensor."""
    with torch.no_grad():
        outputs = model.mobilenet_v2(pixel_values=pixel_values)
        pooled = outputs.pooler_output  # shape: (B, 1280)
        return F.normalize(pooled, p=2, dim=-1)


def calibrate_indian_crop_prototypes(model_dir: str = MODEL_DIR) -> None:
    """
    Build augmented deep-feature prototypes in 1280-dim MobileNetV2 embedding space
    for Indian plantation crops not present in North-American PlantVillage (e.g., Coffee Rust).
    """
    processor = MobileNetV2ImageProcessor.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForImageClassification.from_pretrained(model_dir, local_files_only=True)
    model.eval()

    sample_dir = os.path.join(PROJECT_ROOT, "static", "sample_leaves")
    prototype_specs = {
        "coffee:rust": os.path.join(sample_dir, "coffee_rust.jpg"),
        "tomato:ring_spot": os.path.join(sample_dir, "tomato_blight.jpg"),
        "potato:wet_rot": os.path.join(sample_dir, "potato_late_blight.jpg"),
        "general:healthy": os.path.join(sample_dir, "healthy_leaf.jpg"),
    }

    prototypes: Dict[str, List[float]] = {}
    for label_key, img_path in prototype_specs.items():
        if not os.path.exists(img_path):
            continue
        base_img = Image.open(img_path).convert("RGB")
        augmented_views = [
            base_img,
            ImageOps.mirror(base_img),
            ImageOps.flip(base_img),
            base_img.rotate(15),
            base_img.rotate(-15),
            ImageEnhance.Brightness(base_img).enhance(0.9),
            ImageEnhance.Brightness(base_img).enhance(1.1),
            ImageEnhance.Contrast(base_img).enhance(1.15),
        ]
        inputs = processor(images=augmented_views, return_tensors="pt")
        emb = extract_backbone_embedding(model, inputs["pixel_values"])
        mean_proto = F.normalize(emb.mean(dim=0, keepdim=True), p=2, dim=-1)[0]
        prototypes[label_key] = mean_proto.cpu().tolist()
        print(f"[Calibrated] {label_key} -> 1280-dim L2 prototype from {len(augmented_views)} views")

    torch.save(prototypes, PROTOTYPES_PATH)
    print(f"Saved Indian plantation prototypes to: {PROTOTYPES_PATH}")


def finetune_on_folder(data_dir: str, epochs: int = 8, lr: float = 3e-4, batch_size: int = 16) -> None:
    """Fine-tune the MobileNetV2 classification head on a custom ImageFolder dataset."""
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Dataset directory not found: {data_dir}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    processor = MobileNetV2ImageProcessor.from_pretrained(MODEL_DIR, local_files_only=True)
    base_model = AutoModelForImageClassification.from_pretrained(MODEL_DIR, local_files_only=True)

    tfm = transforms.Compose(
        [
            transforms.RandomResizedCrop(224, scale=(0.75, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
            transforms.ToTensor(),
            transforms.Normalize(mean=processor.image_mean, std=processor.image_std),
        ]
    )

    full_ds = datasets.ImageFolder(data_dir, transform=tfm)
    num_classes = len(full_ds.classes)
    if num_classes < 2:
        raise ValueError("Dataset must contain at least 2 class subdirectories.")

    id2label = {i: name for i, name in enumerate(full_ds.classes)}
    label2id = {name: i for i, name in id2label.items()}

    # Replace classifier head for transfer learning
    in_features = base_model.classifier.in_features
    base_model.classifier = nn.Linear(in_features, num_classes)
    base_model.num_labels = num_classes
    base_model.config.num_labels = num_classes
    base_model.config.id2label = id2label
    base_model.config.label2id = label2id

    # Freeze early MobileNetV2 layers; unfreeze top blocks + classifier head
    for name, param in base_model.mobilenet_v2.named_parameters():
        param.requires_grad = ("layer.14" in name or "layer.15" in name or "conv_1x1" in name)
    for param in base_model.classifier.parameters():
        param.requires_grad = True

    base_model.to(device)

    val_size = max(1, int(0.2 * len(full_ds)))
    train_size = len(full_ds) - val_size
    train_ds, val_ds = random_split(full_ds, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, base_model.parameters()), lr=lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    print(f"Training MobileNetV2 on {device} | Classes: {num_classes} | Train: {train_size} | Val: {val_size}")
    for epoch in range(1, epochs + 1):
        base_model.train()
        running_loss = 0.0
        for imgs, targets in train_loader:
            imgs, targets = imgs.to(device), targets.to(device)
            optimizer.zero_grad()
            logits = base_model(pixel_values=imgs).logits
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * imgs.size(0)

        base_model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for imgs, targets in val_loader:
                imgs, targets = imgs.to(device), targets.to(device)
                preds = base_model(pixel_values=imgs).logits.argmax(dim=-1)
                correct += int((preds == targets).sum().item())
                total += targets.size(0)

        val_acc = (correct / max(1, total)) * 100.0
        print(f"  Epoch {epoch:02d}/{epochs:02d} | Loss: {running_loss / max(1, train_size):.4f} | Val Acc: {val_acc:.1f}%")

    out_dir = os.path.join(PROJECT_ROOT, "models", "leaf_disease_cnn_custom")
    os.makedirs(out_dir, exist_ok=True)
    processor.save_pretrained(out_dir)
    base_model.save_pretrained(out_dir)
    print(f"Saved fine-tuned model to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train or calibrate KisanVaani Leaf Disease PyTorch CNN")
    parser.add_argument("--data-dir", type=str, help="Path to ImageFolder dataset for transfer-learning fine-tuning")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--calibrate-indian-prototypes", action="store_true", help="Calibrate 1280-d Indian plantation prototypes")
    args = parser.parse_args()

    if args.calibrate_indian_prototypes:
        calibrate_indian_crop_prototypes()
    elif args.data_dir:
        finetune_on_folder(args.data_dir, epochs=args.epochs, lr=args.lr)
    else:
        parser.print_help()
