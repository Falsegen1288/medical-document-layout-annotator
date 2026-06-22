# core/canonical_taxonomy.py

CANONICAL_LABELS = [
    "title", "text", "table", "picture", "list_item",
    "caption", "section_header", "page_footer", "page_header",
    "formula", "footnote",
]

def validate_label(label: str) -> None:
    if label not in CANONICAL_LABELS:
        raise ValueError(f"'{label}' is not in CANONICAL_LABELS: {CANONICAL_LABELS}")
