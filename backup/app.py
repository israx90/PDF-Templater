# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, send_file, jsonify, Response
import os
import json
from werkzeug.utils import secure_filename
import shutil
import subprocess

app = Flask(__name__)

# import logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

# Configuración
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'engines'))

@app.route('/')
def home():
    return render_template('tool_pdf.html')

@app.route('/select_folder', methods=['POST'])
def select_folder():
    import subprocess
    try:
        script = """
        set p to choose folder with prompt "Selecciona la carpeta de salida"
        POSIX path of p
        """
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            folder_path = result.stdout.strip()
            return jsonify({'path': folder_path})
        else:
            return jsonify({'path': None})
    except Exception as e:
        print(f"Error selecting folder: {e}")
        return jsonify({'path': None})

@app.route('/process_url', methods=['POST'])
def process_url():
    import json
    from flask import Response
    from engines.web_engine import WebConverter
    
    # Capture Request Data
    url = request.form.get('url')
    paper_size = request.form.get('paper_size', 'letter')
    style_config = request.form.get('style_config') 
    
    # DEBUG: log key style_config fields
    if style_config:
        try:
            import json as _json
            _sc = _json.loads(style_config)
            print(f"[DEBUG style_config] h2_color={_sc.get('h2_color')} | margin_top={_sc.get('margin_top')} | table_header_bg={_sc.get('table_header_bg')} | caratula_enabled={_sc.get('caratula_enabled')} | caratula_imagen={bool(_sc.get('caratula_imagen'))}")
        except Exception as _e:
            print(f"[DEBUG style_config] ERROR parsing: {_e}")
    else:
        print("[DEBUG style_config] VACÍO — no se recibió style_config del frontend")

    output_folder_path = request.form.get('output_folder')

    if not output_folder_path:
        output_folder_path = app.config['OUTPUT_FOLDER']
    # Auto-create the folder (including XLS-derived subfolders)
    print(f"[DEBUG] output_folder_path = '{output_folder_path}'")
    os.makedirs(output_folder_path, exist_ok=True)

    # Filename prefix/suffix
    prefix_val = request.form.get('file_prefix', '')
    suffix_val = request.form.get('file_suffix', '')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    import queue, threading

    def generate():
        msg_queue = queue.Queue()

        def progress(percent, msg):
            print(f"PDF Progress [{percent}%]: {msg}")
            msg_queue.put(json.dumps({'progress': percent, 'msg': msg, 'type': 'info'}) + "\n")

        def run_conversion():
            try:
                converter = WebConverter()
                pdf_buffer, title = converter.convert_to_pdf(url, paper_size, style_config, progress_callback=progress)
                safe_title = secure_filename(title)
                if not safe_title:
                    safe_title = "documento_web"
                # Replace spaces/hyphens from secure_filename with underscores
                safe_title = safe_title.replace(' ', '_').replace('-', '_')
                # Apply prefix/suffix if provided
                file_prefix = prefix_val if prefix_val else ''
                file_suffix = suffix_val if suffix_val else ''
                filename = f"{file_prefix}{safe_title}{file_suffix}.pdf"
                file_path = os.path.join(output_folder_path, filename)
                with open(file_path, 'wb') as f:
                    f.write(pdf_buffer.getvalue())
                print(f"PDF Saved: {file_path}")
                msg_queue.put(json.dumps({'success': True, 'progress': 100, 'result': filename, 'path': file_path, 'msg': f'Guardado en: {filename}', 'type': 'success'}) + "\n")
            except Exception as e:
                print(f"Error processing URL: {e}")
                # Generate an ERROR CRÍTICO PDF so the user has a file to identify the failure
                try:
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    from reportlab.lib import colors
                    from reportlab.lib.pagesizes import letter
                    import io as _io
                    _buf = _io.BytesIO()
                    _doc = SimpleDocTemplate(_buf, pagesize=letter,
                                            rightMargin=50, leftMargin=50,
                                            topMargin=60, bottomMargin=50)
                    _styles = getSampleStyleSheet()
                    _err_title_style = ParagraphStyle('ErrTitle', parent=_styles['Title'],
                                                      textColor=colors.HexColor('#cc0000'),
                                                      fontSize=28, spaceAfter=20)
                    _err_body_style = ParagraphStyle('ErrBody', parent=_styles['Normal'],
                                                     fontSize=11, leading=16)
                    _url_style = ParagraphStyle('ErrUrl', parent=_styles['Normal'],
                                                fontSize=9, textColor=colors.gray,
                                                spaceAfter=30)
                    _story = [
                        Paragraph("ERROR CRÍTICO", _err_title_style),
                        Paragraph(f"URL: {url}", _url_style),
                        Paragraph(f"No fue posible generar el PDF para esta URL.", _err_body_style),
                        Spacer(1, 12),
                        Paragraph(f"Detalle del error:", _err_body_style),
                        Spacer(1, 6),
                        Paragraph(str(e).replace('<', '&lt;').replace('>', '&gt;'),
                                  ParagraphStyle('ErrDetail', parent=_styles['Normal'],
                                                 fontSize=10, textColor=colors.HexColor('#333333'),
                                                 backColor=colors.HexColor('#fff0f0'),
                                                 borderPadding=10, leading=14)),
                    ]
                    _doc.build(_story)
                    # Build filename from URL slug
                    from urllib.parse import urlparse as _up2
                    _slug = _up2(url).path.strip('/').replace('/', '_')[:60] or 'error_url'
                    _slug = secure_filename(_slug).replace('-', '_')
                    file_prefix = prefix_val if prefix_val else ''
                    _err_filename = f"{file_prefix}ERROR_{_slug}.pdf"
                    _err_path = os.path.join(output_folder_path, _err_filename)
                    with open(_err_path, 'wb') as _f:
                        _f.write(_buf.getvalue())
                    print(f"Error PDF saved: {_err_path}")
                    msg_queue.put(json.dumps({'success': True, 'progress': 100,
                                              'result': _err_filename, 'path': _err_path,
                                              'msg': f'ERROR CRÍTICO guardado: {_err_filename}',
                                              'type': 'error'}) + "\n")
                except Exception as pdf_err:
                    print(f"Failed to generate error PDF: {pdf_err}")
                    msg_queue.put(json.dumps({'error': str(e), 'msg': f'Fallo: {str(e)}', 'type': 'error'}) + "\n")
            finally:
                msg_queue.put(None)  # Sentinel


        t = threading.Thread(target=run_conversion, daemon=True)
        t.start()

        while True:
            item = msg_queue.get()
            if item is None:
                break
            yield item

    return Response(generate(), mimetype='application/x-ndjson')

@app.route('/stamp_pdf', methods=['POST'])
def stamp_pdf():
    """
    Receives one or more PDF files and applies the EPD template
    (header image, header text, page numbers) as an overlay.
    Returns NDJSON progress stream like /process_url.
    """
    import queue, threading

    style_config   = request.form.get('style_config')
    output_folder  = request.form.get('output_folder') or app.config['OUTPUT_FOLDER']
    file_prefix    = request.form.get('file_prefix', '')
    file_suffix    = request.form.get('file_suffix', '')
    recolor_accent = request.form.get('recolor_accent', '') == '1'

    # Collect per-file source URLs (source_url_0, source_url_1, ...)
    source_urls = {}
    for key, val in request.form.items():
        if key.startswith('source_url_') and val.strip():
            try:
                idx = int(key.split('_')[-1])
                source_urls[idx] = val.strip()
            except ValueError:
                pass

    os.makedirs(output_folder, exist_ok=True)

    pdf_files = request.files.getlist('pdf_files[]')
    if not pdf_files:
        return jsonify({'error': 'No se recibieron archivos PDF'}), 400

    def generate():
        from engines.pdf_stamp_engine import PdfStamper
        msg_queue = queue.Queue()
        total = len(pdf_files)

        def process_one(idx, file_storage):
            try:
                original_filename = secure_filename(file_storage.filename)
                name, ext = os.path.splitext(original_filename)

                # Save temp copy so PdfStamper can build a proper backup path
                tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
                file_storage.save(tmp_path)
                pdf_bytes = open(tmp_path, 'rb').read()

                def progress(pct, msg):
                    global_pct = int((idx / total) * 100 + pct / total)
                    print(f"[stamp_pdf] [{idx+1}/{total}] {pct}% — {msg}")
                    msg_queue.put(json.dumps({
                        'progress': global_pct,
                        'msg': f"[{idx+1}/{total}] {msg}",
                        'type': 'info'
                    }) + "\n")

                # Merge recolor + source_url into style_config
                sc_dict = json.loads(style_config) if style_config else {}
                if recolor_accent:
                    sc_dict['stamp_recolor_accent'] = True
                source_url = source_urls.get(idx, '')
                if source_url:
                    sc_dict['stamp_source_url'] = source_url
                merged_config = json.dumps(sc_dict)

                stamper = PdfStamper()
                result_buf = stamper.apply_template(
                    pdf_bytes=pdf_bytes,
                    style_config_json=merged_config,
                    src_path=tmp_path,
                    output_folder=output_folder,
                    progress_callback=progress
                )

                out_name = f"{file_prefix}{name}{file_suffix}_STAMPED.pdf"
                out_path = os.path.join(output_folder, out_name)
                with open(out_path, 'wb') as f:
                    f.write(result_buf.getvalue())

                print(f"[stamp_pdf] Saved: {out_path}")
                msg_queue.put(json.dumps({
                    'success': True, 'progress': int((idx + 1) / total * 100),
                    'result': out_name, 'path': out_path,
                    'msg': f'Guardado: {out_name}', 'type': 'success'
                }) + "\n")

            except Exception as e:
                print(f"[stamp_pdf] Error processing {file_storage.filename}: {e}")
                msg_queue.put(json.dumps({
                    'error': str(e),
                    'msg': f'Error en {file_storage.filename}: {str(e)}',
                    'type': 'error'
                }) + "\n")

        def run_all():
            threads = []
            for i, f in enumerate(pdf_files):
                t = threading.Thread(target=process_one, args=(i, f), daemon=True)
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
            msg_queue.put(None)  # Sentinel

        threading.Thread(target=run_all, daemon=True).start()

        while True:
            item = msg_queue.get()
            if item is None:
                break
            yield item

    return Response(generate(), mimetype='application/x-ndjson')


if __name__ == '__main__':

    import sys
    port = 3002
    if '--port' in sys.argv:
        port = int(sys.argv[sys.argv.index('--port') + 1])
    app.run(debug=False, port=port)
