# layout_benchmark/gt_audit.py
import json
import os
import fitz  # PyMuPDF
import numpy as np
import pandas as pd
from PIL import Image

def run_gt_audit():
    pdf_path = r"d:\antigravity\benchmarking\MedCore_Catalogue_v2.pdf"
    gt_path = r"d:\antigravity\benchmarking\MedCore_GT_v2.json"
    output_dir = r"d:\antigravity\benchmarking\layout_benchmark\results"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load GT
    with open(gt_path, "r", encoding="utf-8") as f:
        gt_data = json.load(f)
        
    doc = fitz.open(pdf_path)
    
    # Render all pages at 150 DPI
    page_images = {}
    scale = 150 / 72
    mat = fitz.Matrix(scale, scale)
    for p_idx in range(len(doc)):
        page = doc[p_idx]
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_images[p_idx + 1] = img
        
    doc.close()
    
    ph_pt = 841.89
    pw_pt = 595.28
    
    audit_records = []
    
    # Process each element
    for page_entry in gt_data["pages"]:
        page_num = page_entry["page"]
        img = page_images[page_num]
        pw, ph = img.size
        scale_x = pw / pw_pt
        scale_y = ph / ph_pt
        
        for elem in page_entry["elements"]:
            bbox = elem["bbox_pt"]
            cls = elem["class"]
            elem_id = elem["id"]
            
            # Convert to image pixel space
            x0 = bbox["x"] * scale_x
            y0 = (ph_pt - (bbox["y"] + bbox["h"])) * scale_y
            x1 = (bbox["x"] + bbox["w"]) * scale_x
            y1 = (ph_pt - bbox["y"]) * scale_y
            
            x0, x1 = max(0, int(round(min(x0, x1)))), min(pw, int(round(max(x0, x1))))
            y0, y1 = max(0, int(round(min(y0, y1)))), min(ph, int(round(max(y0, y1))))
            
            w = x1 - x0
            h = y1 - y0
            
            if w <= 4 or h <= 4:
                audit_records.append({
                    "id": elem_id, "class": cls, "page": page_num,
                    "w_px": w, "h_px": h,
                    "pad_left_px": 0, "pad_right_px": 0, "pad_top_px": 0, "pad_bottom_px": 0,
                    "pad_left_frac": 0.0, "pad_right_frac": 0.0, "pad_top_frac": 0.0, "pad_bottom_frac": 0.0
                })
                continue
                
            # Crop
            crop = img.crop((x0, y0, x1, y1))
            arr = np.array(crop)
            
            # Determine dominant border background color
            border_pixels = []
            border_pixels.extend(arr[0, :, :])
            border_pixels.extend(arr[-1, :, :])
            border_pixels.extend(arr[:, 0, :])
            border_pixels.extend(arr[:, -1, :])
            bg_color = np.median(border_pixels, axis=0)
            
            # Binarize
            dist = np.linalg.norm(arr - bg_color, axis=2)
            ink = dist > 35
            
            rows = np.any(ink, axis=1)
            cols = np.any(ink, axis=0)
            
            if not np.any(rows) or not np.any(cols):
                # Empty or background element
                audit_records.append({
                    "id": elem_id, "class": cls, "page": page_num,
                    "w_px": w, "h_px": h,
                    "pad_left_px": 0, "pad_right_px": 0, "pad_top_px": 0, "pad_bottom_px": 0,
                    "pad_left_frac": 0.0, "pad_right_frac": 0.0, "pad_top_frac": 0.0, "pad_bottom_frac": 0.0
                })
            else:
                ymin, ymax = np.where(rows)[0][0], np.where(rows)[0][-1]
                xmin, xmax = np.where(cols)[0][0], np.where(cols)[0][-1]
                
                pad_left = xmin
                pad_right = (w - 1) - xmax
                pad_top = ymin
                pad_bottom = (h - 1) - ymax
                
                audit_records.append({
                    "id": elem_id, "class": cls, "page": page_num,
                    "w_px": w, "h_px": h,
                    "pad_left_px": int(pad_left),
                    "pad_right_px": int(pad_right),
                    "pad_top_px": int(pad_top),
                    "pad_bottom_px": int(pad_bottom),
                    "pad_left_frac": float(pad_left / w),
                    "pad_right_frac": float(pad_right / w),
                    "pad_top_frac": float(pad_top / h),
                    "pad_bottom_frac": float(pad_bottom / h)
                })

    df = pd.DataFrame(audit_records)
    
    # Group by class to calculate average padding metrics
    summary = df.groupby("class").agg({
        "pad_left_frac": ["mean", "median"],
        "pad_right_frac": ["mean", "median"],
        "pad_top_frac": ["mean", "median"],
        "pad_bottom_frac": ["mean", "median"],
        "id": "count"
    })
    
    summary.columns = [
        "pad_left_mean", "pad_left_median",
        "pad_right_mean", "pad_right_median",
        "pad_top_mean", "pad_top_median",
        "pad_bottom_mean", "pad_bottom_median",
        "count"
    ]
    
    summary_path = os.path.join(output_dir, "gt_padding_audit.csv")
    summary.to_csv(summary_path)
    print(f"Audit completed. Summary written to {summary_path}")
    print("\nSummary statistics:")
    print(summary.to_string())

if __name__ == "__main__":
    run_gt_audit()
