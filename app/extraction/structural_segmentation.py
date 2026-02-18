"""
Stage 2: Structural segmentation.
Document outline: heading hierarchy (H1-H4), table boundaries, figure captions.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict

from app.extraction.schemas import (
    Block,
    BlockType,
    ExtractionConfidence,
    Segment,
    SectionType,
)

logger = logging.getLogger(__name__)

DEFAULT_FONT_SIZE_LEVELS = (18, 14, 12, 10)  # H1, H2, H3, H4
FIGURE_CAPTION_RE = re.compile(r"(?i)figure\s+\d+")
TABLE_CAPTION_RE = re.compile(r"(?i)table\s+\d+")


def _has_valid_figure_caption(block: Block) -> bool:
    if block.caption and block.caption.strip():
        return True
    return bool(FIGURE_CAPTION_RE.search(block.content or ""))


def _has_valid_table_caption(block: Block) -> bool:
    if block.caption and block.caption.strip():
        return True
    if TABLE_CAPTION_RE.search(block.content or ""):
        return True
    content = (block.content or "").strip()
    if not content:
        return False
    first_line = content.split("\n")[0].strip()
    if not first_line or len(first_line) > 200:
        return False
    sep_count = sum(first_line.count(c) for c in "|-")
    if sep_count / max(len(first_line), 1) > 0.5:
        return False
    return True


def segment_document(
    blocks: list[Block],
    font_size_levels: tuple[float, float, float, float] = DEFAULT_FONT_SIZE_LEVELS,
) -> list[Segment]:
    """
    Convert layout blocks into segments with heading, level, section_type, content,
    and extraction_confidence.
    """
    if not blocks:
        return []

    segments: list[Segment] = []
    font_h1, font_h2, font_h3, font_h4 = font_size_levels

    text_blocks = [b for b in blocks if b.type == BlockType.TEXT]
    size_counts: dict[float, int] = defaultdict(int)
    for b in text_blocks:
        if b.font_size is not None:
            size_counts[round(b.font_size, 1)] += 1
    body_size = _infer_body_font_size(size_counts)

    i = 0
    while i < len(blocks):
        block = blocks[i]
        if block.type == BlockType.TABLE:
            if not _has_valid_table_caption(block):
                i += 1
                continue
            conf = _table_confidence(block)
            segments.append(
                Segment(
                    heading="",
                    level=1,
                    section_type=SectionType.TABLE,
                    content=block.content,
                    page=block.page,
                    caption=block.caption,
                    extraction_confidence=conf,
                )
            )
            i += 1
            continue
        if block.type == BlockType.FIGURE:
            if not _has_valid_figure_caption(block):
                i += 1
                continue
            conf = _figure_confidence(block)
            segments.append(
                Segment(
                    heading=block.caption or "Figure",
                    level=1,
                    section_type=SectionType.FIGURE,
                    content=block.content or (block.caption or ""),
                    page=block.page,
                    caption=block.caption,
                    extraction_confidence=conf,
                )
            )
            i += 1
            continue
        heading_level, is_heading, confidence = _classify_heading(
            block, body_size, font_h1, font_h2, font_h3, font_h4
        )
        if is_heading and block.content.strip():
            heading_text = block.content.strip()
            body_parts = []
            i += 1
            while i < len(blocks) and blocks[i].type == BlockType.TEXT:
                next_b = blocks[i]
                next_level, next_is_heading, next_conf = _classify_heading(
                    next_b, body_size, font_h1, font_h2, font_h3, font_h4
                )
                if next_is_heading:
                    break
                body_parts.append(next_b.content.strip())
                confidence = _min_confidence(confidence, next_conf)
                i += 1
            content = "\n\n".join(p for p in body_parts if p)
            segments.append(
                Segment(
                    heading=heading_text,
                    level=heading_level,
                    section_type=SectionType.TEXT,
                    content=content or heading_text,
                    page=block.page,
                    caption=None,
                    extraction_confidence=confidence,
                )
            )
        else:
            segments.append(
                Segment(
                    heading="",
                    level=1,
                    section_type=SectionType.TEXT,
                    content=block.content.strip(),
                    page=block.page,
                    caption=None,
                    extraction_confidence=confidence,
                )
            )
            i += 1

    return segments


def _classify_heading(
    block: Block,
    body_size: float | None,
    font_h1: float,
    font_h2: float,
    font_h3: float,
    font_h4: float,
) -> tuple[int, bool, ExtractionConfidence]:
    """Return (level 1-4, is_heading, confidence)."""
    if block.type != BlockType.TEXT:
        return 1, False, ExtractionConfidence.HIGH
    text = (block.content or "").strip()
    if not text:
        return 1, False, ExtractionConfidence.HIGH

    size = block.font_size
    is_bold = block.is_bold
    is_short = len(text) < 100 and text.count("\n") == 0
    looks_numbered = bool(re.match(r"^\s*(\d+\.?)+\s+\S", text))

    level = 1
    is_heading = False
    confidence = ExtractionConfidence.HIGH

    if size is not None:
        if size >= font_h1:
            level, is_heading = 1, True
        elif size >= font_h2:
            level, is_heading = 2, True
        elif size >= font_h3:
            level, is_heading = 3, True
        elif size >= font_h4 and (is_bold or looks_numbered):
            level, is_heading = 4, True
        elif body_size is not None and size > body_size and (is_bold or looks_numbered):
            is_heading = True
            if size > body_size + 4:
                level = 2
            else:
                level = 3
            confidence = ExtractionConfidence.MEDIUM
    else:
        if (is_bold and is_short) or looks_numbered:
            is_heading = True
            level = 2 if is_bold else 3
            confidence = ExtractionConfidence.LOW

    return level, is_heading, confidence


def _infer_body_font_size(size_counts: dict[float, int]) -> float | None:
    if not size_counts:
        return None
    return max(size_counts.keys(), key=lambda s: size_counts[s])


def _table_confidence(block: Block) -> ExtractionConfidence:
    return (
        ExtractionConfidence.HIGH
        if (block.content and len(block.content.strip()) > 0)
        else ExtractionConfidence.MEDIUM
    )


def _figure_confidence(block: Block) -> ExtractionConfidence:
    return ExtractionConfidence.HIGH if block.caption else ExtractionConfidence.MEDIUM


def _min_confidence(
    a: ExtractionConfidence, b: ExtractionConfidence
) -> ExtractionConfidence:
    order = (
        ExtractionConfidence.LOW,
        ExtractionConfidence.MEDIUM,
        ExtractionConfidence.HIGH,
    )
    return order[min(order.index(a), order.index(b))]
