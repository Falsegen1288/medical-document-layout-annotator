"""
DEBUG STEP 3 — Dump environment fingerprint for cross-referencing known
incompatible package combinations (numpy ABI breaks, torch/onnxruntime pairs,
CUDA driver/toolkit mismatches).

Run from the SAME venv:
    venv\\Scripts\\python.exe debug_kernel_crash_step3_env_dump.py > env_dump.txt

Send me the contents of env_dump.txt along with the results of steps 1 and 2.
"""

import sys
import subprocess
import platform

print("=" * 60)
print("SYSTEM")
print("=" * 60)
print("Python:", sys.version)
print("Executable:", sys.executable)
print("Platform:", platform.platform())
print("Machine:", platform.machine())

print("\n" + "=" * 60)
print("PIP FREEZE (full list)")
print("=" * 60)
result = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
print(result.stdout)

print("\n" + "=" * 60)
print("KEY PACKAGE VERSIONS (explicit check)")
print("=" * 60)
for pkg in ["numpy", "torch", "onnxruntime", "transformers", "docling",
            "rapidocr", "rapidocr_onnxruntime", "pycocotools", "img2pdf",
            "accelerate", "timm", "albumentations", "open_clip_torch",
            "landingai-ade", "datasets"]:
    try:
        mod = __import__(pkg.replace("-", "_"))
        print(f"  {pkg}: {getattr(mod, '__version__', 'unknown')}")
    except Exception as e:
        print(f"  {pkg}: NOT IMPORTABLE ({e})")

print("\n" + "=" * 60)
print("NVIDIA / CUDA (driver-level, via nvidia-smi)")
print("=" * 60)
try:
    smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
    print(smi.stdout if smi.returncode == 0 else f"nvidia-smi failed: {smi.stderr}")
except FileNotFoundError:
    print("nvidia-smi not found on PATH")

print("\n" + "=" * 60)
print("TORCH CUDA INFO")
print("=" * 60)
try:
    import torch
    print("torch.__version__:", torch.__version__)
    print("torch.version.cuda:", torch.version.cuda)
    print("torch.cuda.is_available():", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("Device name:", torch.cuda.get_device_name(0))
except Exception as e:
    print(f"Could not retrieve torch CUDA info: {e}")
