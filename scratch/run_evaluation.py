# scratch/run_evaluation.py
import os
import sys
import glob
import json
import time
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageDraw
import torch

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath("."))

from synthetic_layout_gen.core.canonical_taxonomy import CANONICAL_LABELS
from backend.benchmark import (
    DOCLAYNET_TO_CANONICAL,
    compute_map
)

warnings.filterwarnings('ignore')
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Device: {DEVICE}")

def load_synthetic_dataset(output_root="output/"):
    domains = ["financial_invoice", "scientific_paper", "legal_opinion", "medical_report", "commercial_catalog"]
    samples = []
    
    for domain in domains:
        json_pattern = os.path.join(output_root, domain, "json", "*.json")
        json_files = sorted(glob.glob(json_pattern))
        
        for json_path in json_files:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            document_id = data["document_id"]
            for page in data["pages"]:
                image_rel_path = page["image_path"]
                image_abs_path = os.path.abspath(image_rel_path)
                pdf_path = os.path.join(output_root, domain, "pdfs", f"{document_id}.pdf")
                
                gt_boxes = []
                for elem in page["layout_elements"]:
                    gt_boxes.append({
                        "bbox": elem["bbox"],
                        "label": elem["type"]
                    })
                
                samples.append({
                    "document_id": document_id,
                    "domain": domain,
                    "page_number": page["page_number"],
                    "image_path": image_abs_path,
                    "pdf_path": pdf_path,
                    "gt": gt_boxes,
                    "dimensions_pt": page["dimensions_pt"]
                })
    return samples

samples = load_synthetic_dataset()
print(f"Loaded {len(samples)} synthetic pages for evaluation.")

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from transformers import AutoModel, AutoProcessor, AutoTokenizer, GenerationConfig

print("Loading DocLayoutYOLO...")
pipeline_options = PdfPipelineOptions()
pipeline_options.do_table_structure = True
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
print("DocLayoutYOLO loaded.")

print("Loading NVIDIA Nemotron-Parse-v1.1...")
MODEL_PATH = 'nvidia/NVIDIA-Nemotron-Parse-v1.1'
nemo_model = AutoModel.from_pretrained(
    MODEL_PATH,
    trust_remote_code = True,
    torch_dtype       = torch.float16,
    low_cpu_mem_usage = True,
).to(DEVICE).eval()

nemo_tokenizer  = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=True)
nemo_processor  = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True, use_fast=True)
nemo_processor.image_processor.final_size = (1024, 832)
nemo_processor.image_processor._create_transforms()
nemo_gen_config = GenerationConfig.from_pretrained(MODEL_PATH, trust_remote_code=True)
nemo_gen_config.max_new_tokens = 1024
print("Nemotron-Parse loaded.")

import re

PROC_W = 832
PROC_H = 1024
BLOCK_PATTERN = re.compile(
    r'<x_([0-9.]+)><y_([0-9.]+)>'   # top-left (x_L, y_T)
    r'(.*?)'                          # text content
    r'<x_([0-9.]+)><y_([0-9.]+)>'   # bottom-right (x_R, y_B)
    r'<class_([^>]+)>',              # class label
    re.DOTALL
)

def run_docling_on_pdf(pdf_path, page_number):
    try:
        result = converter.convert(pdf_path)
        doc_obj = result.document
        page_info = doc_obj.pages.get(page_number)
        pw_pt, ph_pt = (page_info.size.width, page_info.size.height) if page_info and page_info.size else (612.0, 792.0)
        
        preds = []
        for item, _ in doc_obj.iterate_items():
            if not hasattr(item, 'prov') or not item.prov:
                continue
            prov = item.prov[0]
            if prov.page_no != page_number:
                continue
            bbox = prov.bbox
            label_raw = type(item).__name__.lower().replace('item', '').replace('docling', '')
            canonical = DOCLAYNET_TO_CANONICAL.get(label_raw, 'text')
            
            x0, y0 = bbox.l, ph_pt - bbox.t
            x1, y1 = bbox.r, ph_pt - bbox.b
            x0, x1 = min(x0, x1), max(x0, x1)
            y0, y1 = min(y0, y1), max(y0, y1)
            
            preds.append({
                'bbox': [x0, y0, x1, y1],
                'label': canonical,
                'score': 0.9
            })
        return preds
    except Exception as e:
        print(f"    Docling error: {e}")
        return []

def run_nemotron_on_page(image_path, dpi=150):
    pil_image = Image.open(image_path).convert("RGB")
    orig_w, orig_h = pil_image.size
    
    padded = Image.new('RGB', (PROC_W, PROC_H), (255, 255, 255))
    if orig_w > PROC_W or orig_h > PROC_H:
        scale = min(PROC_W / orig_w, PROC_H / orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        resized = pil_image.resize((new_w, new_h), Image.LANCZOS)
        pad_x = (PROC_W - new_w) // 2
        pad_y = (PROC_H - new_h) // 2
        padded.paste(resized, (pad_x, pad_y))
        effective_scale = scale
    else:
        pad_x = (PROC_W - orig_w) // 2
        pad_y = (PROC_H - orig_h) // 2
        padded.paste(pil_image, (pad_x, pad_y))
        effective_scale = 1.0
        
    task_prompt = '</s><s><predict_bbox><predict_classes>'
    inputs = nemo_processor(images=padded, text=task_prompt, return_tensors='pt', add_special_tokens=False).to(DEVICE)
    
    with torch.no_grad():
        outputs = nemo_model.generate(**inputs, generation_config=nemo_gen_config, max_new_tokens=1024)
        
    decoded = nemo_tokenizer.decode(outputs[0], skip_special_tokens=False)
    
    detections = []
    for m in BLOCK_PATTERN.finditer(decoded):
        x0_n, y0_n = float(m.group(1)), float(m.group(2))
        x1_n, y1_n = float(m.group(4)), float(m.group(5))
        cls = m.group(6).strip()
        
        x0_px = x0_n * PROC_W - pad_x
        y0_px = y0_n * PROC_H - pad_y
        x1_px = x1_n * PROC_W - pad_x
        y1_px = y1_n * PROC_H - pad_y
        
        if effective_scale != 1.0:
            x0_px /= effective_scale; y0_px /= effective_scale
            x1_px /= effective_scale; y1_px /= effective_scale
            
        x0_px = max(0, min(orig_w, x0_px))
        y0_px = max(0, min(orig_h, y0_px))
        x1_px = max(0, min(orig_w, x1_px))
        y1_px = max(0, min(orig_h, y1_px))
        
        canonical = DOCLAYNET_TO_CANONICAL.get(cls, DOCLAYNET_TO_CANONICAL.get(cls.lower(), 'text'))
        
        # Convert px to pt
        x0_pt = x0_px * 72.0 / dpi
        y0_pt = y0_px * 72.0 / dpi
        x1_pt = x1_px * 72.0 / dpi
        y1_pt = y1_px * 72.0 / dpi
        
        if (x1_pt - x0_pt) > 1 and (y1_pt - y0_pt) > 1:
            detections.append({
                'bbox': [x0_pt, y0_pt, x1_pt, y1_pt],
                'label': canonical,
                'score': 0.85
            })
    return detections

print("Running benchmark inference across all domains...")
all_gts = []
docling_preds = []
nemotron_preds = []

t0 = time.time()
for idx, s in enumerate(samples):
    print(f"[{idx+1}/{len(samples)}] Processing {s['document_id']} Page {s['page_number']}...")
    
    # DocLayoutYOLO
    dl_det = run_docling_on_pdf(s['pdf_path'], s['page_number'])
    docling_preds.append(dl_det)
    
    # Nemotron
    nm_det = run_nemotron_on_page(s['image_path'])
    nemotron_preds.append(nm_det)
    
    all_gts.append(s['gt'])

print(f"Finished evaluation loop in {time.time()-t0:.1f}s.")

iou_thresholds = np.linspace(0.5, 0.95, 10)
valid_classes = set(CANONICAL_LABELS)

dl_metrics = compute_map(all_gts, docling_preds, iou_thresholds, valid_classes)
nm_metrics = compute_map(all_gts, nemotron_preds, iou_thresholds, valid_classes)

rows = []
for model_name, metrics in [("DocLayoutYOLO", dl_metrics), ("Nemotron", nm_metrics)]:
    rows.append({
        "Model": model_name,
        "mAP@50": metrics["mAP50"],
        "mAP@50:95": metrics["mAP5095"],
        "Precision": metrics["precision"],
        "Recall": metrics["recall"],
        "F1-Score": metrics["F1"],
        "mean_IoU": metrics["mean_iou"]
    })

df_results = pd.DataFrame(rows).set_index("Model")
print("\n=== OVERALL BENCHMARK RESULTS ===")
print(df_results.to_string())

domain_results = []
domains_list = sorted(list(set(s['domain'] for s in samples)))

for domain in domains_list:
    indices = [i for i, s in enumerate(samples) if s['domain'] == domain]
    domain_gts = [all_gts[i] for i in indices]
    domain_dl = [docling_preds[i] for i in indices]
    domain_nm = [nemotron_preds[i] for i in indices]
    
    dl_dom_m = compute_map(domain_gts, domain_dl, iou_thresholds, valid_classes)
    nm_dom_m = compute_map(domain_gts, domain_nm, iou_thresholds, valid_classes)
    
    domain_results.append({
        "Domain": domain,
        "Model": "DocLayoutYOLO",
        "mAP@50": dl_dom_m["mAP50"],
        "mAP@50:95": dl_dom_m["mAP5095"],
        "F1-Score": dl_dom_m["F1"]
    })
    domain_results.append({
        "Domain": domain,
        "Model": "Nemotron",
        "mAP@50": nm_dom_m["mAP50"],
        "mAP@50:95": nm_dom_m["mAP5095"],
        "F1-Score": nm_dom_m["F1"]
    })

df_domains = pd.DataFrame(domain_results).set_index(["Domain", "Model"])
print("\n=== DOMAIN-SPECIFIC BENCHMARK RESULTS ===")
print(df_domains.to_string())
