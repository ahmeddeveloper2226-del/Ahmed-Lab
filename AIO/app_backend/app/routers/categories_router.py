import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_admin_uid, get_current_user_id, get_db_session
from ..models.category import Category
from ..models.product import Product
from ..models.shop import Shop
from ..models.subcategory import Subcategory
from ..rate_limiter import limiter
from ..schemas.category_schemas import CategoryCreateRequest, CategoryResponse, SubcategoryResponse
from ..schemas.product_schemas import ProductResponse
from ..services.cache_service import get_cached, invalidate_cached, set_cached

logger = logging.getLogger("wasla.categories")

router = APIRouter()

CATEGORIES_CACHE_KEY = "categories:all"


@router.get("/", response_model=list[CategoryResponse])
@limiter.limit("60/minute")
async def get_categories(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Returns all categories. Auth required so this can never be hit without a
    valid, non-revoked Firebase token. Rate-limited generously (60/min) since
    it's a normal browsing action every screen load may trigger.
    """
    cached = await get_cached(CATEGORIES_CACHE_KEY)
    if cached is not None:
        return cached

    try:
        result = await db.execute(select(Category))
        categories = result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load categories right now. Please try again.",
        )

    response_data = [CategoryResponse.model_validate(c).model_dump() for c in categories]
    await set_cached(CATEGORIES_CACHE_KEY, response_data)

    return response_data


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_category(
    request: Request,
    payload: CategoryCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin_uid: str = Depends(get_current_admin_uid),
):
    """
    Creates a new category. Requires the `role: admin` custom claim on the
    caller's Firebase token (see dependencies.get_current_admin_uid) — a
    regular customer account is rejected with 403, by default, not by
    remembering to add a check. Rate-limited tightly (5/min) since this is
    an infrequent administrative action, not normal traffic.
    """
    try:
        category = Category(id=payload.id, name=payload.name)
        db.add(category)
        await db.commit()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with id '{payload.id}' already exists.",
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create category: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create category right now. Please try again.",
        )

    await invalidate_cached(CATEGORIES_CACHE_KEY)

    return category


def _subcategories_cache_key(category_id: str) -> str:
    return f"subcategories:by_category:{category_id}"


@router.get("/{category_id}/subcategories", response_model=list[SubcategoryResponse])
@limiter.limit("60/minute")
async def get_subcategories(
    request: Request,
    category_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Returns this category's subcategories, ordered the way they were seeded
    (sort_order), not alphabetically/insertion-order — for the pill-chip
    filter row in the app (see shops_screen.dart). Confirms the category
    itself exists first so a bad category_id gives a clean 404 instead of
    an indistinguishable empty list.
    """
    cache_key = _subcategories_cache_key(category_id)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        category_result = await db.execute(select(Category).where(Category.id == category_id))
        if category_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' does not exist.",
            )

        result = await db.execute(
            select(Subcategory)
            .where(Subcategory.category_id == category_id)
            .order_by(Subcategory.sort_order.asc())
        )
        subcategories = result.scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch subcategories for category={category_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load subcategories right now. Please try again.",
        )

    response_data = [SubcategoryResponse.model_validate(s).model_dump() for s in subcategories]
    await set_cached(cache_key, response_data)

    return response_data

def _category_fast_picks_cache_key(category_id: str, limit: int) -> str:
    return f"products:fast_picks:category:{category_id}:{limit}"


@router.get("/{category_id}/fast-picks", response_model=list[ProductResponse])
@limiter.limit("60/minute")
async def get_category_fast_picks(
    request: Request,
    category_id: str,
    limit: int = Query(30, ge=1, le=60),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    AIO Fast Picks scoped to one category — same discounted-product rail as
    products_router.get_fast_picks, but joined through Shop so only
    products from shops inside THIS category show up (the single-row
    version that sits above the shop list on the category screen).
    """
    cache_key = _category_fast_picks_cache_key(category_id, limit)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        category_result = await db.execute(select(Category).where(Category.id == category_id))
        if category_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' does not exist.",
            )

        query = (
            select(Product)
            .join(Shop, Product.shop_id == Shop.id)
            .where(Shop.category_id == category_id)
            .where(Product.sale_price.is_not(None))
            .where(Product.sale_price < Product.price)
            .order_by(Product.id.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        products = result.scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch fast picks for category={category_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load Fast Picks right now. Please try again.",
        )

    response_data = [ProductResponse.from_product(p).model_dump() for p in products]
    await set_cached(cache_key, response_data)

    return response_data
