# scratch/cache_predictions.py
import os
import sys
import json
import re
import fitz  # PyMuPDF
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor, AutoTokenizer, GenerationConfig
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

sys.path.insert(0, os.path.abspath("."))

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

def run_docling_detection(pdf_path):
    print("Running DocLayoutYOLO (via Docling)...")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(pdf_path)
    doc_obj = result.document
    
    pages_preds = [[] for _ in range(4)]
    for item, _ in doc_obj.iterate_items():
        if not hasattr(item, 'prov') or not item.prov:
            continue
        prov = item.prov[0]
        pg_num = prov.page_no
        if pg_num < 1 or pg_num > 4:
            continue
        bbox = prov.bbox
        x0, y0, x1, y1 = bbox.l, bbox.b, bbox.r, bbox.t
        raw_label = type(item).__name__.lower().replace('item', '').replace('docling', '')
        mapped_label = MAPPING.get(raw_label, raw_label)
        
        pages_preds[pg_num - 1].append({
            "bbox": [x0, y0, x1, y1],
            "label": mapped_label,
            "score": 0.9
        })
    return pages_preds

def run_nemotron_on_page(img, pw_pt, ph_pt, model, processor, tokenizer, gen_config, device, dpi=150):
    orig_w, orig_h = img.size
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
        
        x0_px = (x0_n * PROC_W - pad_x) / effective_scale
        y0_px = (y0_n * PROC_H - pad_y) / effective_scale
        x1_px = (x1_n * PROC_W - pad_x) / effective_scale
        y1_px = (y1_n * PROC_H - pad_y) / effective_scale
        
        x0_pt_tl = x0_px * 72.0 / dpi
        y0_pt_tl = y0_px * 72.0 / dpi
        x1_pt_tl = x1_px * 72.0 / dpi
        y1_pt_tl = y1_px * 72.0 / dpi
        
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

def main():
    pdf_path = "layout_corpora/synthetic_by_claude/MedCore_Catalogue.pdf"
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # Run DocLayoutYOLO
    dly_preds = run_docling_detection(pdf_path)
    
    # Run Nemotron
    print("Loading NVIDIA Nemotron-Parse-v1.1...")
    MODEL_PATH = 'nvidia/NVIDIA-Nemotron-Parse-v1.1'
    nemo_model = AutoModel.from_pretrained(
        MODEL_PATH, trust_remote_code=True, torch_dtype=torch.float16, low_cpu_mem_usage=True
    ).to(device).eval()
    nemo_tokenizer  = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=True)
    nemo_processor  = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True, use_fast=True)
    nemo_processor.image_processor.final_size = (1024, 832)
    nemo_processor.image_processor._create_transforms()
    nemo_gen_config = GenerationConfig.from_pretrained(MODEL_PATH, trust_remote_code=True)
    nemo_gen_config.max_new_tokens = 1024
    
    print("Running Nemotron-Parse...")
    nemo_preds = []
    for page_num in range(1, 5):
        # render
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        scale = 150 / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        pw_pt, ph_pt = page.rect.width, page.rect.height
        doc.close()
        
        dets = run_nemotron_on_page(img, pw_pt, ph_pt, nemo_model, nemo_processor, nemo_tokenizer, nemo_gen_config, device, dpi=150)
        nemo_preds.append(dets)
        
    cache = {
        "docling": dly_preds,
        "nemotron": nemo_preds
    }
    
    cache_path = "results/evaluation/predictions_cache.json"
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    print(f"Saved predictions cache to {cache_path}")

if __name__ == "__main__":
    main()
