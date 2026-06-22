# generate_dataset.py
import argparse
import importlib
import os
import sys
import traceback
import json
import glob
from collections import Counter

# Add parent directory of synthetic_layout_gen to path so imports start with synthetic_layout_gen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

DOMAINS = [
    "financial_invoice",
    "scientific_paper",
    "legal_opinion",
    "medical_report",
    "commercial_catalog"
]

def print_distributional_report(domain: str, output_root: str = "output/"):
    """
    Computes and prints the Section 7.4 distributional report for a given domain:
    - Label frequency histogram
    - Bbox area distribution
    - Page count distribution
    - Fraction of documents with split tables/paragraphs
    - Fraction of medical reports degraded to scan-like
    """
    json_dir = os.path.join(output_root, domain, "json")
    json_pattern = os.path.join(json_dir, "*.json")
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        print(f"\n--- Distributional Report for '{domain}': No files found ---")
        return
        
    total_docs = len(json_files)
    label_counts = Counter()
    all_areas = []
    page_counts = Counter()
    docs_with_splits = 0
    degraded_docs = 0
    
    for f_path in json_files:
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            pages = data.get("pages", [])
            page_counts[len(pages)] += 1
            
            has_split = False
            is_degraded = False
            
            # Check if any element represents scan degradation or splits
            for page in pages:
                # Check for scan degradation metadata or check image path to see if it's a degraded file
                # Medical reports use degrade_to_scanlike which changes the image itself, check attributes
                for elem in page.get("layout_elements", []):
                    label = elem["type"]
                    label_counts[label] += 1
                    
                    # Compute area in pt^2
                    x0, y0, x1, y1 = elem["bbox"]
                    area = (x1 - x0) * (y1 - y0)
                    all_areas.append(area)
                    
                    # Split tracking
                    attrs = elem.get("attributes", {})
                    if attrs.get("is_continued_from") or attrs.get("is_continued_on_next_page"):
                        has_split = True
                        
                    if attrs.get("is_degraded") or attrs.get("scanned_degradation"):
                        is_degraded = True
            
            if has_split:
                docs_with_splits += 1
            if is_degraded:
                degraded_docs += 1
                
        except Exception as e:
            print(f"Error reading {f_path} for stats: {e}")
            
    print(f"\n==================================================")
    print(f"DISTRIBUTIONAL REPORT FOR DOMAIN: {domain}")
    print(f"==================================================")
    print(f"Total documents parsed: {total_docs}")
    print(f"Page count distribution:")
    for pc, count in sorted(page_counts.items()):
        print(f"  - {pc} page(s): {count} docs ({count/total_docs*100:.1f}%)")
        
    print(f"Label frequency histogram:")
    total_labels = sum(label_counts.values())
    for label, count in label_counts.most_common():
        print(f"  - {label}: {count} elements ({count/total_labels*100:.1f}%)")
        
    if all_areas:
        all_areas.sort()
        p50 = all_areas[len(all_areas)//2]
        p90 = all_areas[int(len(all_areas)*0.9)]
        print(f"Bounding box area distribution (pt^2):")
        print(f"  - Median area: {p50:.1f}")
        print(f"  - 90th percentile: {p90:.1f}")
        
    print(f"Split-table / Split-paragraph coverage:")
    print(f"  - Docs with at least one split element: {docs_with_splits} ({docs_with_splits/total_docs*100:.1f}%)")
    
    if domain == "medical_report":
        print(f"Scan-like degradation coverage:")
        print(f"  - Degraded documents: {degraded_docs} ({degraded_docs/total_docs*100:.1f}%)")
    print(f"==================================================\n")

def main():
    parser = argparse.ArgumentParser(description="Synthetic Layout Ground-Truth Dataset Generator")
    parser.add_argument(
        "--domains",
        nargs="+",
        choices=DOMAINS,
        default=DOMAINS,
        help="Domains to generate samples for"
    )
    parser.add_argument(
        "--samples-per-domain",
        type=int,
        default=200,
        help="Number of samples to generate per domain (default: 200)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Initial master seed for determinism (default: 42)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Run schema and geometric checks on outputs (default: True)"
    )
    parser.add_argument(
        "--no-validate",
        action="store_false",
        dest="validate",
        help="Disable schema and geometric checks"
    )
    
    args = parser.parse_args()
    
    output_root = "output/"
    
    print(f"Starting synthetic dataset generation...")
    print(f"Target Domains: {args.domains}")
    print(f"Samples per domain: {args.samples-per-domain if hasattr(args, 'samples-per-domain') else args.samples_per_domain}")
    print(f"Master Seed: {args.seed}")
    print(f"Validation: {'Enabled' if args.validate else 'Disabled'}\n")
    
    for domain in args.domains:
        print(f"--------------------------------------------------")
        print(f"Generating domain: {domain}")
        print(f"--------------------------------------------------")
        
        try:
            # Dynamically import the domain's generator module
            module_path = f"synthetic_layout_gen.domains.{domain}.generator"
            gen_module = importlib.import_module(module_path)
            
            samples = args.samples_per_domain
            for i in range(samples):
                # Calculate deterministic seed per sample as specified
                sample_seed = args.seed * 100000 + i
                
                print(f"  [{i+1}/{samples}] Generating sample {domain}_{i:05d} (seed: {sample_seed})...")
                gen_module.generate_one(sample_id=i, seed=sample_seed, output_root=output_root)
                
            print(f"Finished generating all {samples} samples for domain '{domain}'.")
            
            # Run QA validation if requested
            if args.validate:
                print(f"Running QA validation for domain '{domain}'...")
                from synthetic_layout_gen.qa.validate_dataset import validate_domain
                validate_domain(domain, output_root)
                
                # Print distributional report
                print_distributional_report(domain, output_root)
                
        except Exception as e:
            print(f"Error occurred while processing domain '{domain}':")
            traceback.print_exc()
            sys.exit(1)

    print("Dataset generation pipeline completed successfully.")

if __name__ == "__main__":
    main()
