# -*- coding: utf-8 -*-
"""
pdf_stamp_engine.py
Applies EPD template formatting (header image, header text, page numbers)
as an overlay on top of existing PDF files, preserving their content.

Strategy:
  1. Detect page size of each page in the input PDF.
  2. Build a ReportLab "stamp" PDF (header + footer only) for that page size.
  3. Use pikepdf to merge the stamp onto the original page content.
"""

import io
import json
import os
import shutil
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer


class PdfStamper:
    """Applies EPD template header/footer to existing PDF pages."""

    def __init__(self):
        self.style_config = {}
        # -- Defaults (mirrors web_engine defaults) --
        self.margin_top = 50
        self.margin_bottom = 50
        self.margin_left = 50
        self.margin_right = 50
        self.header_type = 'custom'
        self.header_text = ''
        self.header_text_enabled = True
        self.header_image_b64 = None
        self.header_image_height = 40
        self.page_num_format = 'page_n_of_m'
        self.link_hex = '#ef4444'

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def apply_template(self, pdf_bytes: bytes, style_config_json: str,
                       src_path: str, output_folder: str,
                       progress_callback=None) -> io.BytesIO:
        """
        Stamps the EPD template onto every page of `pdf_bytes`.

        Args:
            pdf_bytes: Raw bytes of the original PDF.
            style_config_json: JSON string from the EPD config modal.
            src_path: Original file path (used for backup naming).
            output_folder: Destination folder (backup goes here/_backup/).
            progress_callback: Optional fn(percent, msg).

        Returns:
            BytesIO with the stamped PDF.
        """
        import pikepdf

        self._parse_config(style_config_json)

        if progress_callback:
            progress_callback(5, "Configuración de plantilla cargada...")

        # 1. Backup original
        self._backup_original(src_path, output_folder, progress_callback)

        if progress_callback:
            progress_callback(15, "Analizando páginas del PDF original...")

        # 2. Open original PDF
        original = pikepdf.open(io.BytesIO(pdf_bytes))
        total_pages = len(original.pages)
        result_pdf = pikepdf.Pdf.new()

        if progress_callback:
            progress_callback(20, f"Estampando plantilla en {total_pages} página(s)...")

        for page_idx in range(total_pages):
            # Detect this page's mediabox size
            orig_page = original.pages[page_idx]
            page_w_pt, page_h_pt = self._get_page_size_pt(orig_page)

            # Build stamp for this page size
            stamp_buf = self._build_stamp(page_w_pt, page_h_pt, page_idx + 1, total_pages)
            stamp_buf.seek(0)

            # Open stamp PDF
            stamp_pdf = pikepdf.open(stamp_buf)

            # Append original page to result (correct pikepdf API)
            result_pdf.pages.append(original.pages[page_idx])
            result_page = result_pdf.pages[page_idx]

            # Convert stamp page to an XObject we can embed
            # We use pikepdf's as_form_xobject on a Page wrapper
            stamp_page_obj = stamp_pdf.pages[0]
            form_xobj = pikepdf.Page(stamp_page_obj).as_form_xobject()

            # Add XObject to page resources
            xobj_key = pikepdf.Name(f"/StampOverlay{page_idx}")
            if "/Resources" not in result_page:
                result_page["/Resources"] = pikepdf.Dictionary()
            res = result_page["/Resources"]
            if "/XObject" not in res:
                res["/XObject"] = pikepdf.Dictionary()
            res["/XObject"][xobj_key] = result_pdf.copy_foreign(form_xobj)

            # Wrap existing content stream and append draw command
            # q ... Q wraps existing content; then we invoke our XObject
            xobj_name_str = f"/StampOverlay{page_idx}"
            draw_cmd = f"\nq 1 0 0 1 0 0 cm {xobj_name_str} Do Q\n".encode()

            existing_contents = result_page.get("/Contents")
            wrap_open  = result_pdf.make_stream(b"q\n")
            wrap_close = result_pdf.make_stream(b"\nQ")
            stamp_stream = result_pdf.make_stream(draw_cmd)

            if existing_contents is None:
                result_page["/Contents"] = stamp_stream
            elif isinstance(existing_contents, pikepdf.Array):
                result_page["/Contents"] = pikepdf.Array(
                    [wrap_open] + list(existing_contents) + [wrap_close, stamp_stream]
                )
            else:
                result_page["/Contents"] = pikepdf.Array(
                    [wrap_open, existing_contents, wrap_close, stamp_stream]
                )

            # ── Optional: recolor non-black accent text ──────────────────────
            if getattr(self, 'recolor_accent', False):
                self._recolor_page_content(result_page, result_pdf)

            # ── APA citation block on LAST page only ──────────────────────
            source_url = getattr(self, 'stamp_source_url', '')
            if source_url and page_idx == total_pages - 1:
                apa_buf = self._build_apa_stamp(page_w_pt, page_h_pt, source_url)
                apa_buf.seek(0)
                apa_pdf = pikepdf.open(apa_buf)
                apa_form = pikepdf.Page(apa_pdf.pages[0]).as_form_xobject()
                apa_key = pikepdf.Name(f"/ApaOverlay")
                res['/XObject'][apa_key] = result_pdf.copy_foreign(apa_form)
                apa_cmd = b"\nq 1 0 0 1 0 0 cm /ApaOverlay Do Q\n"
                apa_stream = result_pdf.make_stream(apa_cmd)
                # Append to existing contents
                existing = result_page.get('/Contents')
                if isinstance(existing, pikepdf.Array):
                    result_page['/Contents'] = pikepdf.Array(list(existing) + [apa_stream])
                elif existing is not None:
                    result_page['/Contents'] = pikepdf.Array([existing, apa_stream])
                else:
                    result_page['/Contents'] = apa_stream

            pct = 20 + int((page_idx + 1) / total_pages * 70)
            if progress_callback:
                progress_callback(pct, f"Página {page_idx + 1}/{total_pages} procesada...")



        if progress_callback:
            progress_callback(92, "Guardando PDF final...")

        out_buf = io.BytesIO()
        result_pdf.save(out_buf)
        out_buf.seek(0)

        if progress_callback:
            progress_callback(100, "¡Listo!")

        return out_buf


    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _parse_config(self, style_config_json: str):
        """Parse EPD style_config JSON and populate instance variables."""
        if not style_config_json:
            return
        try:
            config = json.loads(style_config_json)

            def _hex(key, default):
                v = config.get(key)
                if v and str(v).startswith('#'):
                    return v
                return default

            self.margin_top    = int(config.get('margin_top',    50) or 50)
            self.margin_bottom = int(config.get('margin_bottom', 50) or 50)
            self.margin_left   = int(config.get('margin_left',   50) or 50)
            self.margin_right  = int(config.get('margin_right',  50) or 50)

            self.header_type = config.get('header_type', 'custom') or 'custom'
            self.header_text = config.get('header_text', '') or ''

            _hte = config.get('header_text_enabled')
            self.header_text_enabled = True if _hte is None else bool(_hte)

            self.header_image_b64    = config.get('header_imagen') or config.get('headerImageB64')
            self.header_image_height = int(config.get('header_img_height', 40) or 40)
            self.page_num_format     = config.get('page_num_format', 'page_n_of_m') or 'page_n_of_m'
            self.link_hex            = _hex('link_color', '#ef4444')
            self.style_config        = config
            # Recolor: replace non-black accent text with EPD h2 color
            self.recolor_accent      = bool(config.get('stamp_recolor_accent', False))
            self.accent_hex          = _hex('h2_color', None) or _hex('link_color', '#ef4444')
            # APA source URL for last-page citation block
            self.stamp_source_url    = config.get('stamp_source_url', '') or ''

        except Exception as e:
            print(f"[pdf_stamp_engine] Config parse error: {e}")

    def _backup_original(self, src_path: str, output_folder: str, progress_callback=None):
        """Copy src_path into output_folder/_backup/ with a timestamp suffix."""
        try:
            if not src_path or not os.path.isfile(src_path):
                print(f"[pdf_stamp_engine] Backup skipped: file not found at '{src_path}'")
                return

            backup_dir = os.path.join(output_folder, '_backup')
            os.makedirs(backup_dir, exist_ok=True)

            base = os.path.basename(src_path)
            name, ext = os.path.splitext(base)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{name}_{timestamp}{ext}"
            backup_path = os.path.join(backup_dir, backup_name)

            shutil.copy2(src_path, backup_path)
            print(f"[pdf_stamp_engine] Backup created: {backup_path}")
            if progress_callback:
                progress_callback(10, f"Backup: {backup_name}")

        except Exception as e:
            print(f"[pdf_stamp_engine] Backup warning: {e}")
            if progress_callback:
                progress_callback(10, f"Advertencia: no se pudo crear backup ({e})")

    def _get_page_size_pt(self, pikepdf_page) -> tuple:
        """Return (width_pt, height_pt) of a pikepdf page from its MediaBox."""
        try:
            import pikepdf
            mb = pikepdf_page.mediabox
            # MediaBox values are in pt; handle Decimal / pikepdf objects
            x0 = float(mb[0])
            y0 = float(mb[1])
            x1 = float(mb[2])
            y1 = float(mb[3])
            return abs(x1 - x0), abs(y1 - y0)
        except Exception as e:
            print(f"[pdf_stamp_engine] MediaBox read error: {e}, defaulting to Letter")
            return letter[0], letter[1]

    def _build_stamp(self, page_w: float, page_h: float,
                     page_num: int, total_pages: int) -> io.BytesIO:
        """
        Build a transparent ReportLab PDF (single page) with ONLY the header
        and footer drawn, matching the given page dimensions.
        """
        buf = io.BytesIO()

        ps = (page_w, page_h)

        # Capture locals for use inside callbacks
        _self = self
        _page_num = page_num
        _total_pages = total_pages

        def draw_stamp(canvas, doc):
            canvas.saveState()

            # ── Header Image ──────────────────────────────────────────────
            if _self.header_image_b64:
                try:
                    import base64
                    from reportlab.lib.utils import ImageReader

                    b64 = _self.header_image_b64
                    if ',' in b64:
                        b64 = b64.split(',', 1)[1]
                    img_bytes = base64.b64decode(b64)
                    img_buf = io.BytesIO(img_bytes)

                    reader = ImageReader(img_buf)
                    iw, ih = reader.getSize()
                    aspect = iw / float(ih) if ih > 0 else 2.0

                    # Full-bleed: scale to full page width
                    stamp_img_w = page_w
                    stamp_img_h = stamp_img_w / aspect

                    img_x = 0
                    img_y = page_h - stamp_img_h

                    img_buf.seek(0)
                    canvas.drawImage(
                        ImageReader(img_buf), img_x, img_y,
                        width=stamp_img_w, height=stamp_img_h,
                        preserveAspectRatio=True, mask='auto'
                    )
                except Exception as e:
                    print(f"[pdf_stamp_engine] Header image stamp error: {e}")

            # ── Header Text ───────────────────────────────────────────────
            if _self.header_text_enabled:
                ht = ''
                if _self.header_type == 'custom':
                    ht = _self.header_text
                elif _self.header_type == 'title':
                    ht = _self.header_text  # Will be the filename title

                if ht:
                    # Scale text position proportionally to page size vs Letter
                    scale_y = page_h / letter[1]
                    text_y = page_h - (25 * scale_y)
                    line_y = page_h - (30 * scale_y)
                    canvas.setFont('Helvetica', 9)
                    canvas.setFillColor(colors.gray)
                    canvas.drawCentredString(page_w / 2, text_y, ht)
                    canvas.setStrokeColor(colors.lightgrey)
                    canvas.line(
                        _self.margin_left, line_y,
                        page_w - _self.margin_right, line_y
                    )

            # ── Page Number ───────────────────────────────────────────────
            fmt = _self.page_num_format
            p_text = ''
            if fmt == 'page_n':
                p_text = f'Página {_page_num}'
            elif fmt == 'page_n_of_m':
                p_text = f'Página {_page_num} de {_total_pages}'
            elif fmt == 'n_of_m':
                p_text = f'{_page_num} / {_total_pages}'
            elif fmt == 'n':
                p_text = str(_page_num)
            # 'none' → leave blank

            if p_text:
                scale_y = page_h / letter[1]
                footer_y = 30 * scale_y
                canvas.setFont('Helvetica', 9)
                canvas.setFillColor(colors.black)
                canvas.drawRightString(page_w - 50, footer_y, p_text)

            canvas.restoreState()

        # Build a minimal single-page doc — a tiny Spacer is enough to trigger
        # the onFirstPage callback; all actual drawing is in `draw_stamp`.
        doc = SimpleDocTemplate(
            buf,
            pagesize=ps,
            topMargin=0, bottomMargin=0,
            leftMargin=0, rightMargin=0,
        )
        doc.build([Spacer(1, 1)], onFirstPage=draw_stamp)
        return buf

    def _build_apa_stamp(self, page_w: float, page_h: float, source_url: str) -> io.BytesIO:
        """
        Build a single-page ReportLab PDF with ONLY an APA citation block
        at the bottom of the page (last-page stamp).

        The block shows:
            Recuperado de: <source_url>
        styled as a small box, matching the page footer zone.
        """
        buf = io.BytesIO()
        ps  = (page_w, page_h)

        _self      = self
        _url       = source_url
        _margin_l  = self.margin_left
        _margin_r  = self.margin_right
        _margin_b  = self.margin_bottom

        def draw_apa(canvas, doc):
            canvas.saveState()

            # Pick accent color from EPD (h2 or link color)
            try:
                accent = (_self.accent_hex or '#ef4444').lstrip('#')
                ar = int(accent[0:2], 16) / 255.0
                ag = int(accent[2:4], 16) / 255.0
                ab = int(accent[4:6], 16) / 255.0
            except Exception:
                ar, ag, ab = 0.94, 0.27, 0.27  # default red

            # Box dimensions — sits just above footer line
            box_h   = 36      # pt
            box_y   = _margin_b + 18  # just above page number
            box_x   = _margin_l
            box_w   = page_w - _margin_l - _margin_r

            # Draw light background box
            canvas.setFillColorRGB(ar, ag, ab, alpha=0.08)
            canvas.setStrokeColorRGB(ar, ag, ab, alpha=0.4)
            canvas.setLineWidth(0.5)
            canvas.roundRect(box_x, box_y, box_w, box_h, 3, fill=1, stroke=1)

            # Label
            canvas.setFont('Helvetica-Bold', 7)
            canvas.setFillColorRGB(ar, ag, ab)
            canvas.drawString(box_x + 6, box_y + box_h - 12, 'Recuperado de:')

            # URL — truncate if too long for display
            max_chars = int(box_w / 4.2)
            display_url = _url if len(_url) <= max_chars else _url[:max_chars - 3] + '...'
            canvas.setFont('Helvetica', 6.5)
            canvas.setFillColorRGB(0.1, 0.1, 0.1)
            canvas.drawString(box_x + 6, box_y + 6, display_url)

            canvas.restoreState()

        doc = SimpleDocTemplate(
            buf,
            pagesize=ps,
            topMargin=0, bottomMargin=0,
            leftMargin=0, rightMargin=0,
        )
        doc.build([Spacer(1, 1)], onFirstPage=draw_apa)
        return buf

    def _recolor_page_content(self, page, pdf):
        """
        Scan the page content stream(s) for non-black RGB text fill color commands
        (`R G B rg` where R,G,B ≠ 0,0,0) and replace them with the EPD accent color.

        Only `rg` (text/fill in DeviceRGB) is targeted — `RG` (stroke) and
        `k`/`K` (CMYK) are left untouched to avoid breaking graphic elements.
        Black text (0 0 0 rg) and near-black (all channels < 0.05) are preserved.
        """
        import re

        # Parse accent color → float r, g, b
        try:
            accent = self.accent_hex.lstrip('#')
            ar = int(accent[0:2], 16) / 255.0
            ag = int(accent[2:4], 16) / 255.0
            ab = int(accent[4:6], 16) / 255.0
        except Exception:
            return  # Can't parse color, skip

        accent_cmd = f'{ar:.4f} {ag:.4f} {ab:.4f} rg'

        # Regex: matches "R G B rg" where numbers can be int or float
        # Captures three numeric groups before 'rg'
        rg_pat = re.compile(
            rb'([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+rg'
        )

        def replace_rg(m):
            try:
                r = float(m.group(1))
                g = float(m.group(2))
                b = float(m.group(3))
            except ValueError:
                return m.group(0)

            # Preserve black and near-black (all channels < 0.1)
            if r < 0.1 and g < 0.1 and b < 0.1:
                return m.group(0)

            # Preserve white / very light (all channels > 0.9)
            if r > 0.9 and g > 0.9 and b > 0.9:
                return m.group(0)

            # Replace with accent color
            return accent_cmd.encode()

        contents = page.get('/Contents')
        if contents is None:
            return

        def process_stream(stream_obj):
            """Decompress, recolor, recompress a single stream object."""
            try:
                import pikepdf
                raw = stream_obj.read_raw_bytes()
                # Use pikepdf's read_bytes to get decompressed content
                decompressed = stream_obj.read_bytes()
                recolored = rg_pat.sub(replace_rg, decompressed)
                if recolored != decompressed:
                    stream_obj.write(recolored)
                    print(f'[pdf_stamp_engine] Recolored text stream ({len(decompressed)}→{len(recolored)} bytes)')
            except Exception as e:
                print(f'[pdf_stamp_engine] Recolor stream error: {e}')

        import pikepdf
        if isinstance(contents, pikepdf.Array):
            for item in contents:
                try:
                    process_stream(pdf.get_object(item.objgen))
                except Exception:
                    pass
        else:
            try:
                process_stream(pdf.get_object(contents.objgen))
            except Exception:
                pass
