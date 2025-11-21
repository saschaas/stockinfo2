"""Fund validation service."""

import structlog
from typing import Dict, Any

from backend.app.services.sec_edgar import get_sec_edgar_client
from backend.app.core.exceptions import DataSourceException

logger = structlog.get_logger(__name__)


class FundValidatorService:
    """Service for validating fund information."""

    async def validate_fund(self, cik: str, name: str | None = None) -> Dict[str, Any]:
        """Validate that a CIK belongs to a fund with available data.

        Args:
            cik: Central Index Key (CIK) to validate
            name: Optional fund name for logging

        Returns:
            Dictionary with validation results:
            {
                "is_valid": bool,
                "fund_type": str ("fund" or "etf"),
                "name": str,
                "has_13f_filings": bool,
                "latest_filing_date": str | None,
                "error": str | None,
            }
        """
        result = {
            "is_valid": False,
            "fund_type": None,
            "name": name,
            "has_13f_filings": False,
            "latest_filing_date": None,
            "error": None,
        }

        try:
            # Ensure CIK is zero-padded to 10 digits
            cik = cik.strip().lstrip("0").zfill(10)

            # Get SEC EDGAR client
            client = await get_sec_edgar_client()

            # Check if entity exists and get basic info
            try:
                company_info = await client.get_company_filings(cik)
                entity_name = company_info.get("name")
                result["name"] = entity_name or name

                logger.info("Found entity in SEC database", cik=cik, name=entity_name)

            except DataSourceException as e:
                result["error"] = f"Entity not found in SEC database: {str(e)}"
                logger.warning("Entity not found", cik=cik, error=str(e))
                return result

            # Check for 13F-HR filings (only investment managers file these, not ETFs)
            try:
                filings = await client.get_13f_filings(cik)

                if not filings:
                    result["error"] = "No 13F-HR filings found. This may be an ETF or entity that doesn't file 13F forms."
                    result["fund_type"] = "unknown"
                    logger.warning("No 13F filings found", cik=cik, name=result["name"])
                    return result

                result["has_13f_filings"] = True
                result["latest_filing_date"] = filings[0].get("filing_date")
                result["fund_type"] = "fund"

                logger.info(
                    "Found 13F filings",
                    cik=cik,
                    name=result["name"],
                    count=len(filings),
                    latest=result["latest_filing_date"],
                )

            except Exception as e:
                result["error"] = f"Error checking 13F filings: {str(e)}"
                logger.error("Error checking 13F filings", cik=cik, error=str(e))
                return result

            # Try to get holdings data to verify it's accessible
            try:
                if filings:
                    latest_filing = filings[0]
                    holdings = await client.get_13f_holdings(
                        cik, latest_filing["accession_number"]
                    )

                    if not holdings:
                        result["error"] = "No holdings data available in latest filing."
                        logger.warning("No holdings data", cik=cik, filing=latest_filing["filing_date"])
                        return result

                    logger.info("Holdings data verified", cik=cik, holdings_count=len(holdings))

            except Exception as e:
                result["error"] = f"Error retrieving holdings data: {str(e)}"
                logger.error("Error retrieving holdings", cik=cik, error=str(e))
                return result

            # If we got here, validation passed
            result["is_valid"] = True
            logger.info("Fund validation successful", cik=cik, name=result["name"])

        except Exception as e:
            result["error"] = f"Unexpected validation error: {str(e)}"
            logger.error("Unexpected validation error", cik=cik, error=str(e))

        return result


# Singleton instance
_validator: FundValidatorService | None = None


def get_fund_validator() -> FundValidatorService:
    """Get fund validator instance."""
    global _validator
    if _validator is None:
        _validator = FundValidatorService()
    return _validator
