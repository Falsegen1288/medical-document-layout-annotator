# domains/medical_catalog/generator.py
import os
import random
import asyncio
import shutil
from jinja2 import Environment, FileSystemLoader

from synthetic_layout_gen.core.ground_truth_collector import GroundTruthCollector
from synthetic_layout_gen.core.playwright_capture import render_and_capture
from synthetic_layout_gen.core.faker_providers import seed_faker, fake

# Predefined medical category dataset for surgical tools catalog
PRODUCT_DATA = {
    "Surgical Forceps": [
        {"name": "Adson Tissue Forceps", "desc": "Premium stainless steel surgical forceps with 1x2 teeth for secure tissue grip.", "label": "F-ADSON"},
        {"name": "DeBakey Atraumatic Forceps", "desc": "Atraumatic surgical forceps with fine ribbing for delicate vascular procedures.", "label": "F-DEBAKEY"},
        {"name": "Halsted Mosquito Forceps", "desc": "Curved hemostatic forceps for occlusion of small blood vessels.", "label": "F-MOSQ"},
        {"name": "Semken Dressing Forceps", "desc": "Straight forceps without teeth, ideal for dressing and delicate dissection.", "label": "F-SEMKEN"}
    ],
    "Surgical Retractors": [
        {"name": "Senn Handheld Retractor", "desc": "Double-ended retractor with three sharp prongs on one side and a solid blade on the other.", "label": "R-SENN"},
        {"name": "Weitlaner Self-Retaining Retractor", "desc": "Self-retaining retractor with 3x4 blunt prongs for deep abdominal exposure.", "label": "R-WEIT"},
        {"name": "Richardson Appendectomy Retractor", "desc": "Large loop handle retractor with single right-angled blade for laparotomy.", "label": "R-RICH"},
        {"name": "Army-Navy Retractor", "desc": "Double-ended handheld retractor used for exposing superficial wounds.", "label": "R-ARMY"}
    ],
    "Surgical Scalpels": [
        {"name": "Bard-Parker Handle No. 3", "desc": "Standard stainless steel surgical scalpel handle compatible with sizes 10-15 blades.", "label": "S-BARD3"},
        {"name": "Disposable Safety Scalpel No. 10", "desc": "Sterile disposable scalpel with retractable protective safety shield.", "label": "S-SAFE10"},
        {"name": "Scalpel Handle No. 4", "desc": "Heavy-duty surgical handle compatible with larger size 20-25 scalpel blades.", "label": "S-BARD4"}
    ],
    "Surgical Scissors": [
        {"name": "Mayo Dissecting Scissors (Straight)", "desc": "Heavy-duty straight scissors designed for cutting body tissues near the wound surface.", "label": "S-MAYO"},
        {"name": "Metzenbaum Curved Scissors", "desc": "Delicate curved dissecting scissors for exposing organs and deep structures.", "label": "S-METZ"},
        {"name": "Iris Suture Scissors", "desc": "Fine, straight scissors designed for ophthalmic and delicate suture cutting.", "label": "S-IRIS"}
    ]
}

THEME_IDS = ["nordic_light", "emerald_luxury"] # Medical prefers clean/emerald luxury themes

GRADIENT_PAIRS = [
    ("0EA5E9", "0284C7"),  # Sky Blue
    ("0D9488", "115E59"),  # Teal
    ("10B981", "064E3B"),  # Emerald
    ("6366F1", "4338CA"),  # Indigo
]

BRANDS = ["MED-TECH", "SURGI-ALLOY", "NEXUS-MED", "APEX-HEALTH", "PRO-CLINIC"]

SPEC_KEYS = {
    "Surgical Forceps": [("Material", "316L Stainless Steel"), ("Length", "12 cm"), ("Teeth", "1x2 Teeth"), ("Autoclavable", "Yes (134°C)")],
    "Surgical Retractors": [("Material", "Surgical Steel"), ("Blades", "Double-ended"), ("Prongs", "3 Sharp"), ("Origin", "Made in Germany")],
    "Surgical Scalpels": [("Material", "Stainless Steel"), ("Fitment", "Blades 10-15"), ("Autoclavable", "Yes"), ("ISO Standard", "ISO 7153-1")],
    "Surgical Scissors": [("Material", "Tungsten Carbide"), ("Length", "14 cm"), ("Blades", "Curved / Sharp"), ("Warranty", "Lifetime Warranty")]
}

IMAGE_CATEGORY_MAP = {
    "forceps": "forceps",
    "retractor": "retractor",
    "scalpel": "scalpel",
    "scissors": "scissors",
}

def get_image_for_category(category: str, rng: random.Random) -> str:
    manifest_path = "tools/image_pool/MANIFEST.jsonl"
    if not os.path.exists(manifest_path):
        return None
    import json
    from pathlib import Path
    paths = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                # Ensure we match forceps, retractor, scalpel, scissors
                if data.get("category", "").lower() == category.lower() and data.get("path") and data.get("path") != "SKIPPED":
                    if os.path.exists(data["path"]):
                        paths.append(data["path"])
            except:
                pass
    if paths:
        selected = rng.choice(paths)
        return Path(selected).resolve().as_uri()
    return None

async def generate_one_async(sample_id: int, seed: int, output_root: str = "output/"):
    random.seed(seed)
    seed_faker(seed)
    
    domain = "medical_catalog"
    doc_id = f"{domain}_{sample_id:05d}"
    
    theme_id = random.choice(THEME_IDS)
    brand_name = random.choice(BRANDS)
    category = random.choice(list(PRODUCT_DATA.keys()))
    
    # 3, 6, or 9 products to fit 1, 2, or 3 grid rows perfectly
    num_products = random.choice([3, 6, 9])
    
    # Select unique products from the chosen category or pool
    available_products = PRODUCT_DATA[category]
    selected_items = random.sample(available_products, k=min(num_products, len(available_products)))
    if len(selected_items) < num_products:
        all_other_items = []
        for cat, items in PRODUCT_DATA.items():
            if cat != category:
                all_other_items.extend(items)
        extra_items = random.sample(all_other_items, k=num_products - len(selected_items))
        selected_items.extend(extra_items)
        
    # Build products dict for Jinja
    products_payload = []
    for item in selected_items:
        g_start, g_end = random.choice(GRADIENT_PAIRS)
        # Determine specs
        specs = []
        item_category = next((cat for cat, items in PRODUCT_DATA.items() if item in items), category)
        possible_specs = SPEC_KEYS.get(item_category, [("Info", "Clinical Grade")])
        # Pick 2-3 random specs
        selected_specs = random.sample(possible_specs, k=random.randint(2, 3))
        for key, val in selected_specs:
            specs.append({"key": key, "value": val})
            
        # Map product name to image pool category
        img_cat = None
        for keyword, target_cat in IMAGE_CATEGORY_MAP.items():
            if keyword in item["name"].lower():
                img_cat = target_cat
                break
                
        image_uri = None
        if img_cat:
            image_uri = get_image_for_category(img_cat, rng=random.Random(seed))
            
        products_payload.append({
            "name": item["name"],
            "description": item["desc"],
            "price": f"${random.randint(29, 399)}.00",
            "category": item_category.split()[1].upper() if len(item_category.split()) > 1 else "SURGICAL",
            "start_color": g_start,
            "end_color": g_end,
            "product_label": item["label"],
            "specs": specs if random.random() > 0.15 else None,
            "image_path": image_uri
        })
        
    # Render variables
    catalog_title = f"{brand_name} / {category.upper()}"
    catalog_subtitle = f"Clinical-grade surgical instruments and medical equipment manufactured to ISO 13485 standards."
    catalog_version = f"REF {random.randint(100, 999)} / CAT-2026"
    
    # Sample layout skeleton (uses commercial_catalog skeleton distributions as proxy)
    from synthetic_layout_gen.core.layout_skeleton import sample_skeleton_for_domain
    rng = random.Random(seed)
    skeleton = sample_skeleton_for_domain("commercial_catalog", rng)
    
    scale_pt_to_px = 150.0 / 72.0
    margin_left_px = skeleton.margin_left * scale_pt_to_px
    margin_right_px = skeleton.margin_right * scale_pt_to_px
    margin_top_px = skeleton.margin_top * scale_pt_to_px
    margin_bottom_px = skeleton.margin_bottom * scale_pt_to_px
    header_height_px = skeleton.header_zone_height * scale_pt_to_px
    footer_height_px = skeleton.footer_zone_height * scale_pt_to_px
    
    padding_top_px = margin_top_px + header_height_px
    padding_left_px = margin_left_px
    padding_right_px = margin_right_px
    padding_bottom_px = margin_bottom_px + footer_height_px
    
    # Setup Jinja (medical_catalog shares template with commercial_catalog)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(os.path.dirname(current_dir), "commercial_catalog", "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("catalog_base.html.jinja")
    
    html_content = template.render(
        theme_id=theme_id,
        brand_name=brand_name,
        catalog_title=catalog_title,
        catalog_subtitle=catalog_subtitle,
        catalog_version=catalog_version,
        products=products_payload,
        page_num=1,
        margin_top_px=margin_top_px,
        margin_bottom_px=margin_bottom_px,
        padding_top_px=padding_top_px,
        padding_left_px=padding_left_px,
        padding_right_px=padding_right_px,
        padding_bottom_px=padding_bottom_px
    )
    
    # Write temp html to workspace temp dir
    temp_dir = os.path.join(output_root, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_html_path = os.path.join(temp_dir, f"{doc_id}_temp.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # Target file paths
    pdf_path = os.path.abspath(os.path.join(output_root, domain, "pdfs", f"{doc_id}.pdf"))
    image_path = os.path.abspath(os.path.join(output_root, domain, "images", f"{doc_id}_p1.png"))
    json_path = os.path.abspath(os.path.join(output_root, domain, "json", f"{doc_id}.json"))
    
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    
    # Viewport size for US Letter at 150 DPI is 1275 x 1650 px
    viewport_px = (1275, 1650)
    
    # Run playwright capture
    processed_elements, (w_pt, h_pt) = await render_and_capture(
        html_path_or_string=temp_html_path,
        output_image_path=image_path,
        output_pdf_path=pdf_path,
        viewport_px=viewport_px,
        dpi=150
    )
    
    # Remove temporary HTML file
    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)
        
    # Compile Ground Truth JSON
    image_rel_path = f"output/{domain}/images/{doc_id}_p1.png"
    collector = GroundTruthCollector(doc_id, domain, "playwright_html", seed)
    
    # Record the single page
    collector.new_page(
        page_number=1,
        dimensions_pt=(w_pt, h_pt),
        dimensions_px=viewport_px,
        image_path=image_rel_path
    )
    
    # Add each captured element to the collector
    for elem in processed_elements:
        collector.add_element(
            page_number=1,
            element_type=elem["type"],
            bbox=elem["bbox"],
            text=elem["text"],
            attributes=elem["attributes"]
        )
        
    # Finalize reading order
    collector.finalize_reading_order(page_number=1)
    
    # Write ground truth JSON file (automatically validates against schema)
    collector.write_json(json_path)

def generate_one(sample_id: int, seed: int, output_root: str = "output/"):
    # Run the async Playwright generator in synchronous entrypoint
    asyncio.run(generate_one_async(sample_id, seed, output_root))
