import torch
import json
from pathlib import Path

checkpoint_path = Path(
    r"experiment_v3_degradation_aware\checkpoints\model_B_v3_best.pth"
)

normalization_path = Path(
    r"SELECTED_DATASET\degradation_features_160\descriptor_normalization_160.json"
)

print("CHECKPOINT EXISTS:", checkpoint_path.exists())
print("NORMALIZATION EXISTS:", normalization_path.exists())

checkpoint = torch.load(
    checkpoint_path,
    map_location="cpu",
    weights_only=False
)

print("\nCHECKPOINT TYPE:", type(checkpoint))

if isinstance(checkpoint, dict):
    print("\nCHECKPOINT KEYS:")
    for key, value in checkpoint.items():
        if isinstance(value, dict):
            print(key, "-> dictionary,", len(value), "entries")
        else:
            print(key, "->", value)

    state = checkpoint.get("model_state_dict", checkpoint)

    print("\nSTATE DICT KEY COUNT:", len(state))
    print("\nFIRST 30 STATE DICT KEYS:")
    for key in list(state.keys())[:30]:
        print(key, tuple(state[key].shape) if hasattr(state[key], "shape") else type(state[key]))

print("\nNORMALIZATION PARAMETERS:")
with open(normalization_path, "r", encoding="utf-8") as f:
    params = json.load(f)

print(json.dumps(params, indent=2))
