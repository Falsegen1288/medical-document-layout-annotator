# Document Intelligence & Retrieval Pipeline Benchmark

A comprehensive benchmarking suite for complex document understanding, multi-stage vs end-to-end VLM parsing, document chunking strategies, and hybrid retrieval performance. Evaluated on synthetic and real medical catalogue documents (`MedCore_Catalogue_v2.pdf`).

---

## 📂 Repository Structure

```
benchmarking/
├── benchmarks/
│   ├── layout/            # Layout detection benchmarks (DocLayoutYOLO, Nemotron-Parse)
│   ├── text/              # Text OCR benchmarks (EasyOCR, Tesseract)
│   ├── table/             # Table extraction benchmarks (Docling/TableFormer, TATR)
│   ├── image/             # Image captioning & attribute benchmarks (Qwen2.5-VL, LLaMA-4-Scout)
│   └── retrieval/         # Chunking & Embedding retrieval benchmarks (RRF, Dense, BM25, SPLADE)
├── data/
│   ├── raw/               # Raw PDF documents (MedCore_Catalogue_v2.pdf)
│   └── image_pool/        # Extracted figure & table crop assets
├── ground_truth/
│   ├── layout/            # Bounding box ground truth annotations
│   ├── text/              # Text content ground truth (64 elements across 4 pages)
│   ├── table/             # HTML table ground truth (e0043, e0074)
│   └── image/             # Image attribute ground truth
├── results/
│   ├── layout/            # Layout detection metrics & COCO evaluation reports
│   ├── text/              # Character Error Rate (CER) and Word Error Rate (WER) CSVs
│   ├── table/             # Table Edit Distance Similarity (TEDS) and Cell F1 CSVs
│   ├── image/             # Captioning BLEU/ROUGE/CIDEr & attribute F1 leaderboards
│   ├── retrieval/         # Chunking & Embedding Retrieval Leaderboard (Spec Hit@5, Faithfulness)
│   └── evaluation/        # Consolidated evaluation reports
├── src/                   # React + Vite TypeScript layout annotation workspace SPA
├── generate_deck.cjs      # 16:9 PPTX / PDF presentation generator script
└── requirements.txt       # Python dependency manifest
```

---

## 📊 Benchmark Results & Leaderboards

### 1. Chunking & Embedding Retrieval Leaderboard

*Evaluated across a 54 ground-truth Q&A pair bank using 4-stage RRF hybrid retrieval ($k=60$) and Ragas/DeepEval faithfulness scoring with a `qwen3-32b` judge.*

| Rank | Model | Strategy | Spec Hit@5 | Overall Hit@5 | Downstream Faithfulness |
|:---:|:---|:---|:---:|:---:|:---:|
| **1** | **qwen3-embedding-8b-4bit** | **bm25_hybrid** | **1.00** | **0.518** | **0.454** |
| 2 | baseline | bm25_only | 1.00 | 0.722 | 0.272 |
| 3 | bge-m3 | bm25_hybrid | 1.00 | 0.444 | 0.181 |
| 4 | nv-embed-v2-fp16 | bm25_hybrid | 1.00 | 0.500 | 0.181 |
| 5 | bge-m3 | dense_only | 1.00 | 0.240 | 0.090 |
| 6 | nomic-embed-text | bm25_hybrid | 1.00 | 0.462 | 0.000 |
| 7 | bge-m3 | 3-way hybrid (dense+sparse+colbert) | 0.50 | 0.166 | 0.090 |
| 8 | granite-vision-embedding | text_only | 0.50 | 0.363 | 0.000 |

#### Chunking & Embedding Inferences:
- **Lexical BM25 is essential for spec lookups**: Subword tokenizers fragment alphanumeric model/part numbers (e.g. `352952`). A custom regex tokenizer preserving full part numbers hits **100% Spec Hit Rate@5**.
- **Exact lexical context drives downstream LLM faithfulness**: Faithfulness increases from `0.090` (dense-only) to `0.454` (Qwen3-8B + BM25 hybrid) by preventing LLM spec hallucinations.
- **RRF Fusion ($k=60$) provides resilience**: Combining dense semantic representations with BM25 lexical matches outperforms single-retriever strategies.

---

### 2. Document Parsing Benchmarks (Modular Baseline vs GLM-OCR)

| Task / Metric | Modular Baseline Pipeline | GLM-OCR (0.9B VLM) | Notes / Observations |
|:---|:---|:---|:---|
| **Table Extraction (TEDS)** | 0.9816 (EasyOCR+Structure)<br>0.7295 (Docling)<br>0.7444 (TATR) | **0.9996** (`Table Recognition:`) | **GLM-OCR Wins**: 1.0000 TEDS-Struct & Cell-F1 with official task prompt |
| **Text OCR (CER)** | **0.1078** (EasyOCR, per-zone)<br>0.1328 (Tesseract, per-zone) | **0.4894** (Page-level, excl. P3) | Modular evaluated on 64 cropped boxes; GLM-OCR evaluated end-to-end on full pages |
| **Layout Detection (mAP)** | 0.0450 (DocLayoutYOLO)<br>0.0556 (Nemotron-Parse) | N/A (End-to-End Markdown) | GLM-OCR replaces layout bbox step entirely |
| **Image Captioning (BERTScore)** | 0.8329 (LLaMA-4-Scout)<br>0.8171 (Qwen2.5VL-3B) | N/A (Text output) | Cloud API vs local VLM tradeoff |
| **Architecture Complexity** | 4–5 chained models | **1 single 0.9B model** | GLM-OCR drastically simplifies pipeline maintenance |

---

## 🛠️ Quick Start & Local Execution

### Prerequisites
- Node.js (v20+)
- Python 3.10+ (with PyTorch + CUDA 12.1 for GPU models)

### 1. Run Chunking & Embedding Retrieval Benchmark
```bash
python benchmarks/retrieval/run_retrieval_benchmark.py
```

### 2. Run Document Parsing & Table Extraction Benchmarks
```bash
# Run modular layout & parsing benchmark
python benchmarks/layout/run_custom_benchmark.py

# Run GLM-OCR real GPU benchmark & table recognition
python D:/ocr_benchmark/scripts/glm_ocr_benchmark.py
python D:/ocr_benchmark/scripts/eval_glm_ocr_table_recognition.py
```

### 3. Generate Widescreen PPTX / PDF Deliverable Deck
```bash
node generate_deck.cjs
```
- Outputs: `results_review_Week6.pptx` and `results_review_Week6.pdf`
