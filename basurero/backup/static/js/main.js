document.addEventListener('DOMContentLoaded', () => {
    // === ELEMENTS ===
    const headerDropZone = document.getElementById('headerDropZone');
    const headerInput = document.getElementById('headerInput');
    const headerPreview = document.getElementById('headerPreview');

    const mainDropZone = document.getElementById('mainDropZone');
    const clipboardZone = document.getElementById('clipboardZone');
    const docInput = document.getElementById('docInput');
    const heroContent = document.querySelector('.hero-content');
    const processBtn = document.getElementById('processBtn');

    // Production Queue
    const productionQueue = document.getElementById('productionQueue');
    const queueList = document.getElementById('queueList');
    const queueCount = document.getElementById('queueCount');
    const clearQueueBtn = document.getElementById('clearQueueBtn');
    const addMoreBtn = document.getElementById('addMoreBtn');

    // Console (Static Panel)
    const consoleLogs = document.getElementById('consoleLogs');

    // === STATE ===
    let selectedFiles = new Map(); // Key: filename, Value: {file, status, resultDocx, resultPdf}
    let paperSize = 'letter';

    // === PAGE IDENTITY ===
    const isExcel = window.location.pathname.includes('/excel');
    const isPdf = window.location.pathname.includes('/pdf');
    const brandSub = document.querySelector('.brand-sub');
    if (brandSub) {
        if (isExcel) brandSub.textContent = 'EXCEL templater';
        else if (isPdf) brandSub.textContent = 'PDF TEMPLATER';
        else brandSub.textContent = 'PDF TEMPLATER';
    }

    // Config Button Logic (Primary Left Sidebar Button)
    const sidebarConfigBtn = document.getElementById('openConfigBtnSidebar');
    const configModal = document.getElementById('configModal');
    const closeConfigBtn = document.getElementById('closeConfigBtn');
    const saveConfigBtn = document.getElementById('saveConfigBtn');

    if (sidebarConfigBtn && configModal) {
        sidebarConfigBtn.addEventListener('click', () => {
            configModal.classList.add('active');
        });
    }

    if (closeConfigBtn && configModal) {
        closeConfigBtn.addEventListener('click', () => {
            configModal.classList.remove('active');
        });
        // Click outside to close
        configModal.addEventListener('click', (e) => {
            if (e.target === configModal) configModal.classList.remove('active');
        });
    }

    if (saveConfigBtn && configModal) {
        saveConfigBtn.addEventListener('click', () => {
            configModal.classList.remove('active');
            log('Configuración aplicada.', 'success');
        });
    }

    // ── EDTech Config File: Cargar / Guardar ─────────────────────
    const importTemplateBtn = document.getElementById('importTemplateBtn');
    const exportTemplateBtn = document.getElementById('exportTemplateBtn');
    const templateInput = document.getElementById('templateInput');

    if (typeof EDTechConfig !== 'undefined') {
        const tool = EDTechConfig._detectTool();
        const toolInfo = EDTechConfig.TOOL_EXT[tool];

        // Update accept attribute and tooltip with correct extension
        if (templateInput) {
            templateInput.accept = tool === 'pdf' ? `.${toolInfo.ext},.edd` : `.${toolInfo.ext}`;
        }
        if (exportTemplateBtn) exportTemplateBtn.title = `Guardar configuración (.${toolInfo.ext})`;
        if (importTemplateBtn) importTemplateBtn.title = `Cargar configuración (.${toolInfo.ext})`;

        // GUARDAR
        if (exportTemplateBtn) {
            exportTemplateBtn.addEventListener('click', () => {
                try {
                    const ext = EDTechConfig.save();
                    log(`Configuración guardada como .${ext}`, 'success');
                } catch (err) {
                    log(`Error guardando configuración: ${err.message}`, 'error');
                }
            });
        }

        // CARGAR
        if (importTemplateBtn && templateInput) {
            importTemplateBtn.addEventListener('click', () => templateInput.click());
            templateInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                try {
                    importTemplateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Cargando...';
                    const meta = await EDTechConfig.load(file);
                    if (meta) {
                        log(`Configuración cargada: ${meta.tool} (${meta.created?.slice(0, 10)})`, 'success');
                        // ── Diagnostic: verify form fields were set ──
                        console.log('[EPD] Plantilla cargada. Valores aplicados en el formulario:', {
                            font:          document.getElementById('cfgFont')?.value,
                            lineSpacing:   document.getElementById('cfgLineSpacing')?.value,
                            h2Color:       document.getElementById('cfgH2Color')?.value,
                            marginTop:     document.getElementById('cfgMarginTop')?.value,
                            tableHdrBg:    document.getElementById('cfgTableHeaderBg')?.value,
                            enableCaratula:document.getElementById('enableCaratula')?.checked,
                            caratulaImg:   !!(window._edtechImgStore?.caratula),
                        });
                    }
                } catch (err) {
                    log(`Error cargando configuración: ${err.message}`, 'error');
                    console.error('[EPD] Error al cargar plantilla:', err);
                } finally {
                    importTemplateBtn.innerHTML = '<i class="fa-solid fa-file-import"></i> Cargar';
                    templateInput.value = '';
                }
            });
        }
    }

    // === TABS LOGIC ===
    const tabBtns = document.querySelectorAll('.tab-btn');
    if (tabBtns.length > 0) {
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Remove active from all siblings
                const parent = btn.parentElement;
                parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Hide all tab contents in this modal
                const modalBody = btn.closest('.config-window').querySelector('.config-body');
                modalBody.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden-tab'));

                // Show target
                const targetId = btn.getAttribute('data-tab');
                const targetDisplay = document.getElementById(targetId);
                if (targetDisplay) targetDisplay.classList.remove('hidden-tab');
            });
        });
    }

    // Toggle Visibility based on Tool
    if (isExcel) {
        const paperGroup = document.getElementById('paperSizeGroup');
        if (paperGroup) paperGroup.style.display = 'none';

        const excelRow = document.getElementById('excelBoldRow');
        if (excelRow) excelRow.style.display = 'flex';
    }

    // Initialize modal image uploads and toggles
    setTimeout(() => {
        // Register all image upload zones using the EDTech config system
        // edtechRegisterImgUpload stores ALL formats (PNG/JPG/SVG/EMF/WMF) as base64
        // in window._edtechImgStore for save/load via EDTechConfig.save()
        if (typeof edtechRegisterImgUpload === 'function') {
            edtechRegisterImgUpload('caratula', 'caratulaImgDropZone', 'caratulaImgInput', 'caratulaImgPreview');
            edtechRegisterImgUpload('contratapa', 'contratapaImgDropZone', 'contratapaImgInput', 'contratapaImgPreview');
            edtechRegisterImgUpload('header', 'headerDropZone', 'headerInput', 'headerPreview');
            edtechRegisterImgUpload('footer', 'footerImgDropZone', 'footerImgInput', 'footerImgPreview');
            edtechRegisterImgUpload('hojaFinal', 'hojaFinalImgDropZone', 'hojaFinalImgInput', 'hojaFinalImgPreview');
        }

        // Author toggle show/hide
        const autorToggle = document.getElementById('caratulaIncluirAutor');
        const autorField = document.getElementById('caratulaAutorField');
        if (autorToggle && autorField) {
            autorToggle.addEventListener('change', () => {
                autorField.style.display = autorToggle.checked ? 'block' : 'none';
            });
        }

        // ═══ CARÁTULA VISUAL POSITION EDITOR ═══
        (function initCaratulaPositionEditor() {
            const container = document.getElementById('caratulaPreviewContainer');
            if (!container) return;

            const dragLabels = container.querySelectorAll('.caratula-drag-label');
            const sliderX = document.getElementById('cfgCaratulaTitleX');
            const sliderY = document.getElementById('cfgCaratulaTitleY');
            const xVal = document.getElementById('cfgCaratulaTitleXVal');
            const yVal = document.getElementById('cfgCaratulaTitleYVal');

            // --- Draggable logic ---
            let activeDrag = null;
            let startMouseX, startMouseY, startLeft, startTop;

            dragLabels.forEach(label => {
                label.addEventListener('mouseenter', () => label.style.borderColor = '#3b82f6');
                label.addEventListener('mouseleave', () => { if (activeDrag !== label) label.style.borderColor = 'transparent'; });

                label.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    activeDrag = label;
                    label.style.cursor = 'grabbing';
                    label.style.borderColor = '#3b82f6';
                    const rect = container.getBoundingClientRect();
                    startMouseX = e.clientX;
                    startMouseY = e.clientY;
                    startLeft = parseFloat(label.style.left) || 50;
                    startTop = parseFloat(label.style.top) || 50;
                });
            });

            document.addEventListener('mousemove', (e) => {
                if (!activeDrag) return;
                const rect = container.getBoundingClientRect();
                const dx = ((e.clientX - startMouseX) / rect.width) * 100;
                const dy = ((e.clientY - startMouseY) / rect.height) * 100;
                const newX = Math.max(5, Math.min(95, startLeft + dx));
                const newY = Math.max(5, Math.min(95, startTop + dy));
                activeDrag.style.left = newX + '%';
                activeDrag.style.top = newY + '%';

                // Sync sliders if title is being dragged
                if (activeDrag.id === 'caratulaDragTitle' && sliderX && sliderY) {
                    sliderX.value = Math.round(newX);
                    sliderY.value = Math.round(newY);
                    if (xVal) xVal.textContent = Math.round(newX) + '%';
                    if (yVal) yVal.textContent = Math.round(newY) + '%';
                }
            });

            document.addEventListener('mouseup', () => {
                if (activeDrag) {
                    activeDrag.style.cursor = 'grab';
                    activeDrag.style.borderColor = 'transparent';
                    activeDrag = null;
                }
            });

            // --- Slider → Preview sync ---
            if (sliderX) sliderX.addEventListener('input', () => {
                const titleEl = document.getElementById('caratulaDragTitle');
                if (titleEl) titleEl.style.left = sliderX.value + '%';
                if (xVal) xVal.textContent = sliderX.value + '%';
            });
            if (sliderY) sliderY.addEventListener('input', () => {
                const titleEl = document.getElementById('caratulaDragTitle');
                if (titleEl) titleEl.style.top = sliderY.value + '%';
                if (yVal) yVal.textContent = sliderY.value + '%';
            });

            // --- Live text preview from input fields ---
            const fieldMap = {
                'caratulaTitulo': { el: 'caratulaDragTitle', fallback: 'TÍTULO DEL DOCUMENTO', upper: true },
                'caraTulaAutor': { el: 'caratulaDragAutor', fallback: 'Autor (opcional)', upper: false },
                'caraTulaInstitucion': { el: 'caratulaDragInstitucion', fallback: 'INSTITUCIÓN', upper: true },
                'caraTulaFecha': { el: 'caratulaDragFecha', fallback: 'Fecha', upper: false },
            };
            Object.entries(fieldMap).forEach(([inputId, cfg]) => {
                const input = document.getElementById(inputId);
                if (input) {
                    input.addEventListener('input', () => {
                        const dragEl = document.getElementById(cfg.el);
                        if (dragEl) {
                            const txt = input.value || cfg.fallback;
                            dragEl.textContent = cfg.upper ? txt.toUpperCase() : txt;
                        }
                    });
                }
            });

            // --- Sync carátula background image from store ---
            function syncCaratulaBg() {
                const bg = document.getElementById('caratulaPreviewBg');
                if (!bg) return;
                const store = window._edtechImgStore && window._edtechImgStore.caratula;
                if (store && store.dataUrl) {
                    bg.style.backgroundImage = `url(${store.dataUrl})`;
                } else {
                    bg.style.backgroundImage = '';
                }
            }
            // Check periodically for image changes
            setInterval(syncCaratulaBg, 1000);
            syncCaratulaBg();
        })();

        // ═══ LAYOUT PREVIEW SYNC (Diseño Tab) ═══
        (function initLayoutPreview() {
            const page = document.getElementById('layoutPreviewPage');
            if (!page) return;

            const els = {
                marginTop: document.getElementById('lpMarginTop'),
                headerImg: document.getElementById('lpHeaderImg'),
                headerText: document.getElementById('lpHeaderText'),
                headerTextLabel: document.getElementById('lpHeaderTextLabel'),
                marginLeft: document.getElementById('lpMarginLeft'),
                marginRight: document.getElementById('lpMarginRight'),
                contentArea: document.getElementById('lpContentArea'),
            };

            // Page reference: Letter = 792pt tall, 612pt wide
            const PAGE_H = 792;
            const PAGE_W = 612;

            function updatePreview() {
                const mTop = parseFloat(document.getElementById('cfgMarginTop')?.value || 50);
                const mBottom = parseFloat(document.getElementById('cfgMarginBottom')?.value || 50);
                const mLeft = parseFloat(document.getElementById('cfgMarginLeft')?.value || 50);
                const mRight = parseFloat(document.getElementById('cfgMarginRight')?.value || 50);
                const imgH = parseFloat(document.getElementById('cfgHeaderImgHeight')?.value || 40);
                const headerType = document.getElementById('cfgHeaderType')?.value || 'title';

                // Convert pt → % of page
                const topPct = (mTop / PAGE_H * 100);
                const bottomPct = (mBottom / PAGE_H * 100);
                const leftPct = (mLeft / PAGE_W * 100);
                const rightPct = (mRight / PAGE_W * 100);
                const imgHPct = (imgH / PAGE_H * 100);

                // Update margin zones
                if (els.marginTop) els.marginTop.style.height = topPct + '%';
                if (els.marginLeft) els.marginLeft.style.width = leftPct + '%';
                if (els.marginRight) els.marginRight.style.width = rightPct + '%';

                // Header image zone
                const hasHeaderImg = window._edtechImgStore?.header?.dataUrl;
                if (els.headerImg) {
                    els.headerImg.style.top = topPct + '%';
                    els.headerImg.style.left = leftPct + '%';
                    els.headerImg.style.right = rightPct + '%';
                    els.headerImg.style.height = imgHPct + '%';
                    els.headerImg.style.display = hasHeaderImg ? 'flex' : 'none';
                    if (hasHeaderImg) {
                        els.headerImg.style.backgroundImage = `url(${hasHeaderImg})`;
                        els.headerImg.style.backgroundSize = 'cover';
                        els.headerImg.style.backgroundPosition = 'center';
                        els.headerImg.querySelector('span').style.display = 'none';
                    }
                }

                // Header text
                const headerTextTop = hasHeaderImg ? (topPct + imgHPct + 0.5) : (topPct + 0.5);
                if (els.headerText) {
                    els.headerText.style.top = headerTextTop + '%';
                    els.headerText.style.left = leftPct + '%';
                    els.headerText.style.right = rightPct + '%';
                    els.headerText.style.display = headerType !== 'none' ? 'block' : 'none';
                }
                if (els.headerTextLabel) {
                    const labels = { 'title': 'Título del Documento', 'custom': 'Texto personalizado', 'none': '' };
                    els.headerTextLabel.textContent = labels[headerType] || 'Título del Documento';
                }

                // Content area starts after header
                const contentTop = headerTextTop + 3;
                if (els.contentArea) {
                    els.contentArea.style.top = contentTop + '%';
                    els.contentArea.style.left = (leftPct + 1) + '%';
                    els.contentArea.style.right = (rightPct + 1) + '%';
                    els.contentArea.style.bottom = (bottomPct + 2) + '%';
                }
            }

            // Bind to all relevant inputs
            ['cfgMarginTop', 'cfgMarginBottom', 'cfgMarginLeft', 'cfgMarginRight', 'cfgHeaderImgHeight', 'cfgHeaderType'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.addEventListener('input', updatePreview);
                if (el) el.addEventListener('change', updatePreview);
            });

            // Sync header image periodically
            setInterval(updatePreview, 1500);
            updatePreview();
        })();
    }, 100);

    // === DRAG & DROP LOGIC (main workspace) ===
    // === DOCUMENTS LOGIC ===

    // Clipboard Logic for PDF Tool
    const pasteBtn = document.getElementById('pasteBtn');
    if (pasteBtn) {
        pasteBtn.addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text && (text.startsWith('http://') || text.startsWith('https://'))) {
                    // Add URL to Queue
                    handleUrl(text.trim());
                } else {
                    log('No se detectó una URL válida en el portapapeles.', 'error');
                }
            } catch (err) {
                log('Permiso de portapapeles denegado o error: ' + err, 'error');
            }
        });
    }

    if (mainDropZone) {
        mainDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
        });
        mainDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            handleDocs(e.dataTransfer.files);
        });
    }

    if (docInput) {
        docInput.addEventListener('change', (e) => handleDocs(e.target.files));
    }

    function handleUrl(url) {
        if (!selectedFiles.has(url)) {
            selectedFiles.set(url, {
                type: 'url',
                url: url,
                status: 'pend',
                resultPdf: null
            });
            renderQueue();
            log(`URL añadida: ${url}`, 'success');
        } else {
            log('La URL ya está en la cola.', 'info');
        }
    }

    function handleDocs(files) {
        if (!files || files.length === 0) return;

        const isExcel = window.location.pathname.includes('/excel');
        const allowedExt = isExcel ? '.xlsx' : '.docx';

        let addedCount = 0;
        Array.from(files).forEach(f => {
            if (f.name.toLowerCase().endsWith(allowedExt) && !selectedFiles.has(f.name)) {
                selectedFiles.set(f.name, {
                    file: f,
                    status: 'pend',
                    resultDocx: null,
                    resultPdf: null,
                    resultPath: null // Added for Excel result
                });
                addedCount++;
            } else if (!f.name.toLowerCase().endsWith(allowedExt)) {
                log(`Ignorado: ${f.name} (Requiere ${allowedExt})`, 'error');
            }
        });

        if (addedCount > 0) {
            renderQueue();
            log(`${addedCount} archivo(s) añadidos.`, 'success');
        } else if (selectedFiles.size === 0) {
            log('No se añadieron archivos válidos.', 'error');
        } else {
            renderQueue();
        }
    }

    // ── Smart URL Classifier ──────────────────────────────────────────────────
    // Predicts possible extraction issues before processing starts.
    function classifyUrl(url) {
        try {
            const u = new URL(url);
            const host = u.hostname.replace('www.', '').toLowerCase();
            const path = u.pathname.toLowerCase();

            // HIGH RISK — login walls (will likely fail)
            const loginDomains = [
                'facebook.com', 'fb.com', 'linkedin.com', 'instagram.com',
                'twitter.com', 'x.com', 'tiktok.com', 'pinterest.com',
                'accounts.google.com', 'login.', 'signin.'
            ];
            if (loginDomains.some(d => host === d || host.endsWith('.' + d))) {
                return { risk: 'high', label: '⚠ Login requerido', color: '#dc2626', bg: '#fee2e2',
                         tip: 'Esta red social requiere inicio de sesión para acceder al contenido.' };
            }

            // HIGH RISK — paywall / subscription sites
            const paywallPatterns = ['wsj.com','ft.com','hbr.org','economist.com','nytimes.com',
                                     'bloomberg.com','medium.com'];
            if (paywallPatterns.some(d => host.includes(d))) {
                return { risk: 'high', label: '🔒 Paywall', color: '#dc2626', bg: '#fee2e2',
                         tip: 'Este sitio puede requerir suscripción de pago.' };
            }

            // MEDIUM RISK — JS-heavy sites (Playwright needed, slower)
            const jsHeavy = ['canva.com','miro.com','notion.so','figma.com','app.','dashboard.',
                              'lawsofux.com','quicksprout.com'];
            if (jsHeavy.some(d => host.includes(d) || path.includes(d))) {
                return { risk: 'medium', label: '⚙ JS dinámico', color: '#d97706', bg: '#fef3c7',
                         tip: 'Este sitio usa JavaScript dinámico. El proceso tomará más tiempo.' };
            }

            // MEDIUM RISK — academic / complex HTML
            const academic = ['scielo.org','redalyc.org','researchgate.net','academia.edu',
                               'dialnet.unirioja.es','jstor.org','springer.com','tandfonline.com'];
            if (academic.some(d => host.includes(d))) {
                return { risk: 'medium', label: '📄 Académico', color: '#7c3aed', bg: '#ede9fe',
                         tip: 'Artículo académico — extracción compleja, puede tener metadata extra.' };
            }

            // MEDIUM RISK — URL with 404-prone patterns
            if (path.includes('/404') || path.includes('/not-found') || path.includes('/error')) {
                return { risk: 'high', label: '❌ Posible 404', color: '#dc2626', bg: '#fee2e2',
                         tip: 'La URL parece apuntar a una página de error.' };
            }

            // MEDIUM RISK — very long / encoded URLs (often file downloads, not web pages)
            if (url.length > 300 || (url.match(/%[0-9A-Fa-f]{2}/g) || []).length > 10) {
                return { risk: 'medium', label: '⚡ URL compleja', color: '#d97706', bg: '#fef3c7',
                         tip: 'URL muy larga o con muchos caracteres codificados. Podría ser un archivo o descarga.' };
            }

            // UTM params — usually OK but note they are stripped
            if (u.searchParams.has('utm_source') || u.searchParams.has('ref_')) {
                return { risk: 'low', label: '✓ UTM (limpiado)', color: '#059669', bg: '#d1fae5',
                         tip: 'Los parámetros UTM/ref serán eliminados antes de descargar.' };
            }

            return { risk: 'ok', label: '', color: '', bg: '', tip: '' };
        } catch(e) {
            return { risk: 'high', label: '❌ URL inválida', color: '#dc2626', bg: '#fee2e2',
                     tip: 'Esta URL no pudo ser analizada. Verifica el formato.' };
        }
    }

    function renderQueue() {

        // Toggle Visibility
        if (selectedFiles.size > 0) {
            if (mainDropZone) mainDropZone.style.display = 'none';
            if (clipboardZone) clipboardZone.style.display = 'none';
            productionQueue.classList.add('visible');
            productionQueue.style.display = 'flex';
            processBtn.disabled = false;
        } else {
            productionQueue.classList.remove('visible');
            productionQueue.style.display = 'none';
            if (mainDropZone) mainDropZone.style.display = 'flex';
            if (clipboardZone) clipboardZone.style.display = 'flex';
            processBtn.disabled = true;
        }

        // Show/hide PDF stamp options group based on queue contents
        const hasPdfStamp = [...selectedFiles.values()].some(d => d.type === 'pdf_stamp');
        const stampOptGroup = document.getElementById('pdfStampOptionsGroup');
        if (stampOptGroup) stampOptGroup.style.display = hasPdfStamp ? 'block' : 'none';

        queueCount.innerText = selectedFiles.size;
        queueList.innerHTML = '';

        const isExcel = window.location.pathname.includes('/excel');
        const isPdf = window.location.pathname.includes('/pdf');

        selectedFiles.forEach((data, name) => {
            // Determine Info display
            let infoHtml = '';
            let iconClass = 'fa-file';
            let iconColor = '';

            if (data.type === 'url') {
                iconClass = 'fa-globe';
                const _risk = classifyUrl(data.url);
                iconColor = _risk.risk === 'high' ? '#dc2626' : (_risk.risk === 'medium' ? '#d97706' : 'var(--primary)');
                const _riskBadge = _risk.label ? `<span title="${_risk.tip}" style="font-size:0.68rem; background:${_risk.bg}; color:${_risk.color}; border-radius:4px; padding:1px 6px; font-weight:600; cursor:help;">${_risk.label}</span>` : '';
                infoHtml = `
                    <div class="q-info" style="display:flex; align-items:center; gap:15px; flex:1;">
                        <div style="width:40px; height:40px; background:var(--bg-app); border-radius:8px; display:flex; align-items:center; justify-content:center;">
                             <i class="fa-solid ${iconClass}" style="color:${iconColor}; font-size:1.2rem;"></i>
                        </div>
                        <div style="display:flex; flex-direction:column; min-width:0;">
                             <span class="q-name" style="font-weight:500; color:var(--text-color); word-break:break-all; font-size:0.9rem;">${data.url}</span>
                             <div style="display:flex; gap:5px; margin-top:3px; flex-wrap:wrap; align-items:center;">
                                 <span style="font-size:0.75rem; color:var(--text-muted);">Sitio Web</span>
                                 ${_riskBadge}
                             </div>
                        </div>
                    </div>
                `;
            } else if (data.type === 'xls_url') {
                iconClass = 'fa-globe';
                iconColor = '#10b981';
                const _risk2 = classifyUrl(data.url);
                const _riskBadge2 = _risk2.label ? `<span title="${_risk2.tip}" style="font-size:0.68rem; background:${_risk2.bg}; color:${_risk2.color}; border-radius:4px; padding:1px 6px; font-weight:600; cursor:help;">${_risk2.label}</span>` : '';
                infoHtml = `
                    <div class="q-info" style="display:flex; align-items:center; gap:15px; flex:1;">
                        <div style="width:40px; height:40px; background:var(--bg-app); border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                             <i class="fa-solid fa-globe" style="color:#10b981; font-size:1.2rem;"></i>
                        </div>
                        <div style="display:flex; flex-direction:column; min-width:0;">
                             <span class="q-name" style="font-weight:500; color:var(--text-color); word-break:break-all; font-size:0.85rem;">${data.url}</span>
                             <div style="display:flex; gap:5px; margin-top:3px; flex-wrap:wrap;">
                                 <span style="font-size:0.7rem; background:#d1fae5; color:#065f46; border-radius:4px; padding:1px 6px; font-weight:600;">
                                     <i class="fa-solid fa-folder" style="margin-right:3px;"></i>${data.xlsFolder}
                                 </span>
                                 <span style="font-size:0.7rem; background:#e0f2fe; color:#0369a1; border-radius:4px; padding:1px 6px; font-weight:600;">
                                     ${data.xlsPrefix}
                                 </span>
                                 ${_riskBadge2}
                             </div>
                        </div>
                    </div>
                `;
            } else {
                // File (docx, xlsx, or pdf_stamp)
                const sizeMB = (data.file.size / 1024 / 1024).toFixed(2);
                const isPdfStamp = data.type === 'pdf_stamp';
                iconClass = isPdfStamp ? 'fa-file-pdf' : (isExcel ? 'fa-file-excel' : 'fa-file-word');
                iconColor = isPdfStamp ? '#7c3aed' : (isExcel ? '#10b981' : '#3b82f6');
                const stampBadge = isPdfStamp
                    ? `<span style="font-size:0.68rem; background:#ede9fe; color:#7c3aed; border-radius:4px; padding:1px 6px; font-weight:600;">✦ Estampar Plantilla</span>`
                    : '';
                infoHtml = `
                    <div class="q-info" style="display:flex; align-items:center; gap:15px; flex:1;">
                         <div style="width:40px; height:40px; background:var(--bg-app); border-radius:8px; display:flex; align-items:center; justify-content:center;">
                             <i class="fa-solid ${iconClass}" style="color:${iconColor}; font-size:1.2rem;"></i>
                        </div>
                        <div style="display:flex; flex-direction:column; gap:2px;">
                            <span class="q-name" style="font-weight:500; color:var(--text-color); font-size:0.9rem;">${isPdfStamp ? data.filename : name}</span>
                            <div style="display:flex; gap:5px; align-items:center;">
                                <span class="q-size" style="font-size:0.75rem; color:var(--text-muted);">${sizeMB} MB</span>
                                ${stampBadge}
                            </div>
                        </div>
                    </div>
                `;
            }


            let statusBadge = '<div class="q-status">Pendiente</div>';
            if (data.status === 'processing') {
                const pct = data.progress || 0;
                const elapsed = data.elapsedSec || 0;
                let timeLabel = '';
                if (elapsed > 0) {
                    timeLabel = `Tiempo: ${elapsed}s`;
                }
                statusBadge = `
                    <div class="q-status processing" style="flex-direction:column; gap:4px; min-width:120px;">
                        <span>Procesando... ${pct}%</span>
                        <div style="width:100%; height:4px; background:#e2e8f0; border-radius:2px; overflow:hidden;">
                            <div style="height:100%; width:${pct}%; background:var(--primary); border-radius:2px; transition:width 0.4s ease;"></div>
                        </div>
                        ${timeLabel ? `<span style="font-size:0.7rem; color:var(--text-muted);">${timeLabel}</span>` : ''}
                    </div>`;
            }
            if (data.status === 'done') statusBadge = '<div class="q-status done">Completado</div>';
            if (data.status === 'error') statusBadge = '<div class="q-status error">Error</div>';

            let actions = '';
            if (data.status === 'done') {
                if (isPdf && data.resultPath) {
                    // PDF Saved Server-Side
                    actions = `
                        <div style="display:flex; gap:5px;">
                            <button class="btn-mini status-done" title="${data.resultPath}" onclick="alert('Archivo guardado en: ' + this.title)">
                                <i class="fa-solid fa-check"></i> GUARDADO
                            </button>
                        </div>
                    `;
                } else if (isPdf && data.resultPdfUrl) {
                    // Fallback for Blob (Legacy)
                    actions = `
                        <div style="display:flex; gap:5px;">
                            <a href="${data.resultPdfUrl}" download="${data.resultFilename}" class="btn-mini status-done" title="Descargar PDF">
                                <i class="fa-solid fa-file-pdf"></i> GUARDAR PDF
                            </a>
                        </div>
                    `;
                } else if (isExcel) {
                    // Excel Result (Server Side)
                    const downloadName = data.resultPath || `FORMAT_${name}`;
                    actions = `
                        <div style="display:flex; gap:5px;">
                             <button class="btn-mini status-done" title="Archivo guardado" onclick="alert('Archivo guardado en la carpeta de salida.')">
                                <i class="fa-solid fa-check"></i> GUARDADO
                            </button>
                        </div>
                    `;
                } else {
                    // Docs Result (Server Side)
                    const savedPath = data.resultPath || 'la carpeta de salida';
                    actions = `
                        <div style="display:flex; gap:5px;">
                             <button class="btn-mini status-done" title="${savedPath}" onclick="alert('Archivo guardado en: ' + this.title)">
                                <i class="fa-solid fa-check"></i> GUARDADO
                            </button>
                        </div>
                    `;
                }
            } else {
                actions = `<div class="btn-mini disabled"><i class="fa-solid fa-clock"></i> Esperando</div>`;
            }

            const div = document.createElement('div');
            div.className = 'queue-item';
            div.style.flexWrap = 'wrap';

            // For pdf_stamp items: add inline source URL field
            const sourceUrlRow = data.type === 'pdf_stamp' ? `
                <div style="width:100%; padding:6px 0 2px 0; display:flex; gap:6px; align-items:center; border-top:1px solid var(--border-color); margin-top:4px;">
                    <i class="fa-solid fa-link" style="color:#7c3aed; font-size:0.8rem; flex-shrink:0;"></i>
                    <input
                        class="source-url-input"
                        type="url"
                        data-key="${name.replace(/"/g,'&quot;')}"
                        placeholder="Link del original (para cita APA)..."
                        value="${(data.sourceUrl || '').replace(/"/g,'&quot;')}"
                        style="flex:1; padding:4px 8px; font-size:0.78rem; border:1px solid #7c3aed44;
                               border-radius:4px; background:var(--bg-panel); color:var(--text-main);
                               outline:none; font-family:var(--font-mono);"
                    >
                </div>` : '';

            div.innerHTML = `
                ${infoHtml}
                ${statusBadge}
                <div class="q-actions">${actions}</div>
                ${sourceUrlRow}
            `;

            // Wire the source URL input to persist in selectedFiles data
            if (data.type === 'pdf_stamp') {
                const urlInput = div.querySelector('.source-url-input');
                if (urlInput) {
                    urlInput.addEventListener('input', (e) => {
                        const k = e.target.dataset.key;
                        if (selectedFiles.has(k)) {
                            selectedFiles.get(k).sourceUrl = e.target.value.trim();
                        }
                    });
                }
            }

            queueList.appendChild(div);

        });
    }

    // === QUEUE ACTIONS ===
    if (clearQueueBtn) {
        clearQueueBtn.addEventListener('click', () => {
            selectedFiles.clear();
            renderQueue();
            const ga = document.getElementById('globalActions');
            if (ga) ga.style.display = 'none';
            log('Cola vaciada.', 'info');
        });
    }

    if (addMoreBtn) {
        addMoreBtn.addEventListener('click', () => {
            // Show URL input bar (defined later in PDF tool section)
            const bar = document.getElementById('urlInlineBar');
            const inp = document.getElementById('urlInlineInput');
            if (bar) { bar.style.display = 'flex'; }
            if (inp) { inp.value = ''; inp.focus(); }
        });
    }

    // === ADVANCED CONFIG LOGIC ===
    const openConfigBtn = document.getElementById('openConfigBtn');

    if (openConfigBtn && configModal) {
        openConfigBtn.addEventListener('click', () => {
            configModal.classList.add('active');
        });
    }

    // TEMPLATE LOGIC → handled by EDTechConfig module (edtech_config.js)
    // Cargar / Guardar buttons are wired above via EDTechConfig.save() / EDTechConfig.load()

    // Helper: set a color picker + its hex text sibling, and refresh the swatch
    function setColorField(pickerId, hexId, value) {
        if (!value) return;
        const v = value.startsWith('#') ? value : '#' + value;
        const picker = document.getElementById(pickerId);
        const hex = hexId ? document.getElementById(hexId) : null;
        if (picker) { picker.value = v; picker.dispatchEvent(new Event('input')); }
        if (hex) hex.value = v.toUpperCase();
    }

    function applyTemplateConfig(cfg) {
        if (!cfg) return;

        // General
        const fontEl = document.getElementById('cfgFont');
        if (fontEl && cfg.font_name) fontEl.value = cfg.font_name;
        const fsEl = document.getElementById('cfgFontSize');
        if (fsEl && cfg.font_size) fsEl.value = cfg.font_size;
        const lsEl = document.getElementById('cfgLineSpacing');
        if (lsEl && cfg.line_spacing) lsEl.value = cfg.line_spacing;
        if (cfg.link_color) setColorField('cfgLinkColor', 'cfgLinkColorHex', cfg.link_color);
        if (cfg.text_align) {
            const el = document.getElementById('cfgTextAlignment');
            if (el) el.value = cfg.text_align;
        }
        // Layout (PDF)
        if (cfg.header_type) { const el = document.getElementById('cfgHeaderType'); if (el) el.value = cfg.header_type; }
        if (cfg.header_text) { const el = document.getElementById('cfgHeaderText'); if (el) el.value = cfg.header_text; }
        if (cfg.page_num_format) { const el = document.getElementById('cfgPageNumFormat'); if (el) el.value = cfg.page_num_format; }

        // Headings
        if (cfg.headings) {
            const h1 = cfg.headings.h1;
            if (h1) {
                if (h1.size) { const el = document.getElementById('cfgH1Size'); if (el) el.value = h1.size; }
                if (h1.color) setColorField('cfgH1Color', 'cfgH1ColorHex', h1.color);
                if (h1.bold !== undefined) { const el = document.getElementById('cfgH1Bold'); if (el) el.checked = h1.bold; }
            }
            const h2 = cfg.headings.h2;
            if (h2) {
                if (h2.size) { const el = document.getElementById('cfgH2Size'); if (el) el.value = h2.size; }
                if (h2.color) setColorField('cfgH2Color', 'cfgH2ColorHex', h2.color);
                if (h2.bold !== undefined) { const el = document.getElementById('cfgH2Bold'); if (el) el.checked = h2.bold; }
            }
        }

        if (cfg.tables) {
            if (cfg.tables.header_bg) setColorField('cfgTableHeaderBg', 'cfgTableHeaderBgHex', cfg.tables.header_bg);
            if (cfg.tables.header_text) setColorField('cfgTableHeaderText', 'cfgTableHeaderTextHex', cfg.tables.header_text);
            if (cfg.tables.border_color) setColorField('cfgTableBorderColor', 'cfgTableBorderColorHex', cfg.tables.border_color);
            // Docs-specific table fields
            if (cfg.tables.border_v) { const el = document.getElementById('cfgTableBorderV'); if (el) el.value = cfg.tables.border_v; }
            if (cfg.tables.border_h) { const el = document.getElementById('cfgTableBorderH'); if (el) el.value = cfg.tables.border_h; }
            if (cfg.tables.zebra !== undefined) { const el = document.getElementById('cfgTableZebra'); if (el) el.checked = cfg.tables.zebra; }
            if (cfg.tables.align_numbers !== undefined) { const el = document.getElementById('cfgTableNumberAlign'); if (el) el.checked = cfg.tables.align_numbers; }
            // PDF-specific table fields
            if (cfg.tables.row_even) setColorField('cfgTableRowEven', 'cfgTableRowEvenHex', cfg.tables.row_even);
            if (cfg.tables.row_odd) setColorField('cfgTableRowOdd', 'cfgTableRowOddHex', cfg.tables.row_odd);
            if (cfg.tables.border_width !== undefined) { const el = document.getElementById('cfgTableBorderWidth'); if (el) el.value = cfg.tables.border_width; }
            if (cfg.tables.font_size !== undefined) { const el = document.getElementById('cfgTableFontSize'); if (el) el.value = cfg.tables.font_size; }
            if (cfg.tables.padding !== undefined) { const el = document.getElementById('cfgTablePadding'); if (el) el.value = cfg.tables.padding; }
        }

        // Trigger live preview refresh if available
        if (typeof updateTablePreview === 'function') updateTablePreview();
        if (typeof updatePdfTablePreview === 'function') updatePdfTablePreview();
    }

    // === TABLE PREVIEW LOGIC ===
    function updateTablePreview() {
        const bgEl = document.getElementById('cfgTableHeaderBg');
        if (!bgEl) return; // Exit if elements don't exist (e.g. PDF view)

        const bg = bgEl.value;
        const text = document.getElementById('cfgTableHeaderText').value;
        const borderColor = document.getElementById('cfgTableBorderColor').value;
        const borderUsageV = document.getElementById('cfgTableBorderV').value;
        const borderUsageH = document.getElementById('cfgTableBorderH').value;
        const zebra = document.getElementById('cfgTableZebra').checked;

        const table = document.querySelector('.preview-table');
        if (!table) return;

        // Apply Styles via CSS Variables
        table.style.setProperty('--preview-bg', bg);
        table.style.setProperty('--preview-text', text);

        function getBorderCss(type) {
            if (type === 'none') return 'none';
            if (type === 'thick') return '2px solid ' + borderColor;
            if (type === 'dashed') return '1px dashed ' + borderColor;
            return '1px solid ' + borderColor;
        }

        const borderV = getBorderCss(borderUsageV);
        const borderH = getBorderCss(borderUsageH);

        table.style.setProperty('--preview-border-v', borderV);
        table.style.setProperty('--preview-border-h', borderH);

        // Zebra Striping
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach((row, index) => {
            if (zebra && index % 2 !== 0) {
                row.style.background = '#f1f5f9';
            } else {
                row.style.background = 'transparent';
            }
        });
    }

    // Listeners for Preview
    const previewInputs = ['cfgTableHeaderBg', 'cfgTableHeaderText', 'cfgTableBorderV', 'cfgTableBorderH', 'cfgTableBorderColor', 'cfgTableZebra'];
    previewInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateTablePreview);
            el.addEventListener('change', updateTablePreview);
        }
    });

    // === COLOR PICKER SYNC ===
    const colorPairs = [
        { picker: 'cfgLinkColor', hex: 'cfgLinkColorHex' },
        { picker: 'cfgH1Color', hex: 'cfgH1ColorHex' },
        { picker: 'cfgH2Color', hex: 'cfgH2ColorHex' },
        { picker: 'cfgTableHeaderBg', hex: 'cfgTableHeaderBgHex' },
        { picker: 'cfgTableHeaderText', hex: 'cfgTableHeaderTextHex' },
        { picker: 'cfgTableBorderColor', hex: 'cfgTableBorderColorHex' },
        { picker: 'cfgApaBg', hex: 'cfgApaBgHex' },
        { picker: 'cfgApaBorder', hex: 'cfgApaBorderHex' },
        { picker: 'cfgApaTextColor', hex: 'cfgApaTextColorHex' }
    ];

    colorPairs.forEach(pair => {
        const pEl = document.getElementById(pair.picker);
        const hEl = document.getElementById(pair.hex);

        if (pEl && hEl) {
            // Picker -> Hex
            pEl.addEventListener('input', () => {
                hEl.value = pEl.value.toUpperCase();
                updateTablePreview(); // Update preview if applicable
            });
            pEl.addEventListener('change', () => {
                hEl.value = pEl.value.toUpperCase();
                updateTablePreview();
            });

            // Hex -> Picker
            hEl.addEventListener('input', () => {
                let val = hEl.value;
                if (!val.startsWith('#')) {
                    val = '#' + val;
                }
                const isValidHex = /^#[0-9A-F]{6}$/i.test(val);
                if (isValidHex) {
                    pEl.value = val;
                    updateTablePreview();
                }
            });
        }
    });

    // Tab Logic
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.add('hidden-tab'));

            // Activate clicked tab
            tab.classList.add('active');
            const targetId = tab.dataset.tab;
            document.getElementById(targetId).classList.remove('hidden-tab');
        });
    });

    if (openConfigBtn && configModal) {
        openConfigBtn.addEventListener('click', () => {
            configModal.classList.add('active');
        });
    }

    if (openConfigBtn) {
        openConfigBtn.addEventListener('click', () => {
            configModal.classList.add('active');
        });
    }
    // Also bind the new Sidebar button if not done above (redundancy check)
    // The previous edit handled openConfigBtnSidebar


    if (closeConfigBtn) {
        closeConfigBtn.addEventListener('click', () => {
            configModal.classList.remove('active');
        });
    }

    if (configModal) {
        configModal.addEventListener('click', (e) => {
            if (e.target === configModal) configModal.classList.remove('active');
        });
    }

    if (saveConfigBtn) {
        saveConfigBtn.addEventListener('click', () => {
            configModal.classList.remove('active');
            log('Configuración guardada (se aplicará al procesar)', 'success');
        });
    }

    // Live Table Preview in config modal
    function updateTablePreview() {
        const headerBg = document.getElementById('cfgTableHeaderBg');
        const headerText = document.getElementById('cfgTableHeaderText');
        const rowEven = document.getElementById('cfgTableRowEven');
        const rowOdd = document.getElementById('cfgTableRowOdd');
        const borderColor = document.getElementById('cfgTableBorderColor');
        const borderW = document.getElementById('cfgTableBorderWidth');
        const fontSize = document.getElementById('cfgTableFontSize');
        const padding = document.getElementById('cfgTablePadding');
        if (!headerBg) return;

        const hRow = document.getElementById('previewHeaderRow');
        const r1 = document.getElementById('previewRow1');
        const r2 = document.getElementById('previewRow2');
        const tbl = document.getElementById('tablePreviewPdf');
        if (!hRow || !r1 || !r2 || !tbl) return;

        const bdr = `${borderW.value}px solid ${borderColor.value}`;
        const fs = fontSize.value + 'px';
        const pad = padding.value + 'px';

        // Header row
        hRow.style.background = headerBg.value;
        hRow.style.color = headerText.value;
        hRow.style.fontSize = fs;
        Array.from(hRow.cells).forEach(c => { c.style.padding = pad; c.style.borderBottom = bdr; });

        // Data rows (zebra)
        r1.style.background = rowOdd.value;
        r1.style.fontSize = fs;
        Array.from(r1.cells).forEach(c => { c.style.padding = pad; });

        r2.style.background = rowEven.value;
        r2.style.fontSize = fs;
        Array.from(r2.cells).forEach(c => { c.style.padding = pad; });

        tbl.style.border = bdr;
        tbl.style.outline = bdr;
    }

    // Wire all table config inputs to live preview
    ['cfgTableHeaderBg', 'cfgTableHeaderText', 'cfgTableRowEven', 'cfgTableRowOdd',
        'cfgTableBorderColor', 'cfgTableBorderWidth', 'cfgTableFontSize', 'cfgTablePadding'
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateTablePreview);
    });

    // Also wire hex inputs to color pickers for table fields
    [['cfgTableHeaderBg', 'cfgTableHeaderBgHex'], ['cfgTableHeaderText', 'cfgTableHeaderTextHex'],
    ['cfgTableRowEven', 'cfgTableRowEvenHex'], ['cfgTableRowOdd', 'cfgTableRowOddHex'],
    ['cfgTableBorderColor', 'cfgTableBorderColorHex']
    ].forEach(([colorId, hexId]) => {
        const colorEl = document.getElementById(colorId);
        const hexEl = document.getElementById(hexId);
        if (!colorEl || !hexEl) return;
        colorEl.addEventListener('input', () => { hexEl.value = colorEl.value.toUpperCase(); updateTablePreview(); });
        hexEl.addEventListener('input', () => {
            if (/^#[0-9A-Fa-f]{6}$/.test(hexEl.value)) { colorEl.value = hexEl.value; updateTablePreview(); }
        });
    });

    // Run once on load to initialize preview
    updateTablePreview();

    // Capture Advanced Config
    function getAdvancedConfig() {
        const cfgFont = document.getElementById('cfgFont');
        if (!cfgFont) return {};

        const g = (id, fallback) => {
            const el = document.getElementById(id);
            return el ? el.value : fallback;
        };
        const gb = (id, fallback) => {
            const el = document.getElementById(id);
            return el ? el.checked : fallback;
        };

        // Build in the nested format that applyTemplateConfig() expects
        return {
            // Flat keys (used by /process_url and /process endpoints)
            fontPrompt: g('cfgFont', 'Helvetica'),
            fontSize: g('cfgFontSize', 11),
            h1Size: g('cfgH1Size', 26),
            h1Color: g('cfgH1Color', '#000000'),
            h2Size: g('cfgH2Size', 17),
            h2Color: g('cfgH2Color', '#ef4444'),
            linkColor: g('cfgLinkColor', '#ef4444'),
            lineSpacing: g('cfgLineSpacing', 1.5),
            headerType: g('cfgHeaderType', 'title'),
            headerText: g('cfgHeaderText', ''),
            pageNumFormat: g('cfgPageNumFormat', 'page_n_of_m'),
            tableHeaderBg: g('cfgTableHeaderBg', '#1e3a5f'),
            tableHeaderText: g('cfgTableHeaderText', '#ffffff'),
            tableRowEven: g('cfgTableRowEven', '#f0f4f8'),
            tableRowOdd: g('cfgTableRowOdd', '#ffffff'),
            tableBorderColor: g('cfgTableBorderColor', '#cccccc'),
            tableBorderWidth: parseFloat(g('cfgTableBorderWidth', 0.5)),
            tableFontSize: parseInt(g('cfgTableFontSize', 9)),
            tablePadding: parseInt(g('cfgTablePadding', 5)),

            // Nested keys (used by applyTemplateConfig on template load)
            font_name: g('cfgFont', 'Helvetica'),
            font_size: g('cfgFontSize', 11),
            line_spacing: g('cfgLineSpacing', 1.5),
            link_color: g('cfgLinkColor', '#ef4444'),
            headings: {
                h1: {
                    size: g('cfgH1Size', 26),
                    color: g('cfgH1Color', '#000000'),
                    bold: gb('cfgH1Bold', true),
                },
                h2: {
                    size: g('cfgH2Size', 17),
                    color: g('cfgH2Color', '#ef4444'),
                    bold: gb('cfgH2Bold', true),
                },
            },
            tables: {
                header_bg: g('cfgTableHeaderBg', '#1e3a5f'),
                header_text: g('cfgTableHeaderText', '#ffffff'),
                border_color: g('cfgTableBorderColor', '#cccccc'),
                border_v: g('cfgTableBorderV', 'all'),
                border_h: g('cfgTableBorderH', 'all'),
                zebra: gb('cfgTableZebra', true),
                align_numbers: gb('cfgTableNumberAlign', true),
            },
        };
    }





    // === PROCESS LOGIC ===
    if (processBtn) {
        processBtn.addEventListener('click', async () => {
            if (selectedFiles.size === 0) return;

            // If ONLY pdf_stamp items are queued, skip this handler entirely
            // (handled by the PDF stamp handler added separately below)
            const nonStampItems = [...selectedFiles.values()].filter(v => v.type !== 'pdf_stamp');
            if (nonStampItems.length === 0) return;

            // Mark only non-pdf_stamp items as processing immediately for feedback
            selectedFiles.forEach((v, k) => {
                if (v.type !== 'pdf_stamp') {
                    v.status = 'processing';
                    selectedFiles.set(k, v);
                }
            });
            renderQueue();

            processBtn.disabled = true;
            processBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> PROCESANDO...';

            log('Procesando cola...', 'info');

            const isExcel = window.location.pathname.includes('/excel');
            const endpoint = isExcel ? '/process_excel' : '/process';

            const formData = new FormData();
            // Only append non-pdf_stamp files as docs
            selectedFiles.forEach(v => {
                if (v.type !== 'pdf_stamp' && v.file) formData.append('docs', v.file);
            });
            function dataC(config) {
                // Just a helper if needed, but we will put the logic inline or check if it exists
            }

            // Header Type Toggle Logic
            const cfgHeaderType = document.getElementById('cfgHeaderType');
            const customHeaderGroup = document.getElementById('customHeaderGroup');
            if (cfgHeaderType && customHeaderGroup) {
                cfgHeaderType.addEventListener('change', () => {
                    if (cfgHeaderType.value === 'custom') {
                        customHeaderGroup.style.display = 'block';
                    } else {
                        customHeaderGroup.style.display = 'none';
                    }
                });
            }

            // Sync Hex Inputs for PDF Modal
            ['cfgH1Color', 'cfgH2Color', 'cfgLinkColor'].forEach(baseId => {
                const picker = document.getElementById(baseId);
                const text = document.getElementById(baseId + 'Hex');
                if (picker && text) {
                    picker.addEventListener('input', () => text.value = picker.value.toUpperCase());
                    text.addEventListener('change', () => {
                        if (/^#[0-9A-F]{6}$/i.test(text.value)) {
                            picker.value = text.value;
                        }
                    });
                }
            });

            function getAdvancedConfig() {
                // PDF Config — saved in nested format so applyTemplateConfig() can restore it
                const g = (id) => { const el = document.getElementById(id); return el ? el.value : null; };
                const gb = (id) => { const el = document.getElementById(id); return el ? el.checked : null; };
                const gn = (id) => { const el = document.getElementById(id); return el ? parseFloat(el.value) : null; };

                // Get header image from global store (set by edtechRegisterImgUpload)
                const headerImgData = (window._edtechImgStore && window._edtechImgStore.header)
                    ? window._edtechImgStore.header.dataUrl || null
                    : null;

                const config = {
                    // General
                    font_name: g('cfgFont'),
                    font_size: gn('cfgFontSize'),
                    line_spacing: g('cfgLineSpacing'),
                    link_color: g('cfgLinkColor'),
                    // Layout
                    header_type: g('cfgHeaderType'),
                    header_text: g('cfgHeaderText'),
                    page_num_format: g('cfgPageNumFormat'),
                    // Margins (pt)
                    marginTop: gn('cfgMarginTop') || 50,
                    marginBottom: gn('cfgMarginBottom') || 50,
                    marginLeft: gn('cfgMarginLeft') || 50,
                    marginRight: gn('cfgMarginRight') || 50,
                    // Header Image (base64)
                    headerImageB64: headerImgData,
                    headerImageHeight: gn('cfgHeaderImgHeight') || 40,
                    // Headings (nested)
                    headings: {
                        h1: { size: gn('cfgH1Size'), color: g('cfgH1Color') },
                        h2: { size: gn('cfgH2Size'), color: g('cfgH2Color') }
                    },
                    // Tables (nested, PDF fields)
                    tables: {
                        header_bg: g('cfgTableHeaderBg'),
                        header_text: g('cfgTableHeaderText'),
                        row_even: g('cfgTableRowEven'),
                        row_odd: g('cfgTableRowOdd'),
                        border_color: g('cfgTableBorderColor'),
                        border_width: gn('cfgTableBorderWidth'),
                        font_size: gn('cfgTableFontSize'),
                        padding: gn('cfgTablePadding')
                    },
                    // Flat keys for backward compat with web_engine.py style_config
                    fontPrompt: g('cfgFont'),
                    fontSize: gn('cfgFontSize'),
                    lineSpacing: g('cfgLineSpacing'),
                    h1Size: gn('cfgH1Size'),
                    h1Color: g('cfgH1Color'),
                    h2Size: gn('cfgH2Size'),
                    h2Color: g('cfgH2Color'),
                    linkColor: g('cfgLinkColor'),
                    tableHeaderBg: g('cfgTableHeaderBg'),
                    tableHeaderText: g('cfgTableHeaderText'),
                    tableRowEven: g('cfgTableRowEven'),
                    tableRowOdd: g('cfgTableRowOdd'),
                    tableBorderColor: g('cfgTableBorderColor'),
                    tableBorderWidth: gn('cfgTableBorderWidth'),
                    tableFontSize: gn('cfgTableFontSize'),
                    tablePadding: gn('cfgTablePadding'),
                    textAlignment: g('cfgTextAlignment') || 'justify',
                    headerType: gb('enableHeaderText') ? g('cfgHeaderType') : 'none',
                    headerText: g('cfgHeaderText'),
                    pageNumFormat: g('cfgPageNumFormat'),

                    // ── Carátula ─────────────────────────────────────────
                    caratula_enabled: gb('enableCaratula'),
                    caratula_titulo: g('caratulaTitulo'),
                    caratula_autor: g('caraTulaAutor'),
                    caratula_institucion: g('caraTulaInstitucion'),
                    caratula_fecha: g('caraTulaFecha'),
                    caratula_html: g('caraTulaHTML'),
                    caratula_imagen: (window._edtechImgStore && window._edtechImgStore.caratula)
                        ? window._edtechImgStore.caratula.dataUrl || null : null,
                    caratula_title_size: gn('cfgCaratulaTitleSize') || 20,
                    caratula_autor_size: gn('cfgCaratulaAutorSize') || 13,
                    caratula_title_color: g('cfgCaratulaTitleColor') || '#000000',
                    caratula_autor_color: g('cfgCaratulaAutorColor') || '#333333',
                    // Position values (percentage)
                    caratula_title_x: gn('cfgCaratulaTitleX') || 50,
                    caratula_title_y: gn('cfgCaratulaTitleY') || 50,
                    caratula_inst_y: parseFloat(document.getElementById('caratulaDragInstitucion')?.style.top) || 15,
                    caratula_autor_y: parseFloat(document.getElementById('caratulaDragAutor')?.style.top) || 58,
                    caratula_fecha_y: parseFloat(document.getElementById('caratulaDragFecha')?.style.top) || 65,

                    // ── Contratapa (Back Cover) ──────────────────────────
                    contratapa_enabled: gb('enableContratapa'),
                    contratapa_imagen: (window._edtechImgStore && window._edtechImgStore.contratapa)
                        ? window._edtechImgStore.contratapa.dataUrl || null : null,

                    // ── Encabezado ────────────────────────────────────────
                    encabezado_enabled: gb('enableEncabezado'),
                    encabezado_left: g('headerLeft'),
                    encabezado_center: g('headerCenter'),
                    encabezado_right: g('headerRight'),
                    encabezado_line_style: g('headerLineStyle'),
                    encabezado_line_color: g('headerLineColor'),

                    // ── Footer ────────────────────────────────────────────
                    footer_enabled: gb('enableFooter'),
                    footer_left: g('footerLeft'),
                    footer_center: g('footerCenter'),
                    footer_right: g('footerRight'),
                    footer_page_numbers: gb('footerPageNumbers'),
                    footer_page_num_pos: g('footerPageNumPos'),
                    footer_line_style: g('footerLineStyle'),
                    footer_line_color: g('footerLineColor'),

                    // ── Bloque APA ────────────────────────────────────────
                    apa_enabled: gb('enableApaBlock'),
                    apa_bg: g('cfgApaBg'),
                    apa_border: g('cfgApaBorder'),
                    apa_font_size: gn('cfgApaFontSize') || 10,
                    apa_text_color: g('cfgApaTextColor'),

                    // ── Hoja Final ────────────────────────────────────────
                    hoja_final_enabled: gb('enableHojaFinal'),
                    hoja_final_html: g('hojaFinalHTML')
                };
                return config;
            }

            // Common optional fields
            const outFolder = document.getElementById('outputFolderValue');

            formData.append('output_folder', outFolder ? outFolder.value : '');

            if (!isExcel) {
                // Docs Specifics
                formData.append('paper_size', paperSize);
                // Config
                try {
                    const _sc = getAdvancedConfig();
                    // ── Diagnostic: verify what's being sent to backend ──
                    console.log('[Queue] style_config enviado al backend:', {
                        fontPrompt:      _sc.fontPrompt,
                        lineSpacing:     _sc.lineSpacing,
                        h2Color:         _sc.h2Color,
                        marginTop:       _sc.marginTop,
                        tableHeaderBg:   _sc.tableHeaderBg,
                        caratula_enabled:_sc.caratula_enabled,
                        caratula_imagen: !!(_sc.caratula_imagen),
                    });
                    formData.append('style_config', JSON.stringify(_sc));
                } catch (e) { console.warn("Config not found", e); }
            } else {
                // Excel Specifics (if any)
                // formData.append('excel_bold', ...);
            }

            try {
                const response = await fetch(endpoint, { method: 'POST', body: formData });

                // Read Stream (Common for both, assuming Excel also returns NDJSON or similar structure?)
                // Wait, app.py /process_excel returns JSON, NOT stream!
                // We need to handle JSON response for Excel separately unless we update app.py to match stream.

                if (isExcel) {
                    const data = await response.json();
                    if (data.results) {
                        data.results.forEach(res => {
                            if (selectedFiles.has(res.name)) {
                                const f = selectedFiles.get(res.name);
                                f.status = res.status === 'success' ? 'done' : 'error';
                                if (res.result) f.resultPath = res.result; // Store actual filename from server
                                selectedFiles.set(res.name, f);
                            }
                        });
                        renderQueue();
                        log('Proceso Excel finalizado.', 'success');

                        // Show Global Actions if needed
                        const globalActions = document.getElementById('globalActions');
                        if (globalActions) globalActions.style.display = 'flex';
                    } else {
                        // Fallback if structure is different
                        log('Respuesta inesperada del servidor Excel.', 'error');
                    }
                    processBtn.disabled = false;
                    processBtn.innerHTML = 'INICIAR PROCESO'; // Reset text
                    return; // Stop here for Excel
                }


                // === PDF TOOL LOGIC (URLS) ===
                const isPdf = window.location.pathname === '/' || window.location.pathname.includes('/pdf');
                if (isPdf) {
                    // Process URLs sequentially (Client-Side Loop for simplicity as we await blobs)
                    // Server endpoint /process_url takes 1 URL and returns 1 PDF Blob.

                    for (const [key, item] of selectedFiles) {
                        if (item.status === 'done') continue;
                        if (item.type === 'pdf_stamp') continue; // Handled by PDF stamp handler


                        item.status = 'processing';
                        selectedFiles.set(key, item);
                        renderQueue();

                        const fd = new FormData();
                        fd.append('url', item.url);
                        fd.append('paper_size', paperSize);

                        // Add Style Config from EDTechConfig
                        if (typeof EDTechConfig !== 'undefined' && typeof EDTechConfig.collectConfig === 'function') {
                            const styleData = EDTechConfig.collectConfig();
                            // Attach any stored images from _edtechImgStore
                            if (window._edtechImgStore) {
                                if (window._edtechImgStore.caratula)  styleData.caratula_imagen  = window._edtechImgStore.caratula.dataUrl;
                                if (window._edtechImgStore.contratapa) styleData.contratapa_imagen = window._edtechImgStore.contratapa.dataUrl;
                                if (window._edtechImgStore.header)    styleData.header_imagen    = window._edtechImgStore.header.dataUrl;
                            }
                            // paper_size is tracked separately by the paper card selector
                            styleData.paper_size = paperSize;
                            fd.append('style_config', JSON.stringify(styleData));
                            console.log('[PDF] style_config enviado:', {
                                h2_color:        styleData.h2_color,
                                margin_top:      styleData.margin_top,
                                caratula:        styleData.caratula_enabled,
                                table_header_bg: styleData.table_header_bg,
                            });
                        }

                        // Output folder: for xls_url, always append the subject subfolder
                        let itemOutputFolder = outFolder && outFolder.value ? outFolder.value.trim() : '';
                        if (item.type === 'xls_url' && item.xlsFolder) {
                            // Always build subfolder, even if no base folder selected
                            // (server will fall back to outputs/<xlsFolder>/)
                            if (itemOutputFolder) {
                                itemOutputFolder = itemOutputFolder.replace(/\/$/, '') + '/' + item.xlsFolder;
                            } else {
                                itemOutputFolder = 'outputs/' + item.xlsFolder;
                            }
                        }
                        console.log('[XLS] output_folder →', itemOutputFolder, '| type:', item.type);
                        if (itemOutputFolder) fd.append('output_folder', itemOutputFolder);

                        // Prefix: for xls_url use the XLS-derived prefix (spaces → underscores, trailing _)
                        const prefixInput = document.getElementById('filePrefix');
                        const suffixInput = document.getElementById('fileSuffix');
                        if (item.type === 'xls_url' && item.xlsPrefix) {
                            const sanitizedPrefix = item.xlsPrefix.replace(/\s+/g, '_') + '_';
                            fd.append('file_prefix', sanitizedPrefix);
                        } else {
                            if (prefixInput && prefixInput.value) fd.append('file_prefix', prefixInput.value.replace(/\s+/g, '_'));
                            if (suffixInput && suffixInput.value) fd.append('file_suffix', suffixInput.value.replace(/\s+/g, '_'));
                        }

                        try {
                            const res = await fetch('/process_url', { method: 'POST', body: fd });

                            // Stream Reader for PDF Progress
                            const reader = res.body.getReader();
                            const decoder = new TextDecoder();
                            let buffer = '';
                            let successData = null;
                            const startTime = Date.now();

                            while (true) {
                                const { done, value } = await reader.read();
                                if (done) break;

                                buffer += decoder.decode(value, { stream: true });
                                const lines = buffer.split('\n');
                                buffer = lines.pop();

                                for (const line of lines) {
                                    if (!line.trim()) continue;
                                    try {
                                        const data = JSON.parse(line);
                                        if (data.msg) {
                                            // BS4 fallback: show as orange warning
                                            if (data.msg.startsWith('BS4_FALLBACK:')) {
                                                log('⚠️ ' + data.msg.replace('BS4_FALLBACK:', 'Extractor alternativo:').trim(), 'warning');
                                            } else {
                                                log(data.msg, data.type || 'info');
                                            }
                                        }

                                        if (data.progress !== undefined) {
                                            // Update progress on the queue item
                                            const qItem = selectedFiles.get(key);
                                            if (qItem) {
                                                qItem.progress = data.progress;
                                                qItem.elapsedSec = Math.round((Date.now() - startTime) / 1000);
                                                selectedFiles.set(key, qItem);
                                                renderQueue();
                                            }
                                        }

                                        if (data.success) {
                                            successData = data;
                                        }
                                        if (data.error) {
                                            throw new Error(data.error);
                                        }
                                    } catch (e) {
                                        if (e.message && !e.message.includes('JSON')) throw e;
                                        console.warn('JSON Parse Error (PDF Stream):', line, e);
                                    }
                                }
                            }

                            if (successData && successData.success) {
                                item.status = 'done';
                                item.resultFilename = successData.result;
                                item.resultPath = successData.path;

                                selectedFiles.set(key, item);
                                // log(`Guardado en: ${successData.result}`, 'success'); // Already logged by stream
                            } else {
                                throw new Error('El proceso terminó sin confirmación de éxito.');
                            }

                        } catch (e) {
                            item.status = 'error';
                            selectedFiles.set(key, item);
                            // Cloudflare detection: show orange warning instead of red error
                            if (e.message && e.message.includes('CLOUDFLARE')) {
                                log(`⚠️ BLOQUEADO POR Cloudflare Enterprise: ${item.url || key}`, 'warning');
                            } else {
                                log(`Fallo en URL: ${e.message}`, 'error');
                            }
                        }
                        renderQueue();
                    }

                    processBtn.disabled = false;
                    processBtn.innerHTML = 'INICIAR PROCESO';
                    return;
                }

                // Docs Stream Handling
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                const startTime = Date.now();

                let buffer = '';
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    buffer += chunk;
                    const lines = buffer.split('\n');

                    buffer = lines.pop(); // Save the last partial line

                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const data = JSON.parse(line);

                            if (data.msg) log(data.msg, data.type || 'info');

                            // Update progress on the currently-processing file
                            if (data.progress !== undefined && data.type !== 'complete') {
                                selectedFiles.forEach((f, k) => {
                                    if (f.status === 'processing') {
                                        f.progress = data.progress;
                                        f.elapsedSec = Math.round((Date.now() - startTime) / 1000);
                                        selectedFiles.set(k, f);
                                    }
                                });
                                renderQueue();
                            }

                            if (data.type === 'complete' && data.results) {
                                log('Cola finalizada.', 'success');
                                data.results.forEach(res => {
                                    if (selectedFiles.has(res.name)) {
                                        const f = selectedFiles.get(res.name);
                                        f.status = 'done';
                                        f.resultDocx = res.docx;
                                        f.resultPdf = res.pdf;
                                        f.resultPath = res.full_path || res.docx; // Server sends full_path
                                        selectedFiles.set(res.name, f);
                                    }
                                });
                                renderQueue();

                                // Show Global Actions
                                const globalActions = document.getElementById('globalActions');
                                const finalPathDisplay = document.getElementById('finalPathDisplay');

                                if (globalActions) {
                                    globalActions.style.display = 'flex';
                                    if (finalPathDisplay && data.output_folder) {
                                        finalPathDisplay.innerText = data.output_folder;
                                    }
                                }
                            }

                        } catch (e) {
                            console.error("JSON Parse Error on line:", line, e);
                        }
                    }
                }

                processBtn.disabled = false;
                processBtn.innerHTML = '<i class="fa-solid fa-play"></i> INICIAR PROCESO';

            } catch (err) {
                log(`Error: ${err}`, 'error');
                processBtn.disabled = false;
                processBtn.innerHTML = '<i class="fa-solid fa-play"></i> INICIAR PROCESO';
            }
        });
    }

    // === ADD URL TO QUEUE (PDF TOOL) ===
    // Uses inline input instead of prompt() (not supported in Electron)
    const addUrlBtn = document.getElementById('addUrlToQueueBtn');
    const urlInlineInput = document.getElementById('urlInlineInput');
    const urlInlineConfirm = document.getElementById('urlInlineConfirm');
    const urlInlineCancel = document.getElementById('urlInlineCancel');
    const urlInlineBar = document.getElementById('urlInlineBar');

    function showUrlInput() {
        if (urlInlineBar) urlInlineBar.style.display = 'flex';
        if (urlInlineInput) { 
            urlInlineInput.value = ''; 
            if (urlInlineInput.offsetParent !== null) {
                urlInlineInput.focus(); 
            }
        }
    }

    function hideUrlInput() {
        if (urlInlineBar) urlInlineBar.style.display = 'none';
    }

    function submitUrlInput() {
        const val = urlInlineInput ? urlInlineInput.value.trim() : '';
        if (!val) { hideUrlInput(); return; }
        
        if (!val.startsWith('http')) {
            log('URL no válida. Debe comenzar con http/https.', 'error');
            return;
        }
        if (selectedFiles.has(val)) {
            log('Esta URL ya está en la cola.', 'info');
            hideUrlInput();
            return;
        }
        selectedFiles.set(val, { type: 'url', url: val, status: 'pend', resultPdf: null });
        renderQueue();
        log(`Enlace añadido: ${val}`, 'info');
        hideUrlInput();
    }

    if (addUrlBtn) addUrlBtn.addEventListener('click', showUrlInput);
    if (urlInlineConfirm) urlInlineConfirm.addEventListener('click', submitUrlInput);
    if (urlInlineCancel) urlInlineCancel.addEventListener('click', hideUrlInput);
    
    if (urlInlineInput) {
        urlInlineInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') submitUrlInput();
            if (e.key === 'Escape') hideUrlInput();
        });
        
        // Auto-paste from clipboard on focus
        urlInlineInput.addEventListener('focus', async () => {
            try {
                const clip = await navigator.clipboard.readText();
                if (clip && clip.startsWith('http') && !urlInlineInput.value) {
                    urlInlineInput.value = clip.trim();
                }
            } catch (_) { }
        });
    }

    // === PAPER SELECTOR ===
    document.querySelectorAll('.paper-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.paper-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');

            // Support both data-value (sidebar) and data-size (legacy)
            paperSize = card.getAttribute('data-value') || card.getAttribute('data-size');

            // Update Footer Display if exists
            const footerDisplay = document.getElementById('footerPaperSize'); // PDF Tool
            if (footerDisplay) {
                footerDisplay.innerText = paperSize === 'letter' ? 'Carta (Letter)' : 'Oficio (Legal)';
            }

            log(`Tamaño de papel seleccionado: ${paperSize}`, 'info');
        });
    });

    // === FOLDER SELECTION ===
    const selectFolderBtn = document.getElementById('selectFolderBtn');
    const outputFolderDisplay = document.getElementById('outputFolderDisplay');
    const outputFolderValue = document.getElementById('outputFolderValue');

    if (selectFolderBtn) {
        selectFolderBtn.addEventListener('click', async () => {
            try {
                // Change icon to spinner
                const originalIcon = selectFolderBtn.innerHTML;
                selectFolderBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
                selectFolderBtn.disabled = true;

                const res = await fetch('/select_folder', { method: 'POST' });
                const data = await res.json();

                if (data.path) {
                    outputFolderValue.value = data.path;
                    outputFolderDisplay.value = "..." + data.path.slice(-25); // Shorten for display
                    outputFolderDisplay.title = data.path;
                    log(`Carpeta de salida: ${data.path}`, 'info');
                }

                // Restore icon
                selectFolderBtn.innerHTML = originalIcon;
                selectFolderBtn.disabled = false;
            } catch (e) {
                log('Error seleccionando carpeta', 'error');
                selectFolderBtn.innerHTML = '<i class="fa-solid fa-ellipsis"></i>';
                selectFolderBtn.disabled = false;
            }
        });
    }

    function log(msg, type = 'info') {
        if (!consoleLogs) return;
        const div = document.createElement('div');
        div.className = `log-item ${type}`;
        div.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
        consoleLogs.appendChild(div);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // ═══════════════════════════════════════════════════════════════
    // === CARGAR XLS — Batch folder/prefix queue from XLSX =========
    // ═══════════════════════════════════════════════════════════════
    const loadXlsBtn = document.getElementById('loadXlsBtn');
    const xlsInput   = document.getElementById('xlsInput');

    if (loadXlsBtn && xlsInput) {
        loadXlsBtn.addEventListener('click', () => xlsInput.click());

        xlsInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (typeof XLSX === 'undefined') {
                log('SheetJS no disponible. Verifica tu conexión.', 'error');
                return;
            }

            log(`Leyendo archivo XLS: ${file.name}...`, 'info');
            loadXlsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Leyendo...';
            loadXlsBtn.disabled = true;

            try {
                const arrayBuffer = await file.arrayBuffer();
                const workbook   = XLSX.read(arrayBuffer, { type: 'array' });
                const sheetName  = workbook.SheetNames[0];
                const sheet      = workbook.Sheets[sheetName];

                // Read Col A (A1:A54) for folder names — 0-indexed rows 0..53
                // Read Col C (C2:C55) for prefix — 0-indexed rows 1..54
                // Read Col D (D2:D55) for URL    — 0-indexed rows 1..54
                // SheetJS cell address: A1 = {r:0,c:0}, C2 = {r:1,c:2}, D2 = {r:1,c:3}

                let addedCount  = 0;
                let skippedCount = 0;

                // Build a map: row index → folder name from col A
                // Row 1 in Excel = index r:0 in SheetJS
                // A1:A54 → r:0..53 (col A = c:0)
                const folderMap = {};
                for (let r = 0; r <= 53; r++) {
                    const cell = sheet[XLSX.utils.encode_cell({ r, c: 0 })];
                    if (cell && cell.v) folderMap[r] = String(cell.v).trim();
                }

                // Data rows: C2:C55 and D2:D55 → r:1..54
                for (let r = 1; r <= 54; r++) {
                    const cellC = sheet[XLSX.utils.encode_cell({ r, c: 2 })]; // Col C
                    const cellD = sheet[XLSX.utils.encode_cell({ r, c: 3 })]; // Col D

                    const prefix = cellC && cellC.v ? String(cellC.v).trim() : null;
                    const url    = cellD && cellD.v ? String(cellD.v).trim() : null;

                    if (!url || !url.startsWith('http')) { skippedCount++; continue; }

                    // Determine the folder: use the same-row A value if it exists,
                    // otherwise walk backwards to find the last defined folder
                    let folder = folderMap[r] || null;
                    if (!folder) {
                        for (let back = r - 1; back >= 0; back--) {
                            if (folderMap[back]) { folder = folderMap[back]; break; }
                        }
                    }

                    // Sanitize: replace spaces with underscores in folder and prefix
                    const safeFolder = folder ? folder.replace(/\s+/g, '_') : 'SIN_CARPETA';
                    const safePrefix = prefix ? prefix.replace(/\s+/g, '_') : '';

                    const key = `xls::${safeFolder}::${safePrefix}::${url}`;
                    if (selectedFiles.has(key)) { skippedCount++; continue; }

                    selectedFiles.set(key, {
                        type: 'xls_url',
                        url:  url,
                        xlsFolder: safeFolder,
                        xlsPrefix: safePrefix,
                        status: 'pend',
                        resultPdf: null
                    });
                    addedCount++;
                }

                renderQueue();
                if (addedCount > 0) {
                    log(`XLS cargado: ${addedCount} URLs añadidas a la cola (${skippedCount} omitidas).`, 'success');
                } else {
                    log(`XLS leído pero no se encontraron URLs válidas. (${skippedCount} filas omitidas)`, 'error');
                }
            } catch (err) {
                log(`Error al leer el archivo XLS: ${err.message}`, 'error');
                console.error('XLS parse error:', err);
            } finally {
                loadXlsBtn.innerHTML = '<i class="fa-solid fa-file-excel"></i> Cargar XLS';
                loadXlsBtn.disabled = false;
                xlsInput.value = ''; // reset so same file can be re-loaded
            }
        });
    }

    // ── PDF STAMP BUTTON ─────────────────────────────────────────────────────
    // Allows loading blank PDFs and applying the active EPD template header/footer.
    const loadPdfBtn = document.getElementById('loadPdfBtn');
    const pdfStampInput = document.getElementById('pdfStampInput');

    if (loadPdfBtn && pdfStampInput) {
        loadPdfBtn.addEventListener('click', () => pdfStampInput.click());

        pdfStampInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (!files || files.length === 0) return;

            let added = 0;
            Array.from(files).forEach(f => {
                if (!f.name.toLowerCase().endsWith('.pdf')) {
                    log(`Ignorado: ${f.name} (sólo .pdf)`, 'error');
                    return;
                }
                const key = 'PDF_STAMP::' + f.name;
                if (!selectedFiles.has(key)) {
                    selectedFiles.set(key, {
                        type: 'pdf_stamp',
                        file: f,
                        filename: f.name,
                        status: 'pend',
                        resultPath: null
                    });
                    added++;
                }
            });

            if (added > 0) {
                renderQueue();
                log(`${added} PDF(s) añadidos para estampar plantilla.`, 'success');
            }
            pdfStampInput.value = '';
        });
    }

    // ── OVERRIDE renderQueue to render pdf_stamp items ───────────────────────
    // Patch the renderQueue function to handle the new type.
    const _originalRenderQueue = renderQueue;
    // We augment selectedFiles rendering by hooking into the existing forEach.
    // Instead of monkey-patching, we add a rendering branch inside the existing
    // renderQueue (above). Because renderQueue is already defined and closes over
    // 'selectedFiles', we extend the type handling in the same scope.
    // The forEach inside renderQueue handles `data.type === 'pdf_stamp'` via
    // the catch-all `else` branch which shows file size — that's fine.
    // We just need to override the icon color/label.

    // ── processBtn: intercept pdf_stamp items ─────────────────────────────────
    if (processBtn) {
        processBtn.addEventListener('click', async () => {
            const pdfStampItems = [...selectedFiles.entries()]
                .filter(([, d]) => d.type === 'pdf_stamp' && d.status === 'pend');

            const urlItems = [...selectedFiles.entries()]
                .filter(([, d]) => d.type !== 'pdf_stamp' && d.status === 'pend');

            // Process URL items via the existing logic (already handled by prior listener)
            // We only need to add PDF stamp processing.
            if (pdfStampItems.length === 0) return; // Handled by existing listener

            processBtn.disabled = true;
            processBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Estampando...';

            try {
                // --- Collect style_config from active EPD template ---
                let styleConfig = null;
                if (typeof EDTechConfig !== 'undefined') {
                    try { styleConfig = EDTechConfig.collectConfig(); } catch(e) {}
                }

                const outputFolder = document.getElementById('outputFolderValue')?.value || '';
                const filePrefix = document.getElementById('filePrefix')?.value || '';
                const fileSuffix = document.getElementById('fileSuffix')?.value || '';

                // Build FormData with ALL pending pdf_stamp files
                const formData = new FormData();
                formData.append('style_config', JSON.stringify(styleConfig || {}));
                if (outputFolder) formData.append('output_folder', outputFolder);
                if (filePrefix) formData.append('file_prefix', filePrefix);
                if (fileSuffix) formData.append('file_suffix', fileSuffix);

                // Recolor accent flag
                const recolorEl = document.getElementById('stampRecolorAccent');
                if (recolorEl && recolorEl.checked) formData.append('recolor_accent', '1');

                // Per-file: append files + source URLs as indexed fields
                pdfStampItems.forEach(([key, data], idx) => {
                    formData.append('pdf_files[]', data.file, data.filename);
                    if (data.sourceUrl) formData.append(`source_url_${idx}`, data.sourceUrl);
                    data.status = 'processing';
                    data.progress = 0;
                });
                renderQueue();


                const response = await fetch('/stamp_pdf', { method: 'POST', body: formData });
                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const lines = decoder.decode(value).split('\n').filter(l => l.trim());
                    for (const line of lines) {
                        try {
                            const msg = JSON.parse(line);
                            log(msg.msg || '', msg.type || 'info');
                            if (msg.progress !== undefined) {
                                // Update all processing items' progress display
                                pdfStampItems.forEach(([key, data]) => {
                                    if (data.status === 'processing') {
                                        data.progress = msg.progress;
                                    }
                                });
                                renderQueue();
                            }
                            if (msg.success && msg.path) {
                                // Mark the matching item as done
                                const resultFilename = msg.result || '';
                                const matchKey = pdfStampItems.find(([,d]) =>
                                    resultFilename.includes(d.filename.replace('.pdf',''))
                                )?.[0];
                                const targetKey = matchKey || pdfStampItems.find(([,d]) => d.status === 'processing')?.[0];
                                if (targetKey && selectedFiles.has(targetKey)) {
                                    const d = selectedFiles.get(targetKey);
                                    d.status = 'done';
                                    d.resultPath = msg.path;
                                }
                                renderQueue();
                            }
                            if (msg.error) {
                                pdfStampItems.forEach(([key, data]) => {
                                    if (data.status === 'processing') data.status = 'error';
                                });
                                renderQueue();
                            }
                        } catch(pe) {}
                    }
                }

                // Mark any remaining processing items as done
                pdfStampItems.forEach(([key, data]) => {
                    if (data.status === 'processing') data.status = 'done';
                });
                renderQueue();

                const ga = document.getElementById('globalActions');
                if (ga) { ga.style.display = 'flex'; }

            } catch(err) {
                log(`Error en estampado: ${err.message}`, 'error');
                pdfStampItems.forEach(([, d]) => { d.status = 'error'; });
                renderQueue();
            } finally {
                processBtn.disabled = selectedFiles.size === 0;
                processBtn.innerHTML = '<span>INICIAR PROCESO</span><i class="fa-solid fa-bolt"></i>';
            }
        }, { once: false });
    }

});

// ═══════════════════════════════════════════════════════════════
// DOC SECTION TOGGLES (global — called from sidebar HTML onclick)
// ═══════════════════════════════════════════════════════════════

function toggleDocSection(name) {
    const body = document.getElementById('body-' + name);
    const chevron = document.getElementById('chevron-' + name);
    if (!body) return;
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : 'block';
    if (chevron) chevron.classList.toggle('open', !isOpen);
}

const _DEFAULT_CARATULA_HTML = `<style>
  .caratula {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-family: 'Times New Roman', serif;
    text-align: center;
    padding: 60px 40px;
  }
  .caratula .institucion { font-size: 14pt; font-weight: bold; margin-bottom: 40px; }
  .caratula .titulo { font-size: 18pt; font-weight: bold; margin-bottom: 30px; text-transform: uppercase; }
  .caratula .autor { font-size: 12pt; margin-bottom: 10px; }
  .caratula .fecha { font-size: 11pt; color: #555; margin-top: 40px; }
</style>
<div class="caratula">
  <div class="institucion">{{institucion}}</div>
  <div class="titulo">{{titulo}}</div>
  <div class="autor">{{autor}}</div>
  <div class="fecha">{{fecha}}</div>
</div>`;

const _DEFAULT_HOJA_FINAL_HTML = `<style>
  .hoja-final {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-family: 'Times New Roman', serif;
    text-align: center;
    padding: 60px 40px;
  }
  .hoja-final .firma { font-size: 12pt; margin-top: 60px; border-top: 1px solid #000; padding-top: 10px; width: 200px; }
  .hoja-final .fecha { font-size: 11pt; color: #555; margin-top: 20px; }
</style>
<div class="hoja-final">
  <div class="firma">{{autor}}</div>
  <div class="fecha">{{fecha}}</div>
  <p style="font-size:10pt; color:#888;">Página {{total_paginas}}</p>
</div>`;

function resetCaratulaHTML() {
    const el = document.getElementById('caraTulaHTML');
    if (el) el.value = _DEFAULT_CARATULA_HTML;
}

function resetHojaFinalHTML() {
    const el = document.getElementById('hojaFinalHTML');
    if (el) el.value = _DEFAULT_HOJA_FINAL_HTML;
}

function _buildPreviewHTML(templateEl, fields) {
    if (!templateEl) return '<p>No hay contenido.</p>';
    let html = templateEl.value || '';
    Object.entries(fields).forEach(([k, v]) => {
        html = html.replaceAll(`{{${k}}}`, v || `[${k}]`);
    });
    return html;
}

function previewCaratula() {
    const fields = {
        titulo: document.getElementById('caratulaTitulo')?.value || 'Título del Documento',
        autor: document.getElementById('caraTulaAutor')?.value || 'Nombre del Autor',
        institucion: document.getElementById('caraTulaInstitucion')?.value || 'Institución',
        fecha: document.getElementById('caraTulaFecha')?.value || new Date().getFullYear()
    };
    const html = _buildPreviewHTML(document.getElementById('caraTulaHTML'), fields);
    _openPreviewModal('Vista Previa — Carátula', html);
}

function previewHojaFinal() {
    const fields = {
        autor: document.getElementById('caraTulaAutor')?.value || 'Nombre del Autor',
        fecha: document.getElementById('caraTulaFecha')?.value || new Date().getFullYear(),
        total_paginas: '##'
    };
    const html = _buildPreviewHTML(document.getElementById('hojaFinalHTML'), fields);
    _openPreviewModal('Vista Previa — Hoja Final', html);
}

function _openPreviewModal(title, html) {
    // Remove existing preview if any
    const existing = document.getElementById('_docPreviewModal');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = '_docPreviewModal';
    overlay.style.cssText = `
        position:fixed; inset:0; background:rgba(0,0,0,0.6);
        display:flex; align-items:center; justify-content:center;
        z-index:9999; padding:20px;
    `;
    overlay.innerHTML = `
        <div style="background:white; border-radius:8px; overflow:hidden;
                    width:600px; max-height:80vh; display:flex; flex-direction:column;
                    box-shadow:0 20px 60px rgba(0,0,0,0.4);">
            <div style="padding:12px 16px; background:#1e293b; color:white;
                        display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13px; font-weight:600;">${title}</span>
                <button onclick="document.getElementById('_docPreviewModal').remove()"
                    style="background:none; border:none; color:white; cursor:pointer; font-size:16px;">
                    <i class="fa-solid fa-times"></i>
                </button>
            </div>
            <div style="flex:1; overflow:auto; padding:0;
                        background:#f5f5f5; display:flex; align-items:center; justify-content:center;">
                <div style="background:white; width:595px; min-height:842px;
                            box-shadow:0 2px 8px rgba(0,0,0,0.15); position:relative;">
                    <iframe id="_previewFrame" style="width:100%; min-height:842px; border:none;"></iframe>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    // Write HTML into iframe
    const frame = document.getElementById('_previewFrame');
    const doc = frame.contentDocument || frame.contentWindow.document;
    doc.open();
    doc.write(`<!DOCTYPE html><html><body style="margin:0;padding:0;">${html}</body></html>`);
    doc.close();
}
