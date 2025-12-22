"""
ETF Data Extraction Agent

Agent for extracting ETF holdings data from provider websites:
- BeautifulSoup for initial parsing (fast)
- Playwright fallback for JavaScript-heavy sites
- LLM-powered link detection for CSV/PDF downloads
- CSV parsing with pandas
- PDF extraction with pdfplumber + LLM
- Standardized holdings output format
"""

import asyncio
import io
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
import pandas as pd
import structlog
from bs4 import BeautifulSoup
from ollama import Client

from backend.app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


def _get_ollama_client() -> Client:
    """Get Ollama client with proper host configuration."""
    ollama_url = settings.ollama_base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    return Client(host=ollama_url)


@dataclass
class ETFExtractionConfig:
    """Configuration for ETF data extraction."""

    etf_id: int
    ticker: str
    name: str
    url: str
    agent_command: str  # LLM prompt for link finding/extraction
    timeout: int = 120


@dataclass
class ETFExtractionResult:
    """Result from ETF data extraction."""

    success: bool
    holdings: List[Dict[str, Any]] = field(default_factory=list)
    description: Optional[str] = None
    holding_date: Optional[date] = None
    source_url: str = ""
    extraction_method: str = "csv"  # csv, pdf, html
    error: Optional[str] = None
    response_time_ms: int = 0


class ETFDataAgent:
    """Agent for extracting ETF holdings data from provider websites."""

    def __init__(self, llm_model: Optional[str] = None):
        """
        Initialize the ETF data agent.

        Args:
            llm_model: Override LLM model to use (defaults to settings.ollama_model)
        """
        self.settings = get_settings()
        self.llm_model = llm_model or self.settings.ollama_model
        self.http_client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

    # Domains that require JavaScript rendering
    JS_HEAVY_DOMAINS = [
        "ark-funds.com",
        "www.ark-funds.com",
        "ishares.com",
        "www.ishares.com",
        "vanguard.com",
        "www.vanguard.com",
        "ssga.com",  # State Street / SPDR
        "www.ssga.com",
    ]

    async def extract_holdings(self, config: ETFExtractionConfig) -> ETFExtractionResult:
        """
        Extract holdings data from ETF provider website.

        Flow:
        1. Check if domain requires JavaScript (use Playwright directly)
        2. Otherwise try BeautifulSoup first (fast)
        3. Fall back to Playwright if BeautifulSoup fails
        4. Find CSV/PDF download links using LLM
        5. Download and parse CSV (preferred) or PDF (fallback)
        6. Extract from rendered HTML table if no downloads work
        7. Return standardized holdings format

        Args:
            config: ETF extraction configuration

        Returns:
            ETFExtractionResult with holdings data or error
        """
        start_time = time.time()

        try:
            logger.info(
                "Starting ETF holdings extraction",
                etf_id=config.etf_id,
                ticker=config.ticker,
                url=config.url,
            )

            # Check if domain requires JavaScript
            parsed_url = urlparse(config.url)
            domain = parsed_url.netloc.lower()
            needs_js = any(js_domain in domain for js_domain in self.JS_HEAVY_DOMAINS)

            table_data = []  # Initialize table_data

            if needs_js:
                logger.info("Domain requires JavaScript, using Playwright directly", domain=domain)
                page_content, links, table_data = await self._fetch_with_playwright_enhanced(config.url, config.timeout)
            else:
                # Step 1: Try BeautifulSoup first
                page_content, links = await self._fetch_with_beautifulsoup(config.url)

                # If BeautifulSoup returned very little content or no holdings keywords, try Playwright
                has_holdings_data = any(kw in page_content.lower() for kw in ['weight', 'shares', 'market value', 'holdings'])
                if len(page_content) < 500 or len(links) < 3 or not has_holdings_data:
                    logger.info("BeautifulSoup returned insufficient content, trying Playwright")
                    page_content, links, table_data = await self._fetch_with_playwright_enhanced(config.url, config.timeout)

            # Step 2a: Check if Playwright found a direct CSV link (first link with "CSV" text)
            direct_csv_link = None
            for link in links[:5]:  # Check first 5 links
                if "csv" in link.get("text", "").lower() or link.get("url", "").endswith(".csv"):
                    direct_csv_link = link.get("url")
                    logger.info("Found direct CSV link from Playwright", url=direct_csv_link)
                    break

            # Step 2b: Use LLM to find download links
            csv_link, pdf_link, description = await self._find_download_links(
                page_content, links, config.url, config.agent_command
            )

            # Prefer direct CSV link over LLM-detected
            if direct_csv_link:
                csv_link = direct_csv_link

            holdings = []
            holding_date = None
            extraction_method = "csv"

            # Step 3: Try CSV first (with Playwright download fallback), then PDF
            if csv_link:
                logger.info("Trying CSV download", link=csv_link)
                try:
                    holdings, holding_date = await self._download_and_parse_csv(csv_link)
                    extraction_method = "csv"
                except Exception as e:
                    logger.warning("Direct CSV download failed, trying Playwright download", error=str(e))
                    # Try downloading via Playwright (bypasses Cloudflare)
                    try:
                        holdings, holding_date = await self._download_csv_via_playwright(csv_link, config.timeout)
                        extraction_method = "csv"
                    except Exception as e2:
                        logger.warning("Playwright CSV download also failed", error=str(e2))
                        csv_link = None  # Fall through to PDF

            if not holdings and pdf_link:
                logger.info("Trying PDF link", link=pdf_link)
                try:
                    holdings, holding_date = await self._extract_from_pdf(
                        pdf_link, config.agent_command
                    )
                    extraction_method = "pdf"
                except Exception as e:
                    logger.warning("PDF parsing failed", error=str(e))

            # Step 4: Try table data from Playwright if available
            if not holdings and table_data:
                logger.info("Using extracted table data from Playwright", tables_count=len(table_data))
                holdings, holding_date = await self._parse_table_data(table_data, config.agent_command)
                extraction_method = "table"

            # Step 5: If no table data, try HTML extraction with LLM
            if not holdings:
                logger.info("No structured data found, trying HTML extraction with LLM")
                holdings, holding_date = await self._extract_from_html(
                    page_content, config.agent_command
                )
                extraction_method = "html"

            response_time = int((time.time() - start_time) * 1000)

            # Default holding_date to today if not extracted
            if holdings and holding_date is None:
                holding_date = date.today()
                logger.debug("Using today's date as holding_date", holding_date=holding_date)

            if holdings:
                logger.info(
                    "ETF holdings extraction completed",
                    etf_id=config.etf_id,
                    ticker=config.ticker,
                    holdings_count=len(holdings),
                    extraction_method=extraction_method,
                    response_time_ms=response_time,
                )

                return ETFExtractionResult(
                    success=True,
                    holdings=holdings,
                    description=description,
                    holding_date=holding_date,
                    source_url=csv_link or pdf_link or config.url,
                    extraction_method=extraction_method,
                    response_time_ms=response_time,
                )
            else:
                return ETFExtractionResult(
                    success=False,
                    error="Could not extract holdings from any source",
                    source_url=config.url,
                    response_time_ms=response_time,
                )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(
                "ETF holdings extraction failed",
                etf_id=config.etf_id,
                ticker=config.ticker,
                error=str(e),
            )
            return ETFExtractionResult(
                success=False,
                error=str(e),
                source_url=config.url,
                response_time_ms=response_time,
            )

    async def _fetch_with_beautifulsoup(self, url: str) -> tuple[str, List[Dict[str, str]]]:
        """
        Fetch page content using BeautifulSoup (fast method).

        Args:
            url: URL to fetch

        Returns:
            Tuple of (page_text, links)
        """
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Get text content
            page_text = soup.get_text(separator="\n", strip=True)

            # Extract all links
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)

                # Convert relative URLs to absolute
                if href and not href.startswith(("http://", "https://", "javascript:", "#")):
                    href = urljoin(url, href)

                if href and text:
                    links.append({"text": text[:200], "url": href})

            logger.debug("BeautifulSoup fetch completed", url=url, text_length=len(page_text), links_count=len(links))
            return page_text, links

        except Exception as e:
            logger.warning("BeautifulSoup fetch failed", url=url, error=str(e))
            return "", []

    async def _fetch_with_playwright(self, url: str, timeout: int) -> tuple[str, List[Dict[str, str]]]:
        """
        Fetch page content using Playwright (for JavaScript-heavy pages).

        Args:
            url: URL to fetch
            timeout: Timeout in seconds

        Returns:
            Tuple of (page_text, links)
        """
        page_text, links, _ = await self._fetch_with_playwright_enhanced(url, timeout)
        return page_text, links

    async def _fetch_with_playwright_enhanced(self, url: str, timeout: int) -> tuple[str, List[Dict[str, str]], List[List[List[str]]]]:
        """
        Fetch page content using Playwright with enhanced table extraction.

        Args:
            url: URL to fetch
            timeout: Timeout in seconds

        Returns:
            Tuple of (page_text, links, table_data)
            table_data is a list of tables, each table is a list of rows, each row is a list of cell values
        """
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                # Navigate to page
                await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

                # Wait for network to settle
                try:
                    await page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    logger.debug("networkidle timed out, proceeding")

                # Handle consent dialogs
                await self._handle_consent_dialogs(page)

                # Wait for potential dynamic content to load
                await asyncio.sleep(3)

                # Try to click "View All" or "Load More" buttons to get all holdings
                try:
                    view_all_selectors = [
                        'button:has-text("View All")',
                        'a:has-text("View All")',
                        'button:has-text("Load More")',
                        'button:has-text("Show All")',
                        'a:has-text("Show All")',
                        '[class*="view-all"]',
                        '[class*="load-more"]',
                    ]
                    for selector in view_all_selectors:
                        try:
                            btn = page.locator(selector).first
                            if await btn.is_visible(timeout=2000):
                                await btn.click()
                                await asyncio.sleep(3)
                                logger.debug("Clicked view all button", selector=selector)
                                break
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug("No view all button found", error=str(e))

                # Try to scroll to load lazy content (do multiple scrolls)
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)

                # Try to find and click CSV download button/link
                csv_download_url = None
                try:
                    csv_selectors = [
                        'a:has-text("CSV")',
                        'button:has-text("CSV")',
                        'a:has-text("Download CSV")',
                        'a[href*=".csv"]',
                        '[class*="download"]:has-text("CSV")',
                    ]
                    for selector in csv_selectors:
                        try:
                            link = page.locator(selector).first
                            if await link.is_visible(timeout=1000):
                                href = await link.get_attribute("href")
                                if href:
                                    csv_download_url = href if href.startswith("http") else urljoin(url, href)
                                    logger.info("Found CSV download link", url=csv_download_url)
                                break
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug("No CSV download link found", error=str(e))

                # Get text content
                page_text = await page.inner_text("body")

                # Extract links
                links = await page.evaluate("""
                    () => {
                        const anchors = document.querySelectorAll('a[href]');
                        const results = [];
                        for (const a of anchors) {
                            const href = a.href;
                            const text = a.innerText?.trim() || a.textContent?.trim() || '';
                            if (href && !href.startsWith('javascript:') && !href.startsWith('#')) {
                                results.push({text: text.substring(0, 200), url: href});
                            }
                        }
                        return results;
                    }
                """)

                # Extract table data - look for holdings tables
                table_data = await page.evaluate("""
                    () => {
                        const tables = [];

                        // First, try to find the holdings table specifically
                        // ARK Funds uses a specific table structure
                        const holdingsTables = document.querySelectorAll('table');

                        for (const table of holdingsTables) {
                            const rows = [];
                            const tableRows = table.querySelectorAll('tr');

                            // Check if this looks like a holdings table
                            const headerRow = table.querySelector('thead tr, tr:first-child');
                            if (headerRow) {
                                const headerText = headerRow.innerText.toLowerCase();
                                const isHoldingsTable = headerText.includes('ticker') ||
                                                       headerText.includes('company') ||
                                                       headerText.includes('weight') ||
                                                       headerText.includes('shares') ||
                                                       headerText.includes('cusip');

                                if (isHoldingsTable || tableRows.length > 5) {
                                    for (const row of tableRows) {
                                        const cells = [];
                                        const rowCells = row.querySelectorAll('td, th');
                                        for (const cell of rowCells) {
                                            cells.push(cell.innerText?.trim() || '');
                                        }
                                        if (cells.length > 0) {
                                            rows.push(cells);
                                        }
                                    }
                                    if (rows.length > 1) {
                                        tables.push(rows);
                                    }
                                }
                            }
                        }

                        // Also try to find div-based grids (some sites use div grids instead of tables)
                        const gridContainers = document.querySelectorAll('[class*="holdings"], [class*="grid"], [class*="table"]');
                        for (const container of gridContainers) {
                            const gridRows = container.querySelectorAll('[class*="row"], [role="row"], tr');
                            if (gridRows.length > 5) {
                                const rows = [];
                                for (const row of gridRows) {
                                    const cells = [];
                                    // Get direct children that might be cells
                                    const cellElements = row.querySelectorAll('[class*="cell"], [role="cell"], td, th');
                                    if (cellElements.length === 0) {
                                        // Try direct div/span children
                                        for (const child of row.children) {
                                            if (child.tagName === 'DIV' || child.tagName === 'SPAN') {
                                                const text = child.innerText?.trim() || '';
                                                if (text && text.length < 500) {
                                                    cells.push(text);
                                                }
                                            }
                                        }
                                    } else {
                                        for (const cell of cellElements) {
                                            const text = cell.innerText?.trim() || '';
                                            if (text && text.length < 500) {
                                                cells.push(text);
                                            }
                                        }
                                    }
                                    if (cells.length >= 3) {
                                        rows.push(cells);
                                    }
                                }
                                if (rows.length > 5 && !tables.some(t => JSON.stringify(t) === JSON.stringify(rows))) {
                                    tables.push(rows);
                                }
                            }
                        }

                        return tables;
                    }
                """)

                # Add CSV download URL to links if found via button detection
                if csv_download_url:
                    links.insert(0, {"text": "CSV Download", "url": csv_download_url})

                logger.debug(
                    "Playwright enhanced fetch completed",
                    url=url,
                    text_length=len(page_text),
                    links_count=len(links),
                    tables_count=len(table_data),
                    csv_found=csv_download_url is not None
                )
                return page_text, links, table_data

            finally:
                await browser.close()

    async def _handle_consent_dialogs(self, page) -> bool:
        """Try to dismiss common cookie/privacy consent dialogs."""
        consent_selectors = [
            'button:has-text("Accept all")',
            'button:has-text("Accept All")',
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            'button:has-text("Agree")',
            'button:has-text("OK")',
            '#onetrust-accept-btn-handler',
            '.cookie-consent-accept',
        ]

        for selector in consent_selectors:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=1000):
                    await button.click()
                    await page.wait_for_timeout(1500)
                    return True
            except Exception:
                continue

        return False

    async def _find_download_links(
        self,
        page_content: str,
        links: List[Dict[str, str]],
        base_url: str,
        agent_command: str,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Use LLM to find CSV/PDF download links.

        Args:
            page_content: Text content from page
            links: List of links found on page
            base_url: Base URL for context
            agent_command: User-provided extraction instructions

        Returns:
            Tuple of (csv_link, pdf_link, description)
        """
        # Format links for LLM
        links_text = "\n".join([
            f"- \"{link['text'][:60]}\" -> {link['url']}"
            for link in links
            if any(kw in link['text'].lower() or kw in link['url'].lower()
                   for kw in ['csv', 'pdf', 'download', 'holdings', 'excel', 'xls'])
        ][:50])  # Limit to 50 most relevant links

        # If no filtered links, include all
        if not links_text:
            links_text = "\n".join([
                f"- \"{link['text'][:60]}\" -> {link['url']}"
                for link in links
            ][:30])

        prompt = f"""You are analyzing an ETF website to find download links for holdings data.

USER INSTRUCTIONS:
{agent_command}

PAGE URL: {base_url}

AVAILABLE LINKS ON PAGE:
{links_text}

PAGE CONTENT (excerpt):
{page_content[:3000]}

TASK:
1. Find the best link to download the ETF holdings data as CSV (preferred) or PDF
2. Extract a brief description of the ETF if visible on the page

Return a JSON object with:
{{
    "csv_link": "full URL to CSV download or null if not found",
    "pdf_link": "full URL to PDF download or null if not found",
    "description": "brief ETF description if found, or null"
}}

Only return the JSON, no explanations."""

        try:
            client = _get_ollama_client()
            response = client.chat(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction assistant that finds download links on financial websites. Return only valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.1, "num_predict": 500}
            )

            result = self._parse_json_response(response['message']['content'])
            csv_link = result.get("csv_link")
            pdf_link = result.get("pdf_link")
            description = result.get("description")

            # Validate URLs
            if csv_link and not csv_link.startswith("http"):
                csv_link = urljoin(base_url, csv_link)
            if pdf_link and not pdf_link.startswith("http"):
                pdf_link = urljoin(base_url, pdf_link)

            return csv_link, pdf_link, description

        except Exception as e:
            logger.error("LLM link detection failed", error=str(e))
            return None, None, None

    async def _download_csv_via_playwright(self, csv_url: str, timeout: int) -> tuple[List[Dict[str, Any]], Optional[date]]:
        """
        Download CSV using Playwright (bypasses Cloudflare protection).

        Args:
            csv_url: URL to CSV file
            timeout: Timeout in seconds

        Returns:
            Tuple of (holdings_list, holding_date)
        """
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                # Navigate to the CSV URL and capture the response
                response = await page.goto(csv_url, timeout=timeout * 1000, wait_until="commit")

                if response and response.ok:
                    csv_content = await response.text()

                    # Parse CSV with pandas
                    df = pd.read_csv(io.StringIO(csv_content))

                    # Normalize column names
                    df.columns = df.columns.str.lower().str.strip()

                    # Detect column mappings
                    column_mapping = self._detect_csv_columns(df.columns.tolist())

                    if not column_mapping.get("ticker") and not column_mapping.get("company"):
                        raise ValueError("Could not identify required columns in CSV")

                    # Extract holdings (same logic as _download_and_parse_csv)
                    holdings = []
                    holding_date = None

                    for _, row in df.iterrows():
                        holding = {}

                        if column_mapping.get("ticker"):
                            ticker_val = row[column_mapping["ticker"]]
                            if pd.notna(ticker_val) and str(ticker_val).strip():
                                holding["ticker"] = str(ticker_val).strip().upper()

                        if column_mapping.get("company"):
                            company_val = row[column_mapping["company"]]
                            if pd.notna(company_val):
                                holding["company_name"] = str(company_val).strip()

                        if column_mapping.get("cusip"):
                            cusip_val = row[column_mapping["cusip"]]
                            if pd.notna(cusip_val):
                                holding["cusip"] = str(cusip_val).strip()

                        if column_mapping.get("shares"):
                            shares_val = row[column_mapping["shares"]]
                            if pd.notna(shares_val):
                                holding["shares"] = self._parse_numeric(shares_val)

                        if column_mapping.get("market_value"):
                            value_val = row[column_mapping["market_value"]]
                            if pd.notna(value_val):
                                holding["market_value"] = self._parse_numeric(value_val)

                        if column_mapping.get("weight"):
                            weight_val = row[column_mapping["weight"]]
                            if pd.notna(weight_val):
                                weight = self._parse_numeric(weight_val)
                                if weight and weight < 1:
                                    weight = weight * 100
                                holding["weight_pct"] = weight

                        if column_mapping.get("date") and holding_date is None:
                            date_val = row[column_mapping["date"]]
                            if pd.notna(date_val):
                                holding_date = self._parse_date(date_val)

                        if holding.get("ticker") or holding.get("company_name"):
                            holdings.append(holding)

                    logger.info("Playwright CSV download successful", holdings_count=len(holdings), holding_date=holding_date)
                    return holdings, holding_date
                else:
                    raise ValueError(f"Failed to download CSV: HTTP {response.status if response else 'no response'}")

            finally:
                await browser.close()

    async def _download_and_parse_csv(self, csv_url: str) -> tuple[List[Dict[str, Any]], Optional[date]]:
        """
        Download and parse CSV holdings data.

        Args:
            csv_url: URL to CSV file

        Returns:
            Tuple of (holdings_list, holding_date)
        """
        response = await self.http_client.get(csv_url)
        response.raise_for_status()

        # Parse CSV with pandas
        csv_content = response.text
        df = pd.read_csv(io.StringIO(csv_content))

        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()

        # Detect column mappings
        column_mapping = self._detect_csv_columns(df.columns.tolist())

        if not column_mapping.get("ticker") and not column_mapping.get("company"):
            raise ValueError("Could not identify required columns in CSV")

        # Extract holdings
        holdings = []
        holding_date = None

        for _, row in df.iterrows():
            holding = {}

            # Extract ticker
            if column_mapping.get("ticker"):
                ticker_val = row[column_mapping["ticker"]]
                if pd.notna(ticker_val) and str(ticker_val).strip():
                    holding["ticker"] = str(ticker_val).strip().upper()

            # Extract company name
            if column_mapping.get("company"):
                company_val = row[column_mapping["company"]]
                if pd.notna(company_val):
                    holding["company_name"] = str(company_val).strip()

            # Extract CUSIP
            if column_mapping.get("cusip"):
                cusip_val = row[column_mapping["cusip"]]
                if pd.notna(cusip_val):
                    holding["cusip"] = str(cusip_val).strip()

            # Extract shares
            if column_mapping.get("shares"):
                shares_val = row[column_mapping["shares"]]
                if pd.notna(shares_val):
                    holding["shares"] = self._parse_numeric(shares_val)

            # Extract market value
            if column_mapping.get("market_value"):
                value_val = row[column_mapping["market_value"]]
                if pd.notna(value_val):
                    holding["market_value"] = self._parse_numeric(value_val)

            # Extract weight
            if column_mapping.get("weight"):
                weight_val = row[column_mapping["weight"]]
                if pd.notna(weight_val):
                    weight = self._parse_numeric(weight_val)
                    # Convert to percentage if it's a decimal
                    if weight and weight < 1:
                        weight = weight * 100
                    holding["weight_pct"] = weight

            # Extract date if available
            if column_mapping.get("date") and holding_date is None:
                date_val = row[column_mapping["date"]]
                if pd.notna(date_val):
                    holding_date = self._parse_date(date_val)

            # Only add if we have at least ticker or company
            if holding.get("ticker") or holding.get("company_name"):
                holdings.append(holding)

        logger.debug("CSV parsing completed", holdings_count=len(holdings), holding_date=holding_date)
        return holdings, holding_date

    def _detect_csv_columns(self, columns: List[str]) -> Dict[str, str]:
        """
        Detect column mappings from CSV header names.

        Args:
            columns: List of column names

        Returns:
            Dictionary mapping standard names to actual column names
        """
        mapping = {}

        # Ticker patterns
        ticker_patterns = ['ticker', 'symbol', 'stock', 'security']
        for col in columns:
            col_lower = col.lower()
            if any(p in col_lower for p in ticker_patterns) and 'company' not in col_lower:
                mapping['ticker'] = col
                break

        # Company name patterns
        company_patterns = ['company', 'name', 'issuer', 'holding', 'description']
        for col in columns:
            col_lower = col.lower()
            if any(p in col_lower for p in company_patterns):
                if col not in mapping.values():
                    mapping['company'] = col
                    break

        # CUSIP patterns
        cusip_patterns = ['cusip', 'identifier', 'sedol', 'isin']
        for col in columns:
            if any(p in col.lower() for p in cusip_patterns):
                mapping['cusip'] = col
                break

        # Shares patterns
        shares_patterns = ['shares', 'quantity', 'units', 'position']
        for col in columns:
            col_lower = col.lower()
            if any(p in col_lower for p in shares_patterns):
                mapping['shares'] = col
                break

        # Market value patterns
        value_patterns = ['value', 'market', 'amount', 'notional']
        for col in columns:
            col_lower = col.lower()
            if any(p in col_lower for p in value_patterns) and 'weight' not in col_lower:
                mapping['market_value'] = col
                break

        # Weight patterns
        weight_patterns = ['weight', '%', 'percent', 'allocation']
        for col in columns:
            col_lower = col.lower()
            if any(p in col_lower for p in weight_patterns):
                mapping['weight'] = col
                break

        # Date patterns
        date_patterns = ['date', 'as of', 'asof']
        for col in columns:
            if any(p in col.lower() for p in date_patterns):
                mapping['date'] = col
                break

        return mapping

    async def _parse_table_data(
        self, tables: List[List[List[str]]], agent_command: str
    ) -> tuple[List[Dict[str, Any]], Optional[date]]:
        """
        Parse extracted table data into holdings.

        Args:
            tables: List of tables (each table is list of rows, each row is list of cells)
            agent_command: Extraction instructions for context

        Returns:
            Tuple of (holdings_list, holding_date)
        """
        holdings = []
        holding_date = None

        for table in tables:
            if len(table) < 2:
                continue

            # First row is likely header
            header = [cell.lower().strip() for cell in table[0]]

            # Try to detect column indices
            ticker_idx = None
            company_idx = None
            shares_idx = None
            value_idx = None
            weight_idx = None
            cusip_idx = None
            date_idx = None

            for i, col in enumerate(header):
                if ticker_idx is None and any(p in col for p in ['ticker', 'symbol']):
                    ticker_idx = i
                elif company_idx is None and any(p in col for p in ['company', 'name', 'holding', 'description']):
                    company_idx = i
                elif shares_idx is None and any(p in col for p in ['shares', 'quantity', 'units']):
                    shares_idx = i
                elif value_idx is None and any(p in col for p in ['value', 'market']) and 'weight' not in col:
                    value_idx = i
                elif weight_idx is None and any(p in col for p in ['weight', '%', 'percent', 'allocation']):
                    weight_idx = i
                elif cusip_idx is None and any(p in col for p in ['cusip', 'identifier', 'sedol', 'isin']):
                    cusip_idx = i
                elif date_idx is None and any(p in col for p in ['date', 'as of']):
                    date_idx = i

            # If we couldn't find key columns, try using LLM to interpret
            if ticker_idx is None and company_idx is None:
                # Format table for LLM
                table_text = "\n".join(["\t".join(row) for row in table[:50]])  # Limit rows
                holdings, holding_date = await self._extract_holdings_with_llm(table_text, agent_command)
                if holdings:
                    return holdings, holding_date
                continue

            # Parse data rows
            for row in table[1:]:  # Skip header
                if len(row) <= max(filter(None, [ticker_idx, company_idx, 0])):
                    continue

                holding = {}

                # Extract ticker
                if ticker_idx is not None and ticker_idx < len(row):
                    ticker = row[ticker_idx].strip().upper()
                    # Clean up ticker (remove extra info)
                    ticker = ticker.split()[0] if ticker else ""
                    if ticker and len(ticker) <= 10:
                        holding["ticker"] = ticker

                # Extract company name
                if company_idx is not None and company_idx < len(row):
                    company = row[company_idx].strip()
                    if company:
                        holding["company_name"] = company

                # Extract shares
                if shares_idx is not None and shares_idx < len(row):
                    shares = self._parse_numeric(row[shares_idx])
                    if shares is not None:
                        holding["shares"] = int(shares)

                # Extract market value
                if value_idx is not None and value_idx < len(row):
                    value = self._parse_numeric(row[value_idx])
                    if value is not None:
                        holding["market_value"] = value

                # Extract weight
                if weight_idx is not None and weight_idx < len(row):
                    weight = self._parse_numeric(row[weight_idx])
                    if weight is not None:
                        # Convert to percentage if decimal
                        if weight < 1:
                            weight = weight * 100
                        holding["weight_pct"] = weight

                # Extract CUSIP
                if cusip_idx is not None and cusip_idx < len(row):
                    cusip = row[cusip_idx].strip()
                    if cusip:
                        holding["cusip"] = cusip

                # Extract date (first valid date found)
                if date_idx is not None and date_idx < len(row) and holding_date is None:
                    holding_date = self._parse_date(row[date_idx])

                # Only add if we have meaningful data
                if holding.get("ticker") or holding.get("company_name"):
                    holdings.append(holding)

            # If we found holdings in this table, return them
            if len(holdings) > 5:
                logger.debug("Parsed table data", holdings_count=len(holdings), holding_date=holding_date)
                return holdings, holding_date

        # If we parsed but got few holdings, try LLM on the largest table
        if not holdings and tables:
            largest_table = max(tables, key=len)
            table_text = "\n".join(["\t".join(row) for row in largest_table[:100]])
            return await self._extract_holdings_with_llm(table_text, agent_command)

        return holdings, holding_date

    async def _extract_from_pdf(
        self, pdf_url: str, agent_command: str
    ) -> tuple[List[Dict[str, Any]], Optional[date]]:
        """
        Download PDF and extract holdings using pdfplumber + LLM.

        Args:
            pdf_url: URL to PDF file
            agent_command: Extraction instructions

        Returns:
            Tuple of (holdings_list, holding_date)
        """
        import pdfplumber

        # Download PDF
        response = await self.http_client.get(pdf_url)
        response.raise_for_status()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        try:
            # Extract text from PDF
            pdf_text = ""
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages[:10]:  # Limit to first 10 pages
                    text = page.extract_text()
                    if text:
                        pdf_text += text + "\n"

            # Use LLM to extract holdings
            holdings, holding_date = await self._extract_holdings_with_llm(pdf_text, agent_command)
            return holdings, holding_date

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    async def _extract_from_html(
        self, page_content: str, agent_command: str
    ) -> tuple[List[Dict[str, Any]], Optional[date]]:
        """
        Extract holdings from HTML page content using LLM.

        Args:
            page_content: HTML page text content
            agent_command: Extraction instructions

        Returns:
            Tuple of (holdings_list, holding_date)
        """
        return await self._extract_holdings_with_llm(page_content, agent_command)

    async def _extract_holdings_with_llm(
        self, content: str, agent_command: str
    ) -> tuple[List[Dict[str, Any]], Optional[date]]:
        """
        Use LLM to extract holdings from text content.

        Args:
            content: Text content to extract from
            agent_command: Extraction instructions

        Returns:
            Tuple of (holdings_list, holding_date)
        """
        # Truncate if too long
        if len(content) > 15000:
            content = content[:15000] + "\n[Content truncated]"

        prompt = f"""You are extracting ETF holdings data from the following content.

USER INSTRUCTIONS:
{agent_command}

CONTENT:
{content}

TASK:
Extract all stock holdings and return as JSON:
{{
    "holding_date": "YYYY-MM-DD format or null",
    "holdings": [
        {{
            "ticker": "STOCK TICKER",
            "company_name": "Company Name",
            "cusip": "CUSIP if available or null",
            "shares": number or null,
            "market_value": number in USD or null,
            "weight_pct": percentage (0-100) or null
        }}
    ]
}}

Return ONLY valid JSON, no explanations."""

        try:
            client = _get_ollama_client()
            response = client.chat(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You extract structured financial data from text. Return only valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.1, "num_predict": 8000}
            )

            result = self._parse_json_response(response['message']['content'])
            holdings = result.get("holdings", [])

            holding_date = None
            if result.get("holding_date"):
                holding_date = self._parse_date(result["holding_date"])

            return holdings, holding_date

        except Exception as e:
            logger.error("LLM holdings extraction failed", error=str(e))
            return [], None

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        import json

        # Try direct parsing
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        if "```json" in response_text:
            try:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end == -1:
                    end = len(response_text)
                return json.loads(response_text[start:end].strip())
            except json.JSONDecodeError:
                pass

        # Try finding JSON object
        if "{" in response_text:
            start = response_text.find("{")
            try:
                return json.loads(response_text[start:])
            except json.JSONDecodeError:
                pass

        return {}

    def _parse_numeric(self, value: Any) -> Optional[float]:
        """Parse a numeric value, handling various formats."""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        # Convert to string and clean
        s = str(value).strip()
        s = s.replace(",", "").replace("$", "").replace("%", "")
        s = s.replace("(", "-").replace(")", "")  # Handle negative in parens

        try:
            return float(s)
        except ValueError:
            return None

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value from various formats."""
        if value is None:
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        s = str(value).strip()

        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%d/%m/%Y",
            "%Y%m%d",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue

        return None


# Convenience function for creating agent
def get_etf_data_agent(llm_model: Optional[str] = None) -> ETFDataAgent:
    """Get an ETF data agent instance."""
    return ETFDataAgent(llm_model=llm_model)
