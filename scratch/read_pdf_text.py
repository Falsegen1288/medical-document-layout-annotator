# scratch/read_pdf_text.py
import fitz # PyMuPDF
import sys

pdf_path = "results_review_kaliber_Week2.pdf"
out_path = "scratch/pdf_text.txt"
try:
    doc = fitz.open(pdf_path)
    print(f"Loaded {pdf_path} with {len(doc)} pages.")
    with open(out_path, "w", encoding="utf-8") as f:
        for i, page in enumerate(doc):
            f.write(f"--- Page {i+1} ---\n")
            text = page.get_text()
            f.write(text)
            f.write("\n" + "="*50 + "\n")
    print(f"Successfully wrote text to {out_path}")
except Exception as e:
    print(f"Error reading PDF: {e}")
