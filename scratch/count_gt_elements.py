# scratch/count_gt_elements.py
import json

json_path = "layout_corpora/synthetic_by_claude/MedCore_Catalogue_groundtruth.json"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for p_idx, page in enumerate(data["pages"]):
    print(f"=== Page {p_idx+1} ===")
    counts = {}
    for elem in page["elements"]:
        cls = elem["class"]
        counts[cls] = counts.get(cls, 0) + 1
        # Check if coordinates are out of bounds or negative
        bbox = elem["bbox_pt"]
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        if y < 0 or y+h > 841.89 or x < 0 or x+w > 595.28:
            print(f"  Warning: out-of-bounds {cls} bbox: x={x:.2f}, y={y:.2f}, w={w:.2f}, h={h:.2f}")
    for cls, count in sorted(counts.items()):
        print(f"  {cls}: {count}")
