# core/playwright_capture.py
import os
import asyncio
from playwright.async_api import async_playwright
from synthetic_layout_gen.core.coordinate_utils import px_to_pt

async def render_and_capture(html_path_or_string: str, output_image_path: str, output_pdf_path: str, viewport_px: tuple[int, int], dpi: int = 150) -> tuple[list[dict], tuple[float, float]]:
    """
    1. Launches Chromium, sets viewport to viewport_px.
    2. Loads HTML.
    3. Waits for networkidle.
    4. Evaluates Javascript to extract elements and table cells.
    5. Converts coordinates to pt.
    6. Saves page screenshot and page PDF.
    """
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Viewport at 150 DPI matching standard 1275x1650 px US Letter
        context = await browser.new_context(
            viewport={"width": viewport_px[0], "height": viewport_px[1]},
            device_scale_factor=1.0
        )
        page = await context.new_page()
        
        # Load content
        if html_path_or_string.startswith("file://") or os.path.exists(html_path_or_string):
            if not html_path_or_string.startswith("file://"):
                url = f"file:///{os.path.abspath(html_path_or_string).replace('\\', '/')}"
            else:
                url = html_path_or_string
            await page.goto(url)
        else:
            await page.set_content(html_path_or_string)
            
        await page.wait_for_load_state("networkidle")
        
        # JS script to fetch elements
        js_script = """
        async () => {
            const elements = [];
            const els = document.querySelectorAll("[data-gt-type]");
            els.forEach((el, idx) => {
                const type = el.getAttribute("data-gt-type");
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                
                const pTop = parseFloat(style.paddingTop) || 0;
                const pBottom = parseFloat(style.paddingBottom) || 0;
                const pLeft = parseFloat(style.paddingLeft) || 0;
                const pRight = parseFloat(style.paddingRight) || 0;
                
                const bTop = parseFloat(style.borderTopWidth) || 0;
                const bBottom = parseFloat(style.borderBottomWidth) || 0;
                const bLeft = parseFloat(style.borderLeftWidth) || 0;
                const bRight = parseFloat(style.borderRightWidth) || 0;
                
                const x0 = rect.left + pLeft + bLeft;
                const y0 = rect.top + pTop + bTop;
                const x1 = rect.right - pRight - bRight;
                const y1 = rect.bottom - pBottom - bBottom;
                
                let attrs = {};
                const attrStr = el.getAttribute("data-gt-attrs");
                if (attrStr) {
                    try { attrs = JSON.parse(attrStr); } catch(e) {}
                }
                
                if (el.tagName.toLowerCase() === 'table') {
                    const cells = [];
                    const rows = el.querySelectorAll('tr');
                    rows.forEach((row, r_idx) => {
                        const cols = row.querySelectorAll('td, th');
                        cols.forEach((col, c_idx) => {
                            const c_rect = col.getBoundingClientRect();
                            const c_style = window.getComputedStyle(col);
                            const c_pTop = parseFloat(c_style.paddingTop) || 0;
                            const c_pBottom = parseFloat(c_style.paddingBottom) || 0;
                            const c_pLeft = parseFloat(c_style.paddingLeft) || 0;
                            const c_pRight = parseFloat(c_style.paddingRight) || 0;
                            
                            const c_bTop = parseFloat(c_style.borderTopWidth) || 0;
                            const c_bBottom = parseFloat(c_style.borderBottomWidth) || 0;
                            const c_bLeft = parseFloat(c_style.borderLeftWidth) || 0;
                            const c_bRight = parseFloat(c_style.borderRightWidth) || 0;
                            
                            cells.push({
                                row: r_idx,
                                col: c_idx,
                                rect: {
                                    left: c_rect.left + c_pLeft + c_bLeft,
                                    top: c_rect.top + c_pTop + c_bTop,
                                    right: c_rect.right - c_pRight - c_bRight,
                                    bottom: c_rect.bottom - c_pBottom - c_bBottom
                                },
                                text: col.innerText
                            });
                        });
                    });
                    attrs.cells = cells;
                    attrs.n_rows = rows.length;
                    attrs.n_cols = rows.length > 0 ? rows[0].querySelectorAll('td, th').length : 0;
                }
                
                elements.push({
                    type: type,
                    text: el.innerText || null,
                    rect: { left: x0, top: y0, right: x1, bottom: y1 },
                    attrs: attrs
                });
            });
            return elements;
        }
        """
        
        raw_elements = await page.evaluate(js_script)
        
        # Take page screenshot matching viewport size
        await page.screenshot(path=output_image_path, full_page=False)
        
        # Export PDF
        await page.pdf(path=output_pdf_path, print_background=True, prefer_css_page_size=True)
        
        await browser.close()
        
        # Convert px to pt
        processed_elements = []
        for elem in raw_elements:
            rect = elem["rect"]
            x0 = px_to_pt(rect["left"], dpi)
            y0 = px_to_pt(rect["top"], dpi)
            x1 = px_to_pt(rect["right"], dpi)
            y1 = px_to_pt(rect["bottom"], dpi)
            
            # Prevent zero/negative dimensions due to browser subpixel rounding
            if x1 <= x0:
                x1 = x0 + 0.1
            if y1 <= y0:
                y1 = y0 + 0.1
            
            # Map attributes
            attrs = elem["attrs"]
            if "cells" in attrs:
                # Convert cell coordinates
                for cell in attrs["cells"]:
                    c_rect = cell["rect"]
                    cx0 = px_to_pt(c_rect["left"], dpi)
                    cy0 = px_to_pt(c_rect["top"], dpi)
                    cx1 = px_to_pt(c_rect["right"], dpi)
                    cy1 = px_to_pt(c_rect["bottom"], dpi)
                    
                    if cx1 <= cx0:
                        cx1 = cx0 + 0.1
                    if cy1 <= cy0:
                        cy1 = cy0 + 0.1
                        
                    cell["bbox"] = [cx0, cy0, cx1, cy1]
                    del cell["rect"]
            
            processed_elements.append({
                "type": elem["type"],
                "text": elem["text"],
                "bbox": [x0, y0, x1, y1],
                "attributes": attrs
            })
            
        # dimensions in pt
        w_pt = px_to_pt(viewport_px[0], dpi)
        h_pt = px_to_pt(viewport_px[1], dpi)
        
        return processed_elements, (w_pt, h_pt)
