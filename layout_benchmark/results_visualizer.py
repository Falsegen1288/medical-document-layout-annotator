# layout_benchmark/results_visualizer.py
import os
import json
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

def draw_bboxes(img, bboxes, color, width=2):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for b in bboxes:
        draw.rectangle(b["bbox"], outline=color, width=width)
    return Image.alpha_composite(img.convert("RGBA"), overlay)

def generate_visual_comparisons():
    pdf_path = r"d:\antigravity\benchmarking\MedCore_Catalogue_v2.pdf"
    gt_raw_path = r"d:\antigravity\benchmarking\MedCore_GT_v2.json"
    gt_tight_path = r"d:\antigravity\benchmarking\layout_GT_custom_tightened.json"
    pred_path = r"d:\antigravity\benchmarking\results\evaluation\predictions_cache.json"
    output_dir = r"d:\antigravity\benchmarking\layout_benchmark\results\verification"
    os.makedirs(output_dir, exist_ok=True)
    
    # Render all pages at 150 DPI
    doc = fitz.open(pdf_path)
    page_images = {}
    scale = 150 / 72
    mat = fitz.Matrix(scale, scale)
    for p_idx in range(len(doc)):
        page = doc[p_idx]
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_images[p_idx + 1] = img
    doc.close()
    
    # Load GTs
    def load_boxes(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        boxes = {}
        for p in data["pages"]:
            b_list = []
            for elem in p["elements"]:
                b = elem["bbox_pt"]
                # Convert
                y0 = 841.89 - (b["y"] + b["h"])
                y1 = 841.89 - b["y"]
                b_list.append({
                    "bbox": [b["x"] * scale, y0 * scale, (b["x"] + b["w"]) * scale, y1 * scale],
                    "label": elem["class"]
                })
            boxes[p["page"]] = b_list
        return boxes
        
    gt_raw_boxes = load_boxes(gt_raw_path)
    gt_tight_boxes = load_boxes(gt_tight_path)
    
    # Load Preds
    with open(pred_path, "r", encoding="utf-8") as f:
        preds = json.load(f)
        
    for p_num in page_images.keys():
        img = page_images[p_num].convert("RGBA")
        
        # DocLayoutYOLO predictions for this page
        dl_preds = preds["docling"][p_num - 1]
        dl_boxes = []
        for pr in dl_preds:
            dl_boxes.append({
                "bbox": [pr["bbox"][0] * scale, pr["bbox"][1] * scale, pr["bbox"][2] * scale, pr["bbox"][3] * scale]
            })
            
        # Nemotron predictions for this page
        nm_preds = preds["nemotron"][p_num - 1]
        nm_boxes = []
        for pr in nm_preds:
            nm_boxes.append({
                "bbox": [pr["bbox"][0] * scale, pr["bbox"][1] * scale, pr["bbox"][2] * scale, pr["bbox"][3] * scale]
            })
            
        # Draw comparison grids
        # 1. GT-raw (Red) vs GT-tight (Green)
        gt_img = img.copy()
        gt_img = draw_bboxes(gt_img, gt_raw_boxes[p_num], (255, 0, 0, 255), width=2)
        gt_img = draw_bboxes(gt_img, gt_tight_boxes[p_num], (0, 255, 0, 255), width=2)
        
        # 2. GT-tight (Green) vs DocLayoutYOLO predictions (Blue)
        dl_img = img.copy()
        dl_img = draw_bboxes(dl_img, gt_tight_boxes[p_num], (0, 255, 0, 255), width=2)
        dl_img = draw_bboxes(dl_img, dl_boxes, (0, 0, 255, 255), width=2)
        
        # 3. GT-tight (Green) vs Nemotron predictions (Orange)
        nm_img = img.copy()
        nm_img = draw_bboxes(nm_img, gt_tight_boxes[p_num], (0, 255, 0, 255), width=2)
        nm_img = draw_bboxes(nm_img, nm_boxes, (255, 128, 0, 255), width=2)
        
        # Save side-by-side or individually
        gt_img.convert("RGB").save(os.path.join(output_dir, f"page_{p_num}_gt_raw_vs_tight.png"))
        dl_img.convert("RGB").save(os.path.join(output_dir, f"page_{p_num}_yolo_vs_tight_gt.png"))
        nm_img.convert("RGB").save(os.path.join(output_dir, f"page_{p_num}_nemotron_vs_tight_gt.png"))
        
    print(f"Visual overlay images generated and saved to: {output_dir}")

if __name__ == "__main__":
    generate_visual_comparisons()
