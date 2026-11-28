
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).parent
RAW_DIR = BASE_DIR / "dataset" / "raw"

PACKAGES = [
    "IWHR_AI_Lable_Floater_V1-package1",
    "IWHR_AI_Lable_Floater_V1-package2"
]

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"]
CLASS_MAP = {"floater": 0}

LABEL_DIR = BASE_DIR / "dataset" / "labels" / "all"
IMAGE_DIR = BASE_DIR / "dataset" / "images" / "all"

LABEL_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def convert_xml(xml_file, image_file):
    root = ET.parse(xml_file).getroot()

    size = root.find("size")
    image_width = int(size.find("width").text)
    image_height = int(size.find("height").text)

    labels = []

    for obj in root.findall("object"):
        class_name = obj.find("name").text.strip().lower()

        if class_name not in CLASS_MAP:
            continue

        box = obj.find("bndbox")

        xmin = float(box.find("xmin").text)
        ymin = float(box.find("ymin").text)
        xmax = float(box.find("xmax").text)
        ymax = float(box.find("ymax").text)

        if xmax <= xmin or ymax <= ymin:
            continue

        x_center = ((xmin + xmax) / 2) / image_width
        y_center = ((ymin + ymax) / 2) / image_height
        width = (xmax - xmin) / image_width
        height = (ymax - ymin) / image_height

        labels.append(
            f"{CLASS_MAP[class_name]} "
            f"{x_center:.6f} {y_center:.6f} "
            f"{width:.6f} {height:.6f}"
        )

    # Use the numbered XML filename stem for matching
    output_label = LABEL_DIR / f"{xml_file.stem}.txt"
    output_label.write_text("\n".join(labels), encoding="utf-8")

    # Copy the matched image using the same stem
    output_image = IMAGE_DIR / f"{xml_file.stem}{image_file.suffix.lower()}"

    if not output_image.exists():
        import shutil
        shutil.copy2(image_file, output_image)

    return len(labels)


if __name__ == "__main__":
    total_xml = 0
    total_images = 0
    total_objects = 0
    missing_images = []

    for package in PACKAGES:
        package_dir = RAW_DIR / package
        annotation_dir = package_dir / "Annotations"
        image_dir = package_dir / "JPEGImages"

        image_lookup = {
            path.stem: path
            for path in image_dir.iterdir()
            if path.suffix.lower() in IMAGE_EXTENSIONS
        }

        for xml_file in annotation_dir.glob("*.xml"):
            total_xml += 1

            image_file = image_lookup.get(xml_file.stem)

            if image_file is None:
                missing_images.append(str(xml_file))
                continue

            total_objects += convert_xml(xml_file, image_file)
            total_images += 1

    print("Dataset conversion completed!")
    print("XML files checked:", total_xml)
    print("Matched images:", total_images)
    print("Objects converted:", total_objects)
    print("Missing image matches:", len(missing_images))

    if missing_images:
        print("First 10 missing annotations:")
        for item in missing_images[:10]:
            print(item)
