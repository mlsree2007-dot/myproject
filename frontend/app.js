/**
 * ParseAnything — Interactive Universal Document Ingestion Frontend
 * Provenance-aware Bounding Box Inspection, 3-Pane Dashboard, 1-Click Demonstrations
 */

// Application State
const state = {
  currentDocument: null,
  currentPage: 1,
  selectedBlockId: null,
  scaleX: 1.0,
  scaleY: 1.0,
  naturalWidth: 612.0,
  naturalHeight: 792.0,
  zoomLevel: 1.0
};

// DOM References
const elements = {
  dropzone: document.getElementById('dropzone'),
  fileInput: document.getElementById('fileInput'),
  btnBrowse: document.getElementById('btnBrowse'),
  btnRunBenchmarks: document.getElementById('btnRunBenchmarks'),
  benchmarkModal: document.getElementById('benchmarkModal'),
  btnCloseModal: document.getElementById('btnCloseModal'),
  modalBenchmarkBody: document.getElementById('modalBenchmarkBody'),

  // Stepper
  stepUpload: document.getElementById('stepUpload'),
  stepDetect: document.getElementById('stepDetect'),
  stepExtract: document.getElementById('stepExtract'),
  stepAssemble: document.getElementById('stepAssemble'),
  stepVerify: document.getElementById('stepVerify'),

  // Header Telemetry
  headCostPill: document.getElementById('headCostPill'),
  headSpeedPill: document.getElementById('headSpeedPill'),

  // Banner
  bannerFilename: document.getElementById('bannerFilename'),
  bannerStatus: document.getElementById('bannerStatus'),
  bannerFormat: document.getElementById('bannerFormat'),
  bannerParser: document.getElementById('bannerParser'),
  bannerHandwriting: document.getElementById('bannerHandwriting'),
  bannerMeta: document.getElementById('bannerMeta'),
  bannerTablesCount: document.getElementById('bannerTablesCount'),
  bannerFiguresCount: document.getElementById('bannerFiguresCount'),
  bannerEquationsCount: document.getElementById('bannerEquationsCount'),
  bannerConfidenceAvg: document.getElementById('bannerConfidenceAvg'),
  bannerFormatIcon: document.getElementById('bannerFormatIcon'),

  // Left Pane
  previewViewport: document.getElementById('previewViewport'),
  nonVisualFallback: document.getElementById('nonVisualFallback'),
  fallbackRangePill: document.getElementById('fallbackRangePill'),
  btnZoomOut: document.getElementById('btnZoomOut'),
  btnZoomIn: document.getElementById('btnZoomIn'),
  zoomIndicator: document.getElementById('zoomIndicator'),

  // Center Pane
  blocksList: document.getElementById('blocksList'),
  blocksCountBadge: document.getElementById('blocksCountBadge'),

  // Right Pane (Inspector Tabs)
  tabButtons: document.querySelectorAll('.tab-btn'),
  tabPanes: document.querySelectorAll('.tab-pane'),
  provMethodBadge: document.getElementById('provMethodBadge'),
  provConfBadge: document.getElementById('provConfBadge'),
  provOrderBadge: document.getElementById('provOrderBadge'),
  provBlockTitle: document.getElementById('provBlockTitle'),
  provSnippet: document.getElementById('provSnippet'),
  provDocVal: document.getElementById('provDocVal'),
  provPageVal: document.getElementById('provPageVal'),
  provBBoxVal: document.getElementById('provBBoxVal'),
  provLayerVal: document.getElementById('provLayerVal'),
  markdownRenderArea: document.getElementById('markdownRenderArea'),
  btnCopyMd: document.getElementById('btnCopyMd'),
  jsonCodeArea: document.getElementById('jsonCodeArea'),
  btnDownloadJson: document.getElementById('btnDownloadJson'),
  tablesInspectorList: document.getElementById('tablesInspectorList'),
  telCostVal: document.getElementById('telCostVal'),
  telSpeedVal: document.getElementById('telSpeedVal'),
  telPagesVal: document.getElementById('telPagesVal'),
  telBlocksVal: document.getElementById('telBlocksVal'),
  telLowConfVal: document.getElementById('telLowConfVal'),

  btnDownloadJsonMain: document.getElementById('btnDownloadJsonMain'),

  // Previous Files list
  previousFilesList: document.getElementById('previousFilesList')
};

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  loadPreviousFiles();
});

function setupEventListeners() {
  // File Upload Handlers
  elements.btnBrowse.addEventListener('click', (e) => {
    e.stopPropagation();
    elements.fileInput.click();
  });
  elements.dropzone.addEventListener('click', () => elements.fileInput.click());

  elements.fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  elements.dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.dropzone.classList.add('dragover');
  });

  elements.dropzone.addEventListener('dragleave', () => {
    elements.dropzone.classList.remove('dragover');
  });

  elements.dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  // Download JSON main button
  if (elements.btnDownloadJsonMain) {
    elements.btnDownloadJsonMain.addEventListener('click', downloadCurrentJson);
  }

  // Tab Switchers
  elements.tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      elements.tabButtons.forEach(b => b.classList.remove('active'));
      elements.tabPanes.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const targetId = 'tab' + btn.getAttribute('data-tab').charAt(0).toUpperCase() + btn.getAttribute('data-tab').slice(1);
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Zoom controls
  if (elements.btnZoomOut) elements.btnZoomOut.addEventListener('click', () => changeZoom(-0.1));
  if (elements.btnZoomIn) elements.btnZoomIn.addEventListener('click', () => changeZoom(0.1));
  if (elements.btnDownloadBBox) elements.btnDownloadBBox.addEventListener('click', downloadBBoxPdf);

  // Markdown Copy Button
  elements.btnCopyMd.addEventListener('click', () => {
    if (state.currentDocument && state.currentDocument.markdown) {
      navigator.clipboard.writeText(state.currentDocument.markdown);
      elements.btnCopyMd.innerText = 'Copied!';
      setTimeout(() => elements.btnCopyMd.innerText = 'Copy Markdown', 2000);
    }
  });

  // Download JSON tab button
  elements.btnDownloadJson.addEventListener('click', downloadCurrentJson);

  // Benchmarks Modal
  elements.btnRunBenchmarks.addEventListener('click', runBenchmarksModal);
  elements.btnCloseModal.addEventListener('click', () => elements.benchmarkModal.style.display = 'none');
  elements.benchmarkModal.addEventListener('click', (e) => {
    if (e.target === elements.benchmarkModal) elements.benchmarkModal.style.display = 'none';
  });

  // Recalibrate bounding boxes on viewport/window resize
  window.addEventListener('resize', () => {
    if (!state.currentDocument) return;
    const pages = state.currentDocument.pages || [{ page_number: 1, width: 612, height: 792 }];
    pages.forEach(pInfo => {
      recalibrateBoundingBoxes(pInfo.page_number, pInfo.width, pInfo.height);
    });
  });
}

// ============================================================================
// Pipeline Stepper Progress
// ============================================================================

function setPipelineStage(stage) {
  const steps = [elements.stepUpload, elements.stepDetect, elements.stepExtract, elements.stepAssemble, elements.stepVerify];
  steps.forEach(s => s.classList.remove('active', 'completed'));

  const indexMap = {
    'upload': 0,
    'detect': 1,
    'extract': 2,
    'assemble': 3,
    'verify': 4,
    'done': 5
  };

  const targetIdx = indexMap[stage] ?? 0;
  for (let i = 0; i < steps.length; i++) {
    if (i < targetIdx) steps[i].classList.add('completed');
    else if (i === targetIdx) steps[i].classList.add('active');
  }
}

// ============================================================================
// File Ingestion API Handlers
// ============================================================================

async function handleFileUpload(file) {
  setPipelineStage('upload');
  const formData = new FormData();
  formData.append('file', file);

  try {
    setPipelineStage('detect');
    setTimeout(() => setPipelineStage('extract'), 150);

    const res = await fetch('/api/v1/documents/upload', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }

    setPipelineStage('assemble');
    const doc = await res.json();
    setPipelineStage('verify');
    setTimeout(() => setPipelineStage('done'), 200);

    if (doc.processing_status === 'failed') {
      const errMsg = (doc.errors && doc.errors.length > 0) ? doc.errors[0].message : 'Unsupported or corrupted document format.';
      alert(`Processing Failed: ${errMsg}`);
      return;
    }

    renderDocument(doc);
  } catch (error) {
    alert(`Upload error: ${error.message}`);
    setPipelineStage('upload');
  }
}

async function loadPreviousFiles() {
  try {
    const res = await fetch('/api/v1/documents');
    if (!res.ok) return;
    const files = await res.json();
    if (files.length === 0) return;

    elements.previousFilesList.innerHTML = '';
    files.forEach(f => {
      const btn = document.createElement('button');
      btn.className = 'demo-chip';
      btn.innerHTML = `
        <span class="chip-icon">📄</span>
        <div class="chip-meta">
          <span class="chip-name">${escapeHtml(f.filename)}</span>
          <span class="chip-desc">${f.type.toUpperCase()} • ${f.status}</span>
        </div>
      `;
      btn.addEventListener('click', () => loadDocumentById(f.id));
      elements.previousFilesList.appendChild(btn);
    });
  } catch (e) {
    console.error('Error fetching previous files:', e);
  }
}

async function loadDocumentById(docId) {
  setPipelineStage('detect');
  try {
    const res = await fetch(`/api/v1/documents/${docId}`);
    if (!res.ok) throw new Error('Document could not be loaded');
    const doc = await res.json();
    setPipelineStage('done');
    renderDocument(doc);
  } catch (error) {
    console.error('Error loading document:', error);
  }
}

function downloadCurrentJson() {
  if (state.currentDocument) {
    const blob = new Blob([JSON.stringify(state.currentDocument, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${state.currentDocument.document_id}_ir.json`;
    a.click();
  }
}

// ============================================================================
// Document Rendering Orchestration
// ============================================================================

function renderDocument(doc) {
  state.currentDocument = doc;
  state.currentPage = 1;
  state.selectedBlockId = null;
  state.zoomLevel = 1.0;
  if (elements.zoomIndicator) elements.zoomIndicator.innerText = '100%';
  applyZoom();

  // 1. Update Document Summary Banner
  elements.bannerFilename.innerText = doc.filename;
  elements.bannerStatus.innerText = doc.processing_status.toUpperCase();
  elements.bannerStatus.className = `badge ${doc.processing_status === 'success' ? 'badge-success' : 'badge-error'}`;
  elements.bannerFormat.innerText = (doc.file_type || 'PDF').toUpperCase();

  const method = doc.blocks.length > 0 ? doc.blocks[0].extraction_method : 'native';
  elements.bannerParser.innerText = method;

  const hasHandwriting = doc.blocks.some(b => b.extraction_method === 'handwriting_ocr');
  if (elements.bannerHandwriting) {
    elements.bannerHandwriting.style.display = hasHandwriting ? 'inline-block' : 'none';
  }

  const totalPages = doc.stats.pages_processed || 1;
  elements.bannerMeta.innerText = `${totalPages} Page${totalPages > 1 ? 's' : ''} • ${doc.stats.blocks_extracted} Blocks Extracted • Latency: ${doc.stats.processing_time_seconds}s`;

  elements.bannerTablesCount.innerText = doc.stats.tables_detected;
  elements.bannerFiguresCount.innerText = doc.stats.figures_detected;
  elements.bannerEquationsCount.innerText = doc.stats.equations_detected;

  const avgConf = doc.blocks.length > 0
    ? Math.round((doc.blocks.reduce((acc, b) => acc + b.confidence, 0) / doc.blocks.length) * 100)
    : 100;
  elements.bannerConfidenceAvg.innerText = `${avgConf}%`;

  // Update format icon
  const iconMap = { 'pdf': '📄', 'docx': '📝', 'pptx': '📊', 'xlsx': '📗', 'image': '🖼️' };
  elements.bannerFormatIcon.innerText = iconMap[doc.file_type] || '📄';

  // Header Telemetry Pill
  elements.headSpeedPill.innerText = `${doc.stats.pages_per_second} p/s`;
  elements.headCostPill.innerText = `$${doc.stats.estimated_cost_per_1000_pages_usd.toFixed(2)}`;

  // 2. Render Left Pane (Document Page & Bounding Box Overlay)
  renderPagePreview();

  // 3. Render Center Pane (Semantic Blocks List)
  renderBlocksList();

  // 4. Render Right Pane Tabs
  renderMarkdownTab();
  renderJsonTab();
  renderTablesTab();
  renderTelemetryTab();

  // Default select first block
  if (doc.blocks && doc.blocks.length > 0) {
    selectBlock(doc.blocks[0].block_id);
  }
}

// ============================================================================
// Left Pane: Document Preview & Bounding Boxes
// ============================================================================

function renderPagePreview() {
  const doc = state.currentDocument;

  // clean up existing dynamic containers
  const existingContainers = document.querySelectorAll('.dynamic-canvas-container');
  existingContainers.forEach(c => c.remove());

  if (doc.file_type === 'xlsx') {
    elements.nonVisualFallback.style.display = 'block';
    const firstTable = doc.blocks.find(b => b.type === 'table');
    elements.fallbackRangePill.innerText = firstTable && firstTable.source.cell_range
      ? `Sheet: ${firstTable.source.sheet} (${firstTable.source.cell_range})`
      : 'Spreadsheet Grid';
    return;
  }

  elements.nonVisualFallback.style.display = 'none';

  const pages = doc.pages && doc.pages.length > 0 ? doc.pages : [{
    page_number: 1,
    image_url: null,
    width: 612,
    height: 792
  }];

  pages.forEach(pInfo => {
    const container = document.createElement('div');
    container.className = 'preview-canvas-container dynamic-canvas-container';
    container.style.marginBottom = '20px';
    container.dataset.pageNum = pInfo.page_number;

    const img = document.createElement('img');
    img.className = 'page-image';
    img.id = `pagePreviewImg_${pInfo.page_number}`;

    const bboxLayer = document.createElement('div');
    bboxLayer.className = 'bbox-overlay-layer';
    bboxLayer.id = `bboxOverlayLayer_${pInfo.page_number}`;

    container.appendChild(img);
    container.appendChild(bboxLayer);
    elements.previewViewport.appendChild(container);

    if (pInfo.image_url) {
      img.src = pInfo.image_url;
      img.onload = () => recalibrateBoundingBoxes(pInfo.page_number, pInfo.width, pInfo.height);
    } else {
      createSyntheticPageCanvas(img, pInfo.width, pInfo.height, pInfo.page_number);
    }
  });
}

function createSyntheticPageCanvas(imgElem, w, h, pageNum) {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  ctx.strokeRect(0, 0, w, h);

  imgElem.src = canvas.toDataURL();
  imgElem.onload = () => recalibrateBoundingBoxes(pageNum, w, h);
}

function changeZoom(delta) {
  let newZoom = state.zoomLevel + delta;
  if (newZoom < 0.2) newZoom = 0.2;
  if (newZoom > 5.0) newZoom = 5.0;
  state.zoomLevel = newZoom;

  if (elements.zoomIndicator) {
    elements.zoomIndicator.innerText = `${Math.round(state.zoomLevel * 100)}%`;
  }

  applyZoom();
}

function applyZoom() {
  const canvasContainers = document.querySelectorAll('.dynamic-canvas-container');
  canvasContainers.forEach(container => {
    container.style.transform = `scale(${state.zoomLevel})`;
    container.style.transformOrigin = 'top left';
  });
}

function recalibrateBoundingBoxes(pageNum, natWidth, natHeight) {
  const doc = state.currentDocument;
  if (!doc) return;

  const imgElem = document.getElementById(`pagePreviewImg_${pageNum}`);
  if (!imgElem) return;

  const dispWidth = imgElem.clientWidth;
  const dispHeight = imgElem.clientHeight;
  if (dispWidth === 0 || dispHeight === 0) return;

  const scaleX = dispWidth / natWidth;
  const scaleY = dispHeight / natHeight;

  renderBoundingBoxes(pageNum, scaleX, scaleY);
}

function renderBoundingBoxes(pageNum, scaleX, scaleY) {
  const layer = document.getElementById(`bboxOverlayLayer_${pageNum}`);
  if (!layer) return;
  layer.innerHTML = '';

  const doc = state.currentDocument;
  if (!doc || !doc.blocks) return;

  const pageBlocks = doc.blocks.filter(b => {
    if (b.source.page !== undefined && b.source.page !== null) {
      return b.source.page === pageNum;
    }
    if (b.source.slide !== undefined && b.source.slide !== null) {
      return b.source.slide === pageNum;
    }
    return true; // Single sheet or image
  });

  pageBlocks.forEach(b => {
    if (!b.source.bbox) return;

    const [x0, y0, x1, y1] = b.source.bbox;
    const boxElem = document.createElement('div');

    const left = x0 * scaleX;
    const top = y0 * scaleY;
    const width = Math.max(12, (x1 - x0) * scaleX);
    const height = Math.max(12, (y1 - y0) * scaleY);

    boxElem.className = `bbox-rect ${getBBoxColorClass(b)}`;
    boxElem.id = `bbox_${b.block_id}`;
    boxElem.style.left = `${left}px`;
    boxElem.style.top = `${top}px`;
    boxElem.style.width = `${width}px`;
    boxElem.style.height = `${height}px`;
    boxElem.title = `[#${b.reading_order}] ${b.type.toUpperCase()} | Conf: ${Math.round(b.confidence * 100)}%`;

    boxElem.innerText = b.content || "";
    boxElem.style.overflow = "hidden";
    boxElem.style.textOverflow = "ellipsis";
    boxElem.style.whiteSpace = "nowrap";
    boxElem.style.fontSize = "11px";
    boxElem.style.padding = "2px";
    boxElem.style.fontWeight = "600";
    boxElem.style.color = "#0f172a";

    if (b.block_id === state.selectedBlockId) {
      boxElem.classList.add('highlighted');
    }

    boxElem.addEventListener('click', (e) => {
      e.stopPropagation();
      selectBlock(b.block_id, true);
    });

    layer.appendChild(boxElem);
  });
}

function getBBoxColorClass(block) {
  if (block.confidence < 0.70) return 'color-low';
  switch (block.type) {
    case 'table': return 'color-table';
    case 'chart':
    case 'figure': return 'color-chart';
    case 'equation': return 'color-math';
    default: 
      if (block.extraction_method === 'handwriting_ocr') return 'color-orange';
      return 'color-text';
  }
}

// ============================================================================
// Center Pane: Semantic Blocks Stream
// ============================================================================

function renderBlocksList() {
  elements.blocksList.innerHTML = '';
  const doc = state.currentDocument;
  if (!doc || !doc.blocks) return;

  elements.blocksCountBadge.innerText = `${doc.blocks.length} Blocks`;

  doc.blocks.forEach(block => {
    const card = document.createElement('div');
    card.className = `block-card ${block.block_id === state.selectedBlockId ? 'selected' : ''}`;
    card.id = `card_${block.block_id}`;

    // Header with badges
    const confBadgeClass = block.confidence >= 0.90 ? 'badge-success' : (block.confidence >= 0.70 ? 'badge-warn' : 'badge-error');

    let renderedContent = '';
    if (block.type === 'heading') {
      renderedContent = `<div class="block-content-view is-heading">${escapeHtml(block.content)}</div>`;
    } else if (block.type === 'table' && block.table_data && block.table_data.headers.length > 0) {
      renderedContent = renderHtmlMiniTable(block.table_data);
    } else if (block.type === 'equation') {
      const latexStr = block.equation_data ? block.equation_data.latex : block.content;
      renderedContent = `<div class="block-content-view is-equation">$$ ${escapeHtml(latexStr)} $$</div>`;
    } else if (block.type === 'chart' || block.type === 'figure') {
      const title = block.chart_data && block.chart_data.title ? block.chart_data.title : 'Figure/Chart';
      renderedContent = `<div class="block-content-view"><strong>📈 [${title}]</strong><br><span style="color:var(--text-muted);font-size:12px;">Visual figure detected & preserved with bounding box.</span></div>`;
    } else {
      renderedContent = `<div class="block-content-view">${escapeHtml(block.content)}</div>`;
    }

    // Add specific text for Handwriting
    let displayType = block.type.toUpperCase();
    if (block.extraction_method === 'handwriting_ocr') {
        displayType = 'HANDWRITING';
    } else if (block.extraction_method === 'math_ocr' || block.type === 'equation') {
        displayType = 'EQUATION';
    }

    let statusHtml = '';
    if (block.status === 'needs_review' || block.confidence < 0.70) {
        statusHtml = `<span style="color:var(--accent-amber);font-size:12px;margin-left:8px;font-weight:bold;">⚠ Needs Review</span>`;
    }

    card.innerHTML = `
      <div class="block-card-header">
        <div class="block-badges">
          <span class="order-pill">#${block.reading_order}</span>
          <span class="badge badge-neutral">${displayType}</span>
          <span class="badge ${confBadgeClass}">${Math.round(block.confidence * 100)}%</span>
          ${statusHtml}
        </div>
        <span class="badge badge-method">${block.extraction_method}</span>
      </div>
      ${renderedContent}
      <div class="block-card-footer">
        <span>${formatBlockLocation(block.source)}</span>
        <button class="prov-btn" onclick="selectBlock('${block.block_id}', true)">
          Inspect Provenance →
        </button>
      </div>
    `;

    card.addEventListener('click', () => selectBlock(block.block_id, true));
    elements.blocksList.appendChild(card);
  });
}

function renderHtmlMiniTable(td) {
  let html = '<div style="overflow-x:auto;"><table class="mini-table">';
  if (td.headers.length > 0) {
    html += '<thead>';
    td.headers.forEach(hRow => {
      html += '<tr>' + hRow.map(c => `<th>${escapeHtml(c)}</th>`).join('') + '</tr>';
    });
    html += '</thead>';
  }
  html += '<tbody>';
  td.rows.slice(0, 5).forEach(row => {
    html += '<tr>' + row.map(c => `<td>${escapeHtml(c)}</td>`).join('') + '</tr>';
  });
  if (td.rows.length > 5) {
    html += `<tr><td colspan="${td.num_cols}" style="text-align:center;color:var(--text-dim);font-style:italic;">... +${td.rows.length - 5} more rows</td></tr>`;
  }
  html += '</tbody></table></div>';
  return html;
}

function formatBlockLocation(source) {
  const parts = [];
  if (source.page) parts.push(`Page ${source.page}`);
  if (source.slide) parts.push(`Slide ${source.slide}`);
  if (source.sheet) parts.push(`Sheet '${source.sheet}'`);
  if (source.cell_range) parts.push(source.cell_range);
  if (source.bbox) parts.push(`[${source.bbox.map(x => Math.round(x)).join(', ')}]`);
  return parts.join(' • ') || 'Source Root';
}

// ============================================================================
// Block Selection & Provenance Highlighting (Star Differentiator)
// ============================================================================

window.selectBlock = function (blockId, scrollIntoView = false) {
  state.selectedBlockId = blockId;
  const doc = state.currentDocument;
  if (!doc) return;

  const block = doc.blocks.find(b => b.block_id === blockId);
  if (!block) return;

  // Highlight center card
  document.querySelectorAll('.block-card').forEach(c => c.classList.remove('selected'));
  const cardElem = document.getElementById(`card_${blockId}`);
  if (cardElem) {
    cardElem.classList.add('selected');
    if (scrollIntoView) {
      cardElem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  // Highlight bounding box on preview
  document.querySelectorAll('.bbox-rect').forEach(r => r.classList.remove('highlighted'));
  const bboxElem = document.getElementById(`bbox_${blockId}`);
  if (bboxElem) {
    bboxElem.classList.add('highlighted');
  }

  // Update Provenance Tab in Right Pane
  elements.provMethodBadge.innerText = block.extraction_method;
  elements.provConfBadge.innerText = `${Math.round(block.confidence * 100)}% Confidence`;
  elements.provConfBadge.className = `badge ${block.confidence >= 0.90 ? 'badge-success' : (block.confidence >= 0.70 ? 'badge-warn' : 'badge-error')}`;
  elements.provOrderBadge.innerText = `Reading Order: #${block.reading_order}`;

  elements.provBlockTitle.innerText = `${block.type.toUpperCase()}: Block #${block.reading_order}`;
  elements.provSnippet.innerText = block.content.slice(0, 140) + (block.content.length > 140 ? '...' : '');

  elements.provDocVal.innerText = block.source.file || doc.filename;
  elements.provPageVal.innerText = block.source.page ? `Page ${block.source.page}` : (block.source.slide ? `Slide ${block.source.slide}` : (block.source.sheet ? `Sheet ${block.source.sheet}` : 'Root'));

  elements.provBBoxVal.innerText = block.source.bbox ? `[${block.source.bbox.map(x => Number(x).toFixed(1)).join(', ')}]` : (block.source.cell_range || 'N/A');
  elements.provLayerVal.innerText = block.extraction_method.includes('ocr') ? 'Level 2 (Specialized OCR Engine)' : 'Level 1 (Deterministic Native)';
};

// ============================================================================
// Right Pane: Intelligence Tabs
// ============================================================================

function renderMarkdownTab() {
  const doc = state.currentDocument;
  if (!doc) return;
  elements.markdownRenderArea.innerText = doc.markdown || '';
}

function renderJsonTab() {
  const doc = state.currentDocument;
  if (!doc) return;
  elements.jsonCodeArea.innerText = JSON.stringify(doc, null, 2);
}

function renderTablesTab() {
  const doc = state.currentDocument;
  if (!doc) return;
  elements.tablesInspectorList.innerHTML = '';

  const tableBlocks = doc.blocks.filter(b => b.type === 'table');
  if (tableBlocks.length === 0) {
    elements.tablesInspectorList.innerHTML = '<p style="color:var(--text-dim);font-style:italic;">No tabular structures detected in this document.</p>';
    return;
  }

  tableBlocks.forEach((tbl, idx) => {
    const wrap = document.createElement('div');
    wrap.style.marginBottom = '20px';
    wrap.innerHTML = `
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <h4 style="color:#fff;">Table ${idx + 1} (${tbl.source.page ? `Page ${tbl.source.page}` : tbl.source.sheet || 'Grid'})</h4>
        <span class="badge badge-success">Merged Cells: ${tbl.table_data ? tbl.table_data.merged_cells_count : 0}</span>
      </div>
      ${tbl.table_data ? renderHtmlMiniTable(tbl.table_data) : `<pre>${tbl.content}</pre>`}
    `;
    elements.tablesInspectorList.appendChild(wrap);
  });
}

function renderTelemetryTab() {
  const doc = state.currentDocument;
  if (!doc) return;

  elements.telCostVal.innerText = `$${doc.stats.estimated_cost_per_1000_pages_usd.toFixed(2)}`;
  elements.telSpeedVal.innerText = `${doc.stats.pages_per_second} p/s`;
  elements.telPagesVal.innerText = doc.stats.pages_processed;
  elements.telBlocksVal.innerText = doc.stats.blocks_extracted;
  elements.telLowConfVal.innerText = doc.stats.low_confidence_blocks;
}

// ============================================================================
// Benchmark Runner Modal Dialog
// ============================================================================

async function runBenchmarksModal() {
  elements.benchmarkModal.style.display = 'flex';
  elements.modalBenchmarkBody.innerHTML = '<div class="loader-spinner">Running 13x automated multi-format test documents...</div>';

  try {
    const res = await fetch('/api/v1/benchmarks/run');
    if (!res.ok) throw new Error('Benchmark execution failed');
    const data = await res.json();

    let html = `
      <div style="margin-bottom:16px;">
        <span class="badge badge-success" style="font-size:13px;padding:4px 10px;">Success Rate: ${data.success_rate_pct}% (${data.passed_scenarios}/${data.total_scenarios_evaluated})</span>
        <span class="badge badge-neutral" style="font-size:13px;padding:4px 10px;margin-left:8px;">Throughput: ${data.overall_pages_per_second} pages/sec</span>
        <span class="badge badge-method" style="font-size:13px;padding:4px 10px;margin-left:8px;">Cost / 1k: $${data.estimated_cost_per_1000_pages_usd} (Target: < $10)</span>
      </div>
      <table class="mini-table" style="font-size:12px;">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Format</th>
            <th>Status</th>
            <th>Latency</th>
            <th>Blocks</th>
            <th>Provenance</th>
            <th>Avg Conf</th>
            <th>Error Handling</th>
          </tr>
        </thead>
        <tbody>
    `;

    data.scenarios.forEach(sc => {
      const statusBadge = sc.test_passed ? '<span class="badge badge-success">PASSED</span>' : '<span class="badge badge-error">FAILED</span>';
      html += `
        <tr>
          <td><strong>${escapeHtml(sc.scenario)}</strong></td>
          <td>${sc.detected_format}</td>
          <td>${statusBadge}</td>
          <td>${sc.latency_seconds}s</td>
          <td>${sc.blocks_extracted}</td>
          <td>${sc.provenance_completeness_pct}%</td>
          <td>${Math.round(sc.average_confidence * 100)}%</td>
          <td><code>${sc.error_code || 'None'}</code></td>
        </tr>
      `;
    });

    html += '</tbody></table>';
    elements.modalBenchmarkBody.innerHTML = html;
  } catch (error) {
    elements.modalBenchmarkBody.innerHTML = `<div style="color:var(--accent-rose);">Benchmark error: ${error.message}</div>`;
  }
}

// Utility: HTML escaping
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function downloadBBoxPdf() {
  if (!state.currentDocument) return;
  const docId = state.currentDocument.document_id;
  elements.btnDownloadBBox.disabled = true;
  elements.btnDownloadBBox.innerHTML = '<span class="loader"></span> Preparing...';
  try {
    const res = await fetch(`/api/v1/documents/${docId}/export-pdf`);
    if (!res.ok) throw new Error('Failed to generate PDF');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = `${state.currentDocument.filename.replace('.pdf', '')}_bboxes.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  } finally {
    elements.btnDownloadBBox.disabled = false;
    elements.btnDownloadBBox.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> Download PDF';
  }
}
