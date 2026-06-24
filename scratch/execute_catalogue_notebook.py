# scratch/execute_catalogue_notebook.py
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import os
import sys
import time

notebook_in = 'synthetic_catalogue_evaluation.ipynb'
notebook_out = 'synthetic_catalogue_evaluation.ipynb'

print(f"Reading notebook: {notebook_in}")
with open(notebook_in, 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

print("Executing notebook cells with medical-document-layout-annotator-venv kernel...")
t0 = time.time()
ep = ExecutePreprocessor(timeout=600, kernel_name='medical-document-layout-annotator-venv')

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
