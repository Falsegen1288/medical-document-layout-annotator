# scratch/inspect_claude_zip.py
import zipfile

zip_path = "synthetic_by_claude.zip"
try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        print(f"Loaded {zip_path}")
        names = zip_ref.namelist()
        print(f"Total files: {len(names)}")
        for name in names:
            print(f"  {name}")
except Exception as e:
    print(f"Error reading zip: {e}")
