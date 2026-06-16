"""
DEBUG STEP 2 — Detect duplicate/conflicting OpenMP runtimes (the #1 cause of
Windows exit code 3221225477 / 0xC0000005 in mixed torch+onnxruntime+numpy stacks).

Run from the SAME venv:
    venv\\Scripts\\python.exe debug_kernel_crash_step2_openmp.py

This script does two things:
1. Searches site-packages for multiple copies of OpenMP/MKL DLLs (libiomp5md.dll,
   libomp.dll, mkl ones, etc.) — having 2+ different OpenMP runtimes loaded into
   one process is a classic, well-documented cause of silent access violations.
2. Sets the (unsafe but diagnostic) KMP_DUPLICATE_LIB_OK=TRUE env var BEFORE
   importing torch/onnxruntime, then re-runs the same import sequence as step 1.
   If the crash disappears with this env var set, you have DEFINITIVE confirmation
   it's an OpenMP duplicate-library conflict (this is a diagnostic, not the fix —
   the real fix is to pin compatible package versions, not ship with this env var).
"""

import os
import sys
import glob

print("=" * 60, flush=True)
print("PART A: Scanning for duplicate OpenMP / MKL DLLs in venv", flush=True)
print("=" * 60, flush=True)

venv_root = os.path.dirname(os.path.dirname(sys.executable))
site_packages_glob = os.path.join(venv_root, "Lib", "site-packages", "**")

dll_patterns = [
    "libiomp5md.dll",
    "libomp.dll",
    "libiomp5.dll",
    "mkl_rt.dll",
    "vcomp*.dll",
]

found = {}
for pattern in dll_patterns:
    matches = glob.glob(os.path.join(site_packages_glob, pattern), recursive=True)
    if matches:
        found[pattern] = matches

if not found:
    print("No common OpenMP/MKL DLL names found via this glob — they may be named"
          " differently or nested deeper. This does NOT rule out the conflict, just"
          " means this quick scan didn't catch it.", flush=True)
else:
    for pattern, matches in found.items():
        print(f"\n  Pattern '{pattern}' found in {len(matches)} location(s):", flush=True)
        for m in matches:
            print(f"    - {m}", flush=True)
    total_locations = sum(len(v) for v in found.values())
    if total_locations > 1:
        print(f"\n  >>> {total_locations} total DLL copies found across packages."
              f" Multiple copies of OpenMP runtimes from different packages"
              f" (torch, numpy, onnxruntime, scikit-learn, etc.) loading into the"
              f" same process is the single most common cause of this exact crash.", flush=True)

print("\n" + "=" * 60, flush=True)
print("PART B: Re-testing imports WITH KMP_DUPLICATE_LIB_OK=TRUE", flush=True)
print("(diagnostic only — confirms but does not fix the root cause)", flush=True)
print("=" * 60, flush=True)

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    print("\n[1] Importing numpy...", flush=True)
    import numpy as np
    print(f"    OK — numpy {np.__version__}", flush=True)

    print("\n[2] Importing torch...", flush=True)
    import torch
    print(f"    OK — torch {torch.__version__}", flush=True)

    print("\n[3] Importing onnxruntime...", flush=True)
    import onnxruntime as ort
    print(f"    OK — onnxruntime {ort.__version__}", flush=True)

    print("\n[4] Running a trivial torch op...", flush=True)
    x = torch.rand(10, 10)
    y = x @ x
    print(f"    OK — matmul result shape {y.shape}", flush=True)

    print("\n[5] Running a trivial onnxruntime session creation check...", flush=True)
    print(f"    Available providers: {ort.get_available_providers()}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("If you see this line, nothing crashed WITH the env var set.", flush=True)
    print("Compare against Step 1's result (without the env var) to confirm diagnosis.", flush=True)

except Exception as e:
    print(f"\nEXCEPTION (caught, not a hard crash): {e}", flush=True)
