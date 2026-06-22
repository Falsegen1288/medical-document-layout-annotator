# core/test_coordinate_utils.py
import unittest
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
import os

from synthetic_layout_gen.core.coordinate_utils import reportlab_to_topleft, strip_padding

class TestCoordinateUtils(unittest.TestCase):
    def test_reportlab_to_topleft(self):
        # US Letter width = 612, height = 792
        page_height = 792.0
        
        # Test coordinates
        x, y, w, h = 72.0, 72.0, 100.0, 50.0
        
        # Hand-calculated top-left origin:
        # x0 = x = 72.0
        # x1 = x + w = 172.0
        # y0 = page_height - (y + h) = 792.0 - 122.0 = 670.0
        # y1 = page_height - y = 792.0 - 72.0 = 720.0
        
        x0, y0, x1, y1 = reportlab_to_topleft(x, y, w, h, page_height)
        self.assertAlmostEqual(x0, 72.0)
        self.assertAlmostEqual(x1, 172.0)
        self.assertAlmostEqual(y0, 670.0)
        self.assertAlmostEqual(y1, 720.0)

    def test_strip_padding(self):
        bbox = (72.0, 100.0, 172.0, 150.0)
        padding = (5.0, 10.0, 5.0, 10.0) # top, right, bottom, left
        # stripped bbox should be:
        # x0 = 72.0 + 10.0 = 82.0
        # y0 = 100.0 + 5.0 = 105.0
        # x1 = 172.0 - 10.0 = 162.0
        # y1 = 150.0 - 5.0 = 145.0
        x0, y0, x1, y1 = strip_padding(bbox, padding)
        self.assertEqual(x0, 82.0)
        self.assertEqual(y0, 105.0)
        self.assertEqual(x1, 162.0)
        self.assertEqual(y1, 145.0)

if __name__ == '__main__':
    unittest.main()
