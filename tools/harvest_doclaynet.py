# tools/harvest_doclaynet.py
"""
Harvest layout-skeleton statistics from pierreguillou/DocLayNet-small.
Outputs per-domain JSON files to layout_corpora/.

Usage:
    python tools/harvest_doclaynet.py [--max-pages 500]
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime

import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from synthetic_layout_gen.core.doclaynet_label_map import (
    DOCLAYNET_CAT_ID_TO_NAME,
    DOCLAYNET_TO_CANONICAL,
    DOCLAYNET_DOC_CATEGORY_TO_DOMAIN,
    classify_doclaynet_page,
)

DOMAINS = [
    "financial_invoice",
    "scientific_paper",
    "legal_opinion",
    "medical_report",
    "commercial_catalog",
]


def percentiles_from_list(values, keys=("5", "25", "50", "75", "95")):
    """Compute named percentiles from a list of floats."""
    if not values:
        return {k: 0.0 for k in keys}
    arr = np.array(values, dtype=float)
    pcts = [5, 25, 50, 75, 95]
    results = np.percentile(arr, pcts)
    return {k: round(float(v), 2) for k, v in zip(keys, results)}


def extract_page_stats(item):
    """
    Extract layout stats from a single DocLayNet page.
    Returns stats dict or None.
    """
    img_w = item.get("coco_width", 1025)
    img_h = item.get("coco_height", 1025)

    categories = item.get("categories", [])
    bboxes = item.get("bboxes_block", [])
    if not bboxes or not categories:
        return None

    # Scale factor: map pixel coords to standard letter (612x792 pt)
    scale_x = 612.0 / img_w if img_w > 0 else 1.0
    scale_y = 792.0 / img_h if img_h > 0 else 1.0

    label_counts = defaultdict(int)
    all_x0, all_y0, all_x1, all_y1 = [], [], [], []
    element_areas = defaultdict(list)
    page_area = 612.0 * 792.0

    for cat_id, bbox in zip(categories, bboxes):
        cat_name = DOCLAYNET_CAT_ID_TO_NAME.get(cat_id)
        if not cat_name:
            continue
        canonical = DOCLAYNET_TO_CANONICAL.get(cat_name)
        if not canonical:
            continue

        x, y, w, h = bbox
        # Convert pixel coords to pt
        x0_pt = x * scale_x
        y0_pt = y * scale_y
        x1_pt = (x + w) * scale_x
        y1_pt = (y + h) * scale_y

        label_counts[canonical] += 1
        all_x0.append(x0_pt)
        all_y0.append(y0_pt)
        all_x1.append(x1_pt)
        all_y1.append(y1_pt)

        area_ratio = (x1_pt - x0_pt) * (y1_pt - y0_pt) / page_area
        element_areas[canonical].append(area_ratio)

    if not all_x0:
        return None

    margin_left = max(0, min(all_x0))
    margin_right = max(0, 612.0 - max(all_x1))
    margin_top = max(0, min(all_y0))
    margin_bottom = max(0, 792.0 - max(all_y1))

    # Header zone: elements with top edge < 80pt
    header_elements = [y0 for y0 in all_y0 if y0 < 80]
    footer_elements = [y1 for y1 in all_y1 if y1 > 712]
    header_zone_h = max(header_elements) if header_elements else 30.0
    footer_zone_h = 792.0 - min(footer_elements) if footer_elements else 20.0

    # Column detection from text element centers
    text_x_centers = []
    for cat_id, bbox in zip(categories, bboxes):
        cat_name = DOCLAYNET_CAT_ID_TO_NAME.get(cat_id, "")
        canonical = DOCLAYNET_TO_CANONICAL.get(cat_name, "")
        if canonical in ("text", "section_header", "list_item"):
            x, y, w, h = bbox
            text_x_centers.append((x + w / 2) * scale_x)

    n_columns = 1
    if len(text_x_centers) >= 4:
        centers = np.array(text_x_centers)
        page_mid = 306.0
        left_count = np.sum(centers < page_mid - 20)
        right_count = np.sum(centers > page_mid + 20)
        if left_count >= 2 and right_count >= 2:
            n_columns = 2

    # Use doc_category for domain classification (better than heuristic)
    doc_category = item.get("doc_category", "")
    domain = DOCLAYNET_DOC_CATEGORY_TO_DOMAIN.get(doc_category)
    if domain is None:
        # Fallback to heuristic classification
        domain = classify_doclaynet_page(dict(label_counts))

    return {
        "domain": domain,
        "label_counts": dict(label_counts),
        "margins": {
            "left": margin_left,
            "right": margin_right,
            "top": margin_top,
            "bottom": margin_bottom,
        },
        "zones": {
            "header_height": header_zone_h,
            "footer_height": footer_zone_h,
        },
        "n_columns": n_columns,
        "element_areas": {k: v for k, v in element_areas.items()},
    }


def main():
    parser = argparse.ArgumentParser(description="Harvest DocLayNet layout statistics")
    parser.add_argument("--max-pages", type=int, default=500,
                        help="Max pages to process (default: 500)")
    parser.add_argument("--output-dir", type=str, default="layout_corpora",
                        help="Output directory for stats files")
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"Harvesting pierreguillou/DocLayNet-small (max {args.max_pages} pages)...")
    t0 = time.time()

    from datasets import load_dataset

    # Load pierreguillou/DocLayNet-small train split
    dln = load_dataset("pierreguillou/DocLayNet-small", split="train", trust_remote_code=True)

    # Accumulate per-domain stats
    domain_stats = {d: {
        "margins_left": [], "margins_right": [], "margins_top": [], "margins_bottom": [],
        "header_heights": [], "footer_heights": [],
        "column_counts": defaultdict(int),
        "element_areas": defaultdict(list),
        "n_pages": 0,
    } for d in DOMAINS}

    processed = 0
    for item in dln:
        if processed >= args.max_pages:
            break

        stats = extract_page_stats(item)
        if stats is None:
            continue

        domain = stats["domain"]
        if domain not in domain_stats:
            continue

        ds = domain_stats[domain]
        ds["margins_left"].append(stats["margins"]["left"])
        ds["margins_right"].append(stats["margins"]["right"])
        ds["margins_top"].append(stats["margins"]["top"])
        ds["margins_bottom"].append(stats["margins"]["bottom"])
        ds["header_heights"].append(stats["zones"]["header_height"])
        ds["footer_heights"].append(stats["zones"]["footer_height"])
        ds["column_counts"][str(stats["n_columns"])] += 1
        for label, areas in stats["element_areas"].items():
            ds["element_areas"][label].extend(areas)
        ds["n_pages"] += 1

        processed += 1
        if processed % 50 == 0:
            print(f"  Processed {processed} pages...")

    elapsed = time.time() - t0
    print(f"Harvest complete: {processed} pages in {elapsed:.1f}s")

    # Write per-domain stats
    for domain in DOMAINS:
        ds = domain_stats[domain]
        if ds["n_pages"] == 0:
            print(f"  [WARN] No pages classified as '{domain}' - will use heuristic fallback")
            continue

        output = {
            "domain": domain,
            "n_pages_harvested": ds["n_pages"],
            "harvested_at": datetime.now().isoformat(),
            "source_dataset": "pierreguillou/DocLayNet-small",
            "source_license": "CDLA-Permissive-1.0",
            "page_dimensions": {
                "width_pt": percentiles_from_list([612.0] * ds["n_pages"]),
                "height_pt": percentiles_from_list([792.0] * ds["n_pages"]),
            },
            "margins": {
                "left": percentiles_from_list(ds["margins_left"]),
                "right": percentiles_from_list(ds["margins_right"]),
                "top": percentiles_from_list(ds["margins_top"]),
                "bottom": percentiles_from_list(ds["margins_bottom"]),
            },
            "zones": {
                "header_height": percentiles_from_list(ds["header_heights"]),
                "footer_height": percentiles_from_list(ds["footer_heights"]),
                "column_gap": {"5": 10, "25": 12, "50": 14, "75": 16, "95": 20},
            },
            "column_count": {k: round(v / ds["n_pages"], 4)
                            for k, v in ds["column_counts"].items()},
            "element_area_ratios": {
                label: percentiles_from_list(areas)
                for label, areas in ds["element_areas"].items()
            },
        }

        out_path = os.path.join(output_dir, f"{domain}_skeleton_stats.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"  [OK] {domain}: {ds['n_pages']} pages -> {out_path}")

    # Print summary
    print("\n=== Harvest Summary ===")
    for domain in DOMAINS:
        n = domain_stats[domain]["n_pages"]
        print(f"  {domain}: {n} pages")
    print(f"Total: {processed} pages, {elapsed:.1f}s")


if __name__ == "__main__":
    main()
