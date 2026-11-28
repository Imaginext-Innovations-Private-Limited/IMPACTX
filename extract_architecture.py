import json
import os

base = r"D:\FINAL DFDT"

notebooks = [
    "07_amsf_gnet_architecture.ipynb",
    "08_degradation_descriptor_consistency_UPDATED.ipynb"
]

output_path = os.path.join(
    base,
    "deployment_architecture_source.txt"
)

with open(output_path, "w", encoding="utf-8") as output:
    for notebook_name in notebooks:
        notebook_path = os.path.join(base, notebook_name)

        with open(notebook_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        output.write("\n" + "=" * 100 + "\n")
        output.write("NOTEBOOK: " + notebook_name + "\n")
        output.write("=" * 100 + "\n")

        for index, cell in enumerate(notebook["cells"]):
            if cell.get("cell_type") == "code":
                source = "".join(cell.get("source", []))
                output.write(f"\n\n# CELL INDEX: {index}\n")
                output.write(source)
                output.write("\n")

print("SOURCE EXPORT COMPLETED")
print("Output:", output_path)
print("File size:", round(os.path.getsize(output_path) / 1024, 2), "KB")
