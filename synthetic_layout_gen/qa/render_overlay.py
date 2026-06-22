# qa/render_overlay.py
import os
import json
import fitz  # PyMuPDF
from PIL import Image, ImageDraw

COLOR_MAP = {
    "title": "red",
    "text": "blue",
    "table": "green",
    "picture": "magenta",
    "list_item": "cyan",
    "caption": "yellow",
    "section_header": "orange",
    "page_footer": "gray",
    "page_header": "purple",
    "formula": "brown",
    "footnote": "teal"
}

def render_overlays_for_doc(json_path: str, pdf_path: str, output_dir: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    doc_id = data["document_id"]
    
    # Load PDF
    pdf_doc = fitz.open(pdf_path)
    
    for page_data in data["pages"]:
        p_num = page_data["page_number"]
        page_idx = p_num - 1
        if page_idx >= len(pdf_doc):
            print(f"[Warning] PDF {pdf_path} does not have page index {page_idx}")
            continue
            
        pdf_page = pdf_doc[page_idx]
        
        # Rasterize PDF page at 150 DPI (matching output image DPI)
        zoom = 150.0 / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = pdf_page.get_pixmap(matrix=mat)
        img_pdf = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw_pdf = ImageDraw.Draw(img_pdf)
        
        # Open original image if it exists
        orig_img_path = page_data["image_path"]
        img_orig = None
        if os.path.exists(orig_img_path):
            img_orig = Image.open(orig_img_path).convert("RGB")
            draw_orig = ImageDraw.Draw(img_orig)
            
        for elem in page_data["layout_elements"]:
            bbox = elem["bbox"]
            etype = elem["type"]
            color = COLOR_MAP.get(etype, "red")
            
            # Convert pt to px (150 DPI)
            x0_px = bbox[0] * 150.0 / 72.0
            y0_px = bbox[1] * 150.0 / 72.0
            x1_px = bbox[2] * 150.0 / 72.0
            y1_px = bbox[3] * 150.0 / 72.0
            
            box_coords = [x0_px, y0_px, x1_px, y1_px]
            
            # Draw element bbox
            draw_pdf.rectangle(box_coords, outline=color, width=2)
            if img_orig is not None:
                draw_orig.rectangle(box_coords, outline=color, width=2)
                
            # If table, draw cells as well
            if etype == "table" and "cells" in elem["attributes"]:
                for cell in elem["attributes"]["cells"]:
                    c_bbox = cell["bbox"]
                    cx0 = c_bbox[0] * 150.0 / 72.0
                    cy0 = c_bbox[1] * 150.0 / 72.0
                    cx1 = c_bbox[2] * 150.0 / 72.0
                    cy1 = c_bbox[3] * 150.0 / 72.0
                    
                    draw_pdf.rectangle([cx0, cy0, cx1, cy1], outline="yellow", width=1)
                    if img_orig is not None:
                        draw_orig.rectangle([cx0, cy0, cx1, cy1], outline="yellow", width=1)
                        
        # Save output images
        os.makedirs(output_dir, exist_ok=True)
        pdf_overlay_path = os.path.join(output_dir, f"{doc_id}_p{p_num}_pdf_overlay.png")
        img_pdf.save(pdf_overlay_path)
        
        if img_orig is not None:
            orig_overlay_path = os.path.join(output_dir, f"{doc_id}_p{p_num}_orig_overlay.png")
            img_orig.save(orig_overlay_path)
            
    pdf_doc.close()
