
from pathlib import Path
import random
import shutil

BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / "dataset"

IMAGE_DIR = DATASET_DIR / "images" / "all"
LABEL_DIR = DATASET_DIR / "labels" / "all"

random.seed(42)

images = list(IMAGE_DIR.glob("*.jpg"))
random.shuffle(images)

split_index = int(len(images) * 0.8)

train_images = images[:split_index]
val_images = images[split_index:]

def copy_files(image_list, split):
    image_output = DATASET_DIR / "images" / split
    label_output = DATASET_DIR / "labels" / split

    image_output.mkdir(parents=True, exist_ok=True)
    label_output.mkdir(parents=True, exist_ok=True)

    for image in image_list:
        label = LABEL_DIR / f"{image.stem}.txt"

        if not label.exists():
            raise FileNotFoundError(f"Missing label: {label}")

        shutil.copy2(image, image_output / image.name)
        shutil.copy2(label, label_output / label.name)

copy_files(train_images, "train")
copy_files(val_images, "val")

print("Dataset splitting completed!")
print("Training images:", len(train_images))
print("Validation images:", len(val_images))
print("Total images:", len(images))
