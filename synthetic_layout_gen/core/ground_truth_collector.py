# core/ground_truth_collector.py
import json
import os
import contextvars
from synthetic_layout_gen.core.canonical_taxonomy import validate_label

current_collector = contextvars.ContextVar("current_collector", default=None)

class GroundTruthCollector:
    def __init__(self, document_id: str, domain: str, source_engine: str, seed: int):
        self.document_id = document_id
        self.domain = domain
        self.source_engine = source_engine
        self.seed = seed
        self.pages = []
        self._current_page = None
        self._element_counter = 0
        self.uuid_to_element_ids = {}

    def new_page(self, page_number: int, dimensions_pt: tuple[float, float], dimensions_px: tuple[int, int], image_path: str):
        self._current_page = {
            "page_number": page_number,
            "dimensions_pt": list(dimensions_pt),
            "dimensions_px": list(dimensions_px),
            "image_path": image_path,
            "layout_elements": []
        }
        self.pages.append(self._current_page)
        self._element_counter = 0

    def add_element(self, page_number: int, element_type: str, bbox: tuple[float, float, float, float], text: str = None, attributes: dict = None, continued_from: str = None):
        validate_label(element_type)
        
        # Extract short domain prefix and sample string
        parts = self.document_id.split('_')
        domain_short = "".join([p[0] for p in parts[:-1]]) if len(parts) > 1 else "doc"
        try:
            sample_id_val = int(parts[-1])
            sample_str = f"{sample_id_val:05d}"
        except ValueError:
            sample_str = parts[-1] if len(parts) > 0 else "00000"
            
        element_id = f"{domain_short}{sample_str}_p{page_number}_e{self._element_counter:03d}"
        self._element_counter += 1
        
        # Setup element dict
        element = {
            "element_id": element_id,
            "type": element_type,
            "bbox": list(bbox),
            "text": text,
            "reading_order": len(self._current_page["layout_elements"]) if self._current_page else 0,
            "attributes": dict(attributes) if attributes is not None else {}
        }
        
        # Handle splits / continuation
        if continued_from:
            # Check if this shared ID has been recorded before
            if continued_from in self.uuid_to_element_ids:
                prev_element_id = self.uuid_to_element_ids[continued_from][-1]
                element["attributes"]["is_continued_from"] = prev_element_id
                self.set_continued_on_next_page(prev_element_id)
                self.uuid_to_element_ids[continued_from].append(element_id)
            else:
                element["attributes"]["is_continued_from"] = None
                self.uuid_to_element_ids[continued_from] = [element_id]
        else:
            element["attributes"]["is_continued_from"] = None
            
        element["attributes"]["is_continued_on_next_page"] = False
        
        if self._current_page:
            self._current_page["layout_elements"].append(element)

    def set_continued_on_next_page(self, element_id: str):
        for page in self.pages:
            for elem in page["layout_elements"]:
                if elem["element_id"] == element_id:
                    elem["attributes"]["is_continued_on_next_page"] = True
                    return

    def prune_extra_pages(self, num_pages: int):
        """Keep only the first num_pages pages, discarding any trailing empty pages recorded during rendering."""
        self.pages = self.pages[:num_pages]

    def finalize_reading_order(self, page_number: int, order_fn=None):
        page = None
        for p in self.pages:
            if p["page_number"] == page_number:
                page = p
                break
        if not page:
            return
            
        elements = page["layout_elements"]
        if not elements:
            return
            
        if order_fn:
            sorted_elements = order_fn(elements)
        else:
            # Default: sort ascending by top edge (y0), then left edge (x0)
            sorted_elements = sorted(elements, key=lambda e: (e["bbox"][1], e["bbox"][0]))
            
        # Re-assign reading_order to maintain contiguous 0..N-1 sequence
        for idx, elem in enumerate(sorted_elements):
            elem["reading_order"] = idx
            
        page["layout_elements"] = sorted_elements

    def to_dict(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "document_id": self.document_id,
            "domain": self.domain,
            "source_engine": self.source_engine,
            "bbox_convention": {
                "origin": "top-left",
                "units": "pt",
                "dpi_for_px_assets": 150,
                "box_type": "content"
            },
            "generation_seed": self.seed,
            "pages": self.pages
        }

    def write_json(self, path: str) -> None:
        data = self.to_dict()
        
        # Load and validate against schema if exists
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(current_dir, "..", "schema", "ground_truth.schema.json")
        
        if os.path.exists(schema_path):
            from jsonschema import validate
            with open(schema_path, "r", encoding="utf-8") as schema_f:
                schema = json.load(schema_f)
            validate(instance=data, schema=schema)
            
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
