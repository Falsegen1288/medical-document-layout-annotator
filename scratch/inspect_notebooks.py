# scratch/inspect_notebooks.py
import json
import os

notebooks = [
    "synthetic_evaluation_benchmark.ipynb",
    "layout-detection-evaluation.ipynb",
    "layout_detection_benchmark.ipynb"
]

for nb in notebooks:
    if not os.path.exists(nb):
        print(f"{nb} does not exist.")
        continue
    print(f"=== Inspecting {nb} ===")
    with open(nb, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"Error reading {nb}: {e}")
            continue
            
    cells = data.get("cells", [])
    print(f"Total cells: {len(cells)}")
    for i, cell in enumerate(cells):
        ctype = cell.get("cell_type")
        source = cell.get("source", [])
        source_str = "".join(source)
        if ctype == "markdown":
            # Print the first few lines of markdown cells
            lines = source_str.strip().split("\n")
            first_line = lines[0] if lines else ""
            if first_line.startswith("#"):
                print(f"  [{i}] Markdown: {first_line}")
        elif ctype == "code":
            # Check if it imports major libraries or has evaluation functions
            if "compute_map" in source_str or "evaluate" in source_str or "DocLayoutYOLO" in source_str or "Nemotron" in source_str:
                short_code = source_str.strip()[:100].replace("\n", " ")
                print(f"  [{i}] Code (relevant): {short_code}...")
    print("-" * 50)
