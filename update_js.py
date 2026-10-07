import re

with open("frontend/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update DOM Elements
content = re.sub(
    r"pagePreviewImg: document.getElementById\('pagePreviewImg'\),[\s\S]*?zoomIndicator: document.getElementById\('zoomIndicator'\),",
    r"previewViewport: document.getElementById('previewViewport'),\n  nonVisualFallback: document.getElementById('nonVisualFallback'),\n  fallbackRangePill: document.getElementById('fallbackRangePill'),\n  btnZoomOut: document.getElementById('btnZoomOut'),\n  btnZoomIn: document.getElementById('btnZoomIn'),\n  zoomIndicator: document.getElementById('zoomIndicator'),",
    content
)

# 2. Remove Event Listeners for pages
content = re.sub(
    r"// Page Navigation\s*elements.btnPrevPage.addEventListener\('click', \(\) => changePage\(-1\)\);\s*elements.btnNextPage.addEventListener\('click', \(\) => changePage\(1\)\);",
    "",
    content
)

# 3. Replace renderPagePreview and related functions
replacement = """function renderPagePreview() {
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
    container.style.transformOrigin = 'top center';
    container.style.marginBottom = `${20 * state.zoomLevel}px`;
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
}"""

content = re.sub(
    r"function renderPagePreview\(\) \{[\s\S]*?function getBBoxColorClass\(block\) \{",
    replacement + "\n\nfunction getBBoxColorClass(block) {",
    content
)

# 4. Remove resize event recalibrateBoundingBoxes since it requires pageNum
content = re.sub(
    r"window\.addEventListener\('resize', recalibrateBoundingBoxes\);",
    r"// Resize observer removed, zoom handles scale",
    content
)

with open("frontend/app.js", "w", encoding="utf-8") as f:
    f.write(content)
