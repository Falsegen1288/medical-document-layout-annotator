# scratch/print_gt_debug.py
import json

json_path = "layout_corpora/synthetic_by_claude/MedCore_Catalogue_groundtruth.json"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=== GROUND TRUTH PAGE 3 ===")
page = data["pages"][2] # Page 3 is 0-indexed index 2
for elem in page["elements"]:
    bbox = elem["bbox_pt"]
    print(f"Class: {elem['class']} | bbox: x={bbox['x']:.2f}, y={bbox['y']:.2f}, w={bbox['w']:.2f}, h={bbox['h']:.2f}")
