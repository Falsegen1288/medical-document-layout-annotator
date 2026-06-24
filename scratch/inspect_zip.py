# scratch/inspect_zip.py
import zipfile

zip_path = "synthetic_layout_dataset.zip"
try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        print(f"Loaded {zip_path}")
        names = zip_ref.namelist()
        print(f"Total files: {len(names)}")
        print("First 20 files:")
        for name in names[:20]:
            print(f"  {name}")
except Exception as e:
    print(f"Error reading zip: {e}")
