import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..models.category import Category
from ..rate_limiter import limiter
from ..schemas.search_schemas import ProductSearchResult
from ..services.cache_service import get_cached, set_cached
from ..services.search_service import search_products

logger = logging.getLogger("wasla.search")

router = APIRouter()

# Cache is intentionally short-lived and keyed by the exact query — search
# results change less predictably than "browse" endpoints (which product
# shows up depends on live stock too), so this is deliberately a much
# shorter cache window than categories/shops use, not just copy-pasted.
SEARCH_CACHE_TTL_SECONDS = 30


def _search_cache_key(query: str, category_id: str) -> str:
    return f"search:{category_id}:{query.lower().strip()}"


@router.get("/", response_model=list[ProductSearchResult])
@limiter.limit("30/minute")
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100),
    category_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Searches product names within a single category, across all shops in
    that category — matching the product design ("search inside any
    category and get the product you want from many shops").
    """
    try:
        category_result = await db.execute(select(Category).where(Category.id == category_id))
        if category_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{category_id}' does not exist.",
            )
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Failed to validate category for search: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not process this search right now. Please try again.",
        )

    cache_key = _search_cache_key(q, category_id)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        results = await search_products(query=q, category_id=category_id)
    except Exception as e:
        logger.error(f"Search failed for query='{q}' category_id={category_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search is temporarily unavailable. Please try again.",
        )

    await set_cached(cache_key, results, ttl_seconds=SEARCH_CACHE_TTL_SECONDS)

    return results