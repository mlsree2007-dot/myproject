import re

with open("frontend/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Revert state
content = re.sub(
    r"zoomLevel: 1.0,\s*isDebugMode: false,",
    r"zoomLevel: 1.0,",
    content
)

# 2. Revert btnDebugCoords
content = re.sub(
    r"btnZoomIn: document.getElementById\('btnZoomIn'\),\s*btnDebugCoords: document.getElementById\('btnDebugCoords'\),",
    r"btnZoomIn: document.getElementById('btnZoomIn'),",
    content
)

# 3. Revert btnDebugCoords event listener
content = re.sub(
    r"if \(elements\.btnZoomIn\) elements\.btnZoomIn\.addEventListener\('click', \(\) => changeZoom\(0\.1\)\);\s*if \(elements\.btnDebugCoords\) elements\.btnDebugCoords\.addEventListener\('click', \(\) => \{[\s\S]*?\}\);",
    r"if (elements.btnZoomIn) elements.btnZoomIn.addEventListener('click', () => changeZoom(0.1));",
    content
)

# 4. Revert recalibrateBoundingBoxes
old_recal = r"function recalibrateBoundingBoxes\(pageNum, natWidth, natHeight\) \{[\s\S]*?renderBoundingBoxes\(pageNum, scaleX, scaleY, natHeight, natWidth, dispWidth, dispHeight\);\s*\}"

new_recal = """function recalibrateBoundingBoxes(pageNum, natWidth, natHeight) {
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
}"""

content = re.sub(old_recal, new_recal, content)

# 5. Revert renderBoundingBoxes
old_render = r"function renderBoundingBoxes\(pageNum, scaleX, scaleY, natHeight, natWidth, dispWidth, dispHeight\) \{[\s\S]*?layer\.appendChild\(svgElem\);\s*\}"

new_render = """function renderBoundingBoxes(pageNum, scaleX, scaleY) {
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

content = re.sub(old_render, new_render, content)

with open("frontend/app.js", "w", encoding="utf-8") as f:
    f.write(content)
