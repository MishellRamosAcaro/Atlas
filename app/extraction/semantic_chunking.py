"""
Stage 3: Semantic chunking.
One chunk = one section; never split tables; max ~300–600 words per section.
"""

from __future__ import annotations

import hashlib
import re
import uuid

from app.extraction.schemas import (
    DocumentSchema,
    SectionSchema,
    SectionType,
    Segment,
    Source,
)

MAX_WORDS_PER_SECTION = 600
SOFT_MAX_WORDS = 300
MIN_WORDS_SEMANTIC = 40
MIN_UNIQUE_WORD_RATIO = 0.3


def is_semantic(text: str) -> bool:
    """Return True only if word_count >= 40, unique_word_ratio > 0.3, and not looks_like_axis."""
    t = (text or "").strip()
    if not t:
        return False
    words = t.split()
    word_count = len(words)
    if word_count < MIN_WORDS_SEMANTIC:
        return False
    unique_ratio = len(set(w.lower() for w in words)) / max(word_count, 1)
    if unique_ratio <= MIN_UNIQUE_WORD_RATIO:
        return False
    if looks_like_axis(t):
        return False
    return True


def looks_like_axis(text: str) -> bool:
    """True if majority of lines have >50% of characters being | or -."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    separator_heavy = sum(
        1 for ln in lines if sum(1 for c in ln if c in "|-") / max(len(ln), 1) > 0.5
    )
    return separator_heavy / len(lines) > 0.5


def _content_hash(heading: str, content: str) -> str:
    normalized = " ".join((heading + " " + content).lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def chunk_to_sections(
    segments: list[Segment],
    file_id: uuid.UUID,
    source: Source,
    *,
    max_words: int = MAX_WORDS_PER_SECTION,
    soft_max_words: int = SOFT_MAX_WORDS,
) -> tuple[DocumentSchema, list[SectionSchema]]:
    """
    Convert segments into one document and N sections.
    """
    sections: list[SectionSchema] = []
    sec_index = [0]

    for seg in segments:
        if seg.section_type in (SectionType.TABLE, SectionType.FIGURE):
            if not is_semantic(seg.content or ""):
                continue
            sec_index[0] += 1
            sections.append(
                SectionSchema(
                    section_id=str(uuid.uuid4()),
                    file_id=file_id,
                    heading=seg.heading or "",
                    section_type=seg.section_type,
                    content=seg.content,
                    keywords=[],
                    extraction_confidence=seg.extraction_confidence,
                )
            )
            continue
        sub_sections = _split_text_segment(
            seg, file_id, max_words, soft_max_words, sec_index
        )
        sections.extend(sub_sections)

    seen_hashes: set[str] = set()
    result: list[SectionSchema] = []
    idx = 0
    for s in sections:
        h = _content_hash(s.heading, s.content)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        idx += 1
        result.append(s)

    section_ids = [s.section_id for s in result]
    doc = DocumentSchema(
        file_id=file_id,
        source=source,
        sections=section_ids,
    )
    return doc, result


def _split_text_segment(
    seg: Segment,
    file_id: uuid.UUID,
    max_words: int,
    soft_max_words: int,
    sec_index: list[int],
) -> list[SectionSchema]:
    """Split a text segment into one or more sections."""
    content = (seg.content or "").strip()
    heading = (seg.heading or "").strip()
    if not content and not heading:
        return []

    full_text = f"{heading}\n\n{content}".strip() if heading else content
    word_count = len(full_text.split())
    if word_count <= max_words:
        if not is_semantic(full_text):
            return []
        sec_index[0] += 1
        return [
            SectionSchema(
                section_id=str(uuid.uuid4()),
                file_id=file_id,
                heading=heading,
                section_type=SectionType.TEXT,
                content=content or full_text,
                keywords=[],
                extraction_confidence=seg.extraction_confidence,
            )
        ]

    chunks = _semantic_split(full_text, max_words, soft_max_words)
    result = []
    for i, chunk_text in enumerate(chunks):
        if not is_semantic(chunk_text):
            continue
        sec_index[0] += 1
        chunk_heading = heading if i == 0 and heading else ""
        chunk_content = chunk_text
        if chunk_heading and chunk_content.startswith(chunk_heading):
            chunk_content = chunk_content[len(chunk_heading) :].lstrip()
        result.append(
            SectionSchema(
                section_id=str(uuid.uuid4()),
                file_id=file_id,
                heading=chunk_heading,
                section_type=SectionType.TEXT,
                content=chunk_content or chunk_text,
                keywords=[],
                extraction_confidence=seg.extraction_confidence,
            )
        )
    return result


def _semantic_split(text: str, max_words: int, soft_max_words: int) -> list[str]:
    """Split text at paragraph then sentence boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        w = len(para.split())
        if current_words + w <= max_words:
            current.append(para)
            current_words += w
            continue
        if current_words >= soft_max_words or not current:
            if current:
                chunks.append("\n\n".join(current))
            if w <= max_words:
                current = [para]
                current_words = w
            else:
                sub_chunks = _split_paragraph_by_sentences(
                    para, max_words, soft_max_words
                )
                chunks.extend(sub_chunks)
                current = []
                current_words = 0
            continue
        if current:
            chunks.append("\n\n".join(current))
        if w <= max_words:
            current = [para]
            current_words = w
        else:
            sub_chunks = _split_paragraph_by_sentences(para, max_words, soft_max_words)
            chunks.extend(sub_chunks)
            current = []
            current_words = 0

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _split_paragraph_by_sentences(
    paragraph: str, max_words: int, soft_max_words: int
) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks = []
    current = []
    current_words = 0
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        w = len(sent.split())
        if current_words + w <= max_words:
            current.append(sent)
            current_words += w
        else:
            if current:
                chunks.append(" ".join(current))
            if w <= max_words:
                current = [sent]
                current_words = w
            else:
                chunks.append(sent)
                current = []
                current_words = 0
    if current:
        chunks.append(" ".join(current))
    return chunks
