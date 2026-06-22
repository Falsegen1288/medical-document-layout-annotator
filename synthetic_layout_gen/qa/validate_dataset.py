# qa/validate_dataset.py
import json
import os
import glob
from jsonschema import validate, ValidationError

def compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    
    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0
        
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def validate_document(doc_path: str, schema_path: str):
    with open(doc_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    # 1. Schema validation
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        print(f"Schema validation failed for {doc_path}")
        raise e
        
    # 2. Geometric and relationship checks
    all_element_ids = set()
    element_id_to_page = {}
    
    for page in data["pages"]:
        p_num = page["page_number"]
        for elem in page["layout_elements"]:
            e_id = elem["element_id"]
            if e_id in all_element_ids:
                raise ValueError(f"Duplicate element_id '{e_id}' in document {data['document_id']}")
            all_element_ids.add(e_id)
            element_id_to_page[e_id] = p_num

    for page in data["pages"]:
        p_num = page["page_number"]
        w_pt, h_pt = page["dimensions_pt"]
        elements = page["layout_elements"]
        
        # Check reading order
        reading_orders = [e["reading_order"] for e in elements]
        if reading_orders:
            n_elems = len(elements)
            sorted_orders = sorted(reading_orders)
            if sorted_orders != list(range(n_elems)):
                raise ValueError(f"Page {p_num} reading_orders are not a contiguous 0..{n_elems-1} permutation: {reading_orders}")
                
        # Check bboxes
        tables_on_page = []
        for elem in elements:
            e_id = elem["element_id"]
            bbox = elem["bbox"]
            x0, y0, x1, y1 = bbox
            
            # Boundary check
            if not (0 <= x0 < x1) or not (0 <= y0 < y1):
                raise ValueError(f"Invalid bbox dimensions in element {e_id}: {bbox}")
            if x1 > w_pt + 1.0 or y1 > h_pt + 1.0:
                print(f"[Warning] Element {e_id} bbox {bbox} exceeds page dimensions {[w_pt, h_pt]}")
                
            if elem["type"] == "table":
                tables_on_page.append((e_id, bbox))
                
            # Check is_continued_from reference
            cont_from = elem["attributes"].get("is_continued_from")
            if cont_from:
                if cont_from not in all_element_ids:
                    raise ValueError(f"element_id '{e_id}' continues from non-existent ID '{cont_from}'")
                cont_from_page = element_id_to_page[cont_from]
                if cont_from_page >= p_num:
                    raise ValueError(f"element_id '{e_id}' on page {p_num} continues from '{cont_from}' on page {cont_from_page} (not earlier)")
                    
        # Check table overlaps
        for i in range(len(tables_on_page)):
            for j in range(i + 1, len(tables_on_page)):
                idA, boxA = tables_on_page[i]
                idB, boxB = tables_on_page[j]
                iou = compute_iou(boxA, boxB)
                if iou > 0.90:
                    raise ValueError(f"Table elements '{idA}' and '{idB}' on page {p_num} overlap too much (IoU = {iou:.3f} > 0.90)")

    return True

def validate_domain(domain: str, output_root: str = "output/"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(current_dir, "..", "schema", "ground_truth.schema.json")
    
    json_dir = os.path.join(output_root, domain, "json")
    json_pattern = os.path.join(json_dir, "*.json")
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        print(f"No JSON files found to validate for domain {domain}")
        return
        
    print(f"Validating {len(json_files)} files in domain '{domain}'...")
    for f_path in json_files:
        validate_document(f_path, schema_path)
    print(f"Domain '{domain}' validation PASSED.")
