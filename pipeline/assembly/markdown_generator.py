"""Structured Markdown Generation Engine for ParseAnything.
Converts extracted semantic blocks into clean, reading-order aligned Markdown.
Preserves headings, markdown tables, LaTeX equations, provenance links, and flags.
"""

from typing import List
from schemas.models import BlockStatus, BlockType, SemanticBlock


class MarkdownGenerator:
    """Generates clean GitHub-Flavored Markdown from ordered semantic blocks."""

    @classmethod
    def generate(cls, blocks: List[SemanticBlock], filename: str = "document") -> str:
        """Converts semantic blocks strictly ordered by reading_order into structured Markdown."""
        if not blocks:
            return f"# Document: {filename}\n\n*No extractable semantic content detected.*"

        # Sort blocks by reading_order
        sorted_blocks = sorted(blocks, key=lambda b: b.reading_order)

        sections: List[str] = [f"# {filename}\n"]

        for block in sorted_blocks:
            # Skip pure headers and footers from main document flow to avoid clutter
            if block.type in (BlockType.HEADER, BlockType.FOOTER):
                continue

            md_chunk = cls._render_block(block)
            if md_chunk:
                sections.append(md_chunk)

        return "\n\n".join(sections)

    @classmethod
    def _render_block(cls, block: SemanticBlock) -> str:
        """Renders individual semantic block into Markdown representation with provenance."""
        content = block.content.strip()

        # Format provenance tag
        prov_parts = []
        if block.source.page is not None:
            prov_parts.append(f"Page {block.source.page}")
        elif block.source.slide is not None:
            prov_parts.append(f"Slide {block.source.slide}")
        elif block.source.sheet is not None:
            prov_parts.append(f"Sheet '{block.source.sheet}'")
            if block.source.cell_range:
                prov_parts.append(f"Cells {block.source.cell_range}")

        if block.source.bbox:
            bbox_str = f"[{', '.join(str(int(x)) for x in block.source.bbox)}]"
            prov_parts.append(f"bbox {bbox_str}")

        prov_parts.append(f"Confidence: {int(block.confidence * 100)}%")
        prov_parts.append(f"Method: {block.extraction_method}")
        prov_str = " | ".join(prov_parts)

        # Warning indicator if low confidence or review required
        warning_banner = ""
        if block.status == BlockStatus.REVIEW_REQUIRED or block.confidence < 0.70:
            warning_banner = f"> ⚠️ **[REVIEW REQUIRED - Low Confidence ({int(block.confidence * 100)}%)]**\n\n"

        # Heading rendering
        if block.type == BlockType.HEADING:
            level = block.metadata.get("level", 2)
            prefix = "#" * max(1, min(6, level))
            return f"{warning_banner}{prefix} {content}\n*Source: {prov_str}*"

        # Table rendering
        elif block.type == BlockType.TABLE:
            table_md = block.table_data.markdown_table if block.table_data and block.table_data.markdown_table else content
            return f"{warning_banner}{table_md}\n\n*Source: {prov_str}*"

        # Equation rendering
        elif block.type == BlockType.EQUATION:
            eq_latex = block.equation_data.latex if block.equation_data else content
            if not eq_latex.startswith("$"):
                eq_latex = f"$$\n{eq_latex}\n$$"
            return f"{warning_banner}{eq_latex}\n\n*Source: {prov_str}*"

        # Chart / Figure rendering
        elif block.type in (BlockType.CHART, BlockType.FIGURE):
            title = block.chart_data.title if block.chart_data and block.chart_data.title else "Figure/Chart"
            chart_type = block.chart_data.chart_type if block.chart_data and block.chart_data.chart_type else "graphic"
            warning_note = f"\n> *Notice: {block.chart_data.warning}*" if block.chart_data and block.chart_data.warning else ""
            return f"{warning_banner}**[{chart_type.upper()}: {title}]**{warning_note}\n\n*Source: {prov_str}*"

        # Footnote
        elif block.type == BlockType.FOOTNOTE:
            return f"{warning_banner}> 📝 *Footnote: {content}*\n*Source: {prov_str}*"

        # List item
        elif block.type == BlockType.LIST_ITEM:
            return f"- {content}"

        # Standard paragraph
        else:
            return f"{warning_banner}{content}\n\n*Source: {prov_str}*"
