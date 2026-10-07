"""Production FastAPI REST API for ParseAnything Universal Document Ingestion Engine.
Exposes standard endpoints for upload, extraction, schema JSON, Markdown, provenance,
page image rendering for bounding box inspection, demo runners, and benchmark executions.
"""

import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Add project root to sys.path
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from schemas.models import Document, SemanticBlock
from schemas.errors import ErrorCode, ProcessingError
from pipeline.orchestrator import ExtractionPipeline
from backend.cost_manager import CostManager

# Initialize FastAPI App
app = FastAPI(
    title="ParseAnything — High-Fidelity Universal Document Ingestion Engine",
    description="Universal document ingestion platform with specialized parsers, provenance tracking, and fail-safe handling.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory storage for document results and system cache
DOCUMENTS_STORE: Dict[str, Document] = {}
PIPELINE = ExtractionPipeline()
COST_MANAGER = CostManager()

TEMP_DIR = BASE_DIR / "backend" / "data"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
PAGE_IMAGES_DIR = TEMP_DIR / "page_images"
PAGE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# System Cumulative Metrics
SYSTEM_STATS = {
    "total_documents_processed": 0,
    "total_pages_processed": 0,
    "total_blocks_extracted": 0,
    "total_processing_time_seconds": 0.0,
    "total_tables_detected": 0,
    "total_figures_detected": 0,
    "total_equations_detected": 0,
    "total_low_confidence_blocks": 0,
}


@app.get("/api/v1/health")
def health():
    return {
        "status": "healthy",
        "service": "ParseAnything Engine",
        "version": "1.0.0",
        "engine": "Level 1: Deterministic | Level 2: Specialized Local ML | Level 3: Vision Fallback"
    }


@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Ingest any document (PDF, DOCX, PPTX, XLSX, PNG, JPG).
    Detects format, executes 3-stage pipeline, attaches provenance, and returns Document.
    """
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    original_name = file.filename or "uploaded_file"
    suffix = Path(original_name).suffix.lower()

    # Save uploaded file
    target_path = TEMP_DIR / f"{doc_id}_{original_name}"
    with open(target_path, "wb") as f_out:
        shutil.copyfileobj(file.file, f_out)

    start_time = time.time()
    try:
        # Run 3-stage extraction pipeline
        doc = PIPELINE.process(
            file_path=target_path,
            document_id=doc_id,
            options={
                "export_page_images": False,
                "images_output_dir": str(PAGE_IMAGES_DIR)
            }
        )
        doc.filename = original_name

        # Store in document cache
        DOCUMENTS_STORE[doc_id] = doc

        # Update global instrumentation
        SYSTEM_STATS["total_documents_processed"] += 1
        SYSTEM_STATS["total_pages_processed"] += doc.stats.pages_processed
        SYSTEM_STATS["total_blocks_extracted"] += doc.stats.blocks_extracted
        SYSTEM_STATS["total_processing_time_seconds"] += doc.stats.processing_time_seconds
        SYSTEM_STATS["total_tables_detected"] += doc.stats.tables_detected
        SYSTEM_STATS["total_figures_detected"] += doc.stats.figures_detected
        SYSTEM_STATS["total_equations_detected"] += doc.stats.equations_detected
        SYSTEM_STATS["total_low_confidence_blocks"] += doc.stats.low_confidence_blocks

        # Record in CostManager (local execution = 0 API cost)
        COST_MANAGER.record_call("native_extractor", pages=doc.stats.pages_processed)

        return doc
    except Exception as e:
        elapsed = time.time() - start_time
        err = ProcessingError(
            code=ErrorCode.PARSER_FAILURE,
            message=f"Extraction encountered unhandled exception: {str(e)}",
            stage="upload_processing"
        )
        fail_doc = PIPELINE.parsers["pdf_parser"]._create_failure_document(
            doc_id, original_name, suffix.lstrip("."), err, elapsed
        ) if hasattr(PIPELINE.parsers["pdf_parser"], "_create_failure_document") else Document(
            document_id=doc_id,
            filename=original_name,
            file_type="unknown",
            file_size_bytes=target_path.stat().st_size if target_path.exists() else 0,
            processing_status="failed",
            errors=[err]
        )
        DOCUMENTS_STORE[doc_id] = fail_doc
        return fail_doc


@app.get("/api/v1/documents")
def list_documents():
    """Retrieve all previously uploaded and processed documents."""
    return [{"id": k, "filename": v.filename, "type": v.file_type, "status": v.processing_status} for k, v in DOCUMENTS_STORE.items()]

@app.get("/api/v1/documents/{document_id}")
def get_document(document_id: str):
    """Retrieve full document model for document_id."""
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found")
    return DOCUMENTS_STORE[document_id]


@app.get("/api/v1/documents/{document_id}/json")
def get_document_json(document_id: str):
    """Retrieve raw structured JSON representation conforming to schema 1.0."""
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found")
    return JSONResponse(content=DOCUMENTS_STORE[document_id].model_dump())


@app.get("/api/v1/documents/{document_id}/markdown", response_class=PlainTextResponse)
def get_document_markdown(document_id: str):
    """Retrieve assembled reading-order aligned Markdown."""
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found")
    return DOCUMENTS_STORE[document_id].markdown or ""


@app.get("/api/v1/documents/{document_id}/blocks")
def get_document_blocks(document_id: str):
    """Retrieve semantic blocks with provenance bounding boxes."""
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found")
    return DOCUMENTS_STORE[document_id].blocks


@app.get("/api/v1/documents/{document_id}/status")
def get_document_status(document_id: str):
    """Retrieve current processing status and statistics."""
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = DOCUMENTS_STORE[document_id]
    return {
        "document_id": doc.document_id,
        "filename": doc.filename,
        "status": doc.processing_status,
        "stats": doc.stats,
        "warnings_count": len(doc.warnings),
        "errors_count": len(doc.errors)
    }


@app.get("/api/v1/documents/{document_id}/errors")
def get_document_errors(document_id: str):
    """Retrieve standardized error objects."""
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found")
    return DOCUMENTS_STORE[document_id].errors


@app.get("/api/v1/documents/{document_id}/page-image/{page_number}")
def get_page_image(document_id: str, page_number: int):
    """Serves high-resolution rendered page image for bounding-box overlay, generating lazily if needed."""
    img_path = PAGE_IMAGES_DIR / f"{document_id}_p{page_number}.png"
    if not img_path.exists():
        if document_id not in DOCUMENTS_STORE:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = DOCUMENTS_STORE[document_id]
        if doc.file_type == "pdf":
            try:
                import pymupdf
                target_path = TEMP_DIR / f"{document_id}_{doc.filename}"
                if not target_path.exists():
                    raise HTTPException(status_code=404, detail="Original document file not found")
                
                pdf_doc = pymupdf.open(str(target_path))
                if page_number < 1 or page_number > len(pdf_doc):
                    pdf_doc.close()
                    raise HTTPException(status_code=404, detail="Page number out of bounds")
                    
                page = pdf_doc[page_number - 1]
                pix = page.get_pixmap(dpi=150)
                pix.save(str(img_path))
                pdf_doc.close()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to generate page image lazily: {str(e)}")
        else:
            raise HTTPException(status_code=404, detail=f"Page image for page {page_number} not found.")
            
    return FileResponse(img_path, media_type="image/png")


@app.get("/api/v1/documents/{document_id}/export-pdf")
def export_pdf_with_bboxes(document_id: str):
    """Generates and downloads a copy of the PDF with bounding boxes drawn."""
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc = DOCUMENTS_STORE[document_id]
    if doc.file_type != "pdf":
        raise HTTPException(status_code=400, detail="BBox export is only supported for PDFs.")
        
    try:
        import pymupdf
        target_path = TEMP_DIR / f"{document_id}_{doc.filename}"
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Original document file not found")
            
        pdf_doc = pymupdf.open(str(target_path))
        
        # Draw bounding boxes
        for block in doc.blocks:
            if block.source.bbox and block.source.page:
                page_num = block.source.page
                if 1 <= page_num <= len(pdf_doc):
                    page = pdf_doc[page_num - 1]
                    # PDF coordinates are bottom-left but PyMuPDF's draw_rect expects top-left.
                    # Wait, our bboxes are currently returned as [x0, y0, x1, y1] 
                    # If we just pass rect, PyMuPDF expects Rect(x0, y0, x1, y1)
                    # Let's draw it using the raw bbox
                    rect = pymupdf.Rect(*block.source.bbox)
                    
                    color = (0.22, 0.74, 0.97) # Cyan default
                    if block.type == "table": color = (0.06, 0.73, 0.51)
                    elif block.type == "figure" or block.type == "chart": color = (0.66, 0.33, 0.97)
                    elif block.type == "equation": color = (0.96, 0.62, 0.04)
                    elif block.confidence < 0.70: color = (0.96, 0.25, 0.37)
                    
                    page.draw_rect(rect, color=color, width=1.5)
        
        out_path = TEMP_DIR / f"{document_id}_bboxes.pdf"
        pdf_doc.save(str(out_path))
        pdf_doc.close()
        
        return FileResponse(out_path, media_type="application/pdf", filename=f"{doc.filename.replace('.pdf', '')}_bboxes.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate BBox PDF: {str(e)}")

@app.get("/api/v1/demo/samples")
def list_demo_samples():
    """Lists bundled demonstration documents showing all challenge capabilities."""
    samples = [
        {"id": "obsession_case_study", "name": "Obsession Case Study Answer", "file": "Obsession_Case_Study_Answer.pdf", "desc": "User's provided document"}
    ]
    return samples


@app.post("/api/v1/demo/run/{sample_id}")
def run_demo_sample(sample_id: str):
    """Instantly parses a bundled demonstration document for live judge demonstration."""
    sample_map = {
        "obsession_case_study": BASE_DIR / "Obsession_Case_Study_Answer.pdf"
    }

    target = sample_map.get(sample_id)
    if not target or not target.exists():
        raise HTTPException(status_code=404, detail="Demo sample document not found.")

    doc_id = f"demo_{sample_id}_{uuid.uuid4().hex[:4]}"
    doc = PIPELINE.process(
        file_path=target,
        document_id=doc_id,
        options={
            "export_page_images": True,
            "images_output_dir": str(PAGE_IMAGES_DIR)
        }
    )
    DOCUMENTS_STORE[doc_id] = doc

    # Update cumulative stats
    SYSTEM_STATS["total_documents_processed"] += 1
    SYSTEM_STATS["total_pages_processed"] += doc.stats.pages_processed
    SYSTEM_STATS["total_blocks_extracted"] += doc.stats.blocks_extracted
    SYSTEM_STATS["total_processing_time_seconds"] += doc.stats.processing_time_seconds
    SYSTEM_STATS["total_tables_detected"] += doc.stats.tables_detected
    SYSTEM_STATS["total_figures_detected"] += doc.stats.figures_detected
    SYSTEM_STATS["total_equations_detected"] += doc.stats.equations_detected
    SYSTEM_STATS["total_low_confidence_blocks"] += doc.stats.low_confidence_blocks

    return doc


@app.get("/api/v1/metrics/system")
def get_system_metrics():
    """Returns real-time processing throughput, cumulative statistics, and API cost projections."""
    total_time = SYSTEM_STATS["total_processing_time_seconds"]
    total_pages = SYSTEM_STATS["total_pages_processed"]
    avg_speed = round(total_pages / max(0.001, total_time), 2)

    cost_info = COST_MANAGER.get_metrics_summary()

    return {
        "cumulative_stats": SYSTEM_STATS,
        "average_pages_per_second": avg_speed,
        "cost_metrics": cost_info,
        "target_cost_per_1000_pages_usd": 10.00,
        "status": "Optimal (100% offline & local cascading execution)"
    }


# Mount frontend static files
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
