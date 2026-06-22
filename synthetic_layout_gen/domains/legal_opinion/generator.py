# domains/legal_opinion/generator.py
import os
import random
from reportlab.lib.pagesizes import letter
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Spacer, TableStyle, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

from synthetic_layout_gen.core.ground_truth_collector import GroundTruthCollector, current_collector
from synthetic_layout_gen.core.bbox_tracking import TrackedParagraph, TrackedTable, GTTrackingCanvas
from synthetic_layout_gen.core.coordinate_utils import pdf_to_images, reportlab_to_topleft
from synthetic_layout_gen.core.faker_providers import (
    seed_faker, fake_case_citation, fake, fake_company_name
)
from synthetic_layout_gen.core.fonts import get_text_width, compute_rotated_centered_text_bbox

FONT_PAIRINGS = [
    {"body": "Times-Roman", "header": "Times-Bold"},
    {"body": "Helvetica", "header": "Helvetica-Bold"}
]

# Fabricated legal sounding vocabulary
COURT_BOILERPLATE = [
    "IN THE COURT OF APPEALS FOR THE {circuit} CIRCUIT",
    "IN THE SUPREME COURT OF THE STATE OF {state}",
    "UNITED STATES DISTRICT COURT FOR THE {district} DISTRICT"
]

LEGAL_PROSE = [
    "This appeal arises from an order of the District Court granting summary judgment in favor of the appellee. The appellant contends that the court erred in finding no genuine dispute of material fact regarding the contractual ambiguity. Upon review of the record and the relevant precedents, we find the appellant's arguments persuasive.",
    "Under the doctrine of promissory estoppel, a party may be bound by a promise if they should have reasonably expected the other party to rely on it, and the other party did in fact rely to their detriment. Here, the evidence shows that the appellee made explicit representations concerning the partnership agreement.",
    "We review a grant of summary judgment de novo, applying the same standard as the district court. Summary judgment is appropriate only if the movant shows that there is no genuine dispute as to any material fact and the movant is entitled to judgment as a matter of law. We must view the facts in the light most favorable to the non-moving party.",
    "The contract at issue contains an integration clause, stating that the written document represents the final and complete agreement between the parties. While parol evidence is generally inadmissible to contradict the terms of an integrated contract, it may be admitted to resolve an ambiguity that is apparent on the face of the agreement.",
    "For the foregoing reasons, we conclude that the District Court erred in its application of state contract law. Genuine disputes of material fact remain concerning the intent of the parties. Accordingly, the judgment of the District Court is reversed, and the case is remanded for further proceedings consistent with this opinion."
]

def generate_one(sample_id: int, seed: int, output_root: str = "output/"):
    random.seed(seed)
    seed_faker(seed)
    
    domain = "legal_opinion"
    doc_id = f"{domain}_{sample_id:05d}"
    
    from synthetic_layout_gen.core.layout_skeleton import sample_skeleton_for_domain
    rng = random.Random(seed)
    skeleton = sample_skeleton_for_domain("legal_opinion", rng)
    
    font_pair = random.choice(FONT_PAIRINGS)
    
    # Paths
    pdf_path = os.path.join(output_root, domain, "pdfs", f"{doc_id}.pdf")
    json_path = os.path.join(output_root, domain, "json", f"{doc_id}.json")
    image_dir = os.path.join(output_root, domain, "images")
    
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)
    
    collector = GroundTruthCollector(doc_id, domain, "reportlab_platypus", seed)
    token = current_collector.set(collector)
    
    case_citation_num = fake_case_citation()
    
    # Custom draw watermark and gutter callback
    def draw_watermark_and_gutter(canvas_val, doc_val):
        page_h = canvas_val._pagesize[1]
        page_w = canvas_val._pagesize[0]
        
        # 1. Draw Watermark
        canvas_val.saveState()
        canvas_val.setFont("Helvetica-Bold", 60)
        canvas_val.setFillColor(HexColor("#F8FAFC")) # Very light slate gray
        canvas_val.translate(page_w / 2.0, page_h / 2.0)
        canvas_val.rotate(45)
        canvas_val.drawCentredString(0, 0, "DRAFT")
        canvas_val.restoreState()
        
        # Register watermark
        bbox_w = compute_rotated_centered_text_bbox("DRAFT", "Helvetica-Bold", 60, page_w / 2.0, page_h / 2.0, 45, page_h)
        collector.add_element(
            page_number=canvas_val._pageNumber,
            element_type="picture",
            bbox=bbox_w,
            text="DRAFT",
            attributes={"role": "watermark"}
        )
        
        # 2. Draw Gutter Line Numbers
        canvas_val.saveState()
        canvas_val.setFont("Helvetica", 9)
        canvas_val.setFillColor(HexColor("#94A3B8"))
        leading = 20.0
        start_y = skeleton.page_height_pt - skeleton.margin_top - skeleton.header_zone_height - 12
        line_x = skeleton.margin_left / 2.0
        n_lines = int(skeleton.body_height / leading)
        for idx in range(1, n_lines + 1):
            curr_y = start_y - (idx - 1) * leading
            canvas_val.drawRightString(line_x, curr_y, str(idx))
        canvas_val.restoreState()
        
        # 3. Draw Footer (Running citation and page number)
        canvas_val.saveState()
        canvas_val.setFont(font_pair["body"], 9)
        canvas_val.setFillColor(HexColor("#475569"))
        footer_text = f"{case_citation_num} | Page {canvas_val._pageNumber}"
        y_footer = skeleton.margin_bottom + skeleton.footer_zone_height / 2.0
        canvas_val.drawCentredString(page_w / 2.0, y_footer, footer_text)
        canvas_val.restoreState()
        
        w_f = get_text_width(footer_text, font_pair["body"], 9)
        h_f = 9 * 0.75
        bbox_f = reportlab_to_topleft(page_w / 2.0 - w_f/2.0, y_footer - h_f/2.0, w_f, h_f, page_h)
        collector.add_element(
            page_number=canvas_val._pageNumber,
            element_type="page_footer",
            bbox=bbox_f,
            text=footer_text
        )

    try:
        # Document template
        doc = BaseDocTemplate(pdf_path, pagesize=(skeleton.page_width_pt, skeleton.page_height_pt))
        body_frame = Frame(
            skeleton.margin_left,
            skeleton.margin_bottom + skeleton.footer_zone_height,
            skeleton.body_width,
            skeleton.body_height,
            id='body',
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
        )
        template = PageTemplate(id='legal_layout', frames=body_frame, onPage=draw_watermark_and_gutter)
        doc.addPageTemplates([template])
        
        styles = getSampleStyleSheet()
        
        # Styles
        court_style = ParagraphStyle(
            'LegalCourt',
            parent=styles['Heading2'],
            fontName=font_pair["header"],
            fontSize=12,
            leading=15,
            textColor=HexColor("#0F172A"),
            alignment=1, # Center
            spaceAfter=12
        )
        
        caption_style = ParagraphStyle(
            'LegalCaption',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=10,
            leading=14,
            textColor=HexColor("#1E293B"),
            spaceAfter=10
        )
        
        h2_style = ParagraphStyle(
            'LegalH2',
            parent=styles['Heading2'],
            fontName=font_pair["header"],
            fontSize=11,
            leading=14,
            textColor=HexColor("#0F172A"),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'LegalBody',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=10,
            leading=20, # Generous double-ish spacing
            textColor=HexColor("#1E293B"),
            alignment=4, # Justified
            spaceAfter=10
        )
        
        footnote_style = ParagraphStyle(
            'LegalFootnote',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=8,
            leading=11,
            textColor=HexColor("#334155"),
            spaceBefore=8,
            spaceAfter=4
        )
        
        story = []
        
        # 1. Court Name
        c_template = random.choice(COURT_BOILERPLATE)
        circuit_str = random.choice(["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH", "EIGHTH", "NINTH", "TENTH", "ELEVENTH"])
        state_str = fake.state().upper()
        district_str = random.choice(["EASTERN", "WESTERN", "NORTHERN", "SOUTHERN"])
        court_name = c_template.format(circuit=circuit_str, state=state_str, district=district_str)
        story.append(TrackedParagraph(court_name, court_style, canonical_type="title"))
        
        # 2. Case Caption Table
        party1 = fake.name().upper()
        party2 = fake.name().upper()
        caption_text = f"<b>{party1}</b>,<br/>&nbsp;&nbsp;&nbsp;&nbsp;<i>Appellant</i>,<br/><br/>v.<br/><br/><b>{party2}</b>,<br/>&nbsp;&nbsp;&nbsp;&nbsp;<i>Appellee</i>."
        
        docket_num = f"No. {random.randint(18, 26)}-{random.randint(1000, 9999)}"
        docket_text = f"<b>Docket {docket_num}</b><br/><br/>Decided: {fake.date()}<br/><br/>Opinion Filed."
        
        caption_data = [
            [
                TrackedParagraph(caption_text, caption_style, canonical_type="text"),
                TrackedParagraph(docket_text, caption_style, canonical_type="text")
            ]
        ]
        caption_table = TrackedTable(caption_data, colWidths=[234, 234], canonical_type="table")
        caption_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINEAFTER', (0,0), (0,0), 1, HexColor("#475569")), # vertical line between parties and docket info
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(caption_table)
        story.append(Spacer(1, 15))
        
        # 3. Opinion Header
        story.append(TrackedParagraph("OPINION OF THE COURT", h2_style, canonical_type="section_header"))
        
        # 4. Dense opinion flow
        opinion_paras = list(LEGAL_PROSE)
        # Randomly insert section headers
        for idx, para in enumerate(opinion_paras):
            if idx == 2:
                story.append(TrackedParagraph("I. BACKGROUND", h2_style, canonical_type="section_header"))
            elif idx == 4:
                story.append(TrackedParagraph("II. DISCUSSION", h2_style, canonical_type="section_header"))
                
            story.append(TrackedParagraph(para, body_style, canonical_type="text"))
            
        # 5. Optional Footnote at the end of the page
        has_footnote = random.random() < 0.25
        if has_footnote:
            story.append(Spacer(1, 10))
            # Draw line above footnote (structural table line)
            fn_line = Table([[""]], colWidths=[150])
            fn_line.setStyle(TableStyle([
                ('LINEABOVE', (0,0), (-1,-1), 0.5, HexColor("#64748B")),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(fn_line)
            
            fn_num = random.randint(1, 5)
            fn_text = f"<sup>{fn_num}</sup> Under state law, a promise is binding if the promisor makes a clear representation and the promisee relies upon it to their detriment. See, e.g., {fake.name()} v. {fake_company_name()}, {fake_case_citation()}."
            story.append(TrackedParagraph(fn_text, footnote_style, canonical_type="footnote"))
            
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
        
        # Finalize reading order
        for page in collector.pages:
            collector.finalize_reading_order(page["page_number"])
            
        # Write JSON
        collector.write_json(json_path)
        
    finally:
        current_collector.reset(token)
