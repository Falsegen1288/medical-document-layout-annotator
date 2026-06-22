"""
Generate 20 samples per domain for the synthetic layout dataset.
Already have 3 per domain (IDs 00000-00002), generates IDs 00003-00019.
Then runs QA validation on all 20.

Usage:
    cd medical-document-layout-annotator
    venv\Scripts\python.exe -u scratch\generate_20_per_domain.py
"""
import os
import sys
import time
import json
import traceback
import importlib

sys.path.insert(0, os.path.abspath("."))

OUTPUT_ROOT = "output/"
SAMPLES_PER_DOMAIN = 20
START_ID = 3  # Already have 0, 1, 2
SEED_BASE = 42

DOMAINS = [
    "financial_invoice",
    "scientific_paper",
    "legal_opinion",
    "medical_report",
    "commercial_catalog",
]

def main():
    t0 = time.time()
    total_generated = 0
    errors = []

    for domain_name in DOMAINS:
        print(f"\n{'='*60}")
        print(f"Domain: {domain_name}")
        print(f"{'='*60}")

        module_path = f"synthetic_layout_gen.domains.{domain_name}.generator"
        gen_module = importlib.import_module(module_path)

        for sample_id in range(START_ID, SAMPLES_PER_DOMAIN):
            doc_id = f"{domain_name}_{sample_id:05d}"
            json_path = os.path.join(OUTPUT_ROOT, domain_name, "json", f"{doc_id}.json")

            if os.path.exists(json_path):
                print(f"  [{sample_id+1}/{SAMPLES_PER_DOMAIN}] {doc_id} already exists, skipping.")
                total_generated += 1
                continue

            try:
                seed = SEED_BASE * 100000 + sample_id
                print(f"  [{sample_id+1}/{SAMPLES_PER_DOMAIN}] Generating {doc_id} (seed={seed})...", end=" ", flush=True)
                t1 = time.time()
                gen_module.generate_one(sample_id=sample_id, seed=seed, output_root=OUTPUT_ROOT)
                elapsed = time.time() - t1

                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    n_pages = len(data["pages"])
                    n_elements = sum(len(p["layout_elements"]) for p in data["pages"])
                    print(f"OK ({elapsed:.1f}s, {n_pages} pages, {n_elements} elements)")
                    total_generated += 1
                else:
                    print(f"WARN: No JSON produced after {elapsed:.1f}s")
                    errors.append((doc_id, "No JSON file produced"))
            except Exception as e:
                print(f"ERROR: {e}")
                traceback.print_exc()
                errors.append((doc_id, str(e)))

    elapsed_total = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Generation complete: {total_generated} new samples in {elapsed_total:.1f}s")
    if errors:
        print(f"Errors ({len(errors)}):")
        for doc_id, err in errors:
            print(f"  {doc_id}: {err}")
    print(f"{'='*60}")

    # Run QA validation on all samples
    print("\nRunning QA validation on all 20 samples per domain...")
    from synthetic_layout_gen.qa.validate_dataset import validate_domain
    for domain_name in DOMAINS:
        print(f"\nValidating {domain_name}...")
        try:
            validate_domain(domain_name, OUTPUT_ROOT)
            print(f"  {domain_name}: PASSED")
        except Exception as e:
            print(f"  {domain_name}: FAILED - {e}")

if __name__ == "__main__":
    main()
