import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import os
import sys
import time

notebook_in = 'synthetic_evaluation_benchmark.ipynb'
notebook_out = 'synthetic_evaluation_benchmark.ipynb'

print(f"Reading notebook: {notebook_in}")
with open(notebook_in, 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

print("Executing notebook cells. This will run DocLayoutYOLO and Nemotron-Parse on the 10 PDFs (17 pages)...")
t0 = time.time()
ep = ExecutePreprocessor(timeout=1800, kernel_name='python3')

try:
    ep.preprocess(nb, {'metadata': {'path': os.getcwd()}})
    print(f"Notebook executed successfully in {time.time()-t0:.1f}s!")
except Exception as e:
    print("\nExecution failed with error:")
    print(e)
    sys.exit(1)

print(f"Writing executed notebook back to: {notebook_out}")
with open(notebook_out, 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Execution complete!")
