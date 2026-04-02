/**
 * EDTech Config File System  v2.0
 * ─────────────────────────────────────────────────────────────────
 * Formats:
 *   .edd  — EDTech Document  (Doc Formatter)
 *   .edx  — EDTech Excel     (Excel Formatter)
 *   .edp  — EDTech PowerPoint (future)
 *   .epd  — EDTech PDF       (PDF Tools)
 *
 * Images: ALL formats stored as base64 data URLs inside the JSON.
 *   Supported: PNG, JPG, GIF, WEBP, SVG, EMF, WMF
 *   Raster (PNG/JPG/…) → shown as background-image in the drop zone
 *   Vector (SVG/EMF/WMF) → shown as filename label in the drop zone
 *
 * Global image store: window._edtechImgStore = { caratula, header, footer, hojaFinal }
 * Each value: { dataUrl, filename, mimeType }
 * ─────────────────────────────────────────────────────────────────
 */

// ── Global image store ────────────────────────────────────────────
window._edtechImgStore = window._edtechImgStore || {};

/**
 * Register an image upload zone.
 * Call this for every drop zone — replaces the old _setupImgUpload in main.js.
 * @param {string} storeKey   - key in _edtechImgStore ('caratula'|'header'|'footer'|'hojaFinal')
 * @param {string} zoneId     - id of the drop zone div
 * @param {string} inputId    - id of the <input type="file">
 * @param {string} previewId  - id of the preview div inside the zone
 */
function edtechRegisterImgUpload(storeKey, zoneId, inputId, previewId) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (!zone || !input) return;

    zone.addEventListener('click', () => input.click());

    input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const isRaster = file.type.startsWith('image/') &&
            !file.name.toLowerCase().endsWith('.svg') &&
            !file.name.toLowerCase().endsWith('.emf') &&
            !file.name.toLowerCase().endsWith('.wmf');

        const reader = new FileReader();
        reader.onload = (ev) => {
            const dataUrl = ev.target.result;

            // Store in global store
            window._edtechImgStore[storeKey] = {
                dataUrl,
                filename: file.name,
                mimeType: file.type || _guessMime(file.name)
            };

            // Update zone visual
            if (isRaster) {
                zone.style.backgroundImage = `url(${dataUrl})`;
                zone.style.backgroundSize = 'contain';
                zone.style.backgroundRepeat = 'no-repeat';
                zone.style.backgroundPosition = 'center';
                if (preview) preview.style.opacity = '0';
            } else {
                // Vector — show filename
                zone.style.backgroundImage = 'none';
                if (preview) {
                    preview.style.opacity = '1';
                    preview.innerHTML = `
                        <i class="fa-solid fa-vector-square" style="font-size:16px; color:var(--primary);"></i>
                        <span style="font-size:9px; margin-top:4px; word-break:break-all; text-align:center;">${file.name}</span>
                    `;
                }
            }
        };
        reader.readAsDataURL(file);
    });
}

function _guessMime(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const map = {
        png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg',
        gif: 'image/gif', webp: 'image/webp', svg: 'image/svg+xml',
        emf: 'image/emf', wmf: 'image/wmf'
    };
    return map[ext] || 'application/octet-stream';
}

// ─────────────────────────────────────────────────────────────────
const EDTechConfig = (() => {

    // ── Tool → extension mapping ──────────────────────────────────
    const TOOL_EXT = {
        docs: { ext: 'edd', label: 'EDTech Document', mime: 'application/edtech-doc' },
        excel: { ext: 'edx', label: 'EDTech Excel', mime: 'application/edtech-excel' },
        pdf: { ext: 'epd', label: 'EDTech PDF', mime: 'application/edtech-pdf' },
        ppt: { ext: 'edp', label: 'EDTech PowerPoint', mime: 'application/edtech-ppt' },
    };

    function _detectTool() {
        const p = window.location.pathname;
        if (p.includes('/excel')) return 'excel';
        if (p.includes('/ppt')) return 'ppt';
        if (p.includes('/docs')) return 'docs';
        return 'pdf'; // Default to pdf for '/' root in this project
    }

    // ── Helpers ───────────────────────────────────────────────────
    const _g = (id) => { const el = document.getElementById(id); return el ? el.value : null; };
    const _gb = (id) => { const el = document.getElementById(id); return el ? el.checked : null; };
    const _gn = (id) => { const el = document.getElementById(id); return el ? parseFloat(el.value) || null : null; };
    const _s = (id, v) => { const el = document.getElementById(id); if (el && v !== null && v !== undefined) el.value = String(v); };
    const _sb = (id, v) => { const el = document.getElementById(id); if (el && v !== null && v !== undefined) el.checked = Boolean(v); };

    // ── Collect ALL config fields ─────────────────────────────────
    function collectConfig() {
        return {
            // ── General ──────────────────────────────────────────
            font_name: _g('cfgFont'),
            font_size: _gn('cfgFontSize'),
            line_spacing: _g('cfgLineSpacing'),
            link_color: _g('cfgLinkColor'),
            text_alignment: _g('cfgTextAlignment'),
            paper_size: document.querySelector('.paper-card.active')?.dataset.value || 'letter',
            force_styles: _gb('forceStyles'),

            // ── Margins (PDF) ────────────────────────────────────
            margin_top: _gn('cfgMarginTop'),
            margin_bottom: _gn('cfgMarginBottom'),
            margin_left: _gn('cfgMarginLeft'),
            margin_right: _gn('cfgMarginRight'),

            // ── Page Numbering (PDF) ─────────────────────────────
            page_num_format: _g('cfgPageNumFormat'),

            // ── Headings ─────────────────────────────────────────
            h1_size: _gn('cfgH1Size'),
            h1_color: _g('cfgH1Color'),
            h1_bold: _gb('cfgH1Bold'),
            h2_size: _gn('cfgH2Size'),
            h2_color: _g('cfgH2Color'),
            h2_bold: _gb('cfgH2Bold'),

            // ── Tables ───────────────────────────────────────────
            table_header_bg: _g('cfgTableHeaderBg'),
            table_header_text: _g('cfgTableHeaderText'),
            table_border_v: _g('cfgTableBorderV'),
            table_border_h: _g('cfgTableBorderH'),
            table_border_color: _g('cfgTableBorderColor'),
            table_border_width: _gn('cfgTableBorderWidth'),
            table_font_size: _gn('cfgTableFontSize'),
            table_row_even: _g('cfgTableRowEven'),
            table_row_odd: _g('cfgTableRowOdd'),
            table_zebra: _gb('cfgTableZebra'),
            table_num_align: _gb('cfgTableNumberAlign'),
            table_padding: _gn('cfgTablePadding'),

            // ── Header Text Block (PDF) ──────────────────────────
            header_text_enabled: _gb('enableHeaderText'),
            header_type: _g('cfgHeaderType'),
            header_text: _g('cfgHeaderText'),
            header_img_height: _gn('cfgHeaderImgHeight'),

            // ── APA Block (PDF) ──────────────────────────────────
            apa_enabled: _gb('enableApaBlock'),
            apa_bg: _g('cfgApaBg'),
            apa_border: _g('cfgApaBorder'),
            apa_font_size: _gn('cfgApaFontSize'),
            apa_text_color: _g('cfgApaTextColor'),

            // ── Carátula ─────────────────────────────────────────
            caratula_enabled: _gb('enableCaratula'),
            caratula_titulo: _g('caratulaTitulo'),
            caratula_incluir_autor: _gb('caratulaIncluirAutor'),
            caratula_autor: _g('caraTulaAutor'),
            caratula_institucion: _g('caraTulaInstitucion'),
            caratula_fecha: _g('caraTulaFecha'),
            caratula_title_size: _gn('cfgCaratulaTitleSize'),
            caratula_title_color: _g('cfgCaratulaTitleColor'),
            caratula_autor_size: _gn('cfgCaratulaAutorSize'),
            caratula_autor_color: _g('cfgCaratulaAutorColor'),
            caratula_title_x: _gn('cfgCaratulaTitleX'),
            caratula_title_y: _gn('cfgCaratulaTitleY'),

            // ── Contratapa (PDF) ─────────────────────────────────
            contratapa_enabled: _gb('enableContratapa'),

            // ── Encabezado ───────────────────────────────────────
            encabezado_enabled: _gb('enableEncabezado'),
            encabezado_left: _g('headerLeft'),
            encabezado_center: _g('headerCenter'),
            encabezado_right: _g('headerRight'),
            encabezado_line_style: _g('headerLineStyle'),
            encabezado_line_color: _g('headerLineColor'),

            // ── Footer ───────────────────────────────────────────
            footer_enabled: _gb('enableFooter'),
            footer_left: _g('footerLeft'),
            footer_center: _g('footerCenter'),
            footer_right: _g('footerRight'),
            footer_page_numbers: _gb('footerPageNumbers'),
            footer_page_num_pos: _g('footerPageNumPos'),
            footer_line_style: _g('footerLineStyle'),
            footer_line_color: _g('footerLineColor'),

            // ── Hoja Final ───────────────────────────────────────
            hoja_final_enabled: _gb('enableHojaFinal'),
            hoja_final_texto: _g('hojaFinalTexto'),
            hoja_final_size: _gn('cfgHojaFinalSize'),
            hoja_final_color: _g('cfgHojaFinalColor'),

            // ── Filename (PDF) ───────────────────────────────────
            file_prefix: _g('filePrefix'),
            file_suffix: _g('fileSuffix'),
        };
    }

    // ── Collect images from global store ─────────────────────────
    function collectImages() {
        const store = window._edtechImgStore || {};
        const images = {};
        ['caratula', 'contratapa', 'header', 'footer', 'hojaFinal'].forEach(key => {
            if (store[key]) {
                images[key] = {
                    dataUrl: store[key].dataUrl,
                    filename: store[key].filename,
                    mimeType: store[key].mimeType
                };
            }
        });
        return images;
    }

    // ── Apply config to UI ────────────────────────────────────────
    function applyConfig(config) {
        if (!config) return;

        // Backward-compat: EPD files saved with camelCase keys (old format) OR snake_case (new format)
        // Try snake_case first; fall back to camelCase equivalent
        const gc = (snakeKey, camelKey) => {
            const v = config[snakeKey];
            return (v !== null && v !== undefined) ? v : config[camelKey];
        };

        // General
        _s('cfgFont', gc('font_name', 'fontPrompt'));
        _s('cfgFontSize', gc('font_size', 'fontSize'));
        _s('cfgLineSpacing', gc('line_spacing', 'lineSpacing'));
        _s('cfgLinkColor', gc('link_color', 'linkColor'));
        _s('cfgLinkColorHex', gc('link_color', 'linkColor'));
        _s('cfgTextAlignment', gc('text_alignment', 'textAlignment'));
        _sb('forceStyles', gc('force_styles', 'forceStyles'));

        // Paper size
        const _paperSize = gc('paper_size', 'paperSize');
        if (_paperSize) {
            document.querySelectorAll('.paper-card').forEach(c => {
                c.classList.toggle('active', c.dataset.value === _paperSize);
            });
        }

        // Margins
        _s('cfgMarginTop',    gc('margin_top',    'marginTop'));
        _s('cfgMarginBottom', gc('margin_bottom', 'marginBottom'));
        _s('cfgMarginLeft',   gc('margin_left',   'marginLeft'));
        _s('cfgMarginRight',  gc('margin_right',  'marginRight'));

        // Page Numbering
        _s('cfgPageNumFormat', gc('page_num_format', 'pageNumFormat'));

        // Headings
        _s('cfgH1Size',    gc('h1_size',  'h1Size'));
        _s('cfgH1Color',   gc('h1_color', 'h1Color'));
        _s('cfgH1ColorHex',gc('h1_color', 'h1Color'));
        _sb('cfgH1Bold',   gc('h1_bold',  'h1Bold'));
        _s('cfgH2Size',    gc('h2_size',  'h2Size'));
        _s('cfgH2Color',   gc('h2_color', 'h2Color'));
        _s('cfgH2ColorHex',gc('h2_color', 'h2Color'));
        _sb('cfgH2Bold',   gc('h2_bold',  'h2Bold'));

        // Tables
        _s('cfgTableHeaderBg',      gc('table_header_bg',    'tableHeaderBg'));
        _s('cfgTableHeaderBgHex',   gc('table_header_bg',    'tableHeaderBg'));
        _s('cfgTableHeaderText',    gc('table_header_text',  'tableHeaderText'));
        _s('cfgTableHeaderTextHex', gc('table_header_text',  'tableHeaderText'));
        _s('cfgTableBorderV',       gc('table_border_v',     'tableBorderV'));
        _s('cfgTableBorderH',       gc('table_border_h',     'tableBorderH'));
        _s('cfgTableBorderColor',   gc('table_border_color', 'tableBorderColor'));
        _s('cfgTableBorderColorHex',gc('table_border_color', 'tableBorderColor'));
        _s('cfgTableBorderWidth',   gc('table_border_width', 'tableBorderWidth'));
        _s('cfgTableFontSize',      gc('table_font_size',    'tableFontSize'));
        _s('cfgTableRowEven',       gc('table_row_even',     'tableRowEven'));
        _s('cfgTableRowEvenHex',    gc('table_row_even',     'tableRowEven'));
        _s('cfgTableRowOdd',        gc('table_row_odd',      'tableRowOdd'));
        _s('cfgTableRowOddHex',     gc('table_row_odd',      'tableRowOdd'));
        _sb('cfgTableZebra',        gc('table_zebra',        'tableZebra'));
        _sb('cfgTableNumberAlign',  gc('table_num_align',    'tableNumAlign'));
        _s('cfgTablePadding',       gc('table_padding',      'tablePadding'));

        // Header Text Block
        _sb('enableHeaderText', gc('header_text_enabled', 'headerTextEnabled'));
        _s('cfgHeaderType',     gc('header_type',         'headerType'));
        _s('cfgHeaderText',     gc('header_text',         'headerText'));
        _s('cfgHeaderImgHeight',gc('header_img_height',   'headerImgHeight'));
        const _hte = gc('header_text_enabled', 'headerTextEnabled');
        const headerTextZone = document.getElementById('headerTextZone');
        if (headerTextZone) headerTextZone.style.display = _hte === false ? 'none' : 'block';
        const _htype = gc('header_type', 'headerType');
        const customHeaderGroup = document.getElementById('customHeaderGroup');
        if (customHeaderGroup) customHeaderGroup.style.display = _htype === 'custom' ? 'block' : 'none';

        // APA Block
        _sb('enableApaBlock', gc('apa_enabled',    'apaEnabled'));
        _s('cfgApaBg',         gc('apa_bg',         'apaBg'));
        _s('cfgApaBgHex',      gc('apa_bg',         'apaBg'));
        _s('cfgApaBorder',     gc('apa_border',     'apaBorder'));
        _s('cfgApaBorderHex',  gc('apa_border',     'apaBorder'));
        _s('cfgApaFontSize',   gc('apa_font_size',  'apaFontSize'));
        _s('cfgApaTextColor',  gc('apa_text_color', 'apaTextColor'));
        _s('cfgApaTextColorHex',gc('apa_text_color','apaTextColor'));

        // Carátula
        _sb('enableCaratula',       gc('caratula_enabled',        'caratulaEnabled'));
        _s('caratulaTitulo',        gc('caratula_titulo',         'caratulaTitulo'));
        _sb('caratulaIncluirAutor', gc('caratula_incluir_autor',  'caratulaIncluirAutor'));
        _s('caraTulaAutor',         gc('caratula_autor',          'caratulaAutor'));
        _s('caraTulaInstitucion',   gc('caratula_institucion',    'caratulaInstitucion'));
        _s('caraTulaFecha',         gc('caratula_fecha',          'caratulaFecha'));
        _s('cfgCaratulaTitleSize',  gc('caratula_title_size',     'caratulaTitleSize'));
        _s('cfgCaratulaTitleColor', gc('caratula_title_color',    'caratulaTitleColor'));
        _s('cfgCaratulaTitleColorHex',gc('caratula_title_color',  'caratulaTitleColor'));
        _s('cfgCaratulaAutorSize',  gc('caratula_autor_size',     'caratulaAutorSize'));
        _s('cfgCaratulaAutorColor', gc('caratula_autor_color',    'caratulaAutorColor'));
        _s('cfgCaratulaAutorColorHex',gc('caratula_autor_color',  'caratulaAutorColor'));
        _s('cfgCaratulaTitleX',     gc('caratula_title_x',        'caratulaTitleX'));
        _s('cfgCaratulaTitleY',     gc('caratula_title_y',        'caratulaTitleY'));
        const autorField = document.getElementById('caratulaAutorField');
        if (autorField) autorField.style.display = gc('caratula_incluir_autor','caratulaIncluirAutor') ? 'block' : 'none';

        // Contratapa
        _sb('enableContratapa', gc('contratapa_enabled', 'contratapaEnabled'));

        // Encabezado
        _sb('enableEncabezado',  gc('encabezado_enabled',    'encabezadoEnabled'));
        _s('headerLeft',         gc('encabezado_left',       'encabezadoLeft'));
        _s('headerCenter',       gc('encabezado_center',     'encabezadoCenter'));
        _s('headerRight',        gc('encabezado_right',      'encabezadoRight'));
        _s('headerLineStyle',    gc('encabezado_line_style', 'encabezadoLineStyle'));
        _s('headerLineColor',    gc('encabezado_line_color', 'encabezadoLineColor'));
        _s('headerLineColorHex', gc('encabezado_line_color', 'encabezadoLineColor'));

        // Footer
        _sb('enableFooter',      gc('footer_enabled',       'footerEnabled'));
        _s('footerLeft',         gc('footer_left',          'footerLeft'));
        _s('footerCenter',       gc('footer_center',        'footerCenter'));
        _s('footerRight',        gc('footer_right',         'footerRight'));
        _sb('footerPageNumbers', gc('footer_page_numbers',  'footerPageNumbers'));
        _s('footerPageNumPos',   gc('footer_page_num_pos',  'footerPageNumPos'));
        _s('footerLineStyle',    gc('footer_line_style',    'footerLineStyle'));
        _s('footerLineColor',    gc('footer_line_color',    'footerLineColor'));
        _s('footerLineColorHex', gc('footer_line_color',    'footerLineColor'));

        // Hoja Final
        _sb('enableHojaFinal',   gc('hoja_final_enabled', 'hojaFinalEnabled'));
        _s('hojaFinalTexto',     gc('hoja_final_texto',   'hojaFinalTexto'));
        _s('cfgHojaFinalSize',   gc('hoja_final_size',    'hojaFinalSize'));
        _s('cfgHojaFinalColor',  gc('hoja_final_color',   'hojaFinalColor'));
        _s('cfgHojaFinalColorHex',gc('hoja_final_color',  'hojaFinalColor'));

        // Filename
        _s('filePrefix', gc('file_prefix', 'filePrefix'));
        _s('fileSuffix', gc('file_suffix', 'fileSuffix'));
    }

    // ── Apply images from saved data ──────────────────────────────
    function applyImages(images) {
        if (!images) return;
        const zoneMap = {
            caratula: { zoneId: 'caratulaImgDropZone', previewId: 'caratulaImgPreview' },
            contratapa: { zoneId: 'contratapaImgDropZone', previewId: 'contratapaImgPreview' },
            header: { zoneId: 'headerDropZone', previewId: 'headerPreview' },
            footer: { zoneId: 'footerImgDropZone', previewId: 'footerImgPreview' },
            hojaFinal: { zoneId: 'hojaFinalImgDropZone', previewId: 'hojaFinalImgPreview' },
        };

        Object.entries(images).forEach(([key, imgData]) => {
            if (!imgData || !imgData.dataUrl) return;
            const { zoneId, previewId } = zoneMap[key] || {};
            if (!zoneId) return;

            const zone = document.getElementById(zoneId);
            const preview = document.getElementById(previewId);

            // Restore to global store
            window._edtechImgStore[key] = imgData;

            const isRaster = imgData.dataUrl.startsWith('data:image/') &&
                !imgData.filename?.toLowerCase().endsWith('.svg') &&
                !imgData.filename?.toLowerCase().endsWith('.emf') &&
                !imgData.filename?.toLowerCase().endsWith('.wmf');

            if (zone) {
                if (isRaster) {
                    zone.style.backgroundImage = `url(${imgData.dataUrl})`;
                    zone.style.backgroundSize = 'contain';
                    zone.style.backgroundRepeat = 'no-repeat';
                    zone.style.backgroundPosition = 'center';
                    if (preview) preview.style.opacity = '0';
                } else {
                    // Vector — show filename label
                    zone.style.backgroundImage = 'none';
                    if (preview) {
                        preview.style.opacity = '1';
                        preview.innerHTML = `
                            <i class="fa-solid fa-vector-square" style="font-size:16px; color:var(--primary);"></i>
                            <span style="font-size:9px; margin-top:4px; word-break:break-all; text-align:center;">${imgData.filename || key}</span>
                        `;
                    }
                }
            }
        });
    }

    // ── SAVE ──────────────────────────────────────────────────────
    function save() {
        const tool = _detectTool();
        const toolInfo = TOOL_EXT[tool];
        const payload = {
            _meta: {
                version: '2.0',
                tool: toolInfo.label,
                tool_key: tool,
                created: new Date().toISOString(),
                app: 'EDTech Suite v3.5'
            },
            config: collectConfig(),
            images: collectImages()
        };

        const json = JSON.stringify(payload, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const ts = new Date().toISOString().slice(0, 10);
        a.href = url;
        a.download = `edtech-config-${ts}.${toolInfo.ext}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        return toolInfo.ext;
    }

    // ── LOAD ──────────────────────────────────────────────────────
    function load(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const payload = JSON.parse(e.target.result);

                    if (!payload._meta || !payload.config) {
                        reject(new Error('Archivo de configuración inválido (.edd/.edx/.epd)'));
                        return;
                    }

                    // Warn if wrong tool
                    const currentTool = _detectTool();
                    if (payload._meta.tool_key && payload._meta.tool_key !== currentTool) {
                        const msg = `⚠️ Este archivo es para "${payload._meta.tool}" pero estás en "${TOOL_EXT[currentTool].label}".\n¿Continuar de todas formas?`;
                        if (!confirm(msg)) { resolve(null); return; }
                    }

                    applyConfig(payload.config);
                    applyImages(payload.images || {});
                    resolve(payload._meta);
                } catch (err) {
                    reject(new Error(`Error parseando el archivo: ${err.message}`));
                }
            };
            reader.onerror = () => reject(new Error('Error leyendo el archivo'));
            reader.readAsText(file);
        });
    }

    // ── Public API ────────────────────────────────────────────────
    return { save, load, collectConfig, applyConfig, collectImages, applyImages, TOOL_EXT, _detectTool };

})();
