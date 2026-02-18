"""
Block cleaning layer: drop junk blocks before structural segmentation.
"""

from __future__ import annotations

import re
from collections import defaultdict

from app.extraction.schemas import Block, BlockType

PAGE_NUMBER_RE = re.compile(r"^\s*\d+\s*$")
PAGE_RANGE_RE = re.compile(r"^\s*\d+\s*[|/]\s*\d+\s*$")
COPYRIGHT_RE = re.compile(
    r"©|copyright|all rights reserved|not for use in diagnostic",
    re.IGNORECASE,
)


def clean_blocks(blocks: list[Block]) -> list[Block]:
    """
    Drop blocks that fail any keep condition. Preserve order.
    """
    if not blocks:
        return []

    def get_text(block: Block) -> str:
        if block.type == BlockType.FIGURE:
            return ((block.content or "") + " " + (block.caption or "")).strip()
        return (block.content or "").strip()

    def normalize_for_dedup(text: str) -> str:
        return " ".join(text.lower().split()) if text else ""

    page_count: dict[tuple[str, str], set[int]] = defaultdict(set)
    for block in blocks:
        text = get_text(block)
        norm = normalize_for_dedup(text)
        key = (norm, block.type.value)
        page_count[key].add(block.page)
    repeated_keys = {k for k, pages in page_count.items() if len(pages) >= 3}

    result: list[Block] = []
    for block in blocks:
        text = get_text(block)
        norm = normalize_for_dedup(text)

        if len(text) < 20:
            continue
        alnum_or_space = sum(1 for c in text if c.isalnum() or c.isspace())
        if alnum_or_space / len(text) < 0.6:
            continue
        if block.type == BlockType.TEXT and block.bbox:
            x0, top, x1, bottom = block.bbox
            w = x1 - x0
            h = bottom - top
            if w > 0 and h / w > 2:
                continue
        if (norm, block.type.value) in repeated_keys:
            continue
        if PAGE_NUMBER_RE.match(text) or PAGE_RANGE_RE.match(text):
            continue
        if "for research use only" in text.lower():
            continue
        if COPYRIGHT_RE.search(text):
            continue
        if len(text) > 0:
            unique_ratio = len(set(text)) / len(text)
            if unique_ratio < 0.2:
                continue
            sep_ratio = (text.count("|") + text.count("-")) / len(text)
            if sep_ratio > 0.3:
                continue

        result.append(block)

    return result
