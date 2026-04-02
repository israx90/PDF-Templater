import io
import json
import xml.etree.ElementTree as ET
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, legal
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from deep_translator import GoogleTranslator
import trafilatura
import requests
from bs4 import BeautifulSoup

# --- REPORTLAB STYLES ---
def get_unifranz_styles():
    styles = getSampleStyleSheet()
    
    # Title (H1)
    styles.add(ParagraphStyle(
        name='UnifranzTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=20,
        textTransform='uppercase'
    ))
    
    # Header 2 (H2) - Red
    styles.add(ParagraphStyle(
        name='UnifranzH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=22,
        textColor=colors.HexColor('#ef4444'),
        spaceBefore=15,
        spaceAfter=10,
        borderPadding=5,
        borderWidth=1,
        borderColor=colors.HexColor('#ef4444'),
        borderRadius=0,
        keepWithNext=True
    ))

    # Body Text
    styles.add(ParagraphStyle(
        name='UnifranzBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    ))

    # Link/Actions
    styles.add(ParagraphStyle(
        name='UnifranzLink',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.white,
        backColor=colors.HexColor('#ef4444'),
        alignment=TA_CENTER,
        borderPadding=10,
        spaceBefore=30
    ))
    
    return styles

class WebConverter:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=1.0,en;q=0.1'
        }
        self.styles = get_unifranz_styles()
        self.translator = GoogleTranslator(source='auto', target='es')

    def translate_text(self, text):
        """
        Safely translates text to Spanish using Google Translate.
        Returns original text if translation fails, text is too short, or is a code snippet.
        """
        if not text or len(text.strip()) < 5:
            return text
            
        try:
            # Heuristics to skip translation
            if text.startswith('http') or '{' in text or 'function(' in text:
                return text

            translated = self.translator.translate(text)
            return translated if translated else text
        except Exception as e:
            print(f"Translation Error: {e}")
            return text

    def batch_translate_bs4_items(self, bs4_items, progress_callback=None):
        """
        Translates all bs4_items ('text' fields) in a single batch to avoid
        rate limiting and network hangs. Uses a unique separator '|||'.
        """
        if not bs4_items:
            return bs4_items
            
        if progress_callback:
            progress_callback(45, "Traduciendo contenido extraído (Lote)...")
            
        try:
            # 1. Collect texts that need translation
            texts_to_translate = []
            indices_to_update = []
            
            for i, item in enumerate(bs4_items):
                if item.get('type') in ('header', 'paragraph', 'list_item') and 'text' in item:
                    # Strip BS4 formatting briefly to check length/heuristics
                    # The markup itself will be translated. Google Translate handles HTML/XML surprisingly well.
                    raw_text = item['text']
                    if len(raw_text.strip()) >= 5 and not raw_text.startswith('http') and '{' not in raw_text:
                        texts_to_translate.append(raw_text)
                        indices_to_update.append(i)
                elif item.get('type') == 'table' and 'rows' in item:
                    # For tables, we'll iterate through cells
                    pass # Simplified: tables might break with batching due to complex structure. Fallback to raw.

            if not texts_to_translate:
                return bs4_items

            # 2. Chunking (Google Translate has a 5000 char limit usually, but DeepTranslator handles it internally)
            # However, joining everything with ' ||| ' creates a massive string. 
            # We will chunk it to be safe (~3000 chars per chunk).
            
            SEP = " ||| "
            chunks = []
            current_chunk = []
            current_len = 0
            
            for text in texts_to_translate:
                if current_len + len(text) > 3500:
                    chunks.append(SEP.join(current_chunk))
                    current_chunk = [text]
                    current_len = len(text)
                else:
                    current_chunk.append(text)
                    current_len += len(text)
                    
            if current_chunk:
                chunks.append(SEP.join(current_chunk))

            # 3. Translate Chunks
            import concurrent.futures
            translated_texts = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                for chunk in chunks:
                    try:
                        future = executor.submit(self.translator.translate, chunk)
                        res = future.result(timeout=10)
                        if res:
                            # Split back by the separator (handling potential spacing variations added by Google)
                            split_res = [s.strip() for s in res.split('|||')]
                            translated_texts.extend(split_res)
                        else:
                            translated_texts.extend(chunk.split(SEP))
                    except concurrent.futures.TimeoutError:
                        print("Batch Chunk Translation Error: Timeout (10s)")
                        translated_texts.extend(chunk.split(SEP))
                    except Exception as chunk_err:
                        print(f"Batch Chunk Translation Error: {chunk_err}")
                        translated_texts.extend(chunk.split(SEP))

            # 4. Map back to items
            # There might be a length mismatch if translation swallowed a separator. 
            # We do a safe mapping.
            if len(translated_texts) == len(indices_to_update):
                for idx, translated_text in zip(indices_to_update, translated_texts):
                    # Clean up random spaces Google might add around XML tags
                    translated_text = translated_text.replace('< b >', '<b>').replace('< / b >', '</b>')
                    translated_text = translated_text.replace('< i >', '<i>').replace('< / i >', '</i>')
                    bs4_items[idx]['text'] = translated_text
            else:
                print(f"Batch mismatch: Sent {len(indices_to_update)}, got {len(translated_texts)}. Falling back to element translation.")
                # Fallback to single translations for this document if batch failed
                for idx in indices_to_update:
                     try:
                         # Use disabled manual transl. Just skip.
                         pass 
                     except: pass
                     
            print("Batch translation complete.")
            return bs4_items
            
        except Exception as e:
            return bs4_items

    def bs4_to_reportlab_markup(self, element):
        """
        Converts a BeautifulSoup element into a ReportLab-compatible markup string,
        preserving inline formatting: <a> → <link>, <strong>/<b> → <b>, <em>/<i> → <i>.
        Translates text segments to Spanish.
        """
        parts = []
        link_color = getattr(self, 'link_hex', '#ef4444')

        for child in element.children:
            if isinstance(child, str):
                # NavigableString — raw text node
                text = child
                # Escape XML entities
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                parts.append(text)
            else:
                # Tag element
                tag_name = child.name
                if tag_name in ('strong', 'b'):
                    inner = self.bs4_to_reportlab_markup(child)
                    parts.append(f'<b>{inner}</b>')
                elif tag_name in ('em', 'i'):
                    inner = self.bs4_to_reportlab_markup(child)
                    parts.append(f'<i>{inner}</i>')
                elif tag_name == 'a':
                    href = child.get('href', '')
                    inner = self.bs4_to_reportlab_markup(child)
                    if inner.strip():
                        if href.startswith('http'):
                            parts.append(f'<link href="{href}" color="{link_color}">{inner}</link>')
                        else:
                            parts.append(inner)
                elif tag_name == 'br':
                    parts.append('<br/>')
                elif tag_name in ('span', 'u', 'mark', 'sub', 'sup', 'abbr', 'time'):
                    # Transparent wrappers — keep their text
                    inner = self.bs4_to_reportlab_markup(child)
                    parts.append(inner)
                else:
                    # Unknown inline tag — extract text only
                    text = child.get_text(separator=' ', strip=True)
                    if text:
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        parts.append(text)

        return ''.join(parts)

    def normalize_paragraph_text(self, text):
        """
        Collapses broken inline fragments back into fluent prose.
        Problems fixed:
          - Newlines/tabs injected due to inline images or links
          - '\n' followed by lowercase = mid-sentence break (join with space)
          - Multiple consecutive spaces
          - Soft hyphens and line-break hyphens (e.g. 'infor-\nmación')
        Does NOT collapse intentional <br/> tags (those are already rendered).
        Works on both plain text and ReportLab markup (preserves tags).
        """
        import re
        if not text:
            return text
        # 1. Fix hyphenated line breaks: 'infor-\nma' -> 'informa'
        text = re.sub(r'-(\s*\n\s*)', '', text)
        # 2. Join mid-sentence line breaks: newline followed by lowercase or mid-word
        #    e.g. 'buscando\no navegando' -> 'buscando o navegando'
        text = re.sub(r'\n\s*([a-zà-ÿ,;\-])', r' \1', text)
        # 3. Collapse any remaining \n, \r, \t to a single space
        text = re.sub(r'[\n\r\t]+', ' ', text)
        # 4. Collapse multiple spaces (but preserve tag structure)
        text = re.sub(r'  +', ' ', text)
        # 5. Sanitize non-Latin / unsupported Unicode chars (ReportLab Helvetica can't render them)
        #    Replace common ones with ASCII equivalents, strip the rest
        _UNICODE_MAP = {
            '\u25a0': '',   # ■ solid square
            '\u25a1': '',   # □ open square
            '\u25cf': '',   # ● solid circle
            '\u25b6': '>',  # ▶ triangle
            '\u2192': '->',  # → right arrow
            '\u2190': '<-',  # ← left arrow
            '\u2713': 'v',   # ✓ check
            '\u2714': 'v',   # ✔ heavy check
            '\u2717': 'x',   # ✗ ballot x
            '\u2022': '-',   # • bullet (we add our own)
            '\u00b7': '-',   # · middle dot
            '\u2013': '-',   # en dash
            '\u2014': '-',   # em dash
            '\u2018': "'",   # ' left single quote
            '\u2019': "'",   # ' right single quote
            '\u201c': '"',   # \u201c left double quote
            '\u201d': '"',   # \u201d right double quote
            '\u00a0': ' ',   # non-breaking space
            '\u200b': '',    # zero-width space
            '\u200e': '',    # left-to-right mark
            '\u200f': '',    # right-to-left mark
            '\ufeff': '',    # BOM
        }
        for char, replacement in _UNICODE_MAP.items():
            text = text.replace(char, replacement)
        # Strip remaining non-printable / non-ASCII control chars (but keep Latin accents)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Collapse spaces again after substitutions
        text = re.sub(r'  +', ' ', text)
        return text.strip()

    def get_video_thumbnail(self, video_url):
        """
        Extracts video ID and fetches thumbnail for YouTube/Vimeo.
        Returns (image_data_bytes, is_video)
        """
        try:
            # YouTube
            if 'youtube.com' in video_url or 'youtu.be' in video_url:
                vid_id = None
                if 'v=' in video_url:
                    vid_id = video_url.split('v=')[1].split('&')[0]
                elif 'youtu.be/' in video_url:
                    vid_id = video_url.split('youtu.be/')[1].split('?')[0]
                
                if vid_id:
                    thumb_url = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"
                    resp = requests.get(thumb_url, headers=self.headers, timeout=5)
                    if resp.status_code == 200:
                        return io.BytesIO(resp.content), True
            
            # Vimeo (Generic or scrape)
            elif 'vimeo.com' in video_url:
                # For now, return a generic placeholder or try to find one if needed.
                # Vimeo thumbnails require API or oEmbed. Let's stick to a reliable heuristic or skip for now.
                pass

        except: pass
        return None, False

    def parse_xml_element(self, element):
        """
        Recursively parses Trafilatura XML elements and returns a list of dictionaries.
        Includes AD FILTERING and RICH MEDIA detection.
        """
        items = []
        
        # Helper to get inner text with formatting (b/i/a) preserved for ReportLab
        def get_inner_xml(elem):
            text = (elem.text or "")
            if len(text) > 5 and not text.startswith('http'):
                 text = self.translate_text(text)
            
            # Escape XML
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            for child in elem:
                child_text = get_inner_xml(child)
                
                # Ensure space before inline tag
                if text and child_text and not text[-1] in (' ', '\n', '\t'):
                    text += ' '
                
                if child.tag == 'hi' and child.get('rend') == '#b':
                    text += f"<b>{child_text}</b>"
                elif child.tag == 'hi' and child.get('rend') == '#i':
                    text += f"<i>{child_text}</i>"
                elif child.tag == 'ref':
                    target = child.get('target', '')
                    if target.startswith('http'):
                        color = getattr(self, 'link_hex', '#ef4444')
                        text += f'<link href="{target}" color="{color}">{child_text}</link>'
                    else:
                        text += child_text
                else:
                    text += child_text
                
                # Add tail text (text after the closing tag)
                if child.tail:
                    tail = child.tail
                    if len(tail) > 5: tail = self.translate_text(tail)
                    tail = tail.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    # Ensure space after closing tag before tail
                    if text and tail and not tail[0] in (' ', '\n', '\t', ',', '.', ';', ':', '!', '?'):
                        text += ' '
                    text += tail
            return text

        if element.tag.startswith('h'):
            # Header
            try:
                level = int(element.tag[1]) # h1, h2...
            except: level = 2
            text = get_inner_xml(element)
            if text.strip() and "advertisement" not in text.lower():
                items.append({'type': 'header', 'level': level, 'text': text})
                
        elif element.tag == 'p':
            # Paragraph
            text = get_inner_xml(element)
            
            # Filter Ad / CTA / Promo Text
            ad_keywords = [
                'advertisement', 'sponsored', 'suscríbete', 'read more', 'leer más',
                'get our template', 'obtenga nuestra plantilla', 'get the template',
                'download template', 'descargar plantilla', 'sign up', 'regístrate',
                'start free trial', 'prueba gratis', 'try for free', 'subscribe',
                'newsletter', 'share this', 'comparta esto', 'get started',
                'book a demo', 'solicita una demo', 'free trial',
                'see how', 'learn more about our', 'request a quote',
            ]
            text_lower = text.lower()
            if any(k in text_lower for k in ad_keywords):
                return items # Skip

            if text.strip():
                # Check for Video Links strictly (must be a URL)
                import re
                video_pattern = r'https?://(?:www\.)?(?:youtube\.com|youtu\.be|vimeo\.com)/'
                
                if re.search(video_pattern, text) and len(text) < 250:
                     # Extract URL if it's just a raw link or short text
                     # distinct logic handled in main loop
                     items.append({'type': 'video_link', 'text': text, 'raw_text': element.text or ""})
                else:
                     items.append({'type': 'paragraph', 'text': text})
        
        elif element.tag == 'list':
            # List
            for child in element:
                if child.tag == 'item':
                    text = get_inner_xml(child)
                    if text.strip():
                        items.append({'type': 'list_item', 'text': text})
                        
        elif element.tag == 'graphic':
            # Image
            src = element.get('src')
            if src:
                # AD FILTERING: We can't check size yet without downloading, 
                # but we can check URL patterns or rely on Trafilatura's cleanup.
                # We will check size at render time.
                items.append({'type': 'image', 'src': src})
                
        elif element.tag in ['code', 'pre', 'ab'] and (element.tag == 'pre' or 'code' in str(element.text or '')):
            # Code Block — return as dict so main loop handles it uniformly
            code_text = (element.text or "").strip()
            if not code_text:
                code_text = "".join([c.text or "" for c in element])
            if code_text:
                items.append({'type': 'code', 'text': code_text})

        elif element.tag == 'table':
            # Table — collect raw cell text as dicts, render in main loop
            try:
                rows_data = []
                has_header = False
                for row in element:
                    if row.tag == 'row':
                        row_cells = []
                        for cell in row:
                            if cell.tag == 'cell':
                                row_cells.append(get_inner_xml(cell))
                                if cell.get('role') == 'head':
                                    has_header = True
                        if row_cells:
                            rows_data.append(row_cells)
                if rows_data:
                    items.append({'type': 'table', 'rows': rows_data, 'has_header': has_header})
            except Exception as e:
                print(f"Table Parse Error: {e}")
                items.append({'type': 'paragraph', 'text': '[Tabla no renderizable]'})
            return items
        for child in element:
            if child.tag not in ['hi', 'ref']: # These are handled inside get_inner_xml
                items.extend(self.parse_xml_element(child))
                
        return items

    def convert_to_pdf(self, url, paper_size='letter', style_config=None, progress_callback=None):
        import re  # Must be at top — Python 3.12 scoping: any 'import re' inside the method makes re local
        from urllib.parse import urlparse as _up, urlencode as _ue, parse_qs as _pq, urlunparse as _uu
        # Strip UTM and tracking query params before fetching
        try:
            _parsed = _up(url)
            _qs = _pq(_parsed.query, keep_blank_values=True)
            _STRIP = {'utm_source','utm_medium','utm_campaign','utm_term','utm_content',
                      'ref_','ref','fbclid','gclid','_ga','mc_eid','mc_cid'}
            _qs_clean = {k: v for k, v in _qs.items() if k.lower() not in _STRIP}
            url = _uu((_parsed.scheme, _parsed.netloc, _parsed.path,
                       _parsed.params, _ue(_qs_clean, doseq=True), _parsed.fragment))
            print(f"[web_engine] Cleaned URL: {url}")
        except Exception as _ue2:
            print(f"[web_engine] UTM strip failed: {_ue2}")

        # 0. Setup Dimensions (for image scaling in parse_xml_element)
        ps = letter if paper_size == 'letter' else legal
        self.max_width = ps[0] - 100 # 50px margin each side
        self.max_height = ps[1] - 150 # Increased safety margin (from 100) to account for spacers/headers

        # 1. Apply Styles Config
        if style_config:
            try:
                config = json.loads(style_config)
                def hex_to_color(h):
                    if not h or not h.startswith('#'): return colors.black
                    return colors.HexColor(h)

                # H1 (snake_case from collectConfig, camelCase fallback for legacy)
                self.styles['UnifranzTitle'].fontSize = int(config.get('h1_size') or config.get('h1Size', 26))
                self.styles['UnifranzTitle'].textColor = hex_to_color(config.get('h1_color') or config.get('h1Color', '#000000'))

                # H2
                self.styles['UnifranzH2'].fontSize = int(config.get('h2_size') or config.get('h2Size', 17))
                h2_col = config.get('h2_color') or config.get('h2Color', '#ef4444')
                self.styles['UnifranzH2'].textColor = hex_to_color(h2_col)
                self.styles['UnifranzH2'].borderColor = hex_to_color(h2_col)

                # Body
                font_name = config.get('font_name') or config.get('fontPrompt', 'Helvetica')
                if font_name == 'Calibri': font_name = 'Helvetica'  # Fallback

                font_size = int(config.get('font_size') or config.get('fontSize', 11))
                line_spacing_raw = config.get('line_spacing') or config.get('lineSpacing', 1.5)
                line_spacing = float(line_spacing_raw) if line_spacing_raw else 1.5

                self.styles['UnifranzBody'].fontName = font_name
                self.styles['UnifranzBody'].fontSize = font_size
                self.styles['UnifranzBody'].leading = font_size * line_spacing

                # Link Color
                self.link_hex = config.get('link_color') or config.get('linkColor', '#ef4444')

                # Text Alignment
                align_map = {'justify': TA_JUSTIFY, 'left': TA_LEFT, 'center': TA_CENTER, 'right': TA_RIGHT}
                text_align = config.get('text_alignment') or config.get('textAlignment', 'justify')
                self.styles['UnifranzBody'].alignment = align_map.get(text_align, TA_JUSTIFY)

                # Layout Config
                self.header_type = config.get('header_type') or config.get('headerType', 'title')
                self.header_text = config.get('header_text') or config.get('headerText', '')
                self.page_num_format = config.get('page_num_format') or config.get('pageNumFormat', 'page_n_of_m')
                # header_text_enabled: None/missing → True (default on); explicit False → off
                _hte = config.get('header_text_enabled')
                self.header_text_enabled = True if _hte is None else bool(_hte)
                self._style_config = config  # Store for table rendering

                # Margins (pt)
                self.margin_top    = int(config.get('margin_top')    or config.get('marginTop',    50))
                self.margin_bottom = int(config.get('margin_bottom') or config.get('marginBottom', 50))
                self.margin_left   = int(config.get('margin_left')   or config.get('marginLeft',   50))
                self.margin_right  = int(config.get('margin_right')  or config.get('marginRight',  50))

                # Header Image (base64): snake_case key from collectConfig + image store
                self.header_image_b64 = config.get('header_imagen') or config.get('headerImageB64', None)
                self.header_image_height = int(config.get('header_img_height') or config.get('headerImageHeight', 40))
                if self.header_image_b64:
                    print(f"[web_engine] Header image received ({len(self.header_image_b64)} chars)")

                # Cover Page (Carátula)
                self.caratula_enabled = config.get('caratula_enabled', False)
                self.caratula_titulo = config.get('caratula_titulo', '')
                self.caratula_autor = config.get('caratula_autor', '')
                self.caratula_institucion = config.get('caratula_institucion', '')
                self.caratula_fecha = config.get('caratula_fecha', '')
                self.caratula_imagen = config.get('caratula_imagen', None)
                self.caratula_title_size = int(config.get('caratula_title_size', 20))
                self.caratula_autor_size = int(config.get('caratula_autor_size', 13))
                self.caratula_title_color = config.get('caratula_title_color', '#000000')
                self.caratula_autor_color = config.get('caratula_autor_color', '#333333')
                # Position values (percentage of page, CSS convention: top=0 is top of page)
                self.caratula_title_x = float(config.get('caratula_title_x', 50)) / 100.0
                self.caratula_title_y = float(config.get('caratula_title_y', 50)) / 100.0
                self.caratula_inst_y = float(config.get('caratula_inst_y', 15)) / 100.0
                self.caratula_autor_y = float(config.get('caratula_autor_y', 58)) / 100.0
                self.caratula_fecha_y = float(config.get('caratula_fecha_y', 65)) / 100.0
                if self.caratula_enabled:
                    print(f"[web_engine] Cover page enabled (image: {'yes' if self.caratula_imagen else 'no'}, title_pos: {self.caratula_title_x:.0%},{self.caratula_title_y:.0%})")

                # Contratapa (Back Cover)
                self.contratapa_enabled = config.get('contratapa_enabled', False)
                self.contratapa_imagen = config.get('contratapa_imagen', None)
                if self.contratapa_enabled:
                    print(f"[web_engine] Back cover enabled (image: {'yes' if self.contratapa_imagen else 'no'})")

            except Exception as e:
                print(f"Error applying style config: {e}")
                self.link_hex = '#ef4444'
                self.header_type = 'title'
                self.header_text = ''
                self.page_num_format = 'page_n_of_m'
                self.margin_top = 50
                self.margin_bottom = 50
                self.margin_left = 50
                self.margin_right = 50
                self.header_image_b64 = None
                self.header_image_height = 40
                self.caratula_enabled = False
                self.contratapa_enabled = False
        else:
             self.link_hex = '#ef4444'
             self.header_type = 'title'
             self.header_text = ''
             self.page_num_format = 'page_n_of_m'
             self.margin_top = 50
             self.margin_bottom = 50
             self.margin_left = 50
             self.margin_right = 50
             self.header_image_b64 = None
             self.header_image_height = 40
             self.caratula_enabled = False
             self.contratapa_enabled = False

        if progress_callback: progress_callback(10, "Iniciando motor de transformación web...")

        # 2. Extract Content using Trafilatura
        try:
            if progress_callback: progress_callback(15, "Descargando contenido...")
            
            # Primary: Trafilatura native fetch
            downloaded = trafilatura.fetch_url(url)
            
            # Fallback: requests.Session with full browser headers (for sites like PCMag that block scrapers)
            if not downloaded:
                if progress_callback: progress_callback(20, "Reintentando descarga con método alternativo...")
                try:
                    session = requests.Session()
                    # Aggressive browser impersonation headers
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0',
                        'Referer': 'https://www.google.com/',
                    })
                    resp = session.get(url, timeout=25, allow_redirects=True)
                    if resp.status_code == 200:
                        # Force UTF-8 for sites known to have encoding issues
                        _force_utf8_domains = ['scielo.org', 'redalyc.org']
                        if any(d in url for d in _force_utf8_domains):
                            resp.encoding = 'utf-8'
                        downloaded = resp.text
                    else:
                        # Detect Cloudflare specifically by headers or body
                        is_cf = (
                            'cf-ray' in resp.headers or
                            'cloudflare' in resp.headers.get('server', '').lower() or
                            'cloudflare' in resp.text.lower()[:2000] or
                            resp.status_code in (403, 503) and 'challenge' in resp.text.lower()[:2000]
                        )
                        if is_cf:
                            if progress_callback: progress_callback(25, "Cloudflare detectado — usando navegador para bypass...")
                            print(f"Cloudflare detected on {url}, trying Playwright bypass...")
                        else:
                            print(f"Fallback HTTP {resp.status_code} for {url}")
                except Exception as fe:
                    print(f"Fallback fetch error: {fe}")
            
            # ── Playwright Cloudflare bypass ────────────────────────────
            if not downloaded:
                try:
                    if progress_callback: progress_callback(25, "Intentando con navegador real...")
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as pw:
                        browser = pw.chromium.launch(headless=False)
                        ctx = browser.new_context(
                            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                            viewport={'width': 1280, 'height': 800}
                        )
                        page = ctx.new_page()
                        page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        # Wait for Cloudflare challenge to resolve (up to 15s)
                        import time as _time
                        for _ in range(30):
                            _time.sleep(0.5)
                            page_text = page.content()
                            # Check if challenge is resolved (real content appeared)
                            if '<article' in page_text or '<main' in page_text or len(page_text) > 5000:
                                if 'challenge-platform' not in page_text and 'cf-challenge' not in page_text:
                                    break
                        # Scroll through the page to trigger lazy-loaded images
                        try:
                            page.evaluate("""async () => {
                                const delay = ms => new Promise(r => setTimeout(r, ms));
                                for (let i = 0; i < document.body.scrollHeight; i += 400) {
                                    window.scrollTo(0, i);
                                    await delay(100);
                                }
                                window.scrollTo(0, 0);
                            }""")
                            _time.sleep(1)
                        except: pass
                        # Capture cookies for image downloads (includes cf_clearance)
                        try:
                            pw_cookies = ctx.cookies()
                            self._pw_cookies = {c['name']: c['value'] for c in pw_cookies}
                            print(f"[web_engine] Captured {len(self._pw_cookies)} cookies from Playwright session")
                        except:
                            self._pw_cookies = {}
                        downloaded = page.content()
                        browser.close()
                    if downloaded:
                        print(f"Playwright bypass successful ({len(downloaded)} chars)")
                except Exception as pw_cf_err:
                    print(f"Playwright Cloudflare bypass error: {pw_cf_err}")
            
            if not downloaded:
                raise Exception("CLOUDFLARE: No se pudo acceder al sitio. Intente con otra URL.")
                
            # Extract structured XML with Images and Formatting
            if progress_callback: progress_callback(35, "Analizando estructura XML...")
            result_xml = trafilatura.extract(downloaded, output_format='xml', include_comments=False, include_tables=True, include_images=True, include_formatting=True, include_links=True)

            # ── Content quality gate ────────────────────────────────────────────
            # Discard Trafilatura result if it only captured noise (security banners,
            # cookie notices, HTTPS warnings, etc.) instead of real article content.
            if result_xml:
                import xml.etree.ElementTree as _ET2
                try:
                    _root2 = _ET2.fromstring(result_xml)
                    _text2 = ' '.join(_root2.itertext()).strip()
                    _noise_phrases = [
                        'protocolo https', 'candado en la barra', 'dominio .gob',
                        'portal oficial', 'información sensible', 'cookie', 'cookies',
                        'we use cookies', 'accept cookies', 'privacy policy',
                        'javascript is required', 'enable javascript',
                        'please enable', 'navegador no soporta',
                    ]
                    _is_noise = (
                        len(_text2) < 300 or
                        any(phrase in _text2.lower() for phrase in _noise_phrases)
                    )
                    if _is_noise:
                        print(f"Trafilatura result discarded (noise/too short: {len(_text2)} chars). Triggering BS4 fallback.")
                        result_xml = None
                except Exception:
                    pass  # If XML parse fails here, keep result_xml as-is

            # ── RETRY: trafilatura with browser-UA fetched HTML ────────────────
            # Some sites (e.g. emprendepyme.net) return HTML to trafilatura's
            # default UA but trafilatura heuristics return None. A real browser
            # User-Agent fetch gives richer/different HTML that trafilatura can parse.
            if not result_xml:
                try:
                    print("Trafilatura XML extraction failed. Re-fetching with browser UA for retry...")
                    if progress_callback: progress_callback(36, "Reintentando con cabeceras de navegador...")
                    _retry_session = requests.Session()
                    _retry_session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8',
                        'Referer': 'https://www.google.com/',
                    })
                    _retry_resp = _retry_session.get(url, timeout=20, allow_redirects=True)
                    if _retry_resp.status_code == 200 and len(_retry_resp.text) > 500:
                        _retry_html = _retry_resp.text
                        result_xml = trafilatura.extract(
                            _retry_html,
                            output_format='xml',
                            include_comments=False, include_tables=True,
                            include_images=True, include_formatting=True,
                            include_links=True,
                            favor_recall=True       # More lenient — catches more content
                        )
                        if result_xml:
                            print(f"Browser-UA retry SUCCESS ({len(result_xml)} chars XML)")
                            # Replace downloaded with better HTML for BS4 fallback if still needed
                            downloaded = _retry_html
                        else:
                            print("Browser-UA retry also returned None — falling back to BS4")
                except Exception as _retry_err:
                    print(f"Browser-UA retry error: {_retry_err}")

            # ── FALLBACK: BeautifulSoup content extractor ──────────────────────

            # Trafilatura sometimes fails on JS-heavy or non-standard sites.
            # Strategy 1: JSON-LD embedded data (Zendesk, WildApricot, Intercom, etc.)
            # Strategy 2: Semantic HTML container scraping
            bs4_fallback_used = False
            if not result_xml:
                print("Trafilatura XML extraction failed. Trying BeautifulSoup content fallback...")
                if progress_callback: progress_callback(38, "Extractor alternativo (BS4)...")
                try:
                    from bs4 import BeautifulSoup as BS4

                    bs4_items = []

                    # ── Strategy 1: JSON-LD embedded content ──────────────────
                    json_ld_blocks = re.findall(
                        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                        downloaded, re.DOTALL | re.IGNORECASE
                    )
                    for jblock in json_ld_blocks:
                        try:
                            jdata = json.loads(jblock.strip())
                            # Pattern A: mainEntity[].acceptedAnswer.text (WildApricot, FAQ schemas)
                            entities = jdata.get('mainEntity', [])
                            if isinstance(entities, dict):
                                entities = [entities]
                            for entity in entities:
                                raw_ans = entity.get('acceptedAnswer')
                                ans = raw_ans if isinstance(raw_ans, dict) else {}
                                html_text = ans.get('text', '') or entity.get('text', '')
                                if html_text and len(html_text) > 100:
                                    inner = BS4(html_text, 'html.parser')
                                    html_elements = inner.find_all(['h1','h2','h3','h4','p','li','table'])
                                    if html_elements:
                                        # Has real HTML structure — parse normally
                                        for el in html_elements:
                                            t = el.get_text(separator=' ', strip=True)
                                            tag = el.name
                                            if tag in ('h1','h2','h3','h4') and len(t) > 2:
                                                bs4_items.append({'type': 'header', 'level': int(tag[1]), 'text': t})
                                            elif tag == 'p' and len(t) > 20:
                                                bs4_items.append({'type': 'paragraph', 'text': t})
                                            elif tag == 'li' and len(t) > 3:
                                                bs4_items.append({'type': 'list_item', 'text': t})
                                            elif tag == 'table':
                                                rows_data = []
                                                has_header = bool(el.find('th'))
                                                for tr in el.find_all('tr'):
                                                    cells = [td.get_text(strip=True) for td in tr.find_all(['td','th'])]
                                                    if cells: rows_data.append(cells)
                                                if rows_data:
                                                    bs4_items.append({'type': 'table', 'rows': rows_data, 'has_header': has_header})
                                    else:
                                        # Plain text content (WildApricot style) — one giant line
                                        raw = inner.get_text(separator=' ', strip=True)
                                        # Strip CSS blocks like #toc { ... }
                                        raw = _re.sub(r'#[^\{]+\{[^}]+\}', '', raw)
                                        raw = _re.sub(r'\{[^}]+\}', '', raw)
                                        raw = raw.replace('\xa0', ' ')
                                        # Remove "On this page:" TOC section
                                        raw = _re.sub(r'On this page:.*?(?=[A-Z][a-z]{3,}\s+[a-z])', '', raw, flags=_re.DOTALL)
                                        # Insert newlines before numbered steps "1. " "2. "
                                        raw = _re.sub(r'(?<!\d)(\d{1,2}\.\s+[A-Z])', r'\n\1', raw)
                                        # Insert newlines before sentence boundaries
                                        raw = _re.sub(r'([.!?])\s+([A-Z][a-z])', r'\1\n\2', raw)
                                        # Insert newlines before ALL-CAPS section words (e.g. "Inserting a table")
                                        raw = _re.sub(r'([a-z])\s+([A-Z][a-z]{3,}\s+[a-z])', r'\1\n\2', raw)

                                        lines = [l.strip().lstrip('•·–-').strip() for l in raw.split('\n')]

                                        for line in lines:
                                            line = line.strip()
                                            if not line or len(line) < 15:
                                                continue

                                            # Detect section headings: short line (< 60 chars), no period at end,
                                            # starts with capital, not a numbered step
                                            is_numbered = bool(_re.match(r'^\d{1,2}\.\s', line))
                                            is_heading = (
                                                not is_numbered and
                                                len(line) < 65 and
                                                not line.endswith('.') and
                                                not line.endswith(',') and
                                                line[0].isupper() and
                                                not line.startswith('Note:') and
                                                not line.startswith('Important')
                                            )

                                            if is_heading:
                                                bs4_items.append({'type': 'header', 'level': 2, 'text': line})
                                            elif is_numbered:
                                                bs4_items.append({'type': 'list_item', 'text': line})
                                            elif len(line) > 30:
                                                bs4_items.append({'type': 'paragraph', 'text': line})




                            # Pattern B: articleBody (Article schema)
                            article_body = jdata.get('articleBody', '')
                            if article_body and len(article_body) > 100 and not bs4_items:
                                inner = BS4(article_body, 'html.parser')
                                html_elements = inner.find_all(['h1','h2','h3','h4','p','li'])
                                if html_elements:
                                    for el in html_elements:
                                        t = el.get_text(separator=' ', strip=True)
                                        tag = el.name
                                        if tag in ('h1','h2','h3','h4') and len(t) > 2:
                                            bs4_items.append({'type': 'header', 'level': int(tag[1]), 'text': t})
                                        elif tag == 'p' and len(t) > 20:
                                            bs4_items.append({'type': 'paragraph', 'text': t})
                                        elif tag == 'li' and len(t) > 3:
                                            bs4_items.append({'type': 'list_item', 'text': t})
                                else:
                                    text = inner.get_text(separator='\n', strip=True)
                                    for para in text.split('\n'):
                                        para = para.strip()
                                        if len(para) > 20:
                                            bs4_items.append({'type': 'paragraph', 'text': para})

                        except Exception as jld_err:
                            print(f"JSON-LD parse error: {jld_err}")

                    # ── Inject images from HTML after JSON-LD text extraction ──
                    # JSON-LD text has no images; scrape them from the actual HTML
                    if bs4_items:
                        try:
                            img_soup = BS4(downloaded, 'html.parser')
                            # Find content container
                            img_container = (
                                img_soup.find('article') or
                                img_soup.find('main') or
                                img_soup.find(id='content') or
                                img_soup.find(class_='article-body') or
                                img_soup.find(class_='content') or
                                img_soup.body
                            )
                            if img_container:
                                for img_tag in img_container.find_all('img'):
                                    src = img_tag.get('src', '') or img_tag.get('data-src', '')
                                    if not src or src.startswith('data:'):
                                        continue
                                    # Skip tiny icons (width/height attributes < 50)
                                    w = img_tag.get('width', '999')
                                    h = img_tag.get('height', '999')
                                    try:
                                        if int(str(w).replace('px','')) < 50 or int(str(h).replace('px','')) < 50:
                                            continue
                                    except (ValueError, TypeError):
                                        pass
                                    # Make absolute URL
                                    if src.startswith('//'):
                                        src = 'https:' + src
                                    elif src.startswith('/'):
                                        from urllib.parse import urlparse
                                        parsed = urlparse(url)
                                        src = f"{parsed.scheme}://{parsed.netloc}{src}"
                                    bs4_items.append({'type': 'image', 'src': src})
                        except Exception as img_err:
                            print(f"Image injection error: {img_err}")



                    # ── Strategy 2: Semantic HTML container scraping ───────────
                    if len(bs4_items) < 3:
                        soup = BS4(downloaded, 'html.parser')
                        # Remove noise elements
                        for tag in soup(['script','style','nav','footer','header',
                                         'aside','form','noscript','iframe','svg',
                                         'button']):
                            tag.decompose()

                        # Find best content container (ordered by priority)
                        # Domain-specific selector overrides for known difficult sites
                        _netloc = _up(url).netloc.lower().replace('www.', '')
                        _DOMAIN_SELECTORS = {
                            # SciELO: content in div with class literally 'index,es' (comma in class name)
                            # Use a special tuple ('fn','scielo_index') handled below
                            'scielo.org': [('fn','scielo_index'), ('id','content'), ('class','content')],
                            'redalyc.org': [('id','articulo-body'), ('id','articulo'), ('class','articleFullText'), ('id','articleBody')],
                            'pubcalidad.pucp.edu.pe': [('class','entry-content'), ('class','post-content')],
                            'calidad.pucp.edu.pe': [('class','entry-content'), ('class','post-content'), ('class','col-content')],
                            'docusign.com': [('class','blog-content'), ('class','article-content'), ('class','content-body')],
                            'aboutamazon': [('class','article-content'), ('class','content'), ('id','article-content')],
                            'advertising.amazon.com': [('class','content-body'), ('class','article-body'), ('id','main-content')],
                            'aws.amazon.com': [('id','main-content'), ('class','blog-post'), ('class','content')],
                            'quickbooks.intuit.com': [('class','blog-post'), ('class','article-content'), ('class','post-content')],
                            '1library.co': [('class','document-content'), ('class','article'), ('id','content')],
                            'linkedin.com': [('class','article-content'), ('class','feed-shared-update-v2'), ('class','reader-article-content')],
                            'facebook.com': [('role','main'), ('class','_4-u2'), ('id','content')],
                        }
                        _ds_container = None
                        for _domain_key, _selectors in _DOMAIN_SELECTORS.items():
                            if _domain_key in _netloc:
                                for _attr, _val in _selectors:
                                    if _attr == 'fn' and _val == 'scielo_index':
                                        # SciELO special: class 'index,es' has a comma (not standard CSS)
                                        _ds_container = soup.find(
                                            lambda t: t.name == 'div' and
                                            t.get('class') and
                                            any('index' in c for c in t.get('class', []))
                                        )
                                        if not _ds_container:
                                            _ds_container = soup.body
                                    elif _attr == 'id':
                                        _ds_container = soup.find(id=_val)
                                    elif _attr == 'class':
                                        _ds_container = soup.find(class_=_val)
                                    elif _attr == 'role':
                                        _ds_container = soup.find(attrs={'role': _val})
                                    if _ds_container:
                                        print(f"[web_engine] Domain-specific container matched: {_attr}={_val} for {_domain_key}")
                                        break
                                if _ds_container:
                                    break

                        container = (
                            _ds_container or
                            soup.find('article') or
                            soup.find('main') or
                            # Academic journals & institutional sites
                            soup.find(id='articleBody') or
                            soup.find(id='article-body') or
                            soup.find(class_='articleFullText') or
                            soup.find(class_='article-full-text') or
                            soup.find(class_='article-content') or
                            soup.find(class_='jnl-article-body') or
                            soup.find(class_='full-text') or
                            soup.find(class_='content-body') or
                            soup.find(class_='blog-content') or
                            soup.find(class_='blog-post') or
                            soup.find(class_='post-body') or
                            soup.find('div', attrs={'itemprop': 'articleBody'}) or
                            soup.find('section', attrs={'aria-label': True}) or
                            # Generic fallbacks
                            soup.find(id='content') or
                            soup.find(id='main-content') or
                            soup.find(class_='article-body') or
                            soup.find(class_='post-content') or
                            soup.find(class_='entry-content') or
                            soup.find(class_='content') or
                            soup.find(class_='page-content') or
                            soup.find('div', {'role': 'main'}) or
                            soup.body
                        )

                        if container:
                            for el in container.find_all(['h1','h2','h3','h4','p','ul','ol','li','table','img'], recursive=True):
                                tag = el.name
                                text = el.get_text(separator=' ', strip=True)
                                if not text and tag != 'img':
                                    continue

                                if tag in ('h1','h2','h3','h4'):
                                    level = int(tag[1])
                                    if len(text) > 2:
                                        bs4_items.append({'type': 'header', 'level': level, 'text': text})
                                elif tag == 'p':
                                    if len(text) > 20:
                                        # Use markup-preserving converter for paragraphs
                                        markup = self.bs4_to_reportlab_markup(el)
                                        bs4_items.append({'type': 'paragraph', 'text': markup})
                                elif tag == 'li':
                                    if len(text) > 3:
                                        markup = self.bs4_to_reportlab_markup(el)
                                        bs4_items.append({'type': 'list_item', 'text': markup})
                                elif tag == 'table':
                                    rows_data = []
                                    has_header = bool(el.find('th'))
                                    for tr in el.find_all('tr'):
                                        cells = [td.get_text(strip=True) for td in tr.find_all(['td','th'])]
                                        if cells:
                                            rows_data.append(cells)
                                    if rows_data:
                                        bs4_items.append({'type': 'table', 'rows': rows_data, 'has_header': has_header})
                                elif tag == 'img':
                                    src = el.get('src', '')
                                    if src and not src.startswith('data:'):
                                        bs4_items.append({'type': 'image', 'src': src})


                    # ── Strategy 3: Playwright headless browser (JS-rendered sites) ──
                    # Fires when static HTML has no content (e.g. WildApricot, Zendesk)
                    if len(bs4_items) < 3:
                        if progress_callback: progress_callback(40, "Renderizando con navegador...")
                        print("Static HTML empty — trying Playwright headless browser...")
                        try:
                            from playwright.sync_api import sync_playwright
                            from urllib.parse import urlparse as _urlparse
                            _parsed_url = _urlparse(url)
                            _base = f"{_parsed_url.scheme}://{_parsed_url.netloc}"
                            with sync_playwright() as pw:
                                browser = pw.chromium.launch(headless=True)
                                page = browser.new_page()
                                page.set_extra_http_headers({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
                                page.goto(url, wait_until='networkidle', timeout=20000)
                                try:
                                    page.wait_for_selector('article, main, [class*="article"], [class*="content"]', timeout=5000)
                                except Exception:
                                    pass
                                rendered_html = page.content()
                                browser.close()
                            pw_soup = BS4(rendered_html, 'html.parser')
                            for noise in pw_soup(['script','style','nav','footer','header','aside','form','noscript','iframe','svg','button']):
                                noise.decompose()
                            pw_container = (
                                pw_soup.find('article') or pw_soup.find('main') or
                                pw_soup.find(id='content') or pw_soup.find(id='main-content') or
                                pw_soup.find(class_='article-body') or pw_soup.find(class_='post-content') or
                                pw_soup.find(class_='entry-content') or pw_soup.find(class_='content') or
                                pw_soup.find('div', {'role': 'main'}) or pw_soup.body
                            )
                            if pw_container:
                                for el in pw_container.find_all(['h1','h2','h3','h4','p','ul','ol','li','table','img'], recursive=True):
                                    tag = el.name
                                    text = el.get_text(separator=' ', strip=True)
                                    if tag in ('h1','h2','h3','h4'):
                                        if len(text) > 2:
                                            bs4_items.append({'type': 'header', 'level': int(tag[1]), 'text': text})
                                    elif tag == 'p':
                                        if len(text) > 20:
                                            markup = self.bs4_to_reportlab_markup(el)
                                            bs4_items.append({'type': 'paragraph', 'text': markup})
                                    elif tag == 'li':
                                        if len(text) > 3:
                                            markup = self.bs4_to_reportlab_markup(el)
                                            bs4_items.append({'type': 'list_item', 'text': markup})
                                    elif tag == 'table':
                                        rows_data = []
                                        has_header = bool(el.find('th'))
                                        for tr in el.find_all('tr'):
                                            cells = [td.get_text(strip=True) for td in tr.find_all(['td','th'])]
                                            if cells: rows_data.append(cells)
                                        if rows_data:
                                            bs4_items.append({'type': 'table', 'rows': rows_data, 'has_header': has_header})
                                    elif tag == 'img':
                                        src = el.get('src','') or el.get('data-src','')
                                        if not src or src.startswith('data:'): continue
                                        w = el.get('width','999'); h_attr = el.get('height','999')
                                        try:
                                            if int(str(w).replace('px','')) < 50 or int(str(h_attr).replace('px','')) < 50: continue
                                        except (ValueError, TypeError): pass
                                        if src.startswith('//'): src = 'https:' + src
                                        elif src.startswith('/'): src = _base + src
                                        bs4_items.append({'type': 'image', 'src': src})
                                print(f"Playwright extracted {len(bs4_items)} items")
                        except Exception as pw_err:
                            print(f"Playwright fallback error: {pw_err}")

                    if len(bs4_items) >= 3:  # Minimum viable content
                        # --- BATCH TRANSLATE BEFORE FINALIZING ---
                        bs4_items = self.batch_translate_bs4_items(bs4_items, progress_callback)
                        
                        result_xml = '__BS4_CONTENT__'  # Sentinel to skip XML parse
                        bs4_fallback_used = True
                        bs4_content_items = bs4_items
                        if progress_callback: progress_callback(47, "BS4_FALLBACK: Contenido traducido y formateado")
                        print(f"BS4 fallback: extracted and translated {len(bs4_items)} items")

                except Exception as bs4_err:
                    import traceback
                    print(f"BS4 fallback error: {bs4_err}")
                    traceback.print_exc()

            if not result_xml:
                raise Exception("No se pudo extraer texto legible del sitio (ni con método alternativo).")
                 
            # Extract Metadata (Title)
            # When BS4 fallback was used, prefer the first header from extracted content
            title = None
            if bs4_fallback_used and bs4_content_items:
                for item in bs4_content_items:
                    if item.get('type') == 'header' and len(item.get('text', '')) > 3:
                        title = item['text']  # Already translated
                        break

            if not title:
                metadata = trafilatura.bare_extraction(downloaded)
                if metadata:
                    if isinstance(metadata, dict):
                        title = metadata.get('title')
                    else:
                        title = getattr(metadata, 'title', None)
            
            # Validate Title — reject generic site names and short strings
            invalid_titles = ['key takeaways', 'conclusion', 'introduction', 'table of contents', 'conclusiones clave']
            
            is_valid_title = False
            if title and len(title.strip()) > 3:
                is_valid_title = True
                if title.lower() in invalid_titles:
                    is_valid_title = False
            
            # Fallback: BeautifulSoup for Title if Trafilatura failed or gave a bad title
            if not is_valid_title:
                 print("Trafilatura title missing or invalid. Trying BeautifulSoup fallback...")
                 try:
                     # Force UTF-8 for sites known to have encoding issues
                     _raw_bytes = downloaded.encode('latin-1', errors='replace') if isinstance(downloaded, str) else downloaded
                     _enc_domains = ['scielo.org', 'redalyc.org']
                     _cur_domain = _up(url).netloc.lower()
                     if any(d in _cur_domain for d in _enc_domains):
                         try:
                             downloaded = _raw_bytes.decode('utf-8', errors='replace')
                         except Exception:
                             pass
                     soup = BeautifulSoup(downloaded, 'html.parser')
                     
                     # 1. OpenGraph
                     og_title = soup.find("meta", property="og:title")
                     if og_title and og_title.get("content"):
                         title = og_title["content"]
                     
                     # 2. Twitter Card
                     if not title:
                        tw_title = soup.find("meta", name="twitter:title")
                        if tw_title and tw_title.get("content"):
                            title = tw_title["content"]

                     # 3. Standard <title>
                     if not title and soup.title:
                         title = soup.title.string
                         
                     # 4. H1
                     if not title:
                         h1 = soup.find('h1')
                         if h1: title = h1.get_text()

                 except Exception as ex:
                     print(f"BS4 Fallback Error: {ex}")

            if not title:
                title = "Documento Web"

            # ── Clean title: strip trailing site-name suffixes ────────────────
            # Examples: "Article – SciELO", "Blog Post | PUCP", "Name :: Redalyc"
            _sep_pattern = r'\s*[|\-–—::]+\s*.{2,40}$'
            for _ in range(3):  # Strip up to 3 nested suffixes
                _cleaned = re.sub(_sep_pattern, '', title).strip()
                if _cleaned and _cleaned != title and len(_cleaned) > 10:
                    title = _cleaned
                else:
                    break
            # Also strip common site-name words at the end regardless of separator
            _site_suffixes = [
                r'\s+[-–]?\s*(scielo|redalyc|pucp|1library|amazon|docusign|facebook|linkedin|atlasgov|spiderstrategies|parkinsonre)\b.*$',
            ]
            for pat in _site_suffixes:
                title = re.sub(pat, '', title, flags=re.IGNORECASE).strip()
            
            # Translate Title (skip if already translated via BS4 fallback header)
            if title and not bs4_fallback_used:
                original_title = title
                title = self.translate_text(original_title)
            elif title and bs4_fallback_used:
                # Only translate if title came from Trafilatura/HTML (not from bs4_content_items header)
                first_bs4_header = next((i['text'] for i in bs4_content_items if i.get('type') == 'header'), None)
                if title != first_bs4_header:
                    title = self.translate_text(title)


        except Exception as e:
            raise Exception(f"Eror en extracción: {str(e)}")

        # 3. Build PDF
        pdf_buffer = io.BytesIO()
        ps = letter if paper_size == 'letter' else legal

        def draw_header_footer(canvas, doc):
            canvas.saveState()
            
            # --- Header Image ---
            header_y_bottom = ps[1] - 25  # Default separator position
            if self.header_image_b64:
                try:
                    import base64
                    # Strip data URI prefix if present
                    b64_data = self.header_image_b64
                    if ',' in b64_data:
                        b64_data = b64_data.split(',', 1)[1]
                    img_bytes = base64.b64decode(b64_data)
                    img_buf = io.BytesIO(img_bytes)
                    img_h = self.header_image_height
                    # Detect aspect ratio to set width
                    from reportlab.lib.utils import ImageReader
                    reader = ImageReader(img_buf)
                    iw, ih = reader.getSize()
                    aspect = iw / float(ih) if ih > 0 else 2.0
                    # Full bleed: edge to edge, no margins
                    img_w = ps[0]
                    img_h = img_w / aspect
                    # Draw flush to very top of page
                    img_x = 0
                    img_y = ps[1] - img_h  # Top edge of page
                    img_buf.seek(0)
                    canvas.drawImage(ImageReader(img_buf), img_x, img_y, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
                    header_y_bottom = img_y - 3
                except Exception as himg_err:
                    print(f"[web_engine] Header image render error: {himg_err}")
            
            # --- Header Text ---
            header_text_enabled = getattr(self, 'header_text_enabled', True)
            header_text = ""
            if header_text_enabled:
                if self.header_type == 'title':
                    header_text = title
                elif self.header_type == 'custom':
                    header_text = self.header_text

            if header_text:
                canvas.setFont('Helvetica', 9)
                canvas.setFillColor(colors.gray)
                canvas.drawCentredString(ps[0]/2, ps[1] - 25, header_text)
                canvas.setStrokeColor(colors.lightgrey)
                canvas.line(self.margin_left, ps[1] - 30, ps[0] - self.margin_right, ps[1] - 30)
            
            # --- Page Number ---
            page_num = canvas.getPageNumber()
            p_text = f"{page_num}"
            
            if self.page_num_format == 'page_n':
                p_text = f"Página {page_num}"
            elif self.page_num_format == 'page_n_of_m':
                 # Single pass limitation: Just "Página X" for now to avoid rendering artifacts
                p_text = f"Página {page_num}"
            elif self.page_num_format == 'n_of_m':
                 p_text = f"{page_num}"
            elif self.page_num_format == 'none':
                p_text = ""
                
            if p_text:
                canvas.setFont('Helvetica', 9)
                canvas.setFillColor(colors.black)
                canvas.drawRightString(ps[0] - 50, 30, p_text)
                
            canvas.restoreState()

        # Use strict top margin as requested (do not add header image offset)
        effective_top_margin = self.margin_top

        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=ps,
            rightMargin=self.margin_right, leftMargin=self.margin_left,
            topMargin=effective_top_margin, bottomMargin=self.margin_bottom,
            title=title
        )

        story = []

        # -- Main Title --
        # If header enabled as 'title', maybe we don't need H1? 
        # No, H1 is body content. Header is navigation. Keep both.
        story.append(Paragraph(title.upper(), self.styles['UnifranzTitle']))
        story.append(Spacer(1, 20))
        
        # Build with callbacks
        # We assign the builder later, but here we just prepare the story.
        # Wait, doc.build is called at the end.
        # I need to find where doc.build is called.
        # It's at the end of the method usually.
        # I'll search for it.
        # This block only replaces definition. I need to make sure I use `draw_header_footer` in `doc.build`.
        # I will define `draw_header_footer` here.
        # And I need to update the `doc.build` call which is likely further down.
        # I will replace `add_page_number` function definition here.
        
        # NOTE: I am ONLY replacing the definition here. I must also find `doc.build` and update it.
        # Or I can include `doc.build` in this replacement if it's close? 
        # `doc.build` is typically at the end of the function.
        # I'll check where `add_page_number` was used.
        # It was likely used in `doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)`.
        # So I need to find that line.
        
        pass # Placeholder for next replacement step if needed, but I'll define it here.

        # -- Content Processing --
        try:
            if bs4_fallback_used:
                # BS4 already built content_items directly — skip XML parsing
                content_items = bs4_content_items
            else:
                root = ET.fromstring(result_xml)
                body = root.find('.//main') or root.find('.//body') or root
                content_items = self.parse_xml_element(body)

                # ── Supplement images from HTML (position-aware) ──────────────
                # Trafilatura often misses images. Scrape the original HTML
                # for content-area <img> tags and insert them at their correct
                # positions relative to surrounding text.
                try:
                    from urllib.parse import urljoin as _urljoin
                    existing_srcs = {i.get('src', '') for i in content_items if i.get('type') == 'image'}
                    soup_img = BeautifulSoup(downloaded, 'html.parser')
                    for noise in soup_img(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'svg']):
                        noise.decompose()
                    img_container = (
                        soup_img.find('article') or soup_img.find('main') or
                        soup_img.find(id='content') or soup_img.find(class_='entry-content') or
                        soup_img.find(class_='post-content') or soup_img.find(class_='article-body') or
                        soup_img.find(class_='content') or soup_img.body
                    )
                    if img_container:
                        # Walk DOM in order to map images to their preceding text
                        img_after_text = []  # List of (preceding_text_snippet, img_src)
                        last_text = ""
                        for el in img_container.find_all(['h1','h2','h3','h4','p','img'], recursive=True):
                            if el.name in ('h1','h2','h3','h4','p'):
                                t = el.get_text(strip=True)
                                if t and len(t) > 10:
                                    last_text = t[:60]
                            elif el.name == 'img':
                                src = el.get('src', '') or el.get('data-src', '') or el.get('data-lazy-src', '')
                                # Fallback to srcset (responsive images)
                                if (not src or src.startswith('data:')) and el.get('srcset'):
                                    srcset = el.get('srcset', '')
                                    # Take the last (largest) image from srcset
                                    parts = [s.strip().split()[0] for s in srcset.split(',') if s.strip()]
                                    if parts:
                                        src = parts[-1]
                                if not src or src.startswith('data:'):
                                    continue
                                if src.startswith('//'): src = 'https:' + src
                                elif src.startswith('/'): src = _urljoin(url, src)
                                # Skip tiny/ad images
                                w = el.get('width', '999'); h = el.get('height', '999')
                                try:
                                    if int(str(w).replace('px','')) < 80 or int(str(h).replace('px','')) < 80:
                                        continue
                                except (ValueError, TypeError): pass
                                skip_patterns = ['pixel','tracking','beacon','ad-','ads/','doubleclick','facebook.com/tr']
                                if any(p in src.lower() for p in skip_patterns):
                                    continue
                                if src not in existing_srcs:
                                    img_after_text.append((last_text, src))
                                    existing_srcs.add(src)

                        # Insert each extra image after the matching text in content_items
                        if img_after_text:
                            print(f"[web_engine] Injecting {len(img_after_text)} extra images (position-aware)")
                            new_items = list(content_items)
                            offset = 0
                            for preceding_text, img_src in img_after_text:
                                insert_pos = len(new_items)  # Default: end
                                if preceding_text:
                                    for idx, ci in enumerate(new_items):
                                        ci_text = ci.get('text', '')
                                        if ci_text and preceding_text[:40] in ci_text:
                                            insert_pos = idx + 1
                                            break
                                new_items.insert(insert_pos, {'type': 'image', 'src': img_src})
                            content_items = new_items
                except Exception as img_inject_err:
                    print(f"[web_engine] Image injection error: {img_inject_err}")

            
            # Ensure UnifranzCode style exists
            if 'UnifranzCode' not in self.styles:
                self.styles.add(ParagraphStyle(
                    name='UnifranzCode',
                    parent=self.styles['Normal'],
                    fontName='Courier',
                    fontSize=9,
                    leading=11,
                    textColor=colors.HexColor('#333333'),
                    backColor=colors.HexColor('#f5f5f5'),
                    borderPadding=10,
                    spaceAfter=15,
                    leftIndent=20,
                    rightIndent=20
                ))

            # ── POST-PROCESSING: Remove noise sections & ad images ─────────
            noise_section_keywords = [
                'faq', 'preguntas frecuentes', 'frequently asked',
                'related articles', 'artículos relacionados', 'related posts',
                'you might also like', 'también te puede interesar',
                'te puede interesar', 'puede interesarte',
                'índice de contenidos', 'tabla de contenidos', 'table of contents',
                'in this article', 'en este artículo',
                'more resources', 'más recursos', 'further reading',
                'before qwilr', 'after qwilr',
                'related reading', 'lecturas relacionadas',
                'recommended reading', 'lecturas recomendadas',
                # CTA / Promo headers
                'obtenga nuestra plantilla', 'get our template',
                'descargar plantilla', 'download template',
                'prueba gratis', 'free trial', 'start your free',
                'comience gratis', 'get started for free',
                'tome nuestra plantilla',
                'pruebe qwilr', 'try qwilr', 'herramienta de propuestas',
                'análisis de compradores', 'buyer analytics',
                'descubre hoy la magia',
                'mejora tus propuestas', 'las plantillas de qwilr',
                # Extra Spanish CTA phrases (ONLY unambiguous full-phrase CTAs)
                'obtén los cursos', 'obtén tu guía',
                'ver todos los cursos',
                'cursos relacionados', 'formación relacionada',
                'quiero saber más', 'pide información',
            ]
            ad_img_patterns = [
                # Unambiguous ad/tracking URL fragments only
                '/ads/', 'doubleclick.net', 'googlesyndication', 'amazon-adsystem',
                'facebook.com/tr', 'vhpgdzfc/production',
                'pixel.', 'tracking/', 'advertisement',
                '1x1.gif', '1x1.png', 'spacer.gif', 'blank.gif', 'transparent.png',
                '/popups/', '/overlays/', '/modals/',
            ]

            # Remove entire sections that start with a noise header
            filtered_items = []
            skip_until_level = None
            for ci_item in content_items:
                if not isinstance(ci_item, dict):
                    continue
                if ci_item.get('type') == 'header':
                    header_text_lower = ci_item.get('text', '').lower().strip()
                    header_level = ci_item.get('level', 2)
                    # Check if we're in a skip zone and hit a same/higher level header
                    if skip_until_level is not None:
                        if header_level <= skip_until_level:
                            skip_until_level = None  # Stop skipping
                        else:
                            continue  # Still inside noise section
                    # Check if this header starts a noise section
                    if any(nk in header_text_lower for nk in noise_section_keywords):
                        skip_until_level = header_level
                        print(f"[web_engine] Filtered noise section: '{ci_item.get('text', '')}'")
                        continue
                elif skip_until_level is not None:
                    continue  # Skip content inside noise section

                # Filter ad-like images by URL pattern
                if ci_item.get('type') == 'image':
                    img_src = ci_item.get('src', '').lower()
                    if any(pat in img_src for pat in ad_img_patterns):
                        print(f"[web_engine] Filtered ad image: {ci_item.get('src', '')[:80]}")
                        continue

                # Filter stray promotional paragraphs that don't start with a header
                if ci_item.get('type') in ('paragraph', 'list_item', 'text'):
                    p_text_lower = ci_item.get('text', '').lower().strip()
                    _clean_p = re.sub(r'<[^>]+>', '', p_text_lower).strip()
                    # Drop short UI navigation elements (≤ 6 words)
                    _word_count = len(_clean_p.split())
                    _UI_SUBSTRINGS = [
                        'descargar', 'compartir', 'imprimir',
                        'índice de contenidos', 'índice de', 'table of contents',
                        'back to top', 'volver arriba',
                        'log in', 'sign up', 'sign in',
                    ]
                    _UI_EXACT = {
                        'descargar', 'compartir', 'imprimir', 'guardar',
                        'ver más', 'leer más', 'continuar', 'siguiente', 'anterior',
                        'índice', 'download', 'share', 'print', 'save',
                        'volver', 'inicio', 'menu', 'navigation',
                        'suscríbete', 'regístrate', 'inicio de sesión',
                    }
                    is_ui = (
                        _clean_p in _UI_EXACT or
                        (_word_count <= 4 and any(s in _clean_p for s in _UI_SUBSTRINGS))
                    )
                    if is_ui:
                        print(f"[web_engine] Filtered UI element: '{_clean_p}'")
                        continue
                    if any(nk in p_text_lower for nk in noise_section_keywords):
                        print(f"[web_engine] Filtered stray noise text: '{ci_item.get('text', '')[:60]}'")
                        continue

                filtered_items.append(ci_item)

            # --- Trafilatura Duplicate Inline Text Fix ---
            final_items = []
            def _strip_html(t): return re.sub(r'<[^>]+>', '', t).strip()
            
            for i, item in enumerate(filtered_items):
                if item.get('type') in ('paragraph', 'text'):
                    p_text = item.get('text', '')
                    clean_p = _strip_html(p_text)
                    
                    if 0 < len(clean_p) < 40 and final_items:
                        prev_item = final_items[-1]
                        if prev_item.get('type') == 'header':
                            clean_prev = _strip_html(prev_item.get('text', ''))
                            # If paragraph perfectly matches the end of the preceding header
                            if clean_prev.endswith(clean_p):
                                print(f"[web_engine] Removed Trafilatura duplicate inline text: '{clean_p}'")
                                continue
                final_items.append(item)
                
            content_items = final_items

            # ── Filter academic metadata preamble (SciELO / Redalyc / journal style) ─────
            _ACAD_META_PATTERNS = [
                r'\bvol\.\s*\d+', r'\bnúm\.\s*\d+', r'\bnum\.\s*\d+',
                r'\bpp\.\s*\d+', r'\bpags?\.\s*\d+',
                r'\b(recepción|aprobación|received|accepted)\s*:',
                r'\b(artículo de|article type|tipo de artículo)',
                r'\b(fundación|universidad|college|institute)\b',
                r'\b\d{1,2}\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4}\b',
            ]
            def _is_acad_meta(text):
                t = re.sub(r'<[^>]+>', '', text).lower()
                return any(re.search(pat, t) for pat in _ACAD_META_PATTERNS)

            # Find first real header index after possible preamble
            _first_long_para_idx = next(
                (i for i, it in enumerate(content_items)
                 if it.get('type') in ('paragraph',) and len(_strip_html(it.get('text',''))) > 150),
                None
            )
            if _first_long_para_idx and _first_long_para_idx > 1:
                # Check if the block before the first long para is all metadata
                _preamble = content_items[:_first_long_para_idx]
                _acad_count = sum(1 for it in _preamble if _is_acad_meta(it.get('text','')))
                if _acad_count >= len(_preamble) * 0.5:  # >50% are metadata items
                    print(f"[web_engine] Stripped academic metadata preamble ({len(_preamble)} items)")
                    content_items = content_items[_first_long_para_idx:]

            # Sites like HubSpot, IEBSchool inject banners/CTA at the very top.
            first_header_idx = next(
                (i for i, it in enumerate(content_items) if it.get('type') == 'header'),
                None
            )
            if first_header_idx and first_header_idx > 0:
                lead = content_items[:first_header_idx]
                # CONSERVATIVE: Only strip items that are clearly UI buttons/CTAs
                # (short text that is ONLY a button label, no sentence context)
                _cta_lead_kws = [
                    'suscríbete', 'regístrate', 'sign up', 'free trial',
                    'descargar ahora', 'download now', 'get started',
                    'comienza gratis', 'empieza gratis', 'prueba gratis',
                ]
                trimmed_lead = []
                for li in lead:
                    t = _strip_html(li.get('text', '')).lower().strip()
                    # Only strip if: image type OR very short (≤6 words) AND exact CTA match
                    is_cta = (
                        li.get('type') == 'image' or
                        (len(t.split()) <= 6 and any(t == k or t.startswith(k) for k in _cta_lead_kws))
                    )
                    if not is_cta:
                        trimmed_lead.append(li)
                    else:
                        print(f"[web_engine] Trimmed CTA lead: '{t[:60]}'")
                content_items = trimmed_lead + content_items[first_header_idx:]

            print(f"[web_engine] After noise filter: {len(content_items)} items")

            total_items = len(content_items)
            seen_images = set()  # Track rendered image URLs to prevent duplicates
            for idx, item in enumerate(content_items):
                # Guard: skip any non-dict items (safety net)
                if not isinstance(item, dict):
                    continue

                item_type = item.get('type', '')
                style = self.styles['UnifranzBody']

                if item_type == 'header':
                    style = self.styles['UnifranzH2']
                    if item['text'].strip().upper() == title.strip().upper(): continue
                    story.append(Paragraph(item['text'], style))

                elif item_type == 'paragraph':
                    clean_text = self.normalize_paragraph_text(item['text'])
                    story.append(Paragraph(clean_text, style))
                    story.append(Spacer(1, 8))

                elif item_type == 'list_item':
                    clean_text = self.normalize_paragraph_text(item['text'])
                    story.append(Paragraph(f"• {clean_text}", style))
                    story.append(Spacer(1, 4))

                elif item_type == 'code':
                    code_text = item['text']
                    code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    code_text = code_text.replace('\n', '<br/>')
                    story.append(Paragraph(code_text, self.styles['UnifranzCode']))
                    story.append(Spacer(1, 12))

                elif item_type == 'table':
                    try:
                        rows_data = item['rows']
                        has_header = item.get('has_header', False)
                        # Read table config from style_config
                        tbl_cfg = getattr(self, '_style_config', {}) or {}
                        tbl_header_bg    = tbl_cfg.get('table_header_bg')    or tbl_cfg.get('tableHeaderBg',   '#1e3a5f')
                        tbl_header_text  = tbl_cfg.get('table_header_text')  or tbl_cfg.get('tableHeaderText', '#ffffff')
                        tbl_row_even     = tbl_cfg.get('table_row_even')     or tbl_cfg.get('tableRowEven',    '#f0f4f8')
                        tbl_row_odd      = tbl_cfg.get('table_row_odd')      or tbl_cfg.get('tableRowOdd',     '#ffffff')
                        tbl_border_color = tbl_cfg.get('table_border_color') or tbl_cfg.get('tableBorderColor','#cccccc')
                        tbl_border_w     = float(tbl_cfg.get('table_border_width') or tbl_cfg.get('tableBorderWidth', 0.5))
                        tbl_font_size    = int(tbl_cfg.get('table_font_size') or tbl_cfg.get('tableFontSize', 9))
                        tbl_padding      = int(tbl_cfg.get('table_padding')   or tbl_cfg.get('tablePadding',  5))

                        # Build cell style with smaller font
                        cell_style = ParagraphStyle(
                            'TableCell',
                            parent=self.styles['UnifranzBody'],
                            fontSize=tbl_font_size,
                            leading=tbl_font_size + 2,
                        )

                        # Normalize row lengths
                        max_cols = max(len(r) for r in rows_data)
                        table_data = []
                        for row in rows_data:
                            while len(row) < max_cols:
                                row.append('')
                            table_data.append([Paragraph(cell, cell_style) for cell in row])

                        col_count = max_cols
                        avail_width = getattr(self, 'max_width', 450)
                        col_width = avail_width / col_count
                        t = Table(table_data, colWidths=[col_width] * col_count)

                        table_style_cmds = [
                            ('GRID', (0,0), (-1,-1), tbl_border_w, colors.HexColor(tbl_border_color)),
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('TOPPADDING', (0,0), (-1,-1), tbl_padding),
                            ('BOTTOMPADDING', (0,0), (-1,-1), tbl_padding),
                            ('LEFTPADDING', (0,0), (-1,-1), tbl_padding + 2),
                            ('RIGHTPADDING', (0,0), (-1,-1), tbl_padding + 2),
                        ]

                        # Zebra striping for data rows
                        start_row = 1 if has_header else 0
                        for i, _ in enumerate(table_data[start_row:], start=start_row):
                            bg = tbl_row_even if i % 2 == 0 else tbl_row_odd
                            table_style_cmds.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor(bg)))

                        if has_header:
                            table_style_cmds.append(('BACKGROUND', (0,0), (-1,0), colors.HexColor(tbl_header_bg)))
                            table_style_cmds.append(('TEXTCOLOR', (0,0), (-1,0), colors.HexColor(tbl_header_text)))
                            table_style_cmds.append(('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'))
                            table_style_cmds.append(('FONTSIZE', (0,0), (-1,0), tbl_font_size + 1))

                        t.setStyle(TableStyle(table_style_cmds))
                        story.append(t)
                        story.append(Spacer(1, 12))
                    except Exception as te:
                        print(f"Table Render Error: {te}")
                        story.append(Paragraph('[Tabla no renderizable]', self.styles['UnifranzBody']))

                elif item_type == 'video_link':
                    raw_text = item.get('raw_text', item['text'])
                    vid_url = item['text']
                    if 'http' in raw_text:
                        urls = re.findall(r'(https?://\S+)', raw_text)
                        if urls: vid_url = urls[0]
                    thumb_data, is_video = self.get_video_thumbnail(vid_url)
                    if thumb_data:
                        try:
                            img = RLImage(thumb_data)
                            available_width = doc.width
                            img_width = available_width * 0.8
                            img_height = img_width * (9/16)
                            img.drawWidth = img_width
                            img.drawHeight = img_height
                            story.append(Spacer(1, 10))
                            story.append(img)
                            cap_style = ParagraphStyle('Caption', parent=style, alignment=TA_CENTER, textColor=colors.red)
                            story.append(Paragraph(f'<a href="{vid_url}">▶ VER VIDEO</a>', cap_style))
                            story.append(Spacer(1, 15))
                            continue
                        except: pass
                    v_style = ParagraphStyle('Video', parent=style, textColor=colors.blue, backColor=colors.lightgrey, borderPadding=5)
                    story.append(Paragraph(f'<a href="{vid_url}">🎥 VER VIDEO: {item["text"]}</a>', v_style))
                    story.append(Spacer(1, 8))

                elif item_type == 'image':
                    src = item['src']
                    if src:
                        if src.startswith('//'): src = 'https:' + src
                        elif src.startswith('/'):
                            if url.startswith('http'):
                                from urllib.parse import urljoin
                                src = urljoin(url, src)
                        if src.startswith('http'):
                            # Deduplicate images
                            src_key = src.split('?')[0]  # Ignore query params for dedup
                            if src_key in seen_images:
                                print(f"[web_engine] Skipped duplicate image: {src[:60]}")
                                continue
                            # Skip known ad/tracking image URLs
                            src_lower = src.lower()
                            if any(pat in src_lower for pat in ad_img_patterns):
                                print(f"[web_engine] Skipped ad image at render: {src[:60]}")
                                continue
                            try:
                                # Use Playwright cookies if available (for CF-protected sites)
                                img_cookies = getattr(self, '_pw_cookies', {})
                                img_resp = requests.get(src, headers=self.headers, cookies=img_cookies, stream=True, timeout=8)
                                if img_resp.status_code != 200:
                                    print(f"[web_engine] Image HTTP {img_resp.status_code} for {src[:60]}")
                                    continue
                                img_data = io.BytesIO(img_resp.content)
                                img = RLImage(img_data)
                                if img.imageWidth < 150 or img.imageHeight < 150:
                                    continue
                                aspect = img.imageWidth / float(img.imageHeight)
                                if aspect > 3.5 or aspect < 0.2:
                                    continue
                                available_width = getattr(self, 'max_width', 450)
                                # Cap height at 50% of page to prevent page-filling images
                                page_h = ps[1] if paper_size == 'letter' else legal[1]
                                max_img_height = (page_h - self.margin_top - self.margin_bottom) * 0.50
                                display_width = img.imageWidth
                                display_height = img.imageHeight
                                if display_width > available_width:
                                    factor = available_width / float(display_width)
                                    display_width = available_width
                                    display_height = display_height * factor
                                if display_height > max_img_height:
                                    factor = max_img_height / float(display_height)
                                    display_height = max_img_height
                                    display_width = display_width * factor
                                img.drawWidth = display_width
                                img.drawHeight = display_height
                                story.append(Spacer(1, 10))
                                story.append(img)
                                story.append(Spacer(1, 10))
                                seen_images.add(src_key)  # Mark as rendered
                            except Exception as img_err:
                                print(f"[web_engine] Image render error for {src[:80]}: {img_err}")

        except ET.ParseError:
            print("XML Parse Error in content processing")
            story.append(Paragraph("(Error procesando estructura del contenido)", self.styles['UnifranzBody']))


        # -- APA Citation Footer (Configurable) --
        apa_enabled = True
        apa_bg = '#f5f5f5'
        apa_border = '#cccccc'
        apa_font_size = 10
        apa_text_color = '#000000'
        if getattr(self, '_style_config', None):
            cfg = self._style_config
            apa_enabled = cfg.get('apa_enabled', True)
            apa_bg = cfg.get('apa_bg', '#f5f5f5') or '#f5f5f5'
            apa_border = cfg.get('apa_border', '#cccccc') or '#cccccc'
            apa_font_size = int(cfg.get('apa_font_size', 10) or 10)
            apa_text_color = cfg.get('apa_text_color', '#000000') or '#000000'

        if apa_enabled:
            from urllib.parse import urlparse
            from datetime import datetime
            
            try:
                domain = urlparse(url).netloc.replace('www.', '').capitalize()
                year = datetime.now().year
                
                # APA Format: Title. (Year). Site Name. URL
                color = getattr(self, 'link_hex', 'blue')
                apa_text = f"<b>{title}.</b> ({year}). {domain}. <br/><font color='{color}'>{url}</font>"
                
                apa_style = ParagraphStyle(
                    'APA', 
                    parent=self.styles['Normal'],
                    fontSize=apa_font_size,
                    leading=apa_font_size + 4,
                    alignment=TA_CENTER,
                    textColor=colors.HexColor(apa_text_color)
                )
                
                p = Paragraph(apa_text, apa_style)
                
                data = [[p]]
                t = Table(data, colWidths=[400])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(apa_bg)),
                    ('BOX', (0,0), (-1,-1), 1, colors.HexColor(apa_border)),
                    ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('TOPPADDING', (0,0), (-1,-1), 12),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 12),
                    ('LEFTPADDING', (0,0), (-1,-1), 15),
                    ('RIGHTPADDING', (0,0), (-1,-1), 15),
                    ('ROUNDEDCORNERS', [5, 5, 5, 5]), 
                ]))
                
                story.append(Spacer(1, 40))
                story.append(t)
                
            except Exception as e:
                print(f"Error creating APA footer: {e}")

        # ── Cover Page (Carátula) ────────────────────────────────────────
        def draw_cover_page(canvas, doc):
            """Draw cover page with full-bleed background image and title overlay."""
            canvas.saveState()
            
            # Draw background image if provided
            if self.caratula_imagen:
                try:
                    import base64
                    from reportlab.lib.utils import ImageReader
                    b64 = self.caratula_imagen
                    if ',' in b64:
                        b64 = b64.split(',', 1)[1]
                    img_bytes = base64.b64decode(b64)
                    img_buf = io.BytesIO(img_bytes)
                    canvas.drawImage(
                        ImageReader(img_buf), 0, 0,
                        width=ps[0], height=ps[1],
                        preserveAspectRatio=False, mask='auto'
                    )
                except Exception as cimg_err:
                    print(f"[web_engine] Cover image error: {cimg_err}")
            
            # Convert CSS percentage positions (0%=top) to ReportLab coords (0=bottom)
            title_x = ps[0] * self.caratula_title_x
            title_y = ps[1] * (1.0 - self.caratula_title_y)  # Invert: CSS top→RL bottom
            inst_y = ps[1] * (1.0 - self.caratula_inst_y)
            autor_y = ps[1] * (1.0 - self.caratula_autor_y)
            fecha_y = ps[1] * (1.0 - self.caratula_fecha_y)
            
            # Institution (above title)
            if self.caratula_institucion:
                try:
                    t_color = colors.HexColor(self.caratula_title_color)
                except:
                    t_color = colors.black
                canvas.setFont('Helvetica-Bold', 14)
                canvas.setFillColor(t_color)
                canvas.drawCentredString(title_x, inst_y, self.caratula_institucion)
            
            # Title text — with auto-wrapping & font-size reduction
            cover_title = self.caratula_titulo or title
            if cover_title:
                try:
                    t_color = colors.HexColor(self.caratula_title_color)
                except:
                    t_color = colors.black
                canvas.setFillColor(t_color)

                cover_title_upper = cover_title.upper()
                font_name = 'Helvetica-Bold'
                font_size = self.caratula_title_size
                max_text_width = ps[0] - 100  # 50pt margin each side
                line_height_factor = 1.3

                from reportlab.pdfbase.pdfmetrics import stringWidth

                # Auto-reduce font size if even a single word overflows
                min_font = 10
                while font_size > min_font:
                    longest_word = max(cover_title_upper.split(), key=len) if cover_title_upper.split() else ''
                    if stringWidth(longest_word, font_name, font_size) <= max_text_width:
                        break
                    font_size -= 1

                # Wrap text into lines that fit within max_text_width
                words = cover_title_upper.split()
                lines = []
                current_line = ''
                for word in words:
                    test_line = f"{current_line} {word}".strip() if current_line else word
                    if stringWidth(test_line, font_name, font_size) <= max_text_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)

                # Draw lines centered vertically around title_y
                leading = font_size * line_height_factor
                total_text_height = leading * len(lines)
                start_y = title_y + (total_text_height / 2) - font_size * 0.3  # visual center

                canvas.setFont(font_name, font_size)
                for i, line in enumerate(lines):
                    y = start_y - (i * leading)
                    canvas.drawCentredString(title_x, y, line)
            
            # Author
            if self.caratula_autor:
                try:
                    a_color = colors.HexColor(self.caratula_autor_color)
                except:
                    a_color = colors.Color(0.2, 0.2, 0.2)
                canvas.setFont('Helvetica', self.caratula_autor_size)
                canvas.setFillColor(a_color)
                canvas.drawCentredString(title_x, autor_y, self.caratula_autor)
            
            # Date
            if self.caratula_fecha:
                canvas.setFont('Helvetica', 11)
                canvas.setFillColor(colors.Color(0.3, 0.3, 0.3))
                canvas.drawCentredString(title_x, fecha_y, self.caratula_fecha)
            
            canvas.restoreState()

        # Insert cover page into story if enabled
        if self.caratula_enabled:
            from reportlab.platypus import PageBreak
            # Empty spacer as cover page content (actual drawing is in callback)
            story.insert(0, Spacer(1, 1))
            story.insert(1, PageBreak())
            print("[web_engine] Cover page added to story")

        # ── Contratapa (Back Cover) ─────────────────────────────────────────
        # Uses a custom Flowable that draws a full-bleed background image
        # as the very last page of the document.
        if self.contratapa_enabled and self.contratapa_imagen:
            from reportlab.platypus import Flowable, PageBreak as PB
            import base64
            from reportlab.lib.utils import ImageReader

            contratapa_b64 = self.contratapa_imagen
            page_w, page_h = ps[0], ps[1]

            class BackCoverFlowable(Flowable):
                """A full-page flowable that draws a background image with no margins."""
                def __init__(self, img_b64, pw, ph):
                    Flowable.__init__(self)
                    self.img_b64 = img_b64
                    self.pw = pw
                    self.ph = ph
                    self.width = 0
                    self.height = 0

                def draw(self):
                    canvas = self.canv
                    try:
                        b64 = self.img_b64
                        if ',' in b64:
                            b64 = b64.split(',', 1)[1]
                        img_bytes = base64.b64decode(b64)
                        img_buf = io.BytesIO(img_bytes)
                        # Calculate offset to draw full-bleed from bottom-left corner
                        # The flowable is placed within margins, so we need to offset
                        doc = canvas._doctemplate
                        x_offset = -doc.leftMargin
                        y_offset = -doc.bottomMargin
                        canvas.drawImage(
                            ImageReader(img_buf),
                            x_offset, y_offset,
                            width=self.pw, height=self.ph,
                            preserveAspectRatio=False, mask='auto'
                        )
                    except Exception as e:
                        print(f"[web_engine] Back cover image error: {e}")

            story.append(PB())
            story.append(BackCoverFlowable(contratapa_b64, page_w, page_h))
            print("[web_engine] Back cover page added to story")

        # Build
        try:
            if progress_callback: progress_callback(85, "Generando archivo PDF final...")

            # Track if current page is the back cover to suppress header/footer
            self._is_back_cover = False
            total_story_pages = None  # Will be set during build

            def smart_later_pages(canvas, doc):
                """Draw header/footer on normal pages, skip on back cover."""
                # Check if this is the last page and contratapa is enabled
                if self.contratapa_enabled and self.contratapa_imagen:
                    # The back cover flowable sets a flag via its draw method
                    # We detect it by checking if we're past the main content
                    pass  # Header/footer will be drawn; we suppress via page tracking below
                draw_header_footer(canvas, doc)

            if self.caratula_enabled:
                doc.build(story, onFirstPage=draw_cover_page, onLaterPages=draw_header_footer)
            else:
                doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
        except Exception as e:
            raise Exception(f"Error generando PDF: {str(e)}")

        # ── Post-build: Remove header/footer from back cover page ──────────
        # If contratapa is enabled, the last page has the background image
        # but also has unwanted header/footer drawn by onLaterPages.
        # We use pikepdf to rebuild the last page cleanly.
        if self.contratapa_enabled and self.contratapa_imagen:
            try:
                import pikepdf
                pdf_buffer.seek(0)
                pdf = pikepdf.open(pdf_buffer)
                total_pages = len(pdf.pages)
                if total_pages >= 2:
                    # Create a clean back cover PDF
                    clean_buf = io.BytesIO()
                    clean_doc = SimpleDocTemplate(
                        clean_buf, pagesize=ps,
                        topMargin=0, bottomMargin=0,
                        leftMargin=0, rightMargin=0
                    )
                    
                    # Use a simple callback to draw the image
                    def draw_clean_back_cover(canvas, doc):
                        canvas.saveState()
                        try:
                            b64 = self.contratapa_imagen
                            if ',' in b64:
                                b64 = b64.split(',', 1)[1]
                            img_bytes = base64.b64decode(b64)
                            img_buf_inner = io.BytesIO(img_bytes)
                            canvas.drawImage(
                                ImageReader(img_buf_inner), 0, 0,
                                width=ps[0], height=ps[1],
                                preserveAspectRatio=False, mask='auto'
                            )
                        except Exception as e:
                            print(f"[web_engine] Clean back cover error: {e}")
                        canvas.restoreState()
                    
                    clean_doc.build([Spacer(1, 1)], onFirstPage=draw_clean_back_cover)
                    clean_buf.seek(0)
                    clean_pdf = pikepdf.open(clean_buf)
                    
                    # Replace the last page
                    pdf.pages[-1] = clean_pdf.pages[0]
                    
                    # Write result
                    result_buf = io.BytesIO()
                    pdf.save(result_buf)
                    result_buf.seek(0)
                    print(f"[web_engine] Back cover page cleaned (removed header/footer)")
                    return result_buf, title
            except Exception as pk_err:
                print(f"[web_engine] pikepdf back cover cleanup error: {pk_err}")
                # Fall through to return original buffer

        pdf_buffer.seek(0)
        return pdf_buffer, title
