"""Scraped websites API routes."""

import time
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ScrapedWebsite
from backend.app.db.session import get_db
from backend.app.schemas.config import (
    DATA_USE_CATEGORIES,
    DATA_USE_DISPLAY_NAMES,
    DATA_TEMPLATES,
    ScrapedWebsiteCreate,
    ScrapedWebsiteUpdate,
    ScrapedWebsiteResponse,
    ScrapedWebsiteTestRequest,
    ScrapedWebsiteTestResponse,
)

router = APIRouter()
logger = structlog.get_logger(__name__)


def _to_response(website: ScrapedWebsite) -> ScrapedWebsiteResponse:
    """Convert database model to response schema."""
    # Parse data_use as comma-separated list
    data_use_list = [du.strip() for du in website.data_use.split(",") if du.strip()]

    # Create display string from all categories
    data_use_display = ", ".join(
        DATA_USE_DISPLAY_NAMES.get(du, du) for du in data_use_list
    )

    return ScrapedWebsiteResponse(
        id=website.id,
        key=website.key,
        name=website.name,
        url=website.url,
        description=website.description,
        data_use=website.data_use,
        data_use_list=data_use_list,
        data_use_display=data_use_display,
        extraction_template=website.extraction_template,
        is_active=website.is_active,
        last_test_at=website.last_test_at,
        last_test_result=website.last_test_result,
        last_test_success=website.last_test_success,
        created_at=website.created_at,
        updated_at=website.updated_at,
    )


@router.get("/categories")
async def get_data_use_categories() -> dict:
    """Get available data use categories and their templates."""
    return {
        "categories": [
            {
                "value": cat,
                "label": DATA_USE_DISPLAY_NAMES.get(cat, cat),
                "description": DATA_TEMPLATES.get(cat, {}).get("description", ""),
            }
            for cat in DATA_USE_CATEGORIES
        ],
        "templates": {
            cat: {
                "description": template.get("description", ""),
                "template": template.get("template", {}),
            }
            for cat, template in DATA_TEMPLATES.items()
        },
    }


@router.get("", response_model=List[ScrapedWebsiteResponse])
async def list_websites(
    data_use: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
) -> List[ScrapedWebsiteResponse]:
    """List all scraped websites with optional filters."""
    stmt = select(ScrapedWebsite)

    if data_use:
        stmt = stmt.where(ScrapedWebsite.data_use == data_use)
    if is_active is not None:
        stmt = stmt.where(ScrapedWebsite.is_active == is_active)

    stmt = stmt.order_by(ScrapedWebsite.name)
    result = await db.execute(stmt)
    websites = result.scalars().all()

    return [_to_response(w) for w in websites]


@router.get("/{key}", response_model=ScrapedWebsiteResponse)
async def get_website(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> ScrapedWebsiteResponse:
    """Get a specific scraped website by key."""
    stmt = select(ScrapedWebsite).where(ScrapedWebsite.key == key)
    result = await db.execute(stmt)
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with key '{key}' not found",
        )

    return _to_response(website)


@router.post("", response_model=ScrapedWebsiteResponse, status_code=status.HTTP_201_CREATED)
async def create_website(
    website_data: ScrapedWebsiteCreate,
    db: AsyncSession = Depends(get_db),
) -> ScrapedWebsiteResponse:
    """Create a new scraped website configuration."""
    # Parse data_use (validator converts list to comma-separated string)
    data_use_list = [du.strip() for du in website_data.data_use.split(",") if du.strip()]

    # Validate all data_use categories
    for du in data_use_list:
        if du not in DATA_USE_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data_use category '{du}'. Must be one of: {DATA_USE_CATEGORIES}",
            )

    # Check if key already exists
    stmt = select(ScrapedWebsite).where(ScrapedWebsite.key == website_data.key)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Website with key '{website_data.key}' already exists",
        )

    # Build combined extraction template from all categories if not provided
    extraction_template = website_data.extraction_template
    if not extraction_template:
        combined_template = {}
        for du in data_use_list:
            template = DATA_TEMPLATES.get(du, {}).get("template", {})
            combined_template[du] = template
        extraction_template = combined_template

    website = ScrapedWebsite(
        key=website_data.key,
        name=website_data.name,
        url=website_data.url,
        description=website_data.description,
        data_use=website_data.data_use,  # Already comma-separated from validator
        extraction_template=extraction_template,
    )

    db.add(website)
    await db.commit()
    await db.refresh(website)

    logger.info("Created scraped website", key=website.key, name=website.name)

    return _to_response(website)


@router.put("/{key}", response_model=ScrapedWebsiteResponse)
async def update_website(
    key: str,
    website_data: ScrapedWebsiteUpdate,
    db: AsyncSession = Depends(get_db),
) -> ScrapedWebsiteResponse:
    """Update a scraped website configuration."""
    stmt = select(ScrapedWebsite).where(ScrapedWebsite.key == key)
    result = await db.execute(stmt)
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with key '{key}' not found",
        )

    # Validate data_use if provided (can be comma-separated for multiple categories)
    if website_data.data_use:
        data_use_list = [du.strip() for du in website_data.data_use.split(",") if du.strip()]
        for du in data_use_list:
            if du not in DATA_USE_CATEGORIES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid data_use category '{du}'. Must be one of: {DATA_USE_CATEGORIES}",
                )

    # Update fields
    if website_data.name is not None:
        website.name = website_data.name
    if website_data.url is not None:
        website.url = website_data.url
    if website_data.description is not None:
        website.description = website_data.description
    if website_data.data_use is not None:
        website.data_use = website_data.data_use
    if website_data.extraction_template is not None:
        website.extraction_template = website_data.extraction_template
    if website_data.is_active is not None:
        website.is_active = website_data.is_active

    await db.commit()
    await db.refresh(website)

    logger.info("Updated scraped website", key=website.key)

    return _to_response(website)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_website(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a scraped website configuration."""
    stmt = select(ScrapedWebsite).where(ScrapedWebsite.key == key)
    result = await db.execute(stmt)
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with key '{key}' not found",
        )

    await db.delete(website)
    await db.commit()

    logger.info("Deleted scraped website", key=key)


@router.post("/test", response_model=ScrapedWebsiteTestResponse)
async def test_scrape_website(
    request: ScrapedWebsiteTestRequest,
) -> ScrapedWebsiteTestResponse:
    """Test scraping a website and return the extracted data.

    This allows users to preview what data will be scraped before saving
    the website configuration.
    """
    from backend.app.agents.web_scraping_agent import WebScrapingAgent, WebScrapingConfig

    # Validate data_use categories (now supports multiple)
    data_use_list = request.data_use if isinstance(request.data_use, list) else [request.data_use]
    for du in data_use_list:
        if du not in DATA_USE_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data_use category '{du}'. Must be one of: {DATA_USE_CATEGORIES}",
            )

    # Build combined extraction prompt from all selected categories
    extraction_prompts = []
    for du in data_use_list:
        template = DATA_TEMPLATES.get(du, {})
        prompt = template.get("extraction_prompt", "")
        if prompt:
            extraction_prompts.append(f"--- {DATA_USE_DISPLAY_NAMES.get(du, du)} ---\n{prompt}")

    extraction_prompt = "\n\n".join(extraction_prompts)

    # Add user's custom description to the prompt if provided
    if request.description:
        extraction_prompt = f"""{extraction_prompt}

Additional context from user:
{request.description}"""

    try:
        start_time = time.time()

        # Create scraping config with longer timeout (120 seconds)
        config = WebScrapingConfig(
            data_type=",".join(data_use_list),
            url_pattern=request.url,
            extraction_prompt=extraction_prompt,
            timeout=120,  # Increased from 60 to 120 seconds
        )

        # Run scraping
        agent = WebScrapingAgent()
        result = await agent.extract_data(config, {})

        response_time_ms = int((time.time() - start_time) * 1000)

        if result.success:
            return ScrapedWebsiteTestResponse(
                success=True,
                scraped_data=result.data,
                error=None,
                response_time_ms=response_time_ms,
                extraction_prompt_used=extraction_prompt,
            )
        else:
            return ScrapedWebsiteTestResponse(
                success=False,
                scraped_data=None,
                error=result.error,
                response_time_ms=response_time_ms,
                extraction_prompt_used=extraction_prompt,
            )

    except Exception as e:
        logger.error("Test scrape failed", error=str(e))
        return ScrapedWebsiteTestResponse(
            success=False,
            scraped_data=None,
            error=str(e),
            response_time_ms=0,
            extraction_prompt_used=extraction_prompt,
        )


@router.post("/{key}/test", response_model=ScrapedWebsiteTestResponse)
async def test_existing_website(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> ScrapedWebsiteTestResponse:
    """Test scraping an existing website and update its last_test results.

    This allows users to verify that an existing website configuration
    still works correctly.
    """
    from backend.app.agents.web_scraping_agent import WebScrapingAgent, WebScrapingConfig

    # Get the website
    stmt = select(ScrapedWebsite).where(ScrapedWebsite.key == key)
    result = await db.execute(stmt)
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with key '{key}' not found",
        )

    # Parse data_use (can be comma-separated for multiple categories)
    data_use_list = [du.strip() for du in website.data_use.split(",")]

    # Build combined extraction prompt from all selected categories
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

    try:
        start_time = time.time()

        # Create scraping config with longer timeout (120 seconds)
        config = WebScrapingConfig(
            data_type=website.data_use,
            url_pattern=website.url,
            extraction_prompt=extraction_prompt,
            timeout=120,  # Increased from 60 to 120 seconds
        )

        # Run scraping
        agent = WebScrapingAgent()
        result = await agent.extract_data(config, {})

        response_time_ms = int((time.time() - start_time) * 1000)

        # Update website with test results
        website.last_test_at = datetime.utcnow()
        website.last_test_success = result.success
        website.last_test_result = {
            "data": result.data if result.success else None,
            "error": result.error,
            "response_time_ms": response_time_ms,
        }
        await db.commit()

        if result.success:
            return ScrapedWebsiteTestResponse(
                success=True,
                scraped_data=result.data,
                error=None,
                response_time_ms=response_time_ms,
                extraction_prompt_used=extraction_prompt,
            )
        else:
            return ScrapedWebsiteTestResponse(
                success=False,
                scraped_data=None,
                error=result.error,
                response_time_ms=response_time_ms,
                extraction_prompt_used=extraction_prompt,
            )

    except Exception as e:
        logger.error("Test scrape failed", key=key, error=str(e))

        # Update website with error
        website.last_test_at = datetime.utcnow()
        website.last_test_success = False
        website.last_test_result = {"error": str(e)}
        await db.commit()

        return ScrapedWebsiteTestResponse(
            success=False,
            scraped_data=None,
            error=str(e),
            response_time_ms=0,
            extraction_prompt_used=extraction_prompt,
        )
