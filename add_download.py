import re

with open("frontend/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# Add btnDownloadBBox to elements
content = re.sub(
    r"btnUpload: document.getElementById\('btnUpload'\),",
    r"btnUpload: document.getElementById('btnUpload'),\n  btnDownloadBBox: document.getElementById('btnDownloadBBox'),",
    content
)

# Enable button when doc loads
content = re.sub(
    r"elements\.docUploadName\.innerText = doc\.filename;",
    r"elements.docUploadName.innerText = doc.filename;\n  if (elements.btnDownloadBBox) elements.btnDownloadBBox.disabled = false;",
    content
)

# Add event listener
content = re.sub(
    r"if \(elements\.btnZoomIn\) elements\.btnZoomIn\.addEventListener\('click', \(\) => changeZoom\(0\.1\)\);",
    r"if (elements.btnZoomIn) elements.btnZoomIn.addEventListener('click', () => changeZoom(0.1));\n  if (elements.btnDownloadBBox) elements.btnDownloadBBox.addEventListener('click', downloadBBoxPdf);",
    content
)

# Add download function
download_fn = """
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
"""

content += "\n" + download_fn

with open("frontend/app.js", "w", encoding="utf-8") as f:
    f.write(content)
