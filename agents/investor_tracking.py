"""Investor Tracking Agent for monitoring fund holdings."""

from typing import Any
from decimal import Decimal

import yaml
import structlog

from backend.app.config import get_settings
from backend.app.services.sec_edgar import get_sec_edgar_client

logger = structlog.get_logger(__name__)
settings = get_settings()


class InvestorTrackingAgent:
    """Agent for tracking institutional investor holdings."""

    def __init__(self) -> None:
        self.funds = self._load_fund_config()

    def _load_fund_config(self) -> list[dict[str, Any]]:
        """Load fund configuration."""
        try:
            with open("config/config.yaml", "r") as f:
                config = yaml.safe_load(f)

            funds = []
            for category in ["tech_focused", "general"]:
                for fund in config.get("funds", {}).get(category, []):
                    if fund.get("cik"):
                        funds.append({
                            **fund,
                            "category": category,
                        })

            return funds
        except Exception as e:
            logger.error("Failed to load fund config", error=str(e))
            return []

    async def track(self, ticker: str | None = None) -> dict[str, Any]:
        """Track fund holdings and identify ownership.

        Args:
            ticker: Optional ticker to filter holdings for

        Returns:
            Fund tracking results
        """
        logger.info("Investor Tracking Agent starting", ticker=ticker)

        result = {
            "ticker": ticker,
            "funds": [],
            "total_fund_value": Decimal(0),
            "total_fund_shares": 0,
            "ownership_summary": [],
        }

        client = await get_sec_edgar_client()

        for fund_config in self.funds:
            try:
                fund_data = await self._process_fund(client, fund_config, ticker)
                if fund_data:
                    result["funds"].append(fund_data)

                    # Update totals if ticker specified
                    if ticker and fund_data.get("holding"):
                        result["total_fund_value"] += fund_data["holding"].get("value", Decimal(0))
                        result["total_fund_shares"] += fund_data["holding"].get("shares", 0)

            except Exception as e:
                logger.warning(
                    "Failed to process fund",
                    fund=fund_config["name"],
                    error=str(e),
                )

        # Create ownership summary
        if ticker and result["funds"]:
            result["ownership_summary"] = self._create_ownership_summary(result["funds"])

        logger.info(
            "Investor Tracking Agent completed",
            funds_processed=len(result["funds"]),
            ticker=ticker,
        )

        return result

    async def _process_fund(
        self,
        client: Any,
        fund_config: dict[str, Any],
        ticker: str | None,
    ) -> dict[str, Any] | None:
        """Process a single fund's holdings."""
        cik = fund_config["cik"]

        # Get holdings with changes
        holdings_data = await client.get_fund_holdings_with_changes(cik)

        if not holdings_data.get("holdings"):
            return None

        fund_result = {
            "name": fund_config["name"],
            "ticker": fund_config.get("ticker"),
            "cik": cik,
            "category": fund_config.get("category"),
            "filing_date": holdings_data.get("filing_date"),
            "previous_date": holdings_data.get("previous_date"),
            "total_value": holdings_data.get("total_value", Decimal(0)),
            "holdings_count": len(holdings_data["holdings"]),
        }

        # If ticker specified, find specific holding
        if ticker:
            holding = self._find_ticker_in_holdings(ticker, holdings_data["holdings"])
            if holding:
                fund_result["holding"] = holding
                fund_result["owns_ticker"] = True
            else:
                fund_result["owns_ticker"] = False
                return fund_result

        # Get top holdings
        fund_result["top_holdings"] = self._get_top_holdings(holdings_data["holdings"], 10)

        # Get recent changes
        fund_result["changes"] = self._get_changes_summary(holdings_data["holdings"])

        return fund_result

    def _find_ticker_in_holdings(
        self,
        ticker: str,
        holdings: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Find a specific ticker in holdings."""
        ticker_upper = ticker.upper()

        for holding in holdings:
            # Check ticker field
            holding_ticker = holding.get("ticker", "").upper()
            if holding_ticker == ticker_upper:
                return {
                    "ticker": ticker_upper,
                    "company_name": holding.get("company_name"),
                    "shares": holding.get("shares", 0),
                    "value": holding.get("value", Decimal(0)),
                    "percentage": holding.get("percentage", Decimal(0)),
                    "change_type": holding.get("change_type"),
                    "shares_change": holding.get("shares_change"),
                }

            # Also check company name for partial matches
            company_name = holding.get("company_name", "").upper()
            if ticker_upper in company_name:
                return {
                    "ticker": holding.get("ticker") or holding.get("cusip", "")[:10],
                    "company_name": holding.get("company_name"),
                    "shares": holding.get("shares", 0),
                    "value": holding.get("value", Decimal(0)),
                    "percentage": holding.get("percentage", Decimal(0)),
                    "change_type": holding.get("change_type"),
                    "shares_change": holding.get("shares_change"),
                }

        return None

    def _get_top_holdings(
        self,
        holdings: list[dict[str, Any]],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get top holdings by value."""
        sorted_holdings = sorted(
            holdings,
            key=lambda x: x.get("value", 0),
            reverse=True,
        )

        return [
            {
                "ticker": h.get("ticker") or h.get("cusip", "")[:10],
                "company_name": h.get("company_name"),
                "value": h.get("value", Decimal(0)),
                "percentage": h.get("percentage", Decimal(0)),
            }
            for h in sorted_holdings[:limit]
        ]

    def _get_changes_summary(self, holdings: list[dict[str, Any]]) -> dict[str, list]:
        """Get summary of changes in holdings."""
        changes = {
            "new": [],
            "increased": [],
            "decreased": [],
            "sold": [],
        }

        for holding in holdings:
            change_type = holding.get("change_type")
            if change_type in changes:
                changes[change_type].append({
                    "ticker": holding.get("ticker") or holding.get("cusip", "")[:10],
                    "company_name": holding.get("company_name"),
                    "shares_change": holding.get("shares_change"),
                })

        # Limit each category
        for key in changes:
            changes[key] = changes[key][:5]

        return changes

    def _create_ownership_summary(self, funds: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create summary of fund ownership for a ticker."""
        summary = []

        for fund in funds:
            if fund.get("owns_ticker") and fund.get("holding"):
                holding = fund["holding"]
                summary.append({
                    "fund_name": fund["name"],
                    "fund_category": fund.get("category"),
                    "shares": holding.get("shares", 0),
                    "value": float(holding.get("value", 0)),
                    "percentage_of_portfolio": float(holding.get("percentage", 0)),
                    "change_type": holding.get("change_type"),
                    "shares_change": holding.get("shares_change"),
                })

        # Sort by value
        summary.sort(key=lambda x: x["value"], reverse=True)

        return summary

    async def get_new_filings(self) -> list[dict[str, Any]]:
        """Check for new 13F filings across all tracked funds.

        Returns:
            List of funds with new filings
        """
        client = await get_sec_edgar_client()
        new_filings = []

        for fund_config in self.funds:
            try:
                latest = await client.get_latest_13f(fund_config["cik"])
                if latest:
                    new_filings.append({
                        "fund_name": fund_config["name"],
                        "filing_date": latest.get("filing_date"),
                        "accession_number": latest.get("accession_number"),
                    })
            except Exception as e:
                logger.warning(
                    "Failed to check filing",
                    fund=fund_config["name"],
                    error=str(e),
                )

        return new_filings
