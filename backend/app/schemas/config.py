"""Configuration schemas for user settings."""

from typing import Optional, Dict
from pydantic import BaseModel, Field


class AIModelSettings(BaseModel):
    """AI model configuration settings."""

    default_model: Optional[str] = Field(None, description="Default Ollama model")
    stock_research_model: Optional[str] = Field(None, description="Model for stock research")
    market_sentiment_model: Optional[str] = Field(None, description="Model for market sentiment")
    web_scraping_model: Optional[str] = Field(None, description="Model for web scraping")
    temperature: Optional[float] = Field(0.3, ge=0.0, le=1.0, description="Model temperature")
    max_tokens: Optional[int] = Field(2048, ge=512, le=4096, description="Max tokens")


class DisplayPreferences(BaseModel):
    """Display preferences for UI."""

    research_history_items: Optional[int] = Field(10, ge=5, le=50, description="Number of research history items")
    fund_recent_changes_items: Optional[int] = Field(10, ge=5, le=50, description="Number of fund recent changes")
    holdings_per_fund: Optional[int] = Field(50, ge=10, le=100, description="Holdings per fund")
    peers_in_comparison: Optional[int] = Field(5, ge=3, le=10, description="Number of peers in comparison")


class WebsiteInfo(BaseModel):
    """Website information for scraping."""

    name: str = Field(..., description="Website display name")
    url: str = Field(..., description="Website URL")


class MarketScrapingSettings(BaseModel):
    """Market data scraping configuration."""

    website_key: Optional[str] = Field(None, description="Selected website for market scraping")
    scraping_model: Optional[str] = Field(None, description="Model for scraping")
    analysis_model: Optional[str] = Field(None, description="Model for analysis")
    custom_websites: Optional[Dict[str, WebsiteInfo]] = Field(default_factory=dict, description="User-defined custom websites")


class ConfigSettings(BaseModel):
    """Complete user configuration settings."""

    ai_models: AIModelSettings = Field(default_factory=AIModelSettings)
    display_preferences: DisplayPreferences = Field(default_factory=DisplayPreferences)
    market_scraping: MarketScrapingSettings = Field(default_factory=MarketScrapingSettings)


class VPNStatus(BaseModel):
    """VPN connection status."""

    enabled: bool = Field(..., description="Whether VPN mode is enabled in config")
    connected: bool = Field(..., description="Whether VPN is currently connected")
    location: Optional[str] = Field(None, description="VPN connection location")
    message: str = Field(..., description="Status message")


class ConfigResponse(BaseModel):
    """Response for configuration endpoints."""

    settings: ConfigSettings
    has_alpha_vantage_key: bool = Field(False, description="Whether Alpha Vantage API key is configured")
    has_fmp_key: bool = Field(False, description="Whether FMP API key is configured")
    has_sec_user_agent: bool = Field(False, description="Whether SEC user agent is configured")
    vpn_status: Optional[VPNStatus] = Field(None, description="VPN connection status")


class TestAPIKeyRequest(BaseModel):
    """Request to test an API key."""

    provider: str = Field(..., description="API provider (alpha_vantage, fmp)")
    api_key: str = Field(..., description="API key to test")


class TestAPIKeyResponse(BaseModel):
    """Response for API key test."""

    valid: bool = Field(..., description="Whether the API key is valid")
    message: str = Field(..., description="Result message")
    provider: str = Field(..., description="API provider tested")
