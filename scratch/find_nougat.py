# scratch/find_nougat.py
import os

keywords = ["nougat", "meta/nougat", "facebook/nougat", "nougat-small", "nougat-base"]
found = []

for root, dirs, files in os.walk("."):
    # skip venv, git, node_modules, cache, etc.
    if any(p in root for p in ["venv", "venv_old", ".git", "node_modules", "cache", ".agents"]):
        continue
    for file in files:
        if file.endswith((".py", ".ipynb", ".json", ".md", ".txt", ".jsonl", ".sh")):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                for kw in keywords:
                    if kw in content:
                        found.append((path, kw))
            except Exception as e:
                pass

if found:
    print("Found keyword references:")
    for path, kw in found:
        print(f"  {path}: {kw}")
else:
    print("No keyword references found in code files.")
