# scratch/dump_synthetic_evaluation_benchmark.py
import json

nb_path = "synthetic_evaluation_benchmark.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    data = json.load(f)

output_lines = []
for i, cell in enumerate(data.get("cells", [])):
    ctype = cell.get("cell_type")
    source = cell.get("source", [])
    source_str = "".join(source)
    output_lines.append(f"=== Cell {i} ({ctype}) ===")
    output_lines.append(source_str)
    output_lines.append("\n" + "="*50 + "\n")

with open("scratch/synthetic_evaluation_benchmark_dump.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("Dumped synthetic_evaluation_benchmark.ipynb to scratch/synthetic_evaluation_benchmark_dump.txt")
