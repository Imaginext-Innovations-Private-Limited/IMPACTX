import pickle

path = "model/data_exfiltration/cyvora_exfiltration_features.pkl"

with open(path, "rb") as f:
    features = pickle.load(f)

print("Feature count:", len(features))
print("Features:")
for i, feature in enumerate(features, 1):
    print(i, feature)