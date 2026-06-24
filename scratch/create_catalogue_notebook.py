# scratch/create_catalogue_notebook.py
import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 📐 Document Layout Detection Benchmark & Visualization\n",
    "\n",
    "This notebook presents a visual layout evaluation of **DocLayoutYOLO** (via Docling) and **NVIDIA Nemotron-Parse-v1.1** against pixel-perfect ground truth annotations on the 4-page catalog document: `MedCore_Catalogue.pdf`.\n",
    "\n",
    "This notebook is designed for stakeholders and managers who want to visually judge model localization performance, see exact bounding box overlaps, and review baseline tables side-by-side.\n",
    "\n",
    "---\n",
    "\n",
    "## 1. Benchmarks Summary (Tabular Format)\n",
    "\n",
    "Below is the comparison scorecard across all evaluated datasets (including the traditional public benchmarks from the Kaliber Week 2 slide deck and our synthetic catalog evaluation)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "import json\n",
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import matplotlib.patches as patches\n",
    "import fitz  # PyMuPDF\n",
    "from PIL import Image, ImageDraw\n",
    "\n",
    "# Create tabular baseline dataframe\n",
    "traditional_data = [\n",
    "    # Dataset, Model, mAP@50, mAP@50:95, Precision, Recall, F1, Mean IoU\n",
    "    [\"DocLayNet\", \"DocLayoutYOLO\", 0.436, 0.352, 0.588, 0.556, 0.571, 0.894],\n",
    "    [\"DocLayNet\", \"Nemotron-Parse\", 0.439, 0.304, 0.780, 0.593, 0.674, 0.868],\n",
    "    [\"DocLayNet\", \"ADE-DPT2 (API)\", 0.242, 0.144, 0.545, 0.333, 0.414, 0.859],\n",
    "    \n",
    "    [\"PubLayNet\", \"DocLayoutYOLO\", 0.545, 0.412, 0.686, 0.800, 0.738, 0.905],\n",
    "    [\"PubLayNet\", \"Nemotron-Parse\", 0.383, 0.224, 0.818, 0.600, 0.692, 0.884],\n",
    "    [\"PubLayNet\", \"ADE-DPT2 (API)\", 0.490, 0.275, 0.739, 0.567, 0.642, 0.848],\n",
    "    \n",
    "    [\"DocBank\", \"DocLayoutYOLO\", 0.016, 0.007, 0.233, 0.184, 0.206, 0.761],\n",
    "    [\"DocBank\", \"Nemotron-Parse\", 0.015, 0.005, 0.231, 0.158, 0.187, 0.694],\n",
    "    [\"DocBank\", \"ADE-DPT2 (API)\", 0.023, 0.008, 0.333, 0.184, 0.237, 0.691],\n",
    "    \n",
    "    [\"MedCore Catalogue (Naive)\", \"DocLayoutYOLO\", 0.045, 0.031, 0.027, 0.056, 0.037, 0.795],\n",
    "    [\"MedCore Catalogue (Naive)\", \"Nemotron-Parse\", 0.056, 0.022, 0.023, 0.042, 0.030, 0.650],\n",
    "    \n",
    "    [\"MedCore Catalogue (Oracle)\", \"DocLayoutYOLO\", 0.174, 0.142, 0.068, 0.141, 0.092, 0.841],\n",
    "    [\"MedCore Catalogue (Oracle)\", \"Nemotron-Parse\", 0.176, 0.066, 0.055, 0.099, 0.070, 0.649]\n",
    "]\n",
    "\n",
    "cols = [\"Dataset\", \"Model\", \"mAP@50\", \"mAP@50:95\", \"Precision\", \"Recall\", \"F1-Score\", \"Mean IoU\"]\n",
    "df_benchmarks = pd.DataFrame(traditional_data, columns=cols)\n",
    "df_benchmarks"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Diagnostics: Why is catalogue performance different from standard datasets?\n",
    "\n",
    "1. **Background Nesting**: Modern catalogs feature colored column-width background boxes (annotated as `section_header`). Standard flat layout detectors predict either the parent box OR the children (figures, titles, text, tables) inside it. When they predict the parent, all nested elements are counted as misses (False Negatives), dropping the recall.\n",
    "2. **Taxonomy/Category Mismatch**: The models classify titles and headers as generic paragraphs or section headers. Flipping predictions to closest-matching ground truth categories (**Oracle Aligned Mode**) increases mAP from ~0.05 to ~0.176, showing that categorization errors account for a significant share of the drop, but nesting remains the main bottleneck."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Visualizing Bounding Boxes (GT vs. DocLayoutYOLO vs. Nemotron-Parse)\n",
    "\n",
    "Below we load cached predictions and render the pages of `MedCore_Catalogue.pdf` side-by-side with high-contrast bounding boxes:\n",
    "- **Green**: Ground Truth (the target layouts)\n",
    "- **Blue**: DocLayoutYOLO (Docling)\n",
    "- **Orange**: NVIDIA Nemotron-Parse-v1.1"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Helper to render a page and load coordinates\n",
    "def render_pdf_page(pdf_path, page_num, dpi=100):\n",
    "    doc = fitz.open(pdf_path)\n",
    "    page = doc[page_num - 1]\n",
    "    scale = dpi / 72.0\n",
    "    mat = fitz.Matrix(scale, scale)\n",
    "    pix = page.get_pixmap(matrix=mat, alpha=False)\n",
    "    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)\n",
    "    pw_pt, ph_pt = page.rect.width, page.rect.height\n",
    "    doc.close()\n",
    "    return img, pw_pt, ph_pt\n",
    "\n",
    "def draw_bboxes(img, boxes, color, label_prefix, ph_pt, dpi=100):\n",
    "    draw_img = img.copy()\n",
    "    draw = ImageDraw.Draw(draw_img)\n",
    "    scale = dpi / 72.0\n",
    "    \n",
    "    for b in boxes:\n",
    "        # Convert points back to pixels\n",
    "        # bbox is [x0, y0, x1, y1] bottom-left points\n",
    "        x0_pt, y0_pt, x1_pt, y1_pt = b[\"bbox\"]\n",
    "        \n",
    "        # Convert y-axis bottom-left to top-left points\n",
    "        y0_pt_tl = ph_pt - y1_pt\n",
    "        y1_pt_tl = ph_pt - y0_pt\n",
    "        \n",
    "        # Convert points to pixels\n",
    "        x0_px = x0_pt * scale\n",
    "        y0_px = y0_pt_tl * scale\n",
    "        x1_px = x1_pt * scale\n",
    "        y1_px = y1_pt_tl * scale\n",
    "        \n",
    "        # Draw rectangle\n",
    "        draw.rectangle([x0_px, y0_px, x1_px, y1_px], outline=color, width=2)\n",
    "        # Text label\n",
    "        label = f\"{label_prefix}: {b['label']}\"\n",
    "        draw.text((x0_px + 2, y0_px + 2), label, fill=color)\n",
    "    return draw_img"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Load Ground Truth and Cached Predictions\n",
    "gt_path = \"layout_corpora/synthetic_by_claude/MedCore_Catalogue_groundtruth.json\"\n",
    "cache_path = \"results/evaluation/predictions_cache.json\"\n",
    "pdf_path = \"layout_corpora/synthetic_by_claude/MedCore_Catalogue.pdf\"\n",
    "\n",
    "with open(gt_path, \"r\", encoding=\"utf-8\") as f:\n",
    "    gt_data = json.load(f)\n",
    "\n",
    "# Format GT boxes\n",
    "all_gt = []\n",
    "for p_data in gt_data[\"pages\"]:\n",
    "    page_gt = []\n",
    "    for elem in p_data[\"elements\"]:\n",
    "        bbox = elem[\"bbox_pt\"]\n",
    "        page_gt.append({\n",
    "            \"bbox\": [bbox[\"x\"], bbox[\"y\"], bbox[\"x\"] + bbox[\"w\"], bbox[\"y\"] + bbox[\"h\"]],\n",
    "            \"label\": elem[\"class\"]\n",
    "        })\n",
    "    all_gt.append(page_gt)\n",
    "\n",
    "# Load cached predictions\n",
    "if os.path.exists(cache_path):\n",
    "    with open(cache_path, \"r\", encoding=\"utf-8\") as f:\n",
    "        cache_data = json.load(f)\n",
    "    dly_preds = cache_data[\"docling\"]\n",
    "    nemo_preds = cache_data[\"nemotron\"]\n",
    "else:\n",
    "    # Fallback to empty list if cache not found\n",
    "    dly_preds = [[] for _ in range(4)]\n",
    "    nemo_preds = [[] for _ in range(4)]\n",
    "    print(\"Warning: Predictions cache not found! Please run cache_predictions.py first.\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Render and visualize each page side-by-side\n",
    "dpi_val = 110 # Set DPI for display\n",
    "for page_num in range(1, 5):\n",
    "    img, pw, ph = render_pdf_page(pdf_path, page_num, dpi=dpi_val)\n",
    "    \n",
    "    # Draw boxes\n",
    "    img_gt = draw_bboxes(img, all_gt[page_num - 1], \"#2ecc71\", \"GT\", ph, dpi=dpi_val) # Green\n",
    "    img_dly = draw_bboxes(img, dly_preds[page_num - 1], \"#3498db\", \"DLY\", ph, dpi=dpi_val) # Blue\n",
    "    img_nemo = draw_bboxes(img, nemo_preds[page_num - 1], \"#e67e22\", \"Nemo\", ph, dpi=dpi_val) # Orange\n",
    "    \n",
    "    fig, axes = plt.subplots(1, 3, figsize=(20, 8))\n",
    "    fig.suptitle(f\"Page {page_num} Visual Layout Comparison\", fontsize=16, fontweight='bold')\n",
    "    \n",
    "    axes[0].imshow(img_gt)\n",
    "    axes[0].set_title(f\"Ground Truth ({len(all_gt[page_num - 1])} boxes)\", color=\"#2ecc71\", fontweight='bold')\n",
    "    axes[0].axis(\"off\")\n",
    "    \n",
    "    axes[1].imshow(img_dly)\n",
    "    axes[1].set_title(f\"DocLayoutYOLO ({len(dly_preds[page_num - 1])} boxes)\", color=\"#3498db\", fontweight='bold')\n",
    "    axes[1].axis(\"off\")\n",
    "    \n",
    "    axes[2].imshow(img_nemo)\n",
    "    axes[2].set_title(f\"Nemotron-Parse ({len(nemo_preds[page_num - 1])} boxes)\", color=\"#e67e22\", fontweight='bold')\n",
    "    axes[2].axis(\"off\")\n",
    "    \n",
    "    plt.tight_layout()\n",
    "    plt.show()"
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}

with open("synthetic_catalogue_evaluation.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)

print("Created synthetic_catalogue_evaluation.ipynb successfully!")
