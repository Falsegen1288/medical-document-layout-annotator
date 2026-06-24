# scratch/print_predictions_debug.py
import sys
import os
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("layout_corpora/synthetic_by_claude/MedCore_Catalogue.pdf")
doc_obj = result.document

print("=== DOCLING DETECTED ITEMS ===")
for idx, (item, _) in enumerate(doc_obj.iterate_items()):
    if not hasattr(item, 'prov') or not item.prov:
        continue
    prov = item.prov[0]
    bbox = prov.bbox
    print(f"Page {prov.page_no} | {type(item).__name__} | bbox: l={bbox.l:.2f}, b={bbox.b:.2f}, r={bbox.r:.2f}, t={bbox.t:.2f} | text: {getattr(item, 'text', '')[:40]!r}")
