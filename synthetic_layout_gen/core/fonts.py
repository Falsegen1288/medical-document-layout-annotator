# core/fonts.py
import math
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def register_fonts():
    # ReportLab includes the standard 14 Type 1 fonts by default:
    # Helvetica, Helvetica-Bold, Helvetica-Oblique, Helvetica-BoldOblique,
    # Times-Roman, Times-Bold, Times-Italic, Times-BoldItalic,
    # Courier, Courier-Bold, Courier-Oblique, Courier-BoldOblique,
    # Symbol, ZapfDingbats.
    # No extra registration needed for these.
    pass

def get_text_width(text: str, font_name: str, font_size: float) -> float:
    """Returns width of the text in points."""
    try:
        return pdfmetrics.stringWidth(text, font_name, font_size)
    except Exception:
        return pdfmetrics.stringWidth(text, "Helvetica", font_size)

def compute_rotated_text_bbox(text: str, font_name: str, font_size: float, x: float, y: float, angle_deg: float, page_height_pt: float) -> tuple[float, float, float, float]:
    """Computes the axis-aligned bounding box (x0, y0, x1, y1) in top-left origin points
    for text drawn at (x, y) (bottom-left origin) and rotated by angle_deg around (x, y)."""
    w = get_text_width(text, font_name, font_size)
    # Estimate text height using font_size * 0.75
    h = font_size * 0.75
    
    # Local coordinates of the text box corners
    corners = [
        (0.0, 0.0),
        (w, 0.0),
        (w, h),
        (0.0, h)
    ]
    
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    rotated_corners = []
    for cx, cy in corners:
        rx = x + (cx * cos_a - cy * sin_a)
        ry = y + (cx * sin_a + cy * cos_a)
        rotated_corners.append((rx, ry))
        
    min_x = min(c[0] for c in rotated_corners)
    max_x = max(c[0] for c in rotated_corners)
    min_y = min(c[1] for c in rotated_corners)
    max_y = max(c[1] for c in rotated_corners)
    
    x0 = min_x
    x1 = max_x
    y0 = page_height_pt - max_y
    y1 = page_height_pt - min_y
    
    return (x0, y0, x1, y1)

def compute_rotated_centered_text_bbox(text: str, font_name: str, font_size: float, x: float, y: float, angle_deg: float, page_height_pt: float) -> tuple[float, float, float, float]:
    """Computes the axis-aligned bounding box (x0, y0, x1, y1) in top-left origin points
    for text drawn centered at (x, y) (bottom-left origin) and rotated by angle_deg around (x, y)."""
    w = get_text_width(text, font_name, font_size)
    h = font_size * 0.75
    
    # Local coordinates of the text box corners for centered text
    corners = [
        (-w / 2.0, 0.0),
        (w / 2.0, 0.0),
        (w / 2.0, h),
        (-w / 2.0, h)
    ]
    
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    rotated_corners = []
    for cx, cy in corners:
        rx = x + (cx * cos_a - cy * sin_a)
        ry = y + (cx * sin_a + cy * cos_a)
        rotated_corners.append((rx, ry))
        
    min_x = min(c[0] for c in rotated_corners)
    max_x = max(c[0] for c in rotated_corners)
    min_y = min(c[1] for c in rotated_corners)
    max_y = max(c[1] for c in rotated_corners)
    
    x0 = min_x
    x1 = max_x
    y0 = page_height_pt - max_y
    y1 = page_height_pt - min_y
    
    return (x0, y0, x1, y1)

