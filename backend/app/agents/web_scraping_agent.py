"""
Generic Web Scraping Agent using Playwright

Flexible, reusable agent for extracting structured data from web pages:
- URL pattern templating (e.g., https://example.com/quote/{TICKER}/profile/)
- LLM-powered extraction using page content
- Configurable per data type via config.yaml
- Comprehensive error handling and timeouts
- Source attribution for transparency
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
import json

import ollama
import structlog

from backend.app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class WebScrapingConfig:
    """Configuration for web scraping a specific data type."""

    data_type: str  # e.g., "company_profile"
    url_pattern: str  # e.g., "https://finance.yahoo.com/quote/{TICKER}/profile/"
    extraction_prompt: str  # LLM prompt for extracting data
    timeout: int = 30  # Timeout in seconds
    fallback_enabled: bool = True  # Whether to use fallback on failure


@dataclass
class WebScrapingResult:
    """Result from web scraping operation."""

    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    source_url: str = ""
    extraction_method: str = "playwright"  # Direct Playwright
    error: Optional[str] = None
    response_time_ms: int = 0


class WebScrapingAgent:
    """Generic web scraping agent using Playwright directly."""

    def __init__(self):
        """Initialize web scraping agent."""
        self.settings = get_settings()

    async def extract_data(
        self,
        config: WebScrapingConfig,
        context_vars: Dict[str, str],
        mcp_tools: Optional[Any] = None,  # Keep for backward compatibility, but unused
    ) -> WebScrapingResult:
        """
        Extract data from web page using Playwright.

        Args:
            config: Web scraping configuration
            context_vars: Variables to substitute in URL pattern (e.g., {"TICKER": "AAPL"})
            mcp_tools: (Deprecated, kept for backward compatibility)

        Returns:
            WebScrapingResult with extracted data or error information
        """
        start_time = time.time()

        try:
            # Build URL from pattern
            url = self._build_url(config.url_pattern, context_vars)
            logger.info(
                "Starting web scraping",
                data_type=config.data_type,
                url=url,
            )

            # Extract data using Playwright
            data = await self._extract_with_playwright(url, config)

            response_time = int((time.time() - start_time) * 1000)

            logger.info(
                "Web scraping completed",
                data_type=config.data_type,
                success=True,
                response_time_ms=response_time,
            )

            return WebScrapingResult(
                success=True,
                data=data,
                source_url=url,
                extraction_method="playwright",
                response_time_ms=response_time,
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(
                "Web scraping failed",
                data_type=config.data_type,
                error=str(e),
                response_time_ms=response_time,
            )

            return WebScrapingResult(
                success=False,
                error=str(e),
                source_url=url if 'url' in locals() else "",
                response_time_ms=response_time,
            )

    def _build_url(self, pattern: str, context_vars: Dict[str, str]) -> str:
        """
        Build URL from pattern by replacing variables.

        Args:
            pattern: URL pattern with {VARIABLE} placeholders
            context_vars: Dictionary of variable replacements

        Returns:
            Final URL with variables substituted

        Example:
            _build_url("https://example.com/{TICKER}/profile/", {"TICKER": "AAPL"})
            -> "https://example.com/AAPL/profile/"
        """
        url = pattern
        for key, value in context_vars.items():
            placeholder = f"{{{key}}}"
            url = url.replace(placeholder, value)
        return url

    async def _extract_with_playwright(
        self,
        url: str,
        config: WebScrapingConfig,
    ) -> Dict[str, Any]:
        """
        Extract data using Playwright and LLM.

        Args:
            url: Target URL
            config: Web scraping configuration

        Returns:
            Extracted data dictionary
        """
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Navigate to page
                logger.debug("Navigating to page", url=url)
                await page.goto(url, timeout=config.timeout * 1000)

                # Wait for page to load
                await page.wait_for_load_state("networkidle", timeout=config.timeout * 1000)

                # Get page content (text)
                logger.debug("Extracting page content")
                page_text = await page.inner_text("body")

                # Use LLM to extract data from page content
                logger.debug("Extracting data with LLM")
                extracted_data = await self._extract_with_llm(
                    page_text,
                    config.extraction_prompt,
                )

                return extracted_data

            finally:
                await browser.close()

    async def _extract_with_llm(
        self,
        page_text: str,
        extraction_prompt: str,
    ) -> Dict[str, Any]:
        """
        Use LLM to extract structured data from page content.

        Args:
            page_text: Text content extracted from the page
            extraction_prompt: Prompt describing what to extract

        Returns:
            Extracted data dictionary
        """
        # Construct full prompt
        full_prompt = f"""{extraction_prompt}

Here is the webpage content:

{page_text}

Extract the requested information and return it as a JSON object.
If the information is not found, return an empty object {{}}.
"""

        # Call Ollama LLM
        try:
            response = ollama.chat(
                model=self.settings.ollama_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise data extraction assistant. Extract only the information requested from web page snapshots. Return valid JSON only. Never make up information.",
                    },
                    {
                        "role": "user",
                        "content": full_prompt,
                    }
                ],
                options={
                    "temperature": 0.1,  # Low temperature for precision
                    "num_predict": 500,  # Reasonable max tokens
                }
            )

            # Parse LLM response
            response_text = response['message']['content']

            # Try to extract JSON from response
            data = self._parse_json_response(response_text)

            logger.debug("LLM extraction successful", data_keys=list(data.keys()))
            return data

        except Exception as e:
            logger.error("LLM extraction failed", error=str(e))
            return {}

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling various formats.

        Args:
            response_text: LLM response text

        Returns:
            Parsed JSON dictionary
        """
        # Try direct parsing first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        if "```json" in response_text:
            try:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try to extract JSON from code blocks without language
        if "```" in response_text:
            try:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # If all else fails, return empty dict
        logger.warning("Could not parse JSON from LLM response", response=response_text[:100])
        return {}


# Convenience function for creating config from settings
def load_web_scraping_config(data_type: str) -> Optional[WebScrapingConfig]:
    """
    Load web scraping configuration for a specific data type.

    Args:
        data_type: Type of data to scrape (e.g., "company_profile")

    Returns:
        WebScrapingConfig if found in settings, None otherwise
    """
    settings = get_settings()

    # This will be populated from config.yaml in the next step
    # For now, return None to allow graceful fallback
    if not hasattr(settings, 'web_scraping_configs'):
        return None

    return settings.web_scraping_configs.get(data_type)
