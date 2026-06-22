# core/doclaynet_label_map.py
"""
Maps DocLayNet categories to canonical labels, and heuristically classifies
DocLayNet pages into our 5 domain buckets based on element-type distribution.
"""

from typing import Dict, List, Optional

# DocLayNet 11-category → canonical label mapping
# (identical to DOCLAYNET_TO_CANONICAL in backend/benchmark.py but self-contained)
DOCLAYNET_TO_CANONICAL = {
    "Caption": "caption",
    "Footnote": "footnote",
    "Formula": "formula",
    "List-item": "list_item",
    "Page-footer": "page_footer",
    "Page-header": "page_header",
    "Picture": "picture",
    "Section-header": "section_header",
    "Table": "table",
    "Text": "text",
    "Title": "title",
}

# Integer category IDs used in DocLayNet COCO annotations (0-indexed)
DOCLAYNET_CAT_ID_TO_NAME = {
    0: "Caption",
    1: "Footnote",
    2: "Formula",
    3: "List-item",
    4: "Page-footer",
    5: "Page-header",
    6: "Picture",
    7: "Section-header",
    8: "Table",
    9: "Text",
    10: "Title",
}

# DocLayNet doc_category field → our domain mapping
DOCLAYNET_DOC_CATEGORY_TO_DOMAIN = {
    "financial_reports": "financial_invoice",
    "scientific_articles": "scientific_paper",
    "laws_and_regulations": "legal_opinion",
    "government_tenders": "legal_opinion",
    "manuals": "medical_report",  # proxy: single-column reports
    "patents": "scientific_paper",
}


def map_doclaynet_label(label) -> Optional[str]:
    """Map a DocLayNet label (string or int) to a canonical label."""
    if isinstance(label, int):
        name = DOCLAYNET_CAT_ID_TO_NAME.get(label)
        if name:
            return DOCLAYNET_TO_CANONICAL.get(name)
        return None
    return DOCLAYNET_TO_CANONICAL.get(label)


def classify_doclaynet_page(label_counts: Dict[str, int]) -> str:
    """
    Heuristically assign a DocLayNet page to one of our 5 domains
    based on element-type distribution.

    Rules (applied in priority order):
      1. If page has Formula elements → scientific_paper
      2. If page has ≥2 Tables and ≥1 Picture → financial_invoice
      3. If page has ≥2 Tables (no picture) → financial_invoice
      4. If page is mostly Text + Section-header, few Tables → legal_opinion
      5. If page has multiple Pictures → commercial_catalog
      6. Default → medical_report (single-column, text-heavy reports)

    Returns one of: financial_invoice, scientific_paper, legal_opinion,
                    medical_report, commercial_catalog
    """
    total = sum(label_counts.values()) or 1

    n_formula = label_counts.get("formula", 0)
    n_table = label_counts.get("table", 0)
    n_picture = label_counts.get("picture", 0)
    n_text = label_counts.get("text", 0)
    n_section = label_counts.get("section_header", 0)
    n_list = label_counts.get("list_item", 0)
    n_caption = label_counts.get("caption", 0)

    # Rule 1: Formulas → scientific paper
    if n_formula >= 1:
        return "scientific_paper"

    # Rule 2/3: Multiple tables → financial invoice
    if n_table >= 2:
        return "financial_invoice"

    # Rule 4: Heavy text + section headers, few tables → legal
    text_ratio = (n_text + n_section) / total
    if text_ratio > 0.7 and n_table <= 1 and n_picture <= 1:
        return "legal_opinion"

    # Rule 5: Multiple pictures → catalog
    if n_picture >= 3:
        return "commercial_catalog"

    # Rule 6: Single table + text → financial if table present
    if n_table == 1 and n_text >= 2:
        return "financial_invoice"

    # Default: medical report (single-column text-heavy)
    return "medical_report"
