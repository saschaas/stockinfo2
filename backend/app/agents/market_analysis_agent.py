"""
Market Analysis Agent

Analyzes scraped market data to produce sentiment scores, sector analysis,
and market themes. Uses Ollama LLM with configurable model selection.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import json

import ollama
import structlog

from backend.app.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class MarketAnalysisResult:
    """Result from market analysis."""

    success: bool
    overall_sentiment: float = 0.5  # 0-1 scale
    bullish_score: float = 0.5
    bearish_score: float = 0.5
    trending_sectors: list = field(default_factory=list)
    declining_sectors: list = field(default_factory=list)
    market_themes: list = field(default_factory=list)
    key_events: list = field(default_factory=list)
    analysis_summary: str = ""
    confidence_score: float = 0.0
    error: Optional[str] = None


class MarketAnalysisAgent:
    """Agent for analyzing scraped market data."""

    def __init__(self, llm_model: str | None = None):
        """
        Initialize market analysis agent.

        Args:
            llm_model: Optional Ollama model to use. Defaults to settings.ollama_model
        """
        self.settings = get_settings()
        self.model = llm_model if llm_model else self.settings.ollama_model

    async def analyze_market_data(
        self,
        raw_data: Dict[str, Any],
        source_url: str,
    ) -> MarketAnalysisResult:
        """
        Analyze scraped market data to extract sentiment and insights.

        Args:
            raw_data: Raw data extracted by web scraping agent
            source_url: Source URL for context

        Returns:
            MarketAnalysisResult with structured analysis
        """
        try:
            # Construct analysis prompt
            prompt = self._build_analysis_prompt(raw_data, source_url)

            # Call Ollama for analysis
            analysis = self._call_ollama(prompt)

            # Parse and validate response
            result = self._parse_analysis(analysis)

            logger.info(
                "Market analysis completed",
                model=self.model,
                sentiment=result.overall_sentiment,
                confidence=result.confidence_score,
            )

            return result

        except Exception as e:
            logger.error("Market analysis failed", error=str(e))
            return MarketAnalysisResult(
                success=False,
                error=str(e),
            )

    def _build_analysis_prompt(self, raw_data: Dict[str, Any], source_url: str) -> str:
        """Build prompt for LLM analysis."""

        prompt = f"""You are analyzing market data scraped from {source_url}.

IMPORTANT: Base your analysis ONLY on the data provided below. Do not make assumptions or add information not present in the data.

Scraped Market Data:
{json.dumps(raw_data, indent=2)}

Provide a comprehensive market analysis with the following:

1. Overall market sentiment (0-1 scale, where 0=very bearish, 1=very bullish)
2. Bullish score (0-1 scale)
3. Bearish score (0-1 scale)
4. Trending/hot sectors (list up to 5)
5. Declining/concerning sectors (list up to 5)
6. Key market themes or narratives (list up to 5)
7. Significant events mentioned (list up to 5)
8. Brief analysis summary (2-3 sentences)
9. Confidence score (0-1, how complete/reliable is the source data)

Respond with ONLY valid JSON in this exact format:
{{
  "overall_sentiment": 0.X,
  "bullish_score": 0.X,
  "bearish_score": 0.X,
  "trending_sectors": ["sector1", "sector2"],
  "declining_sectors": ["sector1", "sector2"],
  "market_themes": ["theme1", "theme2"],
  "key_events": ["event1", "event2"],
  "analysis_summary": "Brief summary...",
  "confidence_score": 0.X
}}

Guidelines:
- If data is missing or unclear, reflect this in confidence_score
- Sentiment scores should sum meaningfully (not always 0.5)
- Base sector identification on explicit mentions in the data
- Be objective and data-driven
"""
        return prompt

    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama LLM for analysis."""

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst providing objective market analysis. Analyze only the data provided. Return valid JSON only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "temperature": 0.2,  # Low temperature for consistency
                "num_predict": 800,
            },
        )

        return response

    def _parse_analysis(self, response: Dict[str, Any]) -> MarketAnalysisResult:
        """Parse LLM response into structured result."""

        content = response["message"]["content"]

        # Extract JSON from response
        try:
            # Try direct parsing
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try extracting from markdown code blocks
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)
            else:
                raise ValueError("Could not extract JSON from response")

        # Build result
        return MarketAnalysisResult(
            success=True,
            overall_sentiment=float(data.get("overall_sentiment", 0.5)),
            bullish_score=float(data.get("bullish_score", 0.5)),
            bearish_score=float(data.get("bearish_score", 0.5)),
            trending_sectors=data.get("trending_sectors", []),
            declining_sectors=data.get("declining_sectors", []),
            market_themes=data.get("market_themes", []),
            key_events=data.get("key_events", []),
            analysis_summary=data.get("analysis_summary", ""),
            confidence_score=float(data.get("confidence_score", 0.5)),
        )
