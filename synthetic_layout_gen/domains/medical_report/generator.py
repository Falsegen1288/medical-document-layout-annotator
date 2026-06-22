# domains/medical_report/generator.py
import os
import random
from reportlab.lib.pagesizes import letter
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Spacer, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus.flowables import KeepTogether
from reportlab.platypus import ListItem

from synthetic_layout_gen.core.ground_truth_collector import GroundTruthCollector, current_collector
from synthetic_layout_gen.core.bbox_tracking import TrackedParagraph, TrackedTable, TrackedListFlowable, GTTrackingCanvas
from synthetic_layout_gen.core.coordinate_utils import pdf_to_images, reportlab_to_topleft, degrade_to_scanlike
from synthetic_layout_gen.core.faker_providers import (
    seed_faker, fake_patient_id, fake_diagnosis_code, fake
)
from synthetic_layout_gen.core.fonts import get_text_width

THEMES = [
    ("#1E3A8A", "#374151", "#DBEAFE"),  # Dark Blue / Gray / Light Blue
    ("#064E3B", "#374151", "#D1FAE5"),  # Dark Green / Gray / Light Green
    ("#0F172A", "#334155", "#F1F5F9")   # Slate / Slate-Gray / Light Slate
]

FONT_PAIRINGS = [
    {"body": "Helvetica", "header": "Helvetica-Bold"},
    {"body": "Times-Roman", "header": "Helvetica-Bold"}
]

# Fabricated clinical note templates for medical reports
CLINICAL_TEMPLATES = [
    "Patient presented with complaints of mild chest discomfort and dyspnea on exertion. EKG showed normal sinus rhythm with no acute ST-T wave changes. Laboratory evaluation revealed standard troponin levels within normal parameters.",
    "The patient was admitted for observation following a minor syncopal episode at home. Physical examination was unremarkable except for mild orthostatic blood pressure changes. Neurological checks remained entirely normal throughout the stay.",
    "Clinical review indicates stable progression post-intervention. Vital signs remain within physiological limits. The patient reports improved tolerance to ambulation with minimal shortness of breath. Plan is to transition to home-based physical therapy.",
    "Patient report outlines transient joint stiffness and localized swelling in the lower extremities. Diagnostic findings show no evidence of deep vein thrombosis. Symptoms are consistent with mild osteoarthritis, managed conservatively.",
    "Follow-up examination reveals normal pulmonary auscultation. The patient reports adherence to prescribed inhaler therapies with good symptomatic control. Advised to continue current outpatient management plan."
]

MEDICATIONS = [
    "Lisinopril 10mg daily for blood pressure control.",
    "Atorvastatin 20mg daily at bedtime for cholesterol.",
    "Metformin 500mg twice daily with meals for glucose management.",
    "Aspirin 81mg daily for cardiovascular prophylaxis.",
    "Amlodipine 5mg daily for hypertension control.",
    "Gabapentin 300mg three times daily for neuropathic pain.",
    "Levothyroxine 75mcg daily in the morning for thyroid replacement.",
    "Omeprazole 20mg daily before breakfast for acid reflux."
]

DISCHARGE_INSTRUCTIONS = [
    "Follow up with your primary care physician within 7-10 days of discharge.",
    "Do not perform heavy lifting (greater than 10 lbs) for the next 2 weeks.",
    "Monitor blood pressure daily and record measurements in a log.",
    "Seek immediate medical attention if you experience chest pain, shortness of breath, or severe dizziness.",
    "Resume normal physical activity gradually as tolerated.",
    "Continue taking all prescribed discharge medications as directed.",
    "Maintain a low-sodium, heart-healthy diet as discussed."
]

def generate_one(sample_id: int, seed: int, output_root: str = "output/"):
    random.seed(seed)
    seed_faker(seed)
    
    domain = "medical_report"
    doc_id = f"{domain}_{sample_id:05d}"
    
    from synthetic_layout_gen.core.layout_skeleton import sample_skeleton_for_domain
    rng = random.Random(seed)
    skeleton = sample_skeleton_for_domain("medical_report", rng)
    
    theme = random.choice(THEMES)
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
    
    # Draw confidentiality footer
    def draw_decorations(canvas_val, doc_val):
        canvas_val.saveState()
        canvas_val.setFont(font_pair["body"], 8)
        canvas_val.setFillColor(HexColor("#64748B"))
        
        footer_text = f"CONFIDENTIAL MEDICAL RECORD - FOR PROFESSIONAL USE ONLY | Page {canvas_val._pageNumber}"
        y_footer = skeleton.margin_bottom + skeleton.footer_zone_height / 2.0
        canvas_val.drawCentredString(skeleton.page_width_pt / 2.0, y_footer, footer_text)
        canvas_val.restoreState()
        
        w_f = get_text_width(footer_text, font_pair["body"], 8)
        h_f = 8 * 0.75
        page_h = canvas_val._pagesize[1]
        bbox_f = reportlab_to_topleft(skeleton.page_width_pt / 2.0 - w_f/2.0, y_footer - h_f/2.0, w_f, h_f, page_h)
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
        template = PageTemplate(id='medical_layout', frames=body_frame, onPage=draw_decorations)
        doc.addPageTemplates([template])
        
        styles = getSampleStyleSheet()
        
        # Styles
        title_style = ParagraphStyle(
            'MedTitle',
            parent=styles['Heading1'],
            fontName=font_pair["header"],
            fontSize=20,
            leading=24,
            textColor=HexColor(theme[0]),
            spaceAfter=15
        )
        
        h2_style = ParagraphStyle(
            'MedH2',
            parent=styles['Heading2'],
            fontName=font_pair["header"],
            fontSize=12,
            leading=15,
            textColor=HexColor(theme[0]),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'MedBody',
            parent=styles['Normal'],
            fontName=font_pair["body"],
            fontSize=9,
            leading=13,
            textColor=HexColor(theme[1]),
            spaceAfter=6
        )
        
        table_hdr_style = ParagraphStyle(
            'MedTableHdr',
            parent=styles['Normal'],
            fontName=font_pair["header"],
            fontSize=9,
            leading=11,
            textColor=HexColor(theme[0])
        )
        
        story = []
        
        # 1. Main Document Title
        report_type = random.choice(["PATIENT INTAKE REPORT", "DISCHARGE SUMMARY REPORT", "CLINICAL EVALUATION REPORT"])
        story.append(TrackedParagraph(report_type, title_style, canonical_type="title"))
        
        # 2. Patient Information Section
        story.append(TrackedParagraph("Patient Information", h2_style, canonical_type="section_header"))
        
        p_name = fake.name()
        p_dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y-%m-%d")
        p_mrn = fake_patient_id()
        p_date = fake.date()
        
        patient_info_data = [
            [
                TrackedParagraph("<b>Patient Name:</b>", body_style, canonical_type="text"),
                TrackedParagraph(p_name, body_style, canonical_type="text"),
                TrackedParagraph("<b>Date of Birth:</b>", body_style, canonical_type="text"),
                TrackedParagraph(p_dob, body_style, canonical_type="text")
            ],
            [
                TrackedParagraph("<b>MRN / Patient ID:</b>", body_style, canonical_type="text"),
                TrackedParagraph(p_mrn, body_style, canonical_type="text"),
                TrackedParagraph("<b>Report Date:</b>", body_style, canonical_type="text"),
                TrackedParagraph(p_date, body_style, canonical_type="text")
            ]
        ]
        col_w_patient = [
            skeleton.body_width * 120.0 / 504.0,
            skeleton.body_width * 132.0 / 504.0,
            skeleton.body_width * 120.0 / 504.0,
            skeleton.body_width * 132.0 / 504.0
        ]
        patient_table = TrackedTable(patient_info_data, colWidths=col_w_patient, canonical_type="table")
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), HexColor(theme[2])),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, HexColor("#CBD5E0")),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 10))
        
        # 3. Vital Signs Section
        story.append(TrackedParagraph("Vital Signs Log", h2_style, canonical_type="section_header"))
        
        vitals_headers = [
            TrackedParagraph("Time", table_hdr_style, canonical_type="text"),
            TrackedParagraph("Blood Pressure", table_hdr_style, canonical_type="text"),
            TrackedParagraph("Heart Rate (bpm)", table_hdr_style, canonical_type="text"),
            TrackedParagraph("Temp (°F)", table_hdr_style, canonical_type="text"),
            TrackedParagraph("SpO2 (%)", table_hdr_style, canonical_type="text"),
            TrackedParagraph("Weight (lbs)", table_hdr_style, canonical_type="text")
        ]
        vitals_data = [vitals_headers]
        
        weight = random.randint(110, 240)
        times = ["08:00", "12:00", "16:00", "20:00"]
        for t in times:
            bp = f"{random.randint(110, 135)}/{random.randint(70, 88)}"
            hr = str(random.randint(60, 95))
            temp = f"{random.uniform(97.8, 99.2):.1f}"
            spo2 = str(random.randint(95, 100))
            
            vitals_data.append([
                TrackedParagraph(t, body_style, canonical_type="text"),
                TrackedParagraph(bp, body_style, canonical_type="text"),
                TrackedParagraph(hr, body_style, canonical_type="text"),
                TrackedParagraph(temp, body_style, canonical_type="text"),
                TrackedParagraph(spo2, body_style, canonical_type="text"),
                TrackedParagraph(str(weight), body_style, canonical_type="text")
            ])
            
        col_w_vitals = [
            skeleton.body_width * 80.0 / 504.0,
            skeleton.body_width * 100.0 / 504.0,
            skeleton.body_width * 90.0 / 504.0,
            skeleton.body_width * 70.0 / 504.0,
            skeleton.body_width * 70.0 / 504.0,
            skeleton.body_width * 94.0 / 504.0
        ]
        vitals_table = TrackedTable(vitals_data, colWidths=col_w_vitals, canonical_type="table")
        vitals_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), HexColor(theme[2])),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,0), 1, HexColor(theme[0])),
            ('LINEBELOW', (0,1), (-1,-1), 0.5, HexColor("#E2E8F0")),
        ]))
        story.append(vitals_table)
        story.append(Spacer(1, 10))
        
        # 4. Clinical Diagnosis & Notes Section
        story.append(TrackedParagraph("Clinical Notes & Assessment", h2_style, canonical_type="section_header"))
        
        diag_code = fake_diagnosis_code()
        story.append(TrackedParagraph(f"<b>Primary Diagnosis Code:</b> ICD-10 {diag_code}", body_style, canonical_type="text"))
        
        # Generate random clinical notes
        notes_paragraphs = random.sample(CLINICAL_TEMPLATES, k=random.randint(2, 4))
        for note in notes_paragraphs:
            story.append(TrackedParagraph(note, body_style, canonical_type="text"))
            
        story.append(Spacer(1, 10))
        
        # 5. Medications List (TrackedListFlowable)
        story.append(TrackedParagraph("Discharge Medications", h2_style, canonical_type="section_header"))
        
        med_list = random.sample(MEDICATIONS, k=random.randint(2, 4))
        med_items = [ListItem(TrackedParagraph(med, body_style, canonical_type="text"), leftIndent=12, bulletColor=HexColor(theme[0])) for med in med_list]
        med_flowable = TrackedListFlowable(med_items, bulletType='bullet', canonical_type="list_item")
        story.append(med_flowable)
        story.append(Spacer(1, 10))
        
        # 6. Discharge Instructions (TrackedListFlowable)
        story.append(TrackedParagraph("Discharge Instructions", h2_style, canonical_type="section_header"))
        
        inst_list = random.sample(DISCHARGE_INSTRUCTIONS, k=random.randint(3, 5))
        inst_items = [ListItem(TrackedParagraph(inst, body_style, canonical_type="text"), leftIndent=12, bulletColor=HexColor(theme[0])) for inst in inst_list]
        inst_flowable = TrackedListFlowable(inst_items, bulletType='bullet', canonical_type="list_item")
        story.append(inst_flowable)
        
        # Build Document
        doc.build(story, canvasmaker=GTTrackingCanvas)
        
        # Prune pages
        import fitz
        pdf_doc = fitz.open(pdf_path)
        actual_pages = len(pdf_doc)
        collector.prune_extra_pages(actual_pages)
        pdf_doc.close()
        
        # Rasterize images
        image_paths = pdf_to_images(pdf_path, image_dir, doc_id)
        
        # Finalize reading order
        for page in collector.pages:
            collector.finalize_reading_order(page["page_number"])
            
        # Write JSON
        collector.write_json(json_path)
        
        # Scanned-style degradation: ~20% of samples
        is_scanned = random.random() < 0.20
        # Save flag in attributes of doc, or we can just run degradation
        if is_scanned:
            for img_path in image_paths:
                degrade_to_scanlike(img_path, img_path)
                
    finally:
        current_collector.reset(token)
