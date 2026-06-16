"""
DEBUG STEP 1 — Isolate which import causes the access violation.

Run this as a plain .py script from the SAME venv (not inside the Jupyter kernel),
e.g. from cmd/powershell in the project folder:

    venv\\Scripts\\python.exe debug_kernel_crash_step1_imports.py

Why a script and not a notebook cell: if the crash is a native DLL-level access
violation, the whole kernel process dies and you may not even see which line
caused it inside the notebook. Running as a script with flush=True prints lets
you see exactly which import survives and which one kills the process (the
process will just disappear / exit code will be non-zero after the last
printed line).

This script imports each major dependency ONE AT A TIME, with a clear print
after each successful import. Run it, then tell me the LAST line that printed
successfully — that pinpoints which library's native code is crashing.
"""

import sys
print(f"Python: {sys.version}", flush=True)
print(f"Executable: {sys.executable}", flush=True)
print("=" * 60, flush=True)

print("\n[1] Importing numpy...", flush=True)
import numpy as np
print(f"    OK — numpy {np.__version__}", flush=True)

print("\n[2] Importing torch...", flush=True)
import torch
print(f"    OK — torch {torch.__version__}, CUDA build: {torch.version.cuda}", flush=True)

print("\n[3] Checking torch.cuda.is_available() (do NOT skip — this itself can crash)...", flush=True)
try:
    avail = torch.cuda.is_available()
    print(f"    OK — cuda available: {avail}", flush=True)
except Exception as e:
    print(f"    EXCEPTION (not a crash, caught): {e}", flush=True)

print("\n[4] Importing PIL...", flush=True)
from PIL import Image
print("    OK — PIL imported", flush=True)

print("\n[5] Importing onnxruntime (used internally by RapidOCR)...", flush=True)
import onnxruntime as ort
print(f"    OK — onnxruntime {ort.__version__}, providers: {ort.get_available_providers()}", flush=True)

print("\n[6] Importing rapidocr...", flush=True)
from rapidocr import RapidOCR
print("    OK — rapidocr imported", flush=True)

print("\n[7] Importing docling (DocumentConverter)...", flush=True)
from docling.document_converter import DocumentConverter
print("    OK — docling imported", flush=True)

print("\n[8] Importing transformers...", flush=True)
import transformers
print(f"    OK — transformers {transformers.__version__}", flush=True)

print("\n[9] Importing pycocotools...", flush=True)
from pycocotools.coco import COCO
print("    OK — pycocotools imported", flush=True)

print("\n[10] Importing img2pdf...", flush=True)
import img2pdf
print("    OK — img2pdf imported", flush=True)

print("\n" + "=" * 60, flush=True)
print("ALL IMPORTS SUCCEEDED — crash is NOT at import time.", flush=True)
print("Proceed to debug_kernel_crash_step2_runtime.py to test actual execution paths.", flush=True)
