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

import os

from ollama import Client
import structlog

from backend.app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Initialize Ollama client with configured URL
def _get_ollama_client() -> Client:
    """Get Ollama client with proper host configuration."""
    ollama_url = settings.ollama_base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    return Client(host=ollama_url)


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

    async def _handle_consent_dialogs(self, page) -> bool:
        """
        Try to dismiss common cookie/privacy consent dialogs.

        Returns:
            True if a consent dialog was found and clicked
        """
        # Common consent button selectors (in order of preference)
        consent_selectors = [
            # Generic accept buttons
            'button:has-text("Accept all")',
            'button:has-text("Accept All")',
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            'button:has-text("I Agree")',
            'button:has-text("Agree")',
            'button:has-text("OK")',
            'button:has-text("Got it")',
            # Yahoo specific
            'button[name="agree"]',
            'button.accept-all',
            '[data-testid="consent-accept-all"]',
            # Common consent frameworks
            '#onetrust-accept-btn-handler',
            '.cookie-consent-accept',
            '#cookie-accept',
            '#gdpr-consent-accept',
            '.gdpr-accept',
            # Reject tracking but accept necessary (fallback)
            'button:has-text("Reject all")',
            'button:has-text("Reject All")',
        ]

        for selector in consent_selectors:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=1000):
                    await button.click()
                    logger.debug("Clicked consent button", selector=selector)
                    # Wait a bit for dialog to dismiss
                    await page.wait_for_timeout(1500)
                    return True
            except Exception:
                continue

        return False

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
        import asyncio
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Navigate to page - wait for domcontentloaded first (faster)
                logger.debug("Navigating to page", url=url)
                await page.goto(url, timeout=config.timeout * 1000, wait_until="domcontentloaded")

                # Try networkidle with shorter timeout, but don't fail if it times out
                # (Some sites like Perplexity have constant network activity)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)  # 15 second max
                except Exception:
                    logger.debug("networkidle timed out, proceeding with current content")

                # Handle cookie/privacy consent dialogs
                consent_handled = await self._handle_consent_dialogs(page)
                if consent_handled:
                    logger.debug("Consent dialog handled, waiting for content to load")
                    # Wait for page to reload/update after consent
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    await asyncio.sleep(2)

                # Additional wait for dynamic content to render
                await asyncio.sleep(2)  # Give JS time to render

                # Get page content (text)
                logger.debug("Extracting page content")
                page_text = await page.inner_text("body")

                # Extract links from the page for news articles
                logger.debug("Extracting links from page")
                links_data = await self._extract_links(page)

                # Use LLM to extract data from page content (with links)
                logger.debug("Extracting data with LLM")
                extracted_data = await self._extract_with_llm(
                    page_text,
                    config.extraction_prompt,
                    links_data,
                )

                return extracted_data

            finally:
                await browser.close()

    async def _extract_links(self, page) -> list[dict]:
        """
        Extract all links from the page with their text and href.

        Args:
            page: Playwright page object

        Returns:
            List of dictionaries with link text and URL
        """
        try:
            # Get all anchor tags with href attributes
            links = await page.evaluate("""
                () => {
                    const anchors = document.querySelectorAll('a[href]');
                    const results = [];
                    for (const a of anchors) {
                        const href = a.href;
                        const text = a.innerText?.trim() || a.textContent?.trim() || '';
                        // Filter out empty links, javascript links, and very short text
                        if (href &&
                            !href.startsWith('javascript:') &&
                            !href.startsWith('#') &&
                            text.length > 10) {
                            results.push({
                                text: text.substring(0, 200),  // Limit text length
                                url: href
                            });
                        }
                    }
                    return results;
                }
            """)

            logger.debug("Extracted links from page", count=len(links))
            return links
        except Exception as e:
            logger.warning("Failed to extract links", error=str(e))
            return []

    async def _extract_with_llm(
        self,
        page_text: str,
        extraction_prompt: str,
        links_data: list[dict] | None = None,
    ) -> Dict[str, Any]:
        """
        Use LLM to extract structured data from page content.

        Args:
            page_text: Text content extracted from the page
            extraction_prompt: Prompt describing what to extract
            links_data: Optional list of links with text and URLs

        Returns:
            Extracted data dictionary
        """
        # Truncate page text if too long (LLMs have context limits)
        max_chars = 12000  # Reduced to make room for links
        if len(page_text) > max_chars:
            page_text = page_text[:max_chars] + "\n\n[Content truncated due to length]"

        # Format links data for the LLM
        links_section = ""
        if links_data and len(links_data) > 0:
            # Limit to most relevant links (those that look like article links)
            article_links = [
                link for link in links_data
                if len(link.get('text', '')) > 25  # More text = more likely article
                and not any(x in link.get('url', '').lower() for x in [
                    'login', 'signup', 'subscribe', 'privacy', 'terms', 'cookie',
                    'mailto:', 'javascript:', '/user/', '/settings/', '/about/',
                    '/help/', '/contact/', 'facebook.com', 'twitter.com', 'linkedin.com'
                ])
                and any(x in link.get('url', '').lower() for x in [
                    '/news/', '/article/', '/story/', 'finance.yahoo.com/news',
                    'reuters.com', 'bloomberg.com', 'cnbc.com', 'wsj.com',
                    '-news', '.html', '/m/'  # Common article URL patterns
                ])
            ][:30]  # Limit to 30 links to keep prompt manageable

            if article_links:
                links_text = "\n".join([
                    f"- \"{link['text'][:80]}\" -> {link['url']}"
                    for link in article_links
                ])
                links_section = f"""

ARTICLE LINKS (match article titles to these URLs):
{links_text}
"""

        # Count how many categories are being requested
        category_count = extraction_prompt.count("---")

        # Construct full prompt - make it clear we're providing content, not asking to access URLs
        if category_count > 2:
            # Multiple categories - request combined JSON
            full_prompt = f"""You are analyzing text content that has already been extracted from a webpage.
Your task is to extract specific information from this text and return it as a SINGLE combined JSON object.

IMPORTANT: You must return ALL requested data categories in ONE JSON object. Combine the data structures.
IMPORTANT: For news articles, you MUST include the URL for each article. Match article titles to the AVAILABLE LINKS section below to find the correct URL.

EXTRACTION REQUIREMENTS (extract ALL of these):
{extraction_prompt}

TEXT CONTENT TO ANALYZE:
---
{page_text}
---
{links_section}
Return a SINGLE valid JSON object containing ALL the requested categories combined.
For news articles, ALWAYS include a "url" field by matching the article title to the available links above.
For example, if asked for news AND hot_stocks, return: {{"articles": [{{"title": "...", "url": "https://...", ...}}], "hot_stocks": [...], ...}}
If specific information cannot be found, use empty arrays.
Return ONLY the JSON - no explanations or markdown.
"""
        else:
            # Single category - simpler prompt
            full_prompt = f"""You are analyzing text content that has already been extracted from a webpage.
Your task is to extract specific information from this text and return it as JSON.

IMPORTANT: For news articles, you MUST include the URL for each article. Match article titles to the AVAILABLE LINKS section below.

EXTRACTION REQUIREMENTS:
{extraction_prompt}

TEXT CONTENT TO ANALYZE:
---
{page_text}
---
{links_section}
Based on the text content above, extract the requested information and return ONLY a valid JSON object.
For news articles, ALWAYS include a "url" field by matching the article title to the available links.
If specific information cannot be found in the text, use empty arrays or default values.
Do not explain or add commentary - just return the JSON.
"""

        # Call Ollama LLM using configured client
        try:
            client = _get_ollama_client()
            response = client.chat(
                model=self.settings.ollama_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction assistant. You will be given text content that was scraped from a webpage. Your job is to extract structured information from that text and return it as valid JSON. You do NOT need to access any external URLs - all the content you need is provided in the user's message. Always return valid JSON only, with no additional explanation.",
                    },
                    {
                        "role": "user",
                        "content": full_prompt,
                    }
                ],
                options={
                    "temperature": 0.1,  # Low temperature for precision
                    "num_predict": 16000,  # Large limit for complex multi-category extraction with links
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
        Parse JSON from LLM response, handling various formats including truncated responses.

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
                if json_end == -1:
                    json_end = len(response_text)
                json_str = response_text[json_start:json_end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try to extract JSON from code blocks without language
        if "```" in response_text:
            try:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                if json_end == -1:
                    json_end = len(response_text)
                json_str = response_text[json_start:json_end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try to find JSON object in the response
        if "{" in response_text:
            json_start = response_text.find("{")
            # Try to find matching closing brace
            json_str = response_text[json_start:]

            # Try parsing as-is
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

            # Try to repair truncated JSON by closing open brackets
            repaired = self._repair_truncated_json(json_str)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

        # If all else fails, return empty dict
        logger.warning("Could not parse JSON from LLM response", response=response_text[:200])
        return {}

    def _repair_truncated_json(self, json_str: str) -> str:
        """
        Try to repair truncated JSON by closing open brackets and braces.

        Args:
            json_str: Potentially truncated JSON string

        Returns:
            Repaired JSON string or original if repair not possible
        """
        # Count open brackets/braces
        open_braces = json_str.count('{') - json_str.count('}')
        open_brackets = json_str.count('[') - json_str.count(']')

        # If we have unclosed structures, try to close them
        if open_braces > 0 or open_brackets > 0:
            # Find the last complete item (ends with } or ] or ", or number)
            # and truncate there
            repaired = json_str.rstrip()

            # Remove trailing incomplete content
            while repaired and repaired[-1] not in '"}]0123456789':
                repaired = repaired[:-1].rstrip()

            # Close open brackets
            for _ in range(open_brackets):
                repaired += ']'
            for _ in range(open_braces):
                repaired += '}'

            return repaired

        return json_str


# Convenience function for creating config from settings
def load_web_scraping_config(website_key: str) -> Optional[WebScrapingConfig]:
    """
    Load web scraping configuration for a specific website key.

    Args:
        website_key: Key of the website to scrape (e.g., "market_overview_perplexity" or custom key)

    Returns:
        WebScrapingConfig if found, None otherwise
    """
    from backend.app.schemas.config import DATA_TEMPLATES, DATA_USE_DISPLAY_NAMES

    settings = get_settings()

    # First, check if it's a custom website in the database using sync query
    website_data = None
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session
        from backend.app.db.models import ScrapedWebsite

        # Create sync engine from async URL
        database_url = settings.database_url
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

        sync_engine = create_engine(database_url, pool_pre_ping=True)
        with Session(sync_engine) as session:
            stmt = select(ScrapedWebsite).where(ScrapedWebsite.key == website_key)
            db_website = session.execute(stmt).scalar_one_or_none()
            if db_website:
                # Copy attributes before session closes
                website_data = {
                    "url": db_website.url,
                    "data_use": db_website.data_use,
                    "description": db_website.description,
                }
        sync_engine.dispose()
    except Exception as e:
        logger.warning("Failed to check database for custom website", error=str(e), website_key=website_key)
        website_data = None

    # Create a simple object from the data
    website = type('Website', (), website_data)() if website_data else None

    if website:
        # Build extraction prompt from data_use categories
        data_use_list = [du.strip() for du in website.data_use.split(",") if du.strip()]
        extraction_prompts = []
        for du in data_use_list:
            template = DATA_TEMPLATES.get(du, {})
            prompt = template.get("extraction_prompt", "")
            if prompt:
                extraction_prompts.append(f"--- {DATA_USE_DISPLAY_NAMES.get(du, du)} ---\n{prompt}")

        extraction_prompt = "\n\n".join(extraction_prompts)

        # Add website's description to the prompt if provided
        if website.description:
            extraction_prompt = f"""{extraction_prompt}

Additional context from user:
{website.description}"""

        return WebScrapingConfig(
            data_type=website.data_use,
            url_pattern=website.url,
            extraction_prompt=extraction_prompt,
            timeout=120,  # Default timeout for custom websites
        )

    # Fallback to config.yaml settings
    if hasattr(settings, 'web_scraping_configs'):
        return settings.web_scraping_configs.get(website_key)

    return None
