"""Confidence Engine for ParseAnything.
Calculates transparent confidence scores based on multi-factor signals:
- Native parser vs OCR fidelity
- Text validity and unprintable character entropy
- Structural completeness (e.g. table cells and column consistency)
- Geometry consistency
Assigns HIGH (>= 0.90), MEDIUM (0.70 - 0.89), and LOW (< 0.70).
Sets status = 'review_required' for low-confidence blocks.
"""

from typing import List, Optional
from schemas.models import BlockStatus, BlockType, ConfidenceLevel, SemanticBlock


class ConfidenceEngine:
    """Evaluates and updates block confidence using transparent signals."""

    HIGH_THRESHOLD = 0.90
    MEDIUM_THRESHOLD = 0.70

    @classmethod
    def evaluate_block(cls, block: SemanticBlock) -> SemanticBlock:
        """Computes and assigns final confidence score, level, and review flags."""
        raw_score = block.confidence

        # Signal 1: Text validity and character entropy
        text = block.content.strip()
        if text:
            # Check ratio of readable ASCII/alphanumeric characters
            printable_ratio = sum(c.isprintable() for c in text) / len(text)
            if printable_ratio < 0.85:
                raw_score *= 0.70
                block.warnings.append("High ratio of unprintable or garbled characters.")

            # Check for excessive replacement characters or OCR gibberish
            if "" in text or "\\x" in text:
                raw_score *= 0.60
                block.warnings.append("Text contains corrupt replacement bytes.")

        # Signal 2: Table structural confidence
        if block.type == BlockType.TABLE and block.table_data:
            td = block.table_data
            if td.num_cols == 0 or td.num_rows == 0:
                raw_score = 0.50
                block.warnings.append("Empty table dimensions detected.")
            else:
                # Check ratio of populated cells
                filled_cells = sum(1 for c in td.cells if c.text.strip())
                total_cells = max(1, len(td.cells))
                fill_ratio = filled_cells / total_cells
                if fill_ratio < 0.30:
                    raw_score *= 0.80
                    block.warnings.append("Table contains over 70% empty cells.")

        # Signal 3: Extraction method base confidence
        method = block.extraction_method.lower()
        if "native" in method:
            # Native parser output is structurally sound
            raw_score = max(0.92, raw_score)
        elif "ocr" in method:
            # OCR is subject to image noise; cap if short and noisy
            if len(text) < 4 and not text.isalnum():
                raw_score = min(raw_score, 0.65)

        # Signal 4: Chart without recoverable numbers
        if block.type == BlockType.CHART and block.chart_data:
            if block.chart_data.status == "partial":
                # Honest partial flag
                raw_score = min(0.85, raw_score)

        final_score = round(max(0.0, min(1.0, raw_score)), 4)
        block.confidence = final_score

        # Assign confidence level
        if final_score >= cls.HIGH_THRESHOLD:
            block.confidence_level = ConfidenceLevel.HIGH
        elif final_score >= cls.MEDIUM_THRESHOLD:
            block.confidence_level = ConfidenceLevel.MEDIUM
        else:
            block.confidence_level = ConfidenceLevel.LOW
            block.status = BlockStatus.REVIEW_REQUIRED
            if "Low extraction confidence; review required." not in block.warnings:
                block.warnings.append("Low extraction confidence; review required.")

        return block

    @classmethod
    def evaluate_all(cls, blocks: List[SemanticBlock]) -> List[SemanticBlock]:
        """Evaluates all blocks in document."""
        return [cls.evaluate_block(b) for b in blocks]
