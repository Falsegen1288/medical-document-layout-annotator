# domains/financial_invoice/generator.py
import os
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image as PILImage

from reportlab.lib.pagesizes import letter
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Spacer, TableStyle, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

from synthetic_layout_gen.core.ground_truth_collector import GroundTruthCollector, current_collector
from synthetic_layout_gen.core.bbox_tracking import TrackedParagraph, TrackedTable, TrackedImage, GTTrackingCanvas
from synthetic_layout_gen.core.coordinate_utils import pdf_to_images, reportlab_to_topleft
from synthetic_layout_gen.core.faker_providers import (
    seed_faker, fake_company_name, fake_invoice_number,
    fake_currency_amount, fake_product_sku, fake
)
from synthetic_layout_gen.core.fonts import get_text_width

# Color Themes: (Primary, Secondary, HeaderBackground)
THEMES = [
    ("#1A365D", "#4A5568", "#EDF2F7"),  # Navy / Slate / Light Grey
    ("#065F46", "#374151", "#ECFDF5"),  # Emerald / Charcoal / Light Emerald
    ("#741B47", "#5B5B5B", "#F3E8EE")   # Burgundy / Warm Grey / Light Burgundy
]

FONT_PAIRINGS = [
    {"body": "Helvetica", "header": "Helvetica-Bold"},
    {"body": "Times-Roman", "header": "Helvetica-Bold"}
]

def make_placeholder_logo(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = PILImage.new("RGB", (60, 60), color="#CBD5E0")
    img.save(path)

def make_matplotlib_chart(path, theme_color):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(4, 2), dpi=150)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    spend = [random.randint(1000, 5000) for _ in range(6)]
    ax.bar(months, spend, color=theme_color, width=0.5)
    ax.set_title("Monthly Spend Analysis", fontsize=8, color="#2D3748")
    ax.tick_params(axis='both', which='major', labelsize=6)
    # Simplify chart look
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    plt.tight_layout()
    plt.savefig(path, bbox_inches='tight')
    plt.close()

def generate_one(sample_id: int, seed: int, output_root: str = "output/"):
    random.seed(seed)
    seed_faker(seed)
    
    domain = "financial_invoice"
    doc_id = f"{domain}_{sample_id:05d}"
    
    from synthetic_layout_gen.core.layout_skeleton import sample_skeleton_for_domain
    rng = random.Random(seed)
    skeleton = sample_skeleton_for_domain("financial_invoice", rng)
    
    # 1. Choose Theme & Font Pairing
    theme = random.choice(THEMES)
    font_pair = random.choice(FONT_PAIRINGS)
    
    # Paths
    pdf_path = os.path.join(output_root, domain, "pdfs", f"{doc_id}.pdf")
    json_path = os.path.join(output_root, domain, "json", f"{doc_id}.json")
    image_dir = os.path.join(output_root, domain, "images")
    
    temp_dir = os.path.join(output_root, "temp")
    logo_path = os.path.join(temp_dir, f"logo_{sample_id}.png")
    chart_path = os.path.join(temp_dir, f"chart_{sample_id}.png")
    
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)
    
    make_placeholder_logo(logo_path)
    has_chart = random.random() < 0.3
    if has_chart:
        make_matplotlib_chart(chart_path, theme[0])
        
    # Setup Ground Truth Collector
    collector = GroundTruthCollector(doc_id, domain, "reportlab_platypus", seed)
    token = current_collector.set(collector)
    
    # Store invoice number on doc so canvas callback can read it
    invoice_num = fake_invoice_number()
    
    # Draw running header and footer callback
    def draw_decorations(canvas_val, doc_val):
        canvas_val.saveState()
        canvas_val.setFont(font_pair["body"], 9)
        canvas_val.setFillColor(HexColor("#4A5568"))
        
        # Draw running footer
        footer_text = f"Payment Terms: Net 30. Remit payments to the address above. | Page {canvas_val._pageNumber}"
        y_footer = skeleton.margin_bottom + skeleton.footer_zone_height / 2.0
        canvas_val.drawCentredString(skeleton.page_width_pt / 2.0, y_footer, footer_text)
        canvas_val.restoreState()
        
        # Record footer element
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
        
        # Draw running header on page 2+
        if canvas_val._pageNumber > 1:
            canvas_val.saveState()
            canvas_val.setFont(font_pair["body"], 9)
            canvas_val.setFillColor(HexColor("#4A5568"))
            header_text = f"Invoice {invoice_num} - Continued"
            y_header = skeleton.page_height_pt - skeleton.margin_top - skeleton.header_zone_height / 2.0
            canvas_val.drawString(skeleton.margin_left, y_header, header_text)
            canvas_val.restoreState()
            
            w_h = get_text_width(header_text, font_pair["body"], 9)
            h_h = 9 * 0.75
            bbox_h = reportlab_to_topleft(skeleton.margin_left, y_header - h_h/2.0, w_h, h_h, page_h)
            collector.add_element(
                page_number=canvas_val._pageNumber,
                element_type="page_header",
                bbox=bbox_h,
                text=header_text
            )

    try:
        # Document layout
        doc = BaseDocTemplate(pdf_path, pagesize=(skeleton.page_width_pt, skeleton.page_height_pt))
        doc.invoice_number = invoice_num
        
        # Frame
        body_frame = Frame(
            skeleton.margin_left,
            skeleton.margin_bottom + skeleton.footer_zone_height,
            skeleton.body_width,
            skeleton.body_height,
            id='body',
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
        )
        template = PageTemplate(id='invoice_layout', frames=body_frame, onPage=draw_decorations)
        doc.addPageTemplates([template])
        
        # Paragraph Styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'InvTitle',
            parent=styles['Heading1'],
            fontName=font_pair["header"],
            fontSize=22,
            leading=26,
            textColor=HexColor(theme[0]),
            spaceAfter=6
        )
        
        h2_style = ParagraphStyle(
            'InvH2',
            parent=styles['Heading2'],
            fontName=font_pair["header"],
            fontSize=11,
            leading=14,
            textColor=HexColor(theme[0]),
            spaceAfter=4
        )
        
        body_style = ParagraphStyle(
            'InvBody',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=9,
            leading=12,
            textColor=HexColor(theme[1])
        )
        
        bold_body_style = ParagraphStyle(
            'InvBoldBody',
            parent=body_style,
            fontName=font_pair["header"]
        )
        
        table_hdr_style = ParagraphStyle(
            'InvTableHdr',
            parent=styles['Normal'],
            fontName=font_pair["header"],
            fontSize=9,
            leading=11,
            textColor=HexColor(theme[0])
        )
        
        story = []
        
        # 1. Company Block (Masthead)
        logo_f = TrackedImage(logo_path, width=50, height=50, canonical_type="picture")
        comp_name = fake_company_name()
        comp_addr = f"{fake.street_address()}\n{fake.city()}, {fake.state_abbr()} {fake.zipcode()}"
        
        comp_details = [
            TrackedParagraph(comp_name, title_style, canonical_type="title"),
            TrackedParagraph(comp_addr.replace("\n", "<br/>"), body_style, canonical_type="text")
        ]
        
        # Structural layout table (no bbox emitted for layout table itself)
        comp_table = Table([[logo_f, comp_details]], colWidths=[60, 444])
        comp_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 15))
        
        # 1b. Invoice details row (Invoice #, Date, Due Date)
        inv_meta_data = [
            [
                TrackedParagraph("INVOICE", h2_style, canonical_type="text"),
                TrackedParagraph(f"<b>Invoice #:</b> {invoice_num}", body_style, canonical_type="text"),
                TrackedParagraph(f"<b>Date:</b> {fake.date()}", body_style, canonical_type="text"),
                TrackedParagraph(f"<b>Due Date:</b> {fake.date()}", body_style, canonical_type="text")
            ]
        ]
        inv_meta_table = TrackedTable(inv_meta_data, colWidths=[126, 126, 126, 126], canonical_type="table")
        inv_meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(inv_meta_table)
        story.append(Spacer(1, 15))
        
        # 2. Bill-to / Ship-to (Side-by-side Table)
        bill_to_paragraphs = [
            TrackedParagraph("<b>Bill To:</b>", bold_body_style, canonical_type="text"),
            TrackedParagraph(fake.name(), body_style, canonical_type="text"),
            TrackedParagraph(fake.street_address(), body_style, canonical_type="text"),
            TrackedParagraph(f"{fake.city()}, {fake.state_abbr()} {fake.zipcode()}", body_style, canonical_type="text")
        ]
        ship_to_paragraphs = [
            TrackedParagraph("<b>Ship To:</b>", bold_body_style, canonical_type="text"),
            TrackedParagraph(fake.name(), body_style, canonical_type="text"),
            TrackedParagraph(fake.street_address(), body_style, canonical_type="text"),
            TrackedParagraph(f"{fake.city()}, {fake.state_abbr()} {fake.zipcode()}", body_style, canonical_type="text")
        ]
        
        address_layout_table = Table([[bill_to_paragraphs, ship_to_paragraphs]], colWidths=[252, 252])
        address_layout_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(address_layout_table)
        story.append(Spacer(1, 20))
        
        # 3. Line Items Table
        line_items_data = [
            [
                TrackedParagraph("Description", table_hdr_style, canonical_type="text"),
                TrackedParagraph("SKU", table_hdr_style, canonical_type="text"),
                TrackedParagraph("Qty", table_hdr_style, canonical_type="text"),
                TrackedParagraph("Price", table_hdr_style, canonical_type="text"),
                TrackedParagraph("Total", table_hdr_style, canonical_type="text")
            ]
        ]
        
        # Random row count to exercise splits (8 to 25)
        num_rows = random.randint(8, 25)
        subtotal = 0.0
        for r in range(num_rows):
            desc = fake.catch_phrase()
            sku = fake_product_sku()
            qty = random.randint(1, 10)
            price = random.uniform(5.0, 300.0)
            total = qty * price
            subtotal += total
            
            line_items_data.append([
                TrackedParagraph(desc, body_style, canonical_type="text"),
                TrackedParagraph(sku, body_style, canonical_type="text"),
                TrackedParagraph(str(qty), body_style, canonical_type="text"),
                TrackedParagraph(f"${price:.2f}", body_style, canonical_type="text"),
                TrackedParagraph(f"${total:.2f}", body_style, canonical_type="text")
            ])
            
        line_table = TrackedTable(line_items_data, colWidths=[200, 80, 40, 90, 94], canonical_type="table")
        line_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), HexColor(theme[2])),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,0), 1, HexColor(theme[0])),
            ('LINEBELOW', (0,1), (-1,-1), 0.5, HexColor("#CBD5E0")),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 15))
        
        # 4. Optional Matplotlib spend chart
        if has_chart:
            chart_f = TrackedImage(chart_path, width=200, height=100, canonical_type="picture")
            story.append(chart_f)
            story.append(Spacer(1, 15))
            
        # 5. Totals block (right-aligned table)
        tax = subtotal * 0.0825
        grand_total = subtotal + tax
        
        totals_data = [
            [TrackedParagraph("Subtotal:", bold_body_style, canonical_type="text"), TrackedParagraph(f"${subtotal:,.2f}", body_style, canonical_type="text")],
            [TrackedParagraph("Tax (8.25%):", bold_body_style, canonical_type="text"), TrackedParagraph(f"${tax:,.2f}", body_style, canonical_type="text")],
            [TrackedParagraph("Grand Total:", bold_body_style, canonical_type="text"), TrackedParagraph(f"${grand_total:,.2f}", bold_body_style, canonical_type="text")]
        ]
        totals_table = TrackedTable(totals_data, colWidths=[120, 100], canonical_type="table")
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('LINEABOVE', (0,2), (-1,2), 1, HexColor(theme[0]))
        ]))
        
        # Align totals table to the right using outer layout Table
        totals_layout = Table([["", totals_table]], colWidths=[284, 220])
        totals_layout.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(totals_layout)
        
        # Build PDF
        doc.build(story, canvasmaker=GTTrackingCanvas)
        
        # Prune pages according to actual PDF size
        import fitz
        pdf_doc = fitz.open(pdf_path)
        actual_pages = len(pdf_doc)
        collector.prune_extra_pages(actual_pages)
        pdf_doc.close()
        
        # Rasterize PDF pages to PNGs
        pdf_to_images(pdf_path, image_dir, doc_id)
        
        # Finalize reading order
        for page in collector.pages:
            collector.finalize_reading_order(page["page_number"])
            
        # Write JSON
        collector.write_json(json_path)
        
    finally:
        current_collector.reset(token)
        # Clear ReportLab's image cache to release file handles on Windows
        from reportlab.lib.utils import ImageReader
        if hasattr(ImageReader, '_cache'):
            ImageReader._cache.clear()
        # Cleanup temp files
        if os.path.exists(logo_path):
            os.remove(logo_path)
        if os.path.exists(chart_path):
            os.remove(chart_path)
        # Empty temp directory if it's empty
        try:
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass
