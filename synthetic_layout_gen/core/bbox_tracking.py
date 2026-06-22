# core/bbox_tracking.py
import uuid
from reportlab.platypus import Paragraph, Table, Image, ListFlowable, ListItem
from reportlab.pdfgen import canvas
from synthetic_layout_gen.core.coordinate_utils import reportlab_to_topleft, strip_padding
from synthetic_layout_gen.core.ground_truth_collector import current_collector

class GTTrackingCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._record_page(1)
        
    def _record_page(self, page_num):
        collector = current_collector.get()
        if collector is not None:
            w_pt, h_pt = self._pagesize
            w_px = int(w_pt * 150.0 / 72.0)
            h_px = int(h_pt * 150.0 / 72.0)
            image_dir = f"output/{collector.domain}/images"
            image_path = f"{image_dir}/{collector.document_id}_p{page_num}.png"
            collector.new_page(
                page_number=page_num,
                dimensions_pt=(w_pt, h_pt),
                dimensions_px=(w_px, h_px),
                image_path=image_path
            )

    def showPage(self):
        super().showPage()
        next_page = self._pageNumber
        self._record_page(next_page)

class BBoxTrackingMixin:
    def drawOn(self, canvas, x, y, _sW=0):
        w = getattr(self, "width", None)
        if w is None:
            w = getattr(self, "_width", None)
        if w is None:
            w = getattr(self, "drawWidth", 0)
            
        h = getattr(self, "height", None)
        if h is None:
            h = getattr(self, "_height", None)
        if h is None:
            h = getattr(self, "drawHeight", 0)
            
        page_h = canvas._pagesize[1]
        bbox = reportlab_to_topleft(x, y, w, h, page_h)
        if getattr(self, "_gt_padding", None):
            bbox = strip_padding(bbox, self._gt_padding)
        
        collector = current_collector.get()
        if collector is not None:
            collector.add_element(
                page_number=canvas.getPageNumber(),
                element_type=self.canonical_type,
                bbox=bbox,
                text=getattr(self, "_gt_text", None),
                attributes=getattr(self, "_gt_attributes", {}),
                continued_from=getattr(self, "_gt_parent_id", None),
            )
        super().drawOn(canvas, x, y, _sW)

class TrackedParagraph(BBoxTrackingMixin, Paragraph):
    def __init__(self, *args, canonical_type="text", gt_id=None, attributes=None, **kwargs):
        self.canonical_type = canonical_type
        self._gt_id = gt_id or str(uuid.uuid4())
        self._gt_text = args[0] if len(args) > 0 else ""
        self._gt_attributes = attributes or {}
        self._gt_parent_id = None
        self._gt_padding = None
        super().__init__(*args, **kwargs)

    def split(self, availWidth, availHeight):
        fragments = super().split(availWidth, availHeight)
        if fragments and len(fragments) > 1:
            shared_id = self._gt_id
            for frag in fragments:
                frag._gt_parent_id = shared_id
                frag._gt_padding = self._gt_padding
                frag._gt_attributes = dict(self._gt_attributes)
                if not hasattr(frag, "_gt_text"):
                    frag._gt_text = getattr(frag, 'text', self._gt_text)
                if not hasattr(frag, 'canonical_type'):
                    frag.canonical_type = self.canonical_type
        return fragments

class TrackedTable(BBoxTrackingMixin, Table):
    def __init__(self, *args, canonical_type="table", gt_id=None, attributes=None, **kwargs):
        self.canonical_type = canonical_type
        self._gt_id = gt_id or str(uuid.uuid4())
        self._gt_attributes = attributes or {}
        self._gt_parent_id = None
        
        style = kwargs.get('style', None)
        if style is None and len(args) > 3:
            style = args[3]
            
        top_p = 5.0
        bottom_p = 5.0
        left_p = 6.0
        right_p = 6.0
        if style:
            for cmd in style:
                if len(cmd) >= 4:
                    op, _, _, val = cmd[:4]
                    if op == 'TOPPADDING':
                        try: top_p = float(val)
                        except: pass
                    elif op == 'BOTTOMPADDING':
                        try: bottom_p = float(val)
                        except: pass
                    elif op == 'LEFTPADDING':
                        try: left_p = float(val)
                        except: pass
                    elif op == 'RIGHTPADDING':
                        try: right_p = float(val)
                        except: pass
        self._gt_padding = (top_p, right_p, bottom_p, left_p)
        super().__init__(*args, **kwargs)

    def drawOn(self, canvas, x, y, _sW=0):
        n_rows = len(self._cellvalues)
        n_cols = len(self._cellvalues[0]) if n_rows > 0 else 0
        self._gt_attributes['n_rows'] = n_rows
        self._gt_attributes['n_cols'] = n_cols
        
        colpositions = getattr(self, '_colpositions', [])
        rowpositions = getattr(self, '_rowpositions', [])
        page_h = canvas._pagesize[1]
        
        cells_data = []
        if len(colpositions) >= n_cols + 1 and len(rowpositions) >= n_rows + 1:
            for r in range(n_rows):
                for c in range(n_cols):
                    cell_val = self._cellvalues[r][c]
                    cell_text = ""
                    if isinstance(cell_val, Paragraph):
                        cell_text = cell_val.text
                    elif hasattr(cell_val, 'getPlainText'):
                        cell_text = cell_val.getPlainText()
                    elif cell_val is not None:
                        cell_text = str(cell_val)
                    
                    x_cell = x + colpositions[c]
                    w_cell = colpositions[c+1] - colpositions[c]
                    y_cell = y + rowpositions[r+1]
                    h_cell = rowpositions[r] - rowpositions[r+1]
                    
                    cell_bbox = reportlab_to_topleft(x_cell, y_cell, w_cell, h_cell, page_h)
                    if self._gt_padding:
                        cell_bbox = strip_padding(cell_bbox, self._gt_padding)
                    
                    cells_data.append({
                        "row": r,
                        "col": c,
                        "bbox": list(cell_bbox),
                        "text": cell_text
                    })
        self._gt_attributes['cells'] = cells_data
        super().drawOn(canvas, x, y, _sW)

    def split(self, availWidth, availHeight):
        fragments = super().split(availWidth, availHeight)
        if fragments and len(fragments) > 1:
            shared_id = self._gt_id
            for frag in fragments:
                frag._gt_parent_id = shared_id
                frag._gt_padding = self._gt_padding
                frag._gt_attributes = dict(self._gt_attributes)
                if not hasattr(frag, 'canonical_type'):
                    frag.canonical_type = self.canonical_type
        return fragments

class TrackedImage(BBoxTrackingMixin, Image):
    def __init__(self, *args, canonical_type="picture", gt_id=None, attributes=None, **kwargs):
        self.canonical_type = canonical_type
        self._gt_id = gt_id or str(uuid.uuid4())
        self._gt_text = None
        self._gt_attributes = attributes or {}
        self._gt_parent_id = None
        self._gt_padding = None
        super().__init__(*args, **kwargs)

class TrackedListFlowable(ListFlowable):
    def __init__(self, *args, canonical_type="list_item", gt_id=None, attributes=None, **kwargs):
        self.canonical_type = canonical_type
        self._gt_id = gt_id or str(uuid.uuid4())
        self._gt_attributes = attributes or {}
        self._gt_parent_id = None
        self._gt_padding = None
        super().__init__(*args, **kwargs)
        
    def drawOn(self, canvas, x, y, _sW=0):
        for idx, item in enumerate(self._content):
            if '_gt_wrapped' not in item.__dict__:
                original_drawOn = item.drawOn
                item_id = str(uuid.uuid4())
                
                def make_custom_drawOn(orig_draw, itm, itm_id):
                    def custom_drawOn(canvas_val, x_val, y_val, _sW=0):
                        w_val = getattr(itm, "_w", getattr(itm, "width", 0))
                        if w_val is None or w_val == 0:
                            w_val = getattr(itm, "_width", getattr(itm, "drawWidth", 0))
                        h_val = getattr(itm, "_h", getattr(itm, "height", 0))
                        if h_val is None or h_val == 0:
                            h_val = getattr(itm, "_height", getattr(itm, "drawHeight", 0))
                        page_h_val = canvas_val._pagesize[1]
                        bbox_val = reportlab_to_topleft(x_val, y_val, w_val, h_val, page_h_val)
                        
                        text_content = ""
                        if hasattr(itm, 'contents'):
                            for sub_f in getattr(itm, 'contents', []):
                                if hasattr(sub_f, 'text'):
                                    text_content += sub_f.text
                                elif hasattr(sub_f, 'getPlainText'):
                                    text_content += sub_f.getPlainText()
                        else:
                            if hasattr(itm, 'text'):
                                text_content = itm.text
                            elif hasattr(itm, 'getPlainText'):
                                text_content = itm.getPlainText()
                        
                        collector = current_collector.get()
                        if collector is not None:
                            collector.add_element(
                                page_number=canvas_val.getPageNumber(),
                                element_type="list_item",
                                bbox=bbox_val,
                                text=text_content if text_content else None,
                                attributes=getattr(itm, '_gt_attributes', {}),
                                continued_from=getattr(itm, '_gt_parent_id', None)
                            )
                        orig_draw(canvas_val, x_val, y_val, _sW)
                    return custom_drawOn
                
                object.__setattr__(item, 'drawOn', make_custom_drawOn(original_drawOn, item, item_id))
                object.__setattr__(item, '_gt_wrapped', True)
                
        super().drawOn(canvas, x, y, _sW)
