import re

with open("frontend/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# Add isDebugMode to state
content = re.sub(
    r"zoomLevel: 1\.0,",
    r"zoomLevel: 1.0,\n  isDebugMode: false,",
    content
)

# Add btnDebugCoords to elements
content = re.sub(
    r"btnZoomIn: document\.getElementById\('btnZoomIn'\),",
    r"btnZoomIn: document.getElementById('btnZoomIn'),\n  btnDebugCoords: document.getElementById('btnDebugCoords'),",
    content
)

# Add event listener for debug button
content = re.sub(
    r"if \(elements\.btnZoomIn\) elements\.btnZoomIn\.addEventListener\('click', \(\) => changeZoom\(0\.1\)\);",
    r"if (elements.btnZoomIn) elements.btnZoomIn.addEventListener('click', () => changeZoom(0.1));\n  if (elements.btnDebugCoords) elements.btnDebugCoords.addEventListener('click', () => {\n    state.isDebugMode = !state.isDebugMode;\n    elements.btnDebugCoords.style.background = state.isDebugMode ? '#38BDF8' : '';\n    elements.btnDebugCoords.style.color = state.isDebugMode ? '#000' : '';\n  });",
    content
)

# Add console.log inside renderBoundingBoxes
debug_log = """
    rect.addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.isDebugMode) {
        const dbg = `Block ID: ${b.block_id}\\n` +
                    `Page: ${pageNum}\\n` +
                    `PDF page: ${natWidth} x ${natHeight}\\n` +
                    `Original PDF bbox: [${pdfX0.toFixed(2)}, ${pdfY0.toFixed(2)}, ${pdfX1.toFixed(2)}, ${pdfY1.toFixed(2)}]\\n` +
                    `Converted top-left bbox: [${topLeftX.toFixed(2)}, ${topLeftY.toFixed(2)}, ${bottomRightX.toFixed(2)}, ${bottomRightY.toFixed(2)}]\\n` +
                    `Display: ${dispWidth} x ${dispHeight}\\n` +
                    `Scale: X=${scaleX.toFixed(4)}, Y=${scaleY.toFixed(4)}\\n` +
                    `Final screen bbox: [${screenX.toFixed(2)}, ${screenY.toFixed(2)}, ${(screenX + screenW).toFixed(2)}, ${(screenY + screenH).toFixed(2)}]`;
        alert(dbg);
        console.log(dbg);
      }
      selectBlock(b.block_id, true);
    });
"""

content = re.sub(
    r"rect\.addEventListener\('click', \(e\) => \{\s*e\.stopPropagation\(\);\s*selectBlock\(b\.block_id, true\);\s*\}\);",
    debug_log.strip(),
    content
)

old_render = "function renderBoundingBoxes(pageNum, scaleX, scaleY, natHeight) {"
new_render = "function renderBoundingBoxes(pageNum, scaleX, scaleY, natHeight, natWidth, dispWidth, dispHeight) {"
content = content.replace(old_render, new_render)

old_recal = "renderBoundingBoxes(pageNum, scaleX, scaleY, natHeight);"
new_recal = "renderBoundingBoxes(pageNum, scaleX, scaleY, natHeight, natWidth, dispWidth, dispHeight);"
content = content.replace(old_recal, new_recal)

with open("frontend/app.js", "w", encoding="utf-8") as f:
    f.write(content)
