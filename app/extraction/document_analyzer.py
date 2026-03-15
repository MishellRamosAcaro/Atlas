"""
Document section analyzer: enrich pipeline JSON (sections + document) with LLM.

One LLM call per section (async, with semaphore), then one document metadata call.
Uses app.llm (generate/agenerate), app.prompts (templates), app.extraction.keyword_refiner.
Never modifies section_id or file_id.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from app.extraction.keyword_polisher import polish_keywords
from app.extraction.keyword_refiner import (
    keyword_refiner_document,
    keyword_refiner_section,
)
from app.llm import LLMConfig, create_llm_client
from app.prompts.enrichment_global_variables import (
    BLACKLIST,
)
from app.prompts.enrichment import (
    document_metadata_template,
    section_enrichment_template,
)

TRUNCATE_CONTENT = 4000


def _keywords_to_objects(keywords: list[Any]) -> list[dict[str, Any]]:
    """Convert list of (term, score) or existing dicts to [{"term": str, "score": float}]."""
    result: list[dict[str, Any]] = []
    for item in keywords:
        if isinstance(item, dict) and "term" in item:
            result.append(
                {
                    "term": str(item["term"]),
                    "score": float(item.get("score", 0.0)),
                }
            )
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            result.append({"term": str(item[0]), "score": float(item[1])})
        elif isinstance(item, (list, tuple)) and len(item) >= 1:
            result.append({"term": str(item[0]), "score": 0.0})
    return result


def _parse_json_from_response(content: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response (raw or inside ```json ... ```)."""
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


class DocumentSectionAnalyzer:
    """
    Enrich pipeline JSON: sections get heading/content/section_summary/keywords;
    document gets metadata and keywords_hierarchy. IDs (section_id, file_id) unchanged.
    """

    def __init__(
        self,
        preset: str,
        config: LLMConfig | None = None,
        max_concurrent: int = 4,
        *,
        anthropic_api_key: str | None = None,
        google_api_key: str | None = None,
        deepseek_api_key: str | None = None,
        openai_api_key: str | None = None,
    ) -> None:
        self._config = config or LLMConfig.from_env()
        self._preset = preset
        self._max_concurrent = max_concurrent
        self._blacklist = set(BLACKLIST)
        self._section_template = section_enrichment_template()
        self._document_template = document_metadata_template()
        self._client = create_llm_client(
            preset,
            self._config,
            anthropic_api_key=anthropic_api_key,
            google_api_key=google_api_key,
            deepseek_api_key=deepseek_api_key,
            openai_api_key=openai_api_key,
        )

    async def _process_one_section(
        self,
        section: dict[str, Any],
        enriched_by_id: dict[str, dict[str, Any]],
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Process one section with LLM and refiner; update enriched_by_id in place."""
        section_id = section.get("section_id")
        if not section_id or section_id not in enriched_by_id:
            return
        try:
            section_type = section.get("section_type", "text")
            content_raw = (section.get("content") or "")[:TRUNCATE_CONTENT]
            prompt = self._section_template.format(
                section_type=section_type,
                content=content_raw,
            )
            async with semaphore:
                response = await self._client.agenerate(prompt)
            parsed = _parse_json_from_response(response)
            if not parsed or not isinstance(parsed, dict):
                return
            out = enriched_by_id[section_id]
            if "heading" in parsed and parsed["heading"] is not None:
                out["heading"] = str(parsed["heading"]).strip()
            if "content" in parsed and parsed["content"] is not None:
                out["content"] = str(parsed["content"]).strip()
            if "section_summary" in parsed and parsed["section_summary"] is not None:
                out["section_summary"] = str(parsed["section_summary"]).strip()
            raw_kw = parsed.get("keywords")
            if isinstance(raw_kw, list):
                raw_kw = [str(k).strip() for k in raw_kw if k]
            else:
                raw_kw = []
            content = out.get("content") or ""
            heading = out.get("heading") or ""
            out["keywords"] = _keywords_to_objects(
                keyword_refiner_section(
                    content,
                    heading,
                    raw_kw,
                    blacklist=self._blacklist,
                    top_k=15,
                )
            )
        except Exception:
            raise

    async def _process_all_sections(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Process all sections concurrently; return list in original order."""
        enriched_by_id: dict[str, dict[str, Any]] = {
            s["section_id"]: dict(s) for s in sections
        }
        semaphore = asyncio.Semaphore(self._max_concurrent)
        try:
            await asyncio.gather(
                *[
                    self._process_one_section(s, enriched_by_id, semaphore)
                    for s in sections
                ]
            )
        except Exception:
            raise
        return [enriched_by_id[s["section_id"]] for s in sections]

    def _process_document_metadata(
        self,
        document: dict[str, Any],
        enriched_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Fill document-level metadata via LLM and keyword_refiner_document."""
        try:
            section_keywords = [s.get("keywords") or [] for s in enriched_sections]
            source = document.get("source") or {}
            section_headings = [s.get("heading") or "" for s in enriched_sections[:10]]
            document_context = {
                "source": source,
                "title": source.get("file_name", ""),
                "intended_use": "",
                "first_headings": section_headings,
            }
            for s in enriched_sections:
                h = (s.get("heading") or "").lower()
                if (
                    "intended use" in h
                    or "intended use" in (s.get("content") or "")[:500].lower()
                ):
                    document_context["intended_use"] = (s.get("content") or "")[:2000]
                    break

            def _kw_strings(kw_list: list) -> str:
                if not kw_list:
                    return ""
                terms = []
                for t in kw_list:
                    if isinstance(t, dict) and "term" in t:
                        terms.append(str(t["term"]))
                    elif isinstance(t, (list, tuple)) and len(t) >= 1:
                        terms.append(str(t[0]))
                    else:
                        terms.append(str(t))
                return ", ".join(terms)

            section_keywords_text = (
                "\n".join(f"- {_kw_strings(kw)}" for kw in section_keywords if kw)
                or "(none)"
            )
            doc_ctx_str = json.dumps(
                {
                    "source": source,
                    "section_headings": section_headings,
                    "section_keywords": section_keywords_text,
                },
                indent=2,
                ensure_ascii=False,
            )
            prompt = self._document_template.format(document_context=doc_ctx_str)
            response = self._client.generate(prompt)
            parsed = _parse_json_from_response(response)
            if not parsed or not isinstance(parsed, dict):
                return document

            out = dict(document)
            for key in (
                "document_type",
                "risk_level",
                "audience",
                "state",
                "technical_context",
                "effective_date",
                "owner_team",
                "supersedes_file_id",
            ):
                if key in parsed and parsed[key] is not None:
                    out[key] = parsed[key]
            if "technical_context" in parsed and isinstance(
                parsed["technical_context"], dict
            ):
                out["technical_context"] = parsed["technical_context"]

            raw_keywords = parsed.get("keywords")
            raw_hierarchy = parsed.get("keywords_hierarchy")
            doc_raw = (
                raw_hierarchy
                if isinstance(raw_hierarchy, dict)
                else (raw_keywords if isinstance(raw_keywords, list) else [])
            )
            refined = keyword_refiner_document(
                section_keywords_per_section=section_keywords,
                document_raw_keywords_or_hierarchy=doc_raw,
                document_context=document_context,
                blacklist=self._blacklist,
                top_per_category=15,
            )
            out["keywords_hierarchy"] = refined.get("keywords_hierarchy", {})
            out["keywords"] = _keywords_to_objects(refined.get("keywords", []))
            if not out["keywords"] and isinstance(raw_keywords, list) and raw_keywords:
                out["keywords"] = [
                    {"term": str(k).strip(), "score": 0.0} for k in raw_keywords if k
                ]
            return out
        except Exception:
            raise

    def process_document(self, input_json: dict[str, Any]) -> dict[str, Any]:
        """
        Enrich document and sections: async sections -> refiner_section -> document LLM -> refiner_document.
        Does not modify section_id or file_id. Returns dict with "document" and "sections".
        """
        document = input_json.get("document") or {}
        sections = input_json.get("sections") or []
        if not sections:
            return input_json

        try:
            enriched_sections = asyncio.run(self._process_all_sections(sections))
        except Exception as e:
            raise ValueError(
                f"Document analysis failed at section enrichment: {e}"
            ) from e

        try:
            enriched_document = self._process_document_metadata(
                document, enriched_sections
            )
        except Exception as e:
            raise ValueError(
                f"Document analysis failed at document metadata: {e}"
            ) from e

        result = {
            "document": enriched_document,
            "sections": enriched_sections,
        }
        return polish_keywords(result, blacklist=self._blacklist)
