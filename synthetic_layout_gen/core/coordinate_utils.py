# core/coordinate_utils.py

def reportlab_to_topleft(x: float, y: float, w: float, h: float, page_height_pt: float) -> tuple[float, float, float, float]:
    """ReportLab gives bottom-left origin (x, y) = bottom-left corner of the box.
    Returns (x0, y0, x1, y1) in top-left-origin points."""
    x0 = x
    x1 = x + w
    y0 = page_height_pt - (y + h)   # top edge
    y1 = page_height_pt - y          # bottom edge
    return (x0, y0, x1, y1)

def px_to_pt(px: float, dpi: int) -> float:
    return px * 72.0 / dpi

def pt_to_px(pt: float, dpi: int) -> float:
    return pt * dpi / 72.0

def strip_padding(allocated_bbox: tuple[float, float, float, float], padding_pt: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """padding_pt = (top, right, bottom, left), all subtracted inward."""
    x0, y0, x1, y1 = allocated_bbox
    top, right, bottom, left = padding_pt
    return (x0 + left, y0 + top, x1 - right, y1 - bottom)

def pdf_to_images(pdf_path: str, output_image_dir: str, prefix: str) -> list[str]:
    import fitz
    import os
    doc = fitz.open(pdf_path)
    image_paths = []
    os.makedirs(output_image_dir, exist_ok=True)
    for i in range(len(doc)):
        page = doc[i]
        zoom = 150.0 / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_path = os.path.join(output_image_dir, f"{prefix}_p{i+1}.png")
        pix.save(img_path)
        image_paths.append(img_path)
    doc.close()
    return image_paths

def degrade_to_scanlike(image_path: str, out_path: str, severity: float = 1.0):
    from PIL import Image, ImageEnhance, ImageFilter
    import random
    import numpy as np
    
    img = Image.open(image_path).convert("RGB")
    
    angle = random.uniform(-2.0, 2.0)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
    
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(random.uniform(0.7, 0.95))
    
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(random.uniform(0.95, 1.05))
    
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, random.uniform(2.0, 5.0), arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    
    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.1, 0.4)))
    img.save(out_path)

