# domains/scientific_paper/generator.py
import os
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image as PILImage

from reportlab.lib.pagesizes import letter
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Spacer, TableStyle, PageBreak, NextPageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

from synthetic_layout_gen.core.ground_truth_collector import GroundTruthCollector, current_collector
from synthetic_layout_gen.core.bbox_tracking import TrackedParagraph, TrackedTable, TrackedImage, GTTrackingCanvas
from synthetic_layout_gen.core.coordinate_utils import pdf_to_images, reportlab_to_topleft
from synthetic_layout_gen.core.faker_providers import (
    seed_faker, fake_company_name, fake
)
from synthetic_layout_gen.core.fonts import get_text_width

# Color Themes: (Primary, Secondary, Accent)
THEMES = [
    ("#1E293B", "#334155", "#0F172A"),  # Slate Theme
    ("#1B365D", "#4A5568", "#111827"),  # Navy Theme
    ("#2D3748", "#4A5568", "#1A202C")   # Charcoal Theme
]

FONT_PAIRINGS = [
    {"body": "Times-Roman", "header": "Times-Bold"},
    {"body": "Helvetica", "header": "Helvetica-Bold"}
]

FORMULAS = [
    r"$E = m c^2$",
    r"$f(x) = \frac{1}{\sigma \sqrt{2\pi}} e^{-\frac{1}{2}\left(\frac{x-\mu}{\sigma}\right)^2}$",
    r"$\nabla \times \mathbf{E} = -\frac{\partial \mathbf{B}}{\partial t}$",
    r"$\sum_{i=1}^{n} i = \frac{n(n+1)}{2}$",
    r"$\int_{a}^{b} f(x) dx = F(b) - F(a)$",
    r"$a^2 + b^2 = c^2$",
    r"$\lim_{x \to 0} \frac{\sin x}{x} = 1$"
]

ABSTRACT_TEMPLATES = [
    "This paper presents a novel framework for the generation of synthetic document datasets with pixel-perfect ground-truth layouts. We address the critical issue of bounding box coordinate drift in traditional layout analysis. By intercepting layout information directly inside the rendering lifecycle, we eliminate approximation errors. Experimental evaluations demonstrate substantial improvements in downstream object detection training efficiency.",
    "Understanding structured layouts in academic and financial documents remains a persistent challenge in doc processing. In this study, we propose a programmatic generator targeting 5 domains. Unlike existing rule-based models, our architecture links split flowables across pages to preserve reading continuity. Initial benchmarks show that training with our synthetic dataset improves bounding box grounding accuracy by 14%."
]

BODY_PARAGRAPHS = [
    "Recent advancements in deep learning models have significantly advanced the state of the art in document understanding. However, training robust neural networks for layout detection requires extensive annotated datasets. Manual labelling of document bounding boxes is labor-intensive and prone to human errors. Synthetic data generators offer a viable alternative by providing unlimited samples with pre-determined coordinate data.",
    "Our approach relies on ReportLab's document rendering engine. We subclass foundational flowable elements to hook into their canvas draw routines. During the compilation of the PDF, the precise positioning coordinates are computed relative to the page height. This method captures the exact pixels where text, tables, and images are drawn, bypassing errors introduced by font substitution and line-wrap calculations.",
    "We describe the architecture of our generator across multiple domains. In the scientific paper domain, the dual-column layout presents a unique challenge for reading order reconstruction. Traditional top-to-bottom geometric sorting fails because it mixes left and right columns. We implement a column-aware sort key that buckets coordinates relative to the page midpoint before sorting vertically within each column.",
    "Furthermore, table splitting across pages requires special correlation. When a table overflows the available vertical space, the engine splits the flowable. We assign a unique identifier to the original parent block. The child fragments inherit this key, allowing downstream ingestion scripts to reassemble the split components. This structure is essential for training chunking algorithms in retrieval-augmented generation pipelines.",
    "In conclusion, our pipeline offers a complete framework for synthetic document engineering. The resulting dataset contains high-fidelity documents spanning commercial, financial, medical, and scientific domains. Future research will explore adding complex graphics, multi-page vector drawings, and advanced OCR noise models to further simulate physical scans while maintaining precise coordinate ground-truth."
]

def make_formula_image(formula_text, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig = plt.figure(figsize=(3, 0.4), dpi=300)
    # Use transparent background
    fig.text(0.5, 0.5, formula_text, fontsize=10, horizontalalignment='center', verticalalignment='center')
    plt.savefig(path, bbox_inches='tight', transparent=True, pad_inches=0.01)
    plt.close()
    
    # Measure image size to convert to points
    img = PILImage.open(path)
    w_px, h_px = img.size
    img.close()
    w_pt = w_px * 72.0 / 300.0
    h_pt = h_px * 72.0 / 300.0
    return w_pt, h_pt

def make_matplotlib_chart(path, theme_color):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(3, 1.8), dpi=150)
    x = [1, 2, 3, 4, 5]
    y = [random.uniform(0.1, 1.0) for _ in x]
    ax.plot(x, y, color=theme_color, marker='o', linewidth=1.5, markersize=3)
    ax.set_title("Experimental Accuracy", fontsize=7, color="#1E293B")
    ax.tick_params(axis='both', which='major', labelsize=5)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    plt.tight_layout()
    plt.savefig(path, bbox_inches='tight')
    plt.close()

def paper_reading_order_fn(elements):
    # Custom reading order for 2-column scientific paper
    # Page width is 612pt. Margins are 54pt. Column width is 243pt.
    # Left column: x0 < 306. Right column: x0 >= 306.
    # Zones:
    # 0 -> Full-width elements at the top (title, authors, abstract)
    # 1 -> Two-column body flowables
    # 2 -> Footer elements (page number)
    def get_sort_key(elem):
        bbox = elem["bbox"]
        x0, y0, x1, y1 = bbox
        etype = elem["type"]
        
        if etype == "page_footer":
            return (2, 0, y0, x0)
            
        # Check if it is a full-width header/abstract that spans across the columns
        # Midpoint of page is 306. If x0 < 297 and x1 > 315, it's full-width
        is_full_width = (x0 < 297 and x1 > 315) or etype == "title"
        if is_full_width:
            return (0, 0, y0, x0)
            
        # Column zone
        col_idx = 0 if x0 < 306 else 1
        return (1, col_idx, y0, x0)
        
    return sorted(elements, key=get_sort_key)

def generate_one(sample_id: int, seed: int, output_root: str = "output/"):
    random.seed(seed)
    seed_faker(seed)
    
    domain = "scientific_paper"
    doc_id = f"{domain}_{sample_id:05d}"
    
    from synthetic_layout_gen.core.layout_skeleton import sample_skeleton_for_domain
    rng = random.Random(seed)
    skeleton = sample_skeleton_for_domain("scientific_paper", rng)
    
    def paper_reading_order_fn(elements):
        page_mid = skeleton.page_width_pt / 2.0
        def get_sort_key(elem):
            bbox = elem["bbox"]
            x0, y0, x1, y1 = bbox
            etype = elem["type"]
            if etype == "page_footer":
                return (2, 0, y0, x0)
            is_full_width = (x1 - x0 > 0.75 * skeleton.page_width_pt) or etype == "title"
            if is_full_width:
                return (0, 0, y0, x0)
            if skeleton.n_columns == 2:
                col_idx = 0 if x0 < page_mid else 1
            else:
                col_idx = 0
            return (1, col_idx, y0, x0)
        return sorted(elements, key=get_sort_key)
        
    theme = random.choice(THEMES)
    font_pair = random.choice(FONT_PAIRINGS)
    
    # Paths
    pdf_path = os.path.join(output_root, domain, "pdfs", f"{doc_id}.pdf")
    json_path = os.path.join(output_root, domain, "json", f"{doc_id}.json")
    image_dir = os.path.join(output_root, domain, "images")
    
    temp_dir = os.path.join(output_root, "temp")
    chart_path = os.path.join(temp_dir, f"chart_{sample_id}.png")
    
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)
    
    make_matplotlib_chart(chart_path, theme[0])
    
    collector = GroundTruthCollector(doc_id, domain, "reportlab_platypus", seed)
    token = current_collector.set(collector)
    
    # Running page footer callback
    def draw_decorations(canvas_val, doc_val):
        canvas_val.saveState()
        canvas_val.setFont(font_pair["body"], 9)
        canvas_val.setFillColor(HexColor("#334155"))
        
        footer_text = f"{canvas_val._pageNumber}"
        y_footer = skeleton.margin_bottom + skeleton.footer_zone_height / 2.0
        canvas_val.drawCentredString(skeleton.page_width_pt / 2.0, y_footer, footer_text)
        canvas_val.restoreState()
        
        w_f = get_text_width(footer_text, font_pair["body"], 9)
        h_f = 9 * 0.75
        page_h = canvas_val._pagesize[1]
        bbox_f = reportlab_to_topleft(skeleton.page_width_pt / 2.0 - w_f/2.0, y_footer - h_f/2.0, w_f, h_f, page_h)
        collector.add_element(
            page_number=canvas_val._pageNumber,
            element_type="page_footer",
            bbox=bbox_f,
            text=footer_text
        )

    try:
        # Base Doc Template
        doc = BaseDocTemplate(pdf_path, pagesize=(skeleton.page_width_pt, skeleton.page_height_pt))
        
        # Cover Page Template (Full width frame for Title + Abstract)
        cover_frame = Frame(
            skeleton.margin_left,
            skeleton.margin_bottom + skeleton.footer_zone_height,
            skeleton.body_width,
            skeleton.body_height,
            id='cover_frame',
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
        )
        cover_template = PageTemplate(id='cover_page', frames=cover_frame, onPage=draw_decorations)
        
        # Body Page Template (1 or 2 column frames)
        if skeleton.n_columns == 2:
            left_x = skeleton.margin_left
            right_x = skeleton.margin_left + skeleton.column_width + skeleton.column_gap_pt
            left_frame = Frame(
                left_x,
                skeleton.margin_bottom + skeleton.footer_zone_height,
                skeleton.column_width,
                skeleton.body_height,
                id='left_frame',
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
            )
            right_frame = Frame(
                right_x,
                skeleton.margin_bottom + skeleton.footer_zone_height,
                skeleton.column_width,
                skeleton.body_height,
                id='right_frame',
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
            )
            body_frames = [left_frame, right_frame]
        else:
            single_frame = Frame(
                skeleton.margin_left,
                skeleton.margin_bottom + skeleton.footer_zone_height,
                skeleton.body_width,
                skeleton.body_height,
                id='single_frame',
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
            )
            body_frames = [single_frame]
            
        body_template = PageTemplate(id='body_page', frames=body_frames, onPage=draw_decorations)
        
        doc.addPageTemplates([cover_template, body_template])
        
        # Paragraph Styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'PaperTitle',
            parent=styles['Heading1'],
            fontName=font_pair["header"],
            fontSize=18,
            leading=22,
            textColor=HexColor(theme[0]),
            alignment=1,  # Center
            spaceAfter=10
        )
        
        author_style = ParagraphStyle(
            'PaperAuthor',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=10,
            leading=13,
            textColor=HexColor(theme[1]),
            alignment=1,  # Center
            spaceAfter=15
        )
        
        abstract_hdr_style = ParagraphStyle(
            'PaperAbsHdr',
            parent=styles['Heading2'],
            fontName=font_pair["header"],
            fontSize=10,
            leading=13,
            textColor=HexColor(theme[0]),
            alignment=1,  # Center
            spaceAfter=4
        )
        
        abstract_style = ParagraphStyle(
            'PaperAbs',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=8.5,
            leading=11,
            textColor=HexColor(theme[1]),
            leftIndent=36,
            rightIndent=36,
            alignment=4,  # Justified
            spaceAfter=20
        )
        
        h2_style = ParagraphStyle(
            'PaperH2',
            parent=styles['Heading2'],
            fontName=font_pair["header"],
            fontSize=11,
            leading=14,
            textColor=HexColor(theme[0]),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'PaperBody',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=9,
            leading=11.5,
            textColor=HexColor(theme[1]),
            alignment=4,  # Justified
            spaceAfter=6
        )
        
        caption_style = ParagraphStyle(
            'PaperCaption',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=7.5,
            leading=10,
            textColor=HexColor("#4A5568"),
            alignment=1,  # Center
            spaceBefore=4,
            spaceAfter=8
        )
        
        story = []
        
        # --- Page 1 (Cover Layout) ---
        # Title
        p_title = fake.sentence(nb_words=8).rstrip(".")
        story.append(TrackedParagraph(p_title, title_style, canonical_type="title"))
        
        # Authors
        authors = f"{fake.name()}* and {fake.name()}†\n*Department of Computer Science, {fake_company_name()}\n†Research Laboratory, {fake_company_name()}"
        story.append(TrackedParagraph(authors.replace("\n", "<br/>"), author_style, canonical_type="text"))
        
        # Abstract
        story.append(TrackedParagraph("Abstract", abstract_hdr_style, canonical_type="section_header"))
        abstract_text = random.choice(ABSTRACT_TEMPLATES)
        story.append(TrackedParagraph(abstract_text, abstract_style, canonical_type="text"))
        
        # Switch to Two-Column Layout for subsequent pages
        story.append(NextPageTemplate('body_page'))
        story.append(PageBreak())
        
        # --- Page 2+ (Two-Column Layout) ---
        sections = [
            ("1. Introduction", 2),
            ("2. Methodology", 2),
            ("3. Experimental Evaluation", 1)
        ]
        
        body_para_idx = 0
        formula_counter = 1
        
        for sec_title, num_paras in sections:
            story.append(TrackedParagraph(sec_title, h2_style, canonical_type="section_header"))
            for _ in range(num_paras):
                if body_para_idx < len(BODY_PARAGRAPHS):
                    story.append(TrackedParagraph(BODY_PARAGRAPHS[body_para_idx], body_style, canonical_type="text"))
                    body_para_idx += 1
                    
            # Add a formula in Methodology or introduction
            if "Methodology" in sec_title:
                story.append(TrackedParagraph("For our mathematical formulation, we define the following relationship:", body_style, canonical_type="text"))
                
                # Render formula to image
                f_latex = random.choice(FORMULAS)
                formula_img_path = os.path.join(temp_dir, f"formula_{sample_id}_{formula_counter}.png")
                w_pt, h_pt = make_formula_image(f_latex, formula_img_path)
                
                formula_f = TrackedImage(formula_img_path, width=w_pt, height=h_pt, canonical_type="formula")
                story.append(formula_f)
                story.append(Spacer(1, 4))
                formula_counter += 1
                
            # Add a figure in Experimental Evaluation
            if "Evaluation" in sec_title:
                # Add chart
                chart_f = TrackedImage(chart_path, width=220, height=132, canonical_type="picture")
                story.append(chart_f)
                
                # Add caption
                caption_text = f"Figure 1: Comparison of baseline models versus our layout detection generator."
                story.append(TrackedParagraph(caption_text, caption_style, canonical_type="caption"))
                
        # Build Document
        doc.build(story, canvasmaker=GTTrackingCanvas)
        
        # Prune pages
        import fitz
        pdf_doc = fitz.open(pdf_path)
        actual_pages = len(pdf_doc)
        collector.prune_extra_pages(actual_pages)
        pdf_doc.close()
        
        # Rasterize images
        pdf_to_images(pdf_path, image_dir, doc_id)
        
        # Finalize reading order (using our column-aware function!)
        for page in collector.pages:
            collector.finalize_reading_order(page["page_number"], order_fn=paper_reading_order_fn)
            
        # Write JSON
        collector.write_json(json_path)
        
    finally:
        current_collector.reset(token)
        # Clear ReportLab's image cache to release file handles on Windows
        from reportlab.lib.utils import ImageReader
        if hasattr(ImageReader, '_cache'):
            ImageReader._cache.clear()
        # Cleanup temp formula files
        for f_idx in range(1, formula_counter):
            f_path = os.path.join(temp_dir, f"formula_{sample_id}_{f_idx}.png")
            if os.path.exists(f_path):
                os.remove(f_path)
        if os.path.exists(chart_path):
            os.remove(chart_path)
        try:
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass
