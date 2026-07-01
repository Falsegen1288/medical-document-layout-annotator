# layout_benchmark/gt_tighten.py
import json
import os
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw

def run_gt_tighten():
    pdf_path = r"d:\antigravity\benchmarking\MedCore_Catalogue_v2.pdf"
    gt_path = r"d:\antigravity\benchmarking\MedCore_GT_v2.json"
    out_gt_path = r"d:\antigravity\benchmarking\layout_GT_custom_tightened.json"
    verification_dir = r"d:\antigravity\benchmarking\layout_benchmark\results\verification"
    os.makedirs(verification_dir, exist_ok=True)
    
    # 1. Load GT
    with open(gt_path, "r", encoding="utf-8") as f:
        gt_data = json.load(f)
        
    doc = fitz.open(pdf_path)
    
    # Render all pages at 150 DPI for visual verification
    page_images = {}
    scale = 150 / 72
    mat = fitz.Matrix(scale, scale)
    for p_idx in range(len(doc)):
        page = doc[p_idx]
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_images[p_idx + 1] = img.convert("RGBA")
        
    doc.close()
    
    ph_pt = 841.89
    pw_pt = 595.28
    
    text_classes = {
        'title', 'paragraph', 'caption', 'spec_list', 'section_header', 
        'header', 'footer', 'list', 'price_tag'
    }
    
    verification_log = []
    
    # Process each page and element
    for page_entry in gt_data["pages"]:
        page_num = page_entry["page"]
        img = page_images[page_num]
        pw, ph = img.size
        scale_x = pw / pw_pt
        scale_y = ph / ph_pt
        
        # Prepare drawing overlay
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        for elem in page_entry["elements"]:
            bbox = elem["bbox_pt"]
            cls = elem["class"]
            elem_id = elem["id"]
            
            # Original coords in image pixels
            x0 = bbox["x"] * scale_x
            y0 = (ph_pt - (bbox["y"] + bbox["h"])) * scale_y
            x1 = (bbox["x"] + bbox["w"]) * scale_x
            y1 = (ph_pt - bbox["y"]) * scale_y
            
            x0_px = max(0, int(round(min(x0, x1))))
            x1_px = min(pw, int(round(max(x0, x1))))
            y0_px = max(0, int(round(min(y0, y1))))
            y1_px = min(ph, int(round(max(y0, y1))))
            
            w = x1_px - x0_px
            h = y1_px - y0_px
            
            # Draw original GT box (Red)
            draw.rectangle([x0_px, y0_px, x1_px, y1_px], outline=(255, 0, 0, 255), width=2)
            
            tightened = False
            x0_t, y0_t, x1_t, y1_t = x0_px, y0_px, x1_px, y1_px
            
            if cls in text_classes and w > 4 and h > 4:
                # Crop and binarize
                crop = img.crop((x0_px, y0_px, x1_px, y1_px)).convert("RGB")
                arr = np.array(crop)
                
                border_pixels = []
                border_pixels.extend(arr[0, :, :])
                border_pixels.extend(arr[-1, :, :])
                border_pixels.extend(arr[:, 0, :])
                border_pixels.extend(arr[:, -1, :])
                bg_color = np.median(border_pixels, axis=0)
                
                dist = np.linalg.norm(arr - bg_color, axis=2)
                ink = dist > 35
                
                rows = np.any(ink, axis=1)
                cols = np.any(ink, axis=0)
                
                if np.any(rows) and np.any(cols):
                    ymin, ymax = np.where(rows)[0][0], np.where(rows)[0][-1]
                    xmin, xmax = np.where(cols)[0][0], np.where(cols)[0][-1]
                    
                    # Convert crop relative offsets to page absolute coordinates
                    # Add 3px padding buffer
                    x0_t = max(x0_px, x0_px + xmin - 3)
                    y0_t = max(y0_px, y0_px + ymin - 3)
                    x1_t = min(x1_px, x0_px + xmax + 3)
                    y1_t = min(y1_px, y0_px + ymax + 3)
                    
                    tightened = True
                    
            if tightened:
                # Draw tightened GT box (Green)
                draw.rectangle([x0_t, y0_t, x1_t, y1_t], outline=(0, 255, 0, 255), width=2)
                
                # Convert back to PDF points
                new_x = x0_t / scale_x
                new_y = ph_pt - (y1_t / scale_y)
                new_w = (x1_t - x0_t) / scale_x
                new_h = (y1_t - y0_t) / scale_y
                
                elem["bbox_pt"] = {
                    "x": round(new_x, 2),
                    "y": round(new_y, 2),
                    "w": round(new_w, 2),
                    "h": round(new_h, 2)
                }
                
                # Normalize coords (relative to page size)
                norm_x = new_x / pw_pt
                norm_y = (ph_pt - (new_y + new_h)) / ph_pt
                norm_w = new_w / pw_pt
                norm_h = new_h / ph_pt
                
                elem["bbox_norm"] = {
                    "x": round(norm_x, 5),
                    "y": round(norm_y, 5),
                    "w": round(norm_w, 5),
                    "h": round(norm_h, 5)
                }
                
                # Update YOLO label format representation
                cx_norm = norm_x + (norm_w / 2)
                cy_norm = norm_y + (norm_h / 2)
                elem["yolo"] = f"{elem['class_id']} {cx_norm:.4f} {cy_norm:.4f} {norm_w:.4f} {norm_h:.4f}"
                
                verification_log.append(f"Element {elem_id} ({cls}) tightened from {w}x{h}px to {x1_t-x0_t}x{y1_t-y0_t}px")
            else:
                # Keep original and draw outline
                draw.rectangle([x0_px, y0_px, x1_px, y1_px], outline=(0, 0, 255, 255), width=1)
                
        # Save verification page overlays
        base_img = img.copy()
        combined = Image.alpha_composite(base_img, overlay).convert("RGB")
        comb_path = os.path.join(verification_dir, f"page_{page_num}_verification.png")
        combined.save(comb_path)
        
    # 3. Save tightened GT to new file
    with open(out_gt_path, "w", encoding="utf-8") as f:
        json.dump(gt_data, f, indent=2)
        
    print(f"Tightened GT saved successfully to: {out_gt_path}")
    print(f"Visual verification overlays saved to: {verification_dir}")
    print(f"Total elements tightened: {len(verification_log)}")
    
    # Save verification text log
    log_path = os.path.join(verification_dir, "tightening_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(verification_log))
        
if __name__ == "__main__":
    run_gt_tighten()
