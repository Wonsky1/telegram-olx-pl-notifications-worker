"""Utility that wraps calling the LLM to summarise item descriptions."""

from __future__ import annotations

import logging

from core.config import settings
from prompts import get_description_summary_prompt

logger = logging.getLogger(__name__)


class DescriptionSummarizer:
    """Asynchronous helper for shortening raw description text via LLM."""

    async def summarize(self, description: str) -> str:
        try:
            response = await settings.GENERATIVE_MODEL.ainvoke(
                input=get_description_summary_prompt(description)
            )
            return response.content
        except Exception as exc:  # pragma: no cover
            logger.error("Failed summarising description: %s", exc, exc_info=True)
            return ""
