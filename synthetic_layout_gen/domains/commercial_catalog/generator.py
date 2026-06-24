# domains/commercial_catalog/generator.py
import os
import random
import asyncio
import shutil
from jinja2 import Environment, FileSystemLoader

from synthetic_layout_gen.core.ground_truth_collector import GroundTruthCollector
from synthetic_layout_gen.core.playwright_capture import render_and_capture
from synthetic_layout_gen.core.faker_providers import seed_faker, fake

IMAGE_CATEGORY_MAP = {
    "light": "desk_lamp",
    "camera": "camera",
    "chair": "office_chair",
    "sofa": "office_chair",
    "desk": "laptop",
    "hub": "laptop",
    "dock": "laptop",
    "watch": "camera",
    "diver": "camera",
    "skeleton": "camera",
    "minimalist": "camera",
    "gmt": "camera",
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
                if data.get("category", "").lower() == category.lower() and data.get("path") and data.get("path") != "SKIPPED":
                    if os.path.exists(data["path"]):
                        paths.append(data["path"])
            except:
                pass
    if paths:
        selected = rng.choice(paths)
        return Path(selected).resolve().as_uri()
    return None

# Predefined categories and products for realistic fake catalogs
PRODUCT_DATA = {
    "Smart Home Tech": [
        {"name": "AeroGlow Ambient Light", "desc": "Smart lighting panel with voice control and adaptive color gradients.", "label": "A-GLOW"},
        {"name": "Vortex Smart Hub", "desc": "Central command center with touchscreen and integrated voice assistant.", "label": "V-HUB"},
        {"name": "SoundSphere Pro", "desc": "360-degree wireless speaker with spatial audio and acoustic tuning.", "label": "S-SPHERE"},
        {"name": "Nexa Thermostat", "desc": "Sleek temperature controller with AI-driven scheduling and energy tracking.", "label": "N-THERM"},
        {"name": "OmniCharge Dock", "desc": "Multi-device wireless charging station with magnetic alignment.", "label": "O-DOCK"},
        {"name": "Iris Smart Camera", "desc": "High-definition security camera with facial recognition and night vision.", "label": "I-CAM"}
    ],
    "Modern Furniture": [
        {"name": "Harkness Lounge Chair", "desc": "Ergonomic leather lounge chair with polished walnut wood frame.", "label": "H-CHAIR"},
        {"name": "Nouveau Sideboard", "desc": "Minimalist oak sideboard with matte black steel hardware and soft-close doors.", "label": "N-BOARD"},
        {"name": "Strata Coffee Table", "desc": "Sculptural concrete coffee table with dual-level storage shelves.", "label": "S-TABLE"},
        {"name": "Apex Desk", "desc": "Height-adjustable standing desk with solid bamboo top and cable routing.", "label": "A-DESK"},
        {"name": "Helix Bookshelf", "desc": "Modular steel bookshelf with asymmetric oak shelves.", "label": "H-SHELF"},
        {"name": "Stella Sofa", "desc": "Three-seater fabric sofa with high-density foam and tapered oak legs.", "label": "S-SOFA"}
    ],
    "Skincare & Wellness": [
        {"name": "Hydra-Luxe Serum", "desc": "Intense hydration serum with hyaluronic acid and peptide complex.", "label": "H-SERUM"},
        {"name": "Lumiere Facial Oil", "desc": "Nourishing facial oil with organic rosehip and squalane.", "label": "L-OIL"},
        {"name": "Elysian Clay Mask", "desc": "Purifying clay mask with activated charcoal and bentonite.", "label": "E-MASK"},
        {"name": "Aurora Eye Cream", "desc": "Brightening eye cream with vitamin C and caffeine extract.", "label": "A-CREAM"},
        {"name": "Sol-Shield SPF 50", "desc": "Broad-spectrum mineral sunscreen with lightweight matte finish.", "label": "S-SHIELD"},
        {"name": "Nectar Body Butter", "desc": "Rich moisturizing cream with shea butter and sweet almond oil.", "label": "N-BUTTER"}
    ],
    "Precision Timepieces": [
        {"name": "Chronos Classic", "desc": "Automatic chronograph watch with stainless steel case and leather strap.", "label": "C-CLASSIC"},
        {"name": "Vanguard Diver", "desc": "Water-resistant diving watch with rotating ceramic bezel.", "label": "V-DIVER"},
        {"name": "Aether Skeleton", "desc": "Mechanical skeleton watch showing internal gear movement.", "label": "A-SKEL"},
        {"name": "Solara Eco-Drive", "desc": "Solar-powered watch with titanium case and sapphire crystal.", "label": "S-ECO"},
        {"name": "Nomad GMT", "desc": "Dual-time zone watch with robust canvas strap and luminous dial.", "label": "N-GMT"},
        {"name": "Meridian Minimalist", "desc": "Ultra-thin dress watch with simple dial layout.", "label": "M-MINI"}
    ]
}

THEME_IDS = ["nordic_light", "cyberpunk_dark", "emerald_luxury"]

GRADIENT_PAIRS = [
    ("4F46E5", "06B6D4"),  # Indigo to Cyan
    ("F43F5E", "8B5CF6"),  # Rose to Violet
    ("10B981", "059669"),  # Emerald to Dark Green
    ("F59E0B", "D97706"),  # Amber to Dark Orange
    ("EC4899", "F43F5E"),  # Pink to Rose
    ("3B82F6", "1D4ED8"),  # Blue to Royal Blue
    ("8B5CF6", "EC4899")   # Violet to Pink
]

BRANDS = ["AERO", "KRONOS", "STRATA", "LUMI", "ELYSIAN", "NEXUS", "VERDANT", "APEX", "NOMAD"]

SPEC_KEYS = {
    "Smart Home Tech": [("Connectivity", "Wi-Fi, BLE"), ("Power", "12V DC / USB-C"), ("Compatibility", "HomeKit, Alexa"), ("Warranty", "2 Years")],
    "Modern Furniture": [("Material", "Oak Wood"), ("Dimensions", "85x90x105 cm"), ("Origin", "Made in Denmark"), ("Assembly", "Required")],
    "Skincare & Wellness": [("Volume", "50 ml"), ("Skin Type", "All Types"), ("Organic", "98.5% Certified"), ("Cruelty Free", "Yes")],
    "Precision Timepieces": [("Caliber", "Cal. 9015 Auto"), ("Water Resist", "100m (10 ATM)"), ("Glass", "Sapphire Crystal"), ("Case Size", "40 mm")]
}

async def generate_one_async(sample_id: int, seed: int, output_root: str = "output/"):
    random.seed(seed)
    seed_faker(seed)
    
    domain = "commercial_catalog"
    rng = random.Random(seed)
    doc_id = f"{domain}_{sample_id:05d}"
    
    theme_id = random.choice(THEME_IDS)
    brand_name = random.choice(BRANDS)
    category = random.choice(list(PRODUCT_DATA.keys()))
    
    # 3, 6, or 9 products to fit 1, 2, or 3 grid rows perfectly
    num_products = random.choice([3, 6, 9])
    
    # Select unique products from the chosen category or pool
    available_products = PRODUCT_DATA[category]
    selected_items = random.sample(available_products, k=min(num_products, len(available_products)))
    # If we need 9 but only have 6, allow selecting items from other categories to fill it up
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
        possible_specs = SPEC_KEYS.get(item_category, [("Info", "Premium Qualiy")])
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
            image_uri = get_image_for_category(img_cat, rng)
            
        products_payload.append({
            "name": item["name"],
            "description": item["desc"],
            "price": f"${random.randint(49, 1499)}.00",
            "category": item_category.split()[0].upper(),
            "start_color": g_start,
            "end_color": g_end,
            "product_label": item["label"],
            "specs": specs if random.random() > 0.15 else None, # 85% of items have a mini specs table
            "image_path": image_uri
        })
        
    # Render variables
    catalog_title = f"{brand_name} / {category.upper()}"
    catalog_subtitle = f"Curated selection of premium {category.lower()} for contemporary living."
    catalog_version = f"VOL. {random.randint(1, 10)} / 2026"
    
    # Sample layout skeleton
    from synthetic_layout_gen.core.layout_skeleton import sample_skeleton_for_domain
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

    # Setup Jinja
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "templates")
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
        
    # Finalize reading order (default sort by y0, then x0 works great for grid)
    collector.finalize_reading_order(page_number=1)
    
    # Write ground truth JSON file (automatically validates against schema)
    collector.write_json(json_path)

def generate_one(sample_id: int, seed: int, output_root: str = "output/"):
    # Run the async Playwright generator in synchronous entrypoint
    asyncio.run(generate_one_async(sample_id, seed, output_root))
