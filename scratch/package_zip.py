"""
Package the synthetic layout dataset into a ZIP file.
Includes: all PDFs, PNGs, GT JSONs for 20 samples x 5 domains,
          layout_corpora/ with harvested stats, tools/source_manifest.md

Usage:
    cd medical-document-layout-annotator
    venv\Scripts\python.exe scratch\package_zip.py
"""
import os
import zipfile
import glob

OUTPUT_ROOT = "output/"
ZIP_PATH = "synthetic_layout_dataset.zip"

DOMAINS = [
    "financial_invoice",
    "scientific_paper",
    "legal_opinion",
    "medical_report",
    "commercial_catalog",
]

def package():
    files_added = 0
    
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add all domain outputs
        for domain in DOMAINS:
            for subdir in ["json", "pdfs", "images"]:
                pattern = os.path.join(OUTPUT_ROOT, domain, subdir, "*")
                for filepath in sorted(glob.glob(pattern)):
                    if os.path.isfile(filepath):
                        arcname = os.path.relpath(filepath, ".").replace("\\", "/")
                        zf.write(filepath, arcname)
                        files_added += 1
        
        # 2. Add layout_corpora/ directory
        corpora_dir = "layout_corpora"
        if os.path.isdir(corpora_dir):
            for root, dirs, files in os.walk(corpora_dir):
                for f in files:
                    filepath = os.path.join(root, f)
                    arcname = os.path.relpath(filepath, ".").replace("\\", "/")
                    zf.write(filepath, arcname)
                    files_added += 1
        
        # 3. Add tools/source_manifest.md
        manifest = "tools/source_manifest.md"
        if os.path.exists(manifest):
            zf.write(manifest, manifest.replace("\\", "/"))
            files_added += 1
        
        # 4. Add schema
        schema = "synthetic_layout_gen/schema/ground_truth.schema.json"
        if os.path.exists(schema):
            zf.write(schema, schema.replace("\\", "/"))
            files_added += 1
        
        # 5. Add benchmark results if available
        bench_dir = "benchmark_output"
        if os.path.isdir(bench_dir):
            for root, dirs, files in os.walk(bench_dir):
                for f in files:
                    filepath = os.path.join(root, f)
                    arcname = os.path.relpath(filepath, ".").replace("\\", "/")
                    zf.write(filepath, arcname)
                    files_added += 1
    
    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print(f"Created {ZIP_PATH} with {files_added} files ({size_mb:.1f} MB)")

if __name__ == "__main__":
    package()
