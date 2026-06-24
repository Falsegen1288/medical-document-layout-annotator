# scratch/evaluate_claude_all.py
import os
import sys
import json
import re
import time
import fitz  # PyMuPDF
import numpy as np
from collections import defaultdict
from PIL import Image
import torch
from transformers import AutoModel, AutoProcessor, AutoTokenizer, GenerationConfig
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath("."))
from backend.benchmark import compute_map, match_predictions, compute_iou

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

MAPPING = {
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
    'page-header': 'header',
    'page_header': 'header',
    'header': 'header',
    'pagefooter': 'footer',
    'page-footer': 'footer',
    'page_footer': 'footer',
    'footer': 'footer',
    'logo': 'logo',
    'list': 'list',
    'listitem': 'list',
    'list_item': 'list',
    'sectionheader': 'section_header',
    'section-header': 'section_header',
    'sectionheaderitem': 'section_header',
    'section_header': 'section_header',
    'footnote': 'paragraph',
    'formula': 'paragraph'
}

PROC_W = 832
PROC_H = 1024
BLOCK_PATTERN = re.compile(
    r'<x_([0-9.]+)><y_([0-9.]+)>'   # top-left
    r'(.*?)'                          # text content
    r'<x_([0-9.]+)><y_([0-9.]+)>'   # bottom-right
    r'<class_([^>]+)>',              # class label
    re.DOTALL
)

def load_ground_truth(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    pages_gt = []
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

def run_docling_detection(pdf_path, converter):
    result = converter.convert(pdf_path)
    doc_obj = result.document
    
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
        mapped_label = MAPPING.get(raw_label, raw_label)
        
        if mapped_label in CLASSES:
            pages_preds[pg_num - 1].append({
                "bbox": [x0, y0, x1, y1],
                "label": mapped_label,
                "score": 0.9
            })
            
    return pages_preds

def render_pdf_page(pdf_path, page_num_1idx, dpi=150):
    doc = fitz.open(pdf_path)
    page = doc[page_num_1idx - 1]
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
    pw_pt, ph_pt = page.rect.width, page.rect.height
    doc.close()
    return img, pw_pt, ph_pt

def run_nemotron_on_page(img, pw_pt, ph_pt, model, processor, tokenizer, gen_config, device, dpi=150):
    orig_w, orig_h = img.size
    
    # Pad image to PROC_W x PROC_H
    padded = Image.new('RGB', (PROC_W, PROC_H), (255, 255, 255))
    if orig_w > PROC_W or orig_h > PROC_H:
        scale = min(PROC_W / orig_w, PROC_H / orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        pad_x = (PROC_W - new_w) // 2
        pad_y = (PROC_H - new_h) // 2
        padded.paste(resized, (pad_x, pad_y))
        effective_scale = scale
    else:
        pad_x = (PROC_W - orig_w) // 2
        pad_y = (PROC_H - orig_h) // 2
        padded.paste(img, (pad_x, pad_y))
        effective_scale = 1.0
        
    task_prompt = '</s><s><predict_bbox><predict_classes>'
    inputs = processor(images=padded, text=task_prompt, return_tensors='pt', add_special_tokens=False).to(device)
    
    with torch.no_grad():
        outputs = model.generate(**inputs, generation_config=gen_config, max_new_tokens=1024)
        
    decoded = tokenizer.decode(outputs[0], skip_special_tokens=False)
    
    detections = []
    for m in BLOCK_PATTERN.finditer(decoded):
        x0_n, y0_n = float(m.group(1)), float(m.group(2))
        x1_n, y1_n = float(m.group(4)), float(m.group(5))
        cls = m.group(6).strip()
        
        # Unpad
        x0_px = (x0_n * PROC_W - pad_x) / effective_scale
        y0_px = (y0_n * PROC_H - pad_y) / effective_scale
        x1_px = (x1_n * PROC_W - pad_x) / effective_scale
        y1_px = (y1_n * PROC_H - pad_y) / effective_scale
        
        # Convert pixels to top-left points
        x0_pt_tl = x0_px * 72.0 / dpi
        y0_pt_tl = y0_px * 72.0 / dpi
        x1_pt_tl = x1_px * 72.0 / dpi
        y1_pt_tl = y1_px * 72.0 / dpi
        
        # Flip y axis to bottom-left origin
        x0_pt = max(0.0, min(pw_pt, x0_pt_tl))
        y0_pt = max(0.0, min(ph_pt, ph_pt - y1_pt_tl))
        x1_pt = max(0.0, min(pw_pt, x1_pt_tl))
        y1_pt = max(0.0, min(ph_pt, ph_pt - y0_pt_tl))
        
        canonical = MAPPING.get(cls.lower(), 'paragraph')
        
        if (x1_pt - x0_pt) > 1 and (y1_pt - y0_pt) > 1:
            detections.append({
                'bbox': [x0_pt, y0_pt, x1_pt, y1_pt],
                'label': canonical,
                'score': 0.85
            })
    return detections

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
            
            # Spatial alignment threshold IoU > 0.1
            aligned_label = best_label if best_iou > 0.1 else pred["label"]
            page_oracle.append({
                "bbox": pred["bbox"],
                "label": aligned_label,
                "score": pred.get("score", 0.9)
            })
        oracle_preds.append(page_oracle)
    return oracle_preds

def evaluate_run(all_gt, all_preds):
    iou_thresholds = np.arange(0.5, 1.0, 0.05)
    metrics = compute_map(all_gt, all_preds, iou_thresholds, CLASSES)
    
    # Compute per-class F1 at IoU=0.5
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

def metrics_f1(m):
    p, r = m['precision'], m['recall']
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

def main():
    pdf_path = "layout_corpora/synthetic_by_claude/MedCore_Catalogue.pdf"
    json_path = "layout_corpora/synthetic_by_claude/MedCore_Catalogue_groundtruth.json"
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device selected: {device}")
    
    print("Loading Ground Truth...")
    all_gt = load_ground_truth(json_path)
    print(f"Loaded GT for {len(all_gt)} pages.")
        
    # ── DocLayoutYOLO ──────────────────
    print("\n[1/2] Loading DocLayoutYOLO...")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    print("Running DocLayoutYOLO Inference...")
    t_dly_0 = time.time()
    dly_preds = run_docling_detection(pdf_path, converter)
    t_dly = time.time() - t_dly_0
    print(f"DocLayoutYOLO finished in {t_dly:.2f}s (~{t_dly/4.0:.2f}s/page)")
    
    # ── Nemotron-Parse ──────────────────
    print("\n[2/2] Loading NVIDIA Nemotron-Parse-v1.1...")
    MODEL_PATH = 'nvidia/NVIDIA-Nemotron-Parse-v1.1'
    t_nemo_load = time.time()
    nemo_model = AutoModel.from_pretrained(
        MODEL_PATH,
        trust_remote_code = True,
        torch_dtype       = torch.float16,
        low_cpu_mem_usage = True,
    ).to(device).eval()
    
    nemo_tokenizer  = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=True)
    nemo_processor  = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True, use_fast=True)
    nemo_processor.image_processor.final_size = (1024, 832)
    nemo_processor.image_processor._create_transforms()
    nemo_gen_config = GenerationConfig.from_pretrained(MODEL_PATH, trust_remote_code=True)
    nemo_gen_config.max_new_tokens = 1024
    print(f"Nemotron loaded in {time.time() - t_nemo_load:.2f}s")
    
    print("Running Nemotron-Parse Inference...")
    nemo_preds = []
    t_nemo_0 = time.time()
    for page_num in range(1, 5):
        img, pw, ph = render_pdf_page(pdf_path, page_num, dpi=150)
        dets = run_nemotron_on_page(img, pw, ph, nemo_model, nemo_processor, nemo_tokenizer, nemo_gen_config, device, dpi=150)
        nemo_preds.append(dets)
    t_nemo = time.time() - t_nemo_0
    print(f"Nemotron finished in {t_nemo:.2f}s (~{t_nemo/4.0:.2f}s/page)")
    
    # ── Run Evaluation ──────────────────
    print("\nEvaluating DocLayoutYOLO Naive...")
    dly_naive_metrics, dly_naive_class = evaluate_run(all_gt, dly_preds)
    
    print("Evaluating DocLayoutYOLO Oracle...")
    dly_oracle_preds = get_oracle_predictions(all_gt, dly_preds)
    dly_oracle_metrics, dly_oracle_class = evaluate_run(all_gt, dly_oracle_preds)
    
    print("Evaluating Nemotron-Parse Naive...")
    nemo_naive_metrics, nemo_naive_class = evaluate_run(all_gt, nemo_preds)
    
    print("Evaluating Nemotron-Parse Oracle...")
    nemo_oracle_preds = get_oracle_predictions(all_gt, nemo_preds)
    nemo_oracle_metrics, nemo_oracle_class = evaluate_run(all_gt, nemo_oracle_preds)
    
    # Generate unified markdown report
    report_lines = [
        "# Benchmark Report: Document Layout Detection on MedCore_Catalogue.pdf",
        "",
        "This report evaluates **DocLayoutYOLO** (via Docling) and **NVIDIA Nemotron-Parse-v1.1** against pixel-perfect, rendering-time ground truth annotations on the 4-page `MedCore_Catalogue.pdf` dataset.",
        "",
        "## Evaluation Methodology",
        "- **Naive Mode**: Evaluates predictions mapped directly to canonical categories via standard mapping dicts. This captures absolute system performance including categorization errors.",
        "- **Oracle Aligned Mode**: Matches predictions to ground truth bounding boxes spatially (IoU > 0.1) and aligns the prediction's category to the ground truth's category. This isolates purely geometric/spatial localization capabilities from classification taxonomy mismatch errors.",
        "",
        "## 1. Overall Performance Comparison",
        "",
        "| Metric | DocLayoutYOLO (Naive) | DocLayoutYOLO (Oracle) | Nemotron-Parse (Naive) | Nemotron-Parse (Oracle) |",
        "| :--- | :---: | :---: | :---: | :---: |",
        f"| **mAP@0.5 (Primary)** | **{dly_naive_metrics['mAP50']:.4f}** | **{dly_oracle_metrics['mAP50']:.4f}** | **{nemo_naive_metrics['mAP50']:.4f}** | **{nemo_oracle_metrics['mAP50']:.4f}** |",
        f"| **mAP@0.5:0.95 (Secondary)** | **{dly_naive_metrics['mAP5095']:.4f}** | **{dly_oracle_metrics['mAP5095']:.4f}** | **{nemo_naive_metrics['mAP5095']:.4f}** | **{nemo_oracle_metrics['mAP5095']:.4f}** |",
        f"| **Overall Precision (IoU=0.5)** | {dly_naive_metrics['precision']:.4f} | {dly_oracle_metrics['precision']:.4f} | {nemo_naive_metrics['precision']:.4f} | {nemo_oracle_metrics['precision']:.4f} |",
        f"| **Overall Recall (IoU=0.5)** | {dly_naive_metrics['recall']:.4f} | {dly_oracle_metrics['recall']:.4f} | {nemo_naive_metrics['recall']:.4f} | {nemo_oracle_metrics['recall']:.4f} |",
        f"| **Overall F1-Score (IoU=0.5)** | {metrics_f1(dly_naive_metrics):.4f} | {metrics_f1(dly_oracle_metrics):.4f} | {metrics_f1(nemo_naive_metrics):.4f} | {metrics_f1(nemo_oracle_metrics):.4f} |",
        f"| **Mean IoU (Matched Pairs)** | {dly_naive_metrics['mean_iou']:.4f} | {dly_oracle_metrics['mean_iou']:.4f} | {nemo_naive_metrics['mean_iou']:.4f} | {nemo_oracle_metrics['mean_iou']:.4f} |",
        f"| **Average Inference Speed** | {t_dly/4.0:.2f} s/page | {t_dly/4.0:.2f} s/page | {t_nemo/4.0:.2f} s/page | {t_nemo/4.0:.2f} s/page |",
        "",
        "## 2. Per-Class Detail Scorecard (F1-Score at IoU=0.5)",
        "",
        "| Class Name | DLY (Naive) | DLY (Oracle) | Nemotron (Naive) | Nemotron (Oracle) |",
        "| :--- | :---: | :---: | :---: | :---: |"
    ]
    
    for cls in CLASSES:
        dly_n = dly_naive_class[cls]['F1']
        dly_o = dly_oracle_class[cls]['F1']
        nemo_n = nemo_naive_class[cls]['F1']
        nemo_o = nemo_oracle_class[cls]['F1']
        report_lines.append(
            f"| **{cls}** | {dly_n:.4f} | {dly_o:.4f} | {nemo_n:.4f} | {nemo_o:.4f} |"
        )
        
    report_lines.append("")
    report = "\n".join(report_lines)
    print("\n" + report)
    
    os.makedirs("results/evaluation", exist_ok=True)
    report_path = "results/evaluation/medcore_evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nSaved combined evaluation report to {report_path}")

if __name__ == "__main__":
    main()
