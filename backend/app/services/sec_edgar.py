"""SEC EDGAR API client for 13F filings."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from xml.etree import ElementTree

import httpx
import structlog
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.app.config import get_settings
from backend.app.core.exceptions import DataSourceException
from backend.app.core.rate_limiter import get_sec_edgar_limiter
from backend.app.services.cache import cache, CacheService

logger = structlog.get_logger(__name__)
settings = get_settings()


class SECEdgarClient:
    """Client for SEC EDGAR API to fetch 13F filings."""

    BASE_URL = "https://data.sec.gov"
    WWW_URL = "https://www.sec.gov"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"

    def __init__(self) -> None:
        self.user_agent = settings.sec_user_agent
        self.rate_limiter = get_sec_edgar_limiter()
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _make_request(self, url: str, accept: str = "application/json") -> Any:
        """Make a rate-limited request to SEC EDGAR."""
        await self.rate_limiter.wait_for_token()

        try:
            headers = {"Accept": accept}
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()

            if accept == "application/json":
                return response.json()
            return response.text

        except httpx.HTTPError as e:
            logger.error("SEC EDGAR request failed", url=url, error=str(e))
            raise DataSourceException(
                f"Failed to fetch data from SEC EDGAR: {e}",
                source="sec_edgar",
            )

    async def get_company_filings(self, cik: str) -> dict[str, Any]:
        """Get all filings for a company by CIK.

        Args:
            cik: Central Index Key (10 digits, zero-padded)

        Returns:
            Company filings data
        """
        # Ensure CIK is zero-padded to 10 digits
        cik = cik.lstrip("0").zfill(10)

        cache_key = f"sec:filings:{cik}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"
        data = await self._make_request(url)

        result = {
            "cik": data.get("cik"),
            "name": data.get("name"),
            "sic": data.get("sic"),
            "sic_description": data.get("sicDescription"),
            "filings": data.get("filings", {}).get("recent", {}),
        }

        # Cache for 1 hour
        await cache.set(cache_key, result, CacheService.TTL_MEDIUM)

        return result

    async def get_13f_filings(self, cik: str) -> list[dict[str, Any]]:
        """Get 13F-HR filings for a fund.

        Args:
            cik: Central Index Key

        Returns:
            List of 13F filing metadata
        """
        filings_data = await self.get_company_filings(cik)
        filings = filings_data.get("filings", {})

        forms = filings.get("form", [])
        accession_numbers = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        primary_documents = filings.get("primaryDocument", [])

        result = []
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A"):
                result.append({
                    "form": form,
                    "accession_number": accession_numbers[i],
                    "filing_date": filing_dates[i],
                    "primary_document": primary_documents[i],
                    "cik": cik,
                })

        logger.info("Found 13F filings", cik=cik, count=len(result))
        return result

    async def get_latest_13f(self, cik: str) -> dict[str, Any] | None:
        """Get the most recent 13F-HR filing.

        Args:
            cik: Central Index Key

        Returns:
            Latest 13F filing metadata or None
        """
        filings = await self.get_13f_filings(cik)
        return filings[0] if filings else None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_13f_holdings(
        self,
        cik: str,
        accession_number: str,
    ) -> list[dict[str, Any]]:
        """Parse 13F holdings from a filing.

        Args:
            cik: Central Index Key
            accession_number: Filing accession number

        Returns:
            List of holdings
        """
        cache_key = f"sec:holdings:{cik}:{accession_number}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        # Format accession number for URL
        acc_formatted = accession_number.replace("-", "")
        cik_stripped = cik.lstrip("0")

        # Common info table XML file names to try
        common_names = [
            "form13fInfoTable.xml",
            "infotable.xml",
            "InfoTable.xml",
            "INFOTABLE.xml",
        ]

        xml_content = None
        base_path = f"/Archives/edgar/data/{cik_stripped}/{acc_formatted}"

        # Try common file names first (faster)
        for filename in common_names:
            xml_url = f"{self.WWW_URL}{base_path}/{filename}"
            try:
                xml_content = await self._make_request(xml_url, accept="application/xml")
                if xml_content and not xml_content.startswith("<?xml") or "<Error>" not in str(xml_content)[:100]:
                    logger.info("Found info table", url=xml_url)
                    break
                xml_content = None
            except Exception:
                continue

        # If common names didn't work, parse HTML index to find the file
        if not xml_content:
            try:
                index_url = f"{self.WWW_URL}{base_path}/{accession_number}-index.htm"
                html_content = await self._make_request(index_url, accept="text/html")

                # Parse HTML to find info table XML file
                soup = BeautifulSoup(html_content, "lxml")
                for link in soup.find_all("a", href=True):
                    href = link["href"].lower()
                    if "infotable" in href and href.endswith(".xml"):
                        # Extract filename from href
                        filename = link["href"].split("/")[-1]
                        xml_url = f"{self.WWW_URL}{base_path}/{filename}"
                        xml_content = await self._make_request(xml_url, accept="application/xml")
                        break
            except Exception as e:
                logger.warning("Failed to parse HTML index", cik=cik, error=str(e))

        if not xml_content:
            logger.warning("No information table found", cik=cik, accession=accession_number)
            return []

        try:
            holdings = self._parse_13f_xml(xml_content)

            # Cache for 24 hours
            await cache.set(cache_key, holdings, CacheService.TTL_LONG)

            logger.info("Parsed 13F holdings", cik=cik, count=len(holdings))
            return holdings

        except Exception as e:
            logger.error("Failed to parse 13F holdings", cik=cik, error=str(e))
            raise DataSourceException(
                f"Failed to parse 13F holdings: {e}",
                source="sec_edgar",
            )

    def _parse_13f_xml(self, xml_content: str) -> list[dict[str, Any]]:
        """Parse 13F XML information table.

        Args:
            xml_content: Raw XML content

        Returns:
            List of parsed holdings
        """
        holdings = []

        try:
            # Parse XML
            root = ElementTree.fromstring(xml_content)

            # Handle namespaces
            namespaces = {
                "ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable",
            }

            # Find all info table entries
            for entry in root.findall(".//ns:infoTable", namespaces):
                holding = {}

                # Extract fields
                name_elem = entry.find("ns:nameOfIssuer", namespaces)
                holding["company_name"] = name_elem.text if name_elem is not None else None

                title_elem = entry.find("ns:titleOfClass", namespaces)
                holding["title"] = title_elem.text if title_elem is not None else None

                cusip_elem = entry.find("ns:cusip", namespaces)
                holding["cusip"] = cusip_elem.text if cusip_elem is not None else None

                value_elem = entry.find("ns:value", namespaces)
                if value_elem is not None:
                    # Value is in thousands of dollars
                    holding["value"] = Decimal(value_elem.text) * 1000

                shares_elem = entry.find(".//ns:sshPrnamt", namespaces)
                if shares_elem is not None:
                    holding["shares"] = int(shares_elem.text)

                share_type_elem = entry.find(".//ns:sshPrnamtType", namespaces)
                holding["share_type"] = share_type_elem.text if share_type_elem is not None else "SH"

                # Investment discretion
                discretion_elem = entry.find("ns:investmentDiscretion", namespaces)
                holding["discretion"] = discretion_elem.text if discretion_elem is not None else None

                # Voting authority
                sole_elem = entry.find(".//ns:Sole", namespaces)
                shared_elem = entry.find(".//ns:Shared", namespaces)
                none_elem = entry.find(".//ns:None", namespaces)

                holding["voting_authority"] = {
                    "sole": int(sole_elem.text) if sole_elem is not None else 0,
                    "shared": int(shared_elem.text) if shared_elem is not None else 0,
                    "none": int(none_elem.text) if none_elem is not None else 0,
                }

                holdings.append(holding)

        except ElementTree.ParseError as e:
            logger.error("Failed to parse 13F XML", error=str(e))
            raise

        return holdings

    async def get_fund_holdings_with_changes(
        self,
        cik: str,
    ) -> dict[str, Any]:
        """Get current holdings with changes from previous filing.

        Args:
            cik: Central Index Key

        Returns:
            Holdings with change information
        """
        filings = await self.get_13f_filings(cik)

        if not filings:
            return {"holdings": [], "filing_date": None, "previous_date": None}

        # Get current holdings
        current_filing = filings[0]
        current_holdings = await self.get_13f_holdings(
            cik, current_filing["accession_number"]
        )

        # Create lookup by CUSIP
        current_by_cusip = {h["cusip"]: h for h in current_holdings}

        # Get previous holdings if available
        previous_holdings = []
        previous_date = None
        if len(filings) > 1:
            previous_filing = filings[1]
            previous_date = previous_filing["filing_date"]
            previous_holdings = await self.get_13f_holdings(
                cik, previous_filing["accession_number"]
            )

        previous_by_cusip = {h["cusip"]: h for h in previous_holdings}

        # Calculate changes
        result_holdings = []
        total_value = Decimal(0)

        for cusip, holding in current_by_cusip.items():
            value = holding.get("value", Decimal(0))
            total_value += value

            change_info = {
                **holding,
                "change_type": None,
                "shares_change": None,
            }

            if cusip in previous_by_cusip:
                prev = previous_by_cusip[cusip]
                shares_diff = holding.get("shares", 0) - prev.get("shares", 0)
                change_info["shares_change"] = shares_diff

                if shares_diff > 0:
                    change_info["change_type"] = "increased"
                elif shares_diff < 0:
                    change_info["change_type"] = "decreased"
                else:
                    change_info["change_type"] = "unchanged"
            else:
                change_info["change_type"] = "new"
                change_info["shares_change"] = holding.get("shares", 0)

            result_holdings.append(change_info)

        # Find sold positions
        for cusip, holding in previous_by_cusip.items():
            if cusip not in current_by_cusip:
                result_holdings.append({
                    **holding,
                    "change_type": "sold",
                    "shares_change": -holding.get("shares", 0),
                    "shares": 0,
                    "value": Decimal(0),
                })

        # Calculate percentages
        for holding in result_holdings:
            if total_value > 0:
                holding["percentage"] = (holding.get("value", Decimal(0)) / total_value) * 100
            else:
                holding["percentage"] = Decimal(0)

        # Sort by value descending
        result_holdings.sort(key=lambda x: x.get("value", 0), reverse=True)

        return {
            "holdings": result_holdings,
            "filing_date": current_filing["filing_date"],
            "previous_date": previous_date,
            "total_value": total_value,
        }

    async def cusip_to_ticker(self, cusip: str) -> str | None:
        """Convert CUSIP to stock ticker.

        Note: This is a simplified implementation. In production,
        you would use a proper CUSIP lookup service.

        Args:
            cusip: CUSIP identifier

        Returns:
            Stock ticker or None
        """
        # This would typically use a mapping service
        # For now, we'll cache any manual mappings
        cache_key = f"sec:cusip:{cusip}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        # In production, implement actual lookup
        logger.debug("CUSIP lookup not implemented", cusip=cusip)
        return None


# Singleton instance
_client: SECEdgarClient | None = None


async def get_sec_edgar_client() -> SECEdgarClient:
    """Get SEC EDGAR client instance."""
    global _client
    if _client is None:
        _client = SECEdgarClient()
    return _client


async def close_sec_edgar_client() -> None:
    """Close SEC EDGAR client."""
    global _client
    if _client:
        await _client.close()
        _client = None
