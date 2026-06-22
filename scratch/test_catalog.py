# scratch/test_catalog.py
import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from synthetic_layout_gen.domains.commercial_catalog.generator import generate_one
from synthetic_layout_gen.qa.render_overlay import render_overlays_for_doc

def main():
    print("Generating one sample of commercial_catalog...")
    generate_one(sample_id=1, seed=12345, output_root="output/")
    
    json_path = "output/commercial_catalog/json/commercial_catalog_00001.json"
    pdf_path = "output/commercial_catalog/pdfs/commercial_catalog_00001.pdf"
    overlay_dir = "qa/overlays/commercial_catalog"
    
    print("JSON file exists:", os.path.exists(json_path))
    print("PDF file exists:", os.path.exists(pdf_path))
    
    # Render overlay to check visually
    if os.path.exists(json_path) and os.path.exists(pdf_path):
        print("Rendering overlays...")
        render_overlays_for_doc(json_path, pdf_path, overlay_dir)
        print(f"Overlay rendered to {overlay_dir}")

if __name__ == "__main__":
    main()
