# scratch/count_pred_elements.py
import os
import sys
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("layout_corpora/synthetic_by_claude/MedCore_Catalogue.pdf")
doc_obj = result.document

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

pages_counts = [{} for _ in range(4)]
for item, _ in doc_obj.iterate_items():
    if not hasattr(item, 'prov') or not item.prov:
        continue
    prov = item.prov[0]
    pg_num = prov.page_no
    if pg_num < 1 or pg_num > 4:
        continue
    raw_label = type(item).__name__.lower().replace('item', '').replace('docling', '')
    mapped_label = DOCLING_TO_CANONICAL.get(raw_label, raw_label)
    pages_counts[pg_num - 1][mapped_label] = pages_counts[pg_num - 1].get(mapped_label, 0) + 1

for idx, counts in enumerate(pages_counts):
    print(f"=== Page {idx+1} ===")
    for cls, count in sorted(counts.items()):
        print(f"  {cls}: {count}")
