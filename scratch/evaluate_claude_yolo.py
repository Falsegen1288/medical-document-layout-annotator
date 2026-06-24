# scratch/evaluate_claude_yolo.py
import os
import sys
import json
import numpy as np
from collections import defaultdict
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath("."))

from backend.benchmark import compute_map, match_predictions, compute_iou

# Define the 10 canonical classes
CLASSES = [
    "title",
    "paragraph",
    "table",
    "figure",
    "caption",
    "header",
    "footer",
    "logo",
    "list",
    "section_header"
]

DOCLING_TO_CANONICAL = {
    'title': 'title',
    'titleitem': 'title',
    'text': 'paragraph',
    'paragraphitem': 'paragraph',
    'textitem': 'paragraph',
    'keyvalueitem': 'paragraph',
    'table': 'table',
    'tableitem': 'table',
    'picture': 'figure',
    'pictureitem': 'figure',
    'figurecaption': 'caption',
    'caption': 'caption',
    'pageheader': 'header',
    'header': 'header',
    'pagefooter': 'footer',
    'footer': 'footer',
    'logo': 'logo',
    'list': 'list',
    'listitem': 'list',
    'list_item': 'list',
    'sectionheader': 'section_header',
    'sectionheaderitem': 'section_header',
    'section_header': 'section_header',
}

def load_ground_truth(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    pages_gt = []
    # 4 pages expected
    for page_data in data["pages"]:
        gt_boxes = []
        for elem in page_data["elements"]:
            bbox = elem["bbox_pt"]
            # Convert [x, y, w, h] bottom-left to [x0, y0, x1, y1] bottom-left
            x0 = bbox["x"]
            y0 = bbox["y"]
            x1 = bbox["x"] + bbox["w"]
            y1 = bbox["y"] + bbox["h"]
            gt_boxes.append({
                "bbox": [x0, y0, x1, y1],
                "label": elem["class"]
            })
        pages_gt.append(gt_boxes)
    return pages_gt

def run_docling_detection(pdf_path):
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(pdf_path)
    doc_obj = result.document
    
    # We will gather elements per page
    pages_preds = [[] for _ in range(4)]
    
    for item, _ in doc_obj.iterate_items():
        if not hasattr(item, 'prov') or not item.prov:
            continue
        prov = item.prov[0]
        pg_num = prov.page_no # 1-indexed
        if pg_num < 1 or pg_num > 4:
            continue
        
        bbox = prov.bbox
        x0, y0, x1, y1 = bbox.l, bbox.b, bbox.r, bbox.t
        
        raw_label = type(item).__name__.lower().replace('item', '').replace('docling', '')
        mapped_label = DOCLING_TO_CANONICAL.get(raw_label, raw_label)
        
        if mapped_label in CLASSES:
            pages_preds[pg_num - 1].append({
                "bbox": [x0, y0, x1, y1],
                "label": mapped_label
            })
            
    return pages_preds

def get_oracle_predictions(all_gt, all_preds):
    oracle_preds = []
    for page_gt, page_preds in zip(all_gt, all_preds):
        page_oracle = []
        for pred in page_preds:
            best_iou = 0.0
            best_label = pred["label"]
            for gt in page_gt:
                iou = compute_iou(pred["bbox"], gt["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_label = gt["label"]
            
            # If there is a decent overlap, align the label to GT to isolate layout location capacity
            aligned_label = best_label if best_iou > 0.1 else pred["label"]
            page_oracle.append({
                "bbox": pred["bbox"],
                "label": aligned_label
            })
        oracle_preds.append(page_oracle)
    return oracle_preds

def evaluate_run(all_gt, all_preds, name):
    iou_thresholds = np.arange(0.5, 1.0, 0.05)
    metrics = compute_map(all_gt, all_preds, iou_thresholds, CLASSES)
    
    # Compute per-class stats at IoU=0.5
    tp_cls = defaultdict(int)
    fp_cls = defaultdict(int)
    fn_cls = defaultdict(int)
    
    for gt_boxes, pred_boxes in zip(all_gt, all_preds):
        matched, ugt, upr = match_predictions(gt_boxes, pred_boxes, 0.5)
        for gi, pi, iou in matched:
            tp_cls[gt_boxes[gi]['label']] += 1
        for gi in ugt:
            fn_cls[gt_boxes[gi]['label']] += 1
        for pi in upr:
            fp_cls[pred_boxes[pi]['label']] += 1
            
    class_reports = {}
    for cls in CLASSES:
        tp = tp_cls[cls]
        fp = fp_cls[cls]
        fn = fn_cls[cls]
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        class_reports[cls] = {
            "TP": tp, "FP": fp, "FN": fn,
            "precision": p, "recall": r, "F1": f1
        }
        
    return metrics, class_reports

def main():
    pdf_path = "layout_corpora/synthetic_by_claude/MedCore_Catalogue.pdf"
    json_path = "layout_corpora/synthetic_by_claude/MedCore_Catalogue_groundtruth.json"
    
    print("Loading Ground Truth...")
    all_gt = load_ground_truth(json_path)
    print(f"Loaded GT for {len(all_gt)} pages.")
        
    print("\nRunning DocLayoutYOLO via Docling...")
    all_preds = run_docling_detection(pdf_path)
    
    # 1. Evaluate Naive Mapping
    print("\n--- Running Naive Mapping Evaluation ---")
    naive_metrics, naive_class = evaluate_run(all_gt, all_preds, "Naive")
    
    # 2. Evaluate Oracle Aligned Mapping
    print("\n--- Running Oracle Aligned Mapping Evaluation ---")
    oracle_preds = get_oracle_predictions(all_gt, all_preds)
    oracle_metrics, oracle_class = evaluate_run(all_gt, oracle_preds, "Oracle")
    
    # Generate unified markdown report
    report_lines = [
        "# Evaluation Report: DocLayoutYOLO on MedCore_Catalogue.pdf",
        "",
        "This report evaluates **DocLayoutYOLO** (via Docling) on the synthetically generated `MedCore_Catalogue.pdf` dataset containing pixel-perfect ground truth annotations.",
        "To isolate the classification mapping mismatch (a known taxonomy bug) from the spatial localization performance, we report both **Naive Mapping** and **Oracle Aligned Mapping**.",
        "",
        "## 1. Overall Summary Metrics Comparison",
        "",
        "| Metric | Naive Mapping | Oracle Aligned Mapping |",
        "| :--- | :---: | :---: |",
        f"| **mAP@0.5 (Primary)** | **{naive_metrics['mAP50']:.4f}** | **{oracle_metrics['mAP50']:.4f}** |",
        f"| **mAP@0.5:0.95 (Secondary)** | **{naive_metrics['mAP5095']:.4f}** | **{oracle_metrics['mAP5095']:.4f}** |",
        f"| **Overall Precision (IoU=0.5)** | {naive_metrics['precision']:.4f} | {oracle_metrics['precision']:.4f} |",
        f"| **Overall Recall (IoU=0.5)** | {naive_metrics['recall']:.4f} | {oracle_metrics['recall']:.4f} |",
        f"| **Overall F1-Score (IoU=0.5)** | {metrics_f1(naive_metrics):.4f} | {metrics_f1(oracle_metrics):.4f} |",
        f"| **Mean IoU (TP pairs)** | {naive_metrics['mean_iou']:.4f} | {oracle_metrics['mean_iou']:.4f} |",
        "",
        "## 2. Per-Class Detail Scorecard (IoU=0.5)",
        "",
        "| Class Name | Naive F1-Score | Oracle F1-Score | Naive TP / FP / FN | Oracle TP / FP / FN |",
        "| :--- | :---: | :---: | :---: | :---: |"
    ]
    
    for cls in CLASSES:
        n_rep = naive_class[cls]
        o_rep = oracle_class[cls]
        report_lines.append(
            f"| **{cls}** | {n_rep['F1']:.4f} | {o_rep['F1']:.4f} | {n_rep['TP']} / {n_rep['FP']} / {n_rep['FN']} | {o_rep['TP']} / {o_rep['FP']} / {o_rep['FN']} |"
        )
        
    report_lines.append("")
    report = "\n".join(report_lines)
    print("\n" + report)
    
    # Save report
    os.makedirs("results/evaluation", exist_ok=True)
    report_path = "results/evaluation/medcore_evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nSaved evaluation scorecard to {report_path}")

def metrics_f1(m):
    p, r = m['precision'], m['recall']
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

if __name__ == "__main__":
    main()
