
import pandas as pd
import shutil
from pathlib import Path

# ==========================================
# PATHS
# ==========================================

PROJECT_DIR = Path(r"D:\FINAL DFDT")

MANIFEST = (
    PROJECT_DIR
    / "SELECTED_DATASET"
    / "splits"
    / "dataset_split_manifest.csv"
)

DATASET_DIR = PROJECT_DIR / "SELECTED_DATASET"

OUTPUT_DIR = PROJECT_DIR / "TEST_DATA_SEPARATE"

# ==========================================
# LOAD ORIGINAL SPLIT MANIFEST
# ==========================================

df = pd.read_csv(MANIFEST)

required_columns = {
    "class",
    "destination_image",
    "split"
}

if not required_columns.issubset(df.columns):
    raise ValueError("Manifest is missing required columns.")

# Select only original test images
test_df = df[
    df["split"].astype(str).str.lower() == "test"
].copy()

if test_df.empty:
    raise ValueError(
        "No test records found in the manifest. "
        "Check the split column."
    )

# ==========================================
# CREATE OUTPUT FOLDERS
# ==========================================

for label in ["REAL", "FAKE"]:
    (OUTPUT_DIR / label).mkdir(
        parents=True,
        exist_ok=True
    )

# ==========================================
# COPY TEST IMAGES
# ==========================================

counts = {"REAL": 0, "FAKE": 0}
missing = []

for _, row in test_df.iterrows():

    label = str(row["class"]).strip().upper()

    if label not in counts:
        continue

    source = Path(str(row["destination_image"]))

    # Support manifest paths from another drive
    if not source.is_absolute():
        source = DATASET_DIR / source

    if not source.exists():
        missing.append(str(source))
        continue

    destination_folder = OUTPUT_DIR / label
    destination = destination_folder / source.name

    # Avoid filename collisions
    if destination.exists():
        destination = destination_folder / (
            source.stem + "_" +
            str(counts[label]) + source.suffix
        )

    shutil.copy2(source, destination)
    counts[label] += 1

# ==========================================
# REPORT
# ==========================================

print("\nTEST DATA EXTRACTION COMPLETED")
print("=" * 40)

print("REAL images:", counts["REAL"])
print("FAKE images:", counts["FAKE"])
print("TOTAL COPIED:", sum(counts.values()))
print("MISSING FILES:", len(missing))

print("\nOutput folder:")
print(OUTPUT_DIR)

if missing:
    print("\nFirst missing files:")
    for path in missing[:10]:
        print(path)

print("\nOriginal dataset has not been modified.")

