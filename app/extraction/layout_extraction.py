"""
Stage 1: PDF text extraction from bytes.
pypdf (one block per page) with pdfplumber fallback when empty or for layout-aware.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Union

import pdfplumber

from app.extraction.schemas import Block, BlockType

logger = logging.getLogger(__name__)

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[misc, assignment]


def extract_layout_from_bytes(
    content: bytes,
    use_pypdf: bool = True,
) -> list[Block]:
    """
    Extract content from PDF bytes as a list of Block.
    Uses pypdf first (one text block per page), then pdfplumber if empty.
    """
    if not content or len(content) < 100:
        return []

    stream = io.BytesIO(content)

    if use_pypdf and PdfReader is not None:
        blocks = _extract_layout_pypdf_stream(stream)
        if blocks:
            return blocks
        stream.seek(0)

    blocks = _extract_layout_pdfplumber_stream(stream)
    return blocks


def extract_layout(
    pdf_path: Union[str, Path],
    use_tika_fallback: bool = True,
    use_pypdf: bool = True,
) -> list[Block]:
    """
    Extract content from a PDF file path. Used for tests or when path is available.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    with open(path, "rb") as f:
        content = f.read()
    return extract_layout_from_bytes(content, use_pypdf=use_pypdf)


def _extract_layout_pypdf_stream(stream: io.BytesIO) -> list[Block]:
    """Extract text with pypdf from stream: one text block per page."""
    if PdfReader is None:
        return []
    try:
        reader = PdfReader(stream)
        blocks: list[Block] = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                blocks.append(
                    Block(
                        type=BlockType.TEXT,
                        page=page_num,
                        bbox=None,
                        content=text,
                        caption=None,
                    )
                )
        return blocks
    except Exception as e:
        logger.warning("pypdf extraction failed: %s", e)
        return []


def _extract_layout_pdfplumber_stream(stream: io.BytesIO) -> list[Block]:
    """Extract blocks with pdfplumber from stream (layout-aware)."""
    blocks: list[Block] = []
    try:
        with pdfplumber.open(stream) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_blocks = _extract_page_blocks(page, page_num)
                blocks.extend(page_blocks)
        return _sort_blocks_by_reading_order(blocks)
    except Exception as e:
        logger.warning("pdfplumber extraction failed: %s", e)
        return []


def _extract_page_blocks(page, page_num: int) -> list[Block]:
    """Extract blocks from a single pdfplumber page."""
    blocks: list[Block] = []
    table_bboxes: list[tuple[float, float, float, float]] = []

    tables = page.find_tables()
    if tables:
        table_bboxes = [t.bbox for t in tables]
        for t in tables:
            extracted = t.extract()
            if extracted:
                content = _serialize_table(extracted)
                blocks.append(
                    Block(
                        type=BlockType.TABLE,
                        page=page_num,
                        bbox=t.bbox,
                        content=content,
                        caption=None,
                    )
                )

    try:
        for im in getattr(page, "images", []) or []:
            x0, top = im.get("x0", 0), im.get("top", 0)
            x1, bottom = im.get("x1", x0), im.get("bottom", top)
            bbox = (float(x0), float(top), float(x1), float(bottom))
            blocks.append(
                Block(
                    type=BlockType.FIGURE,
                    page=page_num,
                    bbox=bbox,
                    content="",
                    caption=None,
                )
            )
    except Exception as e:
        logger.debug("Figure detection skipped: %s", e)

    chars = page.chars
    if not chars:
        text = page.extract_text()
        if text and text.strip():
            blocks.append(
                Block(
                    type=BlockType.TEXT,
                    page=page_num,
                    bbox=None,
                    content=text.strip(),
                    caption=None,
                )
            )
        return blocks

    from collections import defaultdict

    line_chars: dict[float, list] = defaultdict(list)
    for c in chars:
        top = round(c["top"], 1)
        line_chars[top].append(c)

    lines = []
    for top in sorted(line_chars.keys()):
        line_chars_list = line_chars[top]
        line_chars_list.sort(key=lambda x: x["x0"])
        text = "".join(c["text"] for c in line_chars_list)
        font_size = line_chars_list[0].get("size") if line_chars_list else None
        font_name = (
            (line_chars_list[0].get("fontname") or "") if line_chars_list else ""
        )
        is_bold = "bold" in font_name.lower() or "Bold" in font_name
        x0 = min(c["x0"] for c in line_chars_list)
        x1 = max(c["x1"] for c in line_chars_list)
        bottom = max(c["top"] + (c.get("height") or 0) for c in line_chars_list)
        lines.append(
            {
                "text": text,
                "top": top,
                "x0": x0,
                "x1": x1,
                "bottom": bottom,
                "font_size": font_size,
                "is_bold": is_bold,
            }
        )

    text_blocks = _lines_to_text_blocks(lines, page_num, table_bboxes=table_bboxes)
    blocks.extend(text_blocks)
    return blocks


def _sort_blocks_by_reading_order(blocks: list[Block]) -> list[Block]:
    """Sort blocks by page then vertical then horizontal position."""

    def key(b: Block):
        top = b.bbox[1] if b.bbox else 0
        left = b.bbox[0] if b.bbox else 0
        return (b.page, top, left)

    return sorted(blocks, key=key)


def _serialize_table(rows: list) -> str:
    """Serialize table rows to a string (markdown-like)."""
    lines = []
    for row in rows:
        if row is None:
            continue
        cells = [str(c).strip() if c is not None else "" for c in row]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _lines_to_text_blocks(
    lines: list[dict],
    page_num: int,
    table_bboxes: list[tuple[float, float, float, float]] | None = None,
) -> list[Block]:
    """Merge lines into text blocks; add font_size and is_bold for Stage 2."""
    table_bboxes = table_bboxes or []
    blocks: list[Block] = []
    current_lines: list[dict] = []
    current_bbox: tuple[float, float, float, float] | None = None

    def flush_block():
        nonlocal current_lines, current_bbox
        if not current_lines:
            return
        text = "\n".join(line["text"] for line in current_lines).strip()
        if text:
            first = current_lines[0]
            blocks.append(
                Block(
                    type=BlockType.TEXT,
                    page=page_num,
                    bbox=current_bbox,
                    content=text,
                    caption=None,
                    font_size=first.get("font_size"),
                    is_bold=first.get("is_bold", False),
                )
            )
        current_lines = []
        current_bbox = None

    for line in lines:
        top, x0, x1, bottom = line["top"], line["x0"], line["x1"], line["bottom"]
        if _in_any_bbox((x0, top, x1, bottom), table_bboxes):
            flush_block()
            continue

        prev_bottom = current_lines[-1]["bottom"] if current_lines else None
        line_height = bottom - top
        gap = (top - prev_bottom) if prev_bottom is not None else 999

        if prev_bottom is not None and gap > max(15, line_height * 1.5):
            flush_block()

        current_lines.append(line)
        if current_bbox is None:
            current_bbox = (x0, top, x1, bottom)
        else:
            current_bbox = (
                min(current_bbox[0], x0),
                min(current_bbox[1], top),
                max(current_bbox[2], x1),
                max(current_bbox[3], bottom),
            )

    flush_block()
    return blocks


def _in_any_bbox(
    box: tuple[float, float, float, float],
    bboxes: list[tuple[float, float, float, float]],
) -> bool:
    """Check if box overlaps any of the given bboxes."""
    x0, top, x1, bottom = box
    for tx0, ttop, tx1, tbottom in bboxes:
        if not (x1 <= tx0 or x0 >= tx1 or bottom <= ttop or top >= tbottom):
            return True
    return False
