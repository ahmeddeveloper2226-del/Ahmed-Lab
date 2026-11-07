import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_admin_uid, get_current_user_id, get_db_session
from ..models.category import Category
from ..models.shop import Shop
from ..models.subcategory import Subcategory
from ..rate_limiter import limiter
from ..schemas.shop_schemas import ShopCreateRequest, ShopResponse, ShopUpdateRequest
from ..services.cache_service import get_cached, invalidate_cached, set_cached

logger = logging.getLogger("wasla.shops")

router = APIRouter()


def _shops_by_category_cache_key(category_id: str) -> str:
    return f"shops:by_category:{category_id}"


def _shop_detail_cache_key(shop_id: str) -> str:
    return f"shops:detail:{shop_id}"


@router.get("/categories/{category_id}/shops", response_model=list[ShopResponse])
@limiter.limit("60/minute")
async def get_shops_for_category(
    request: Request,
    category_id: str,
    subcategory_id: str | None = Query(None, description="Filter to shops tagged with this subcategory."),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    # The cached response is for the whole category (no filter) — a
    # subcategory-filtered request always hits the DB. Filtering happens
    # client-side often enough (small per-category shop counts) that this
    # isn't worth a second cache dimension per subcategory right now.
    cache_key = _shops_by_category_cache_key(category_id)
    if subcategory_id is None:
        cached = await get_cached(cache_key)
        if cached is not None:
            return cached

    try:
        # Confirm the category actually exists before returning an empty
        # list — an empty list for a real category (no shops yet) and an
        # empty list for a category_id that's just wrong/typo'd should be
        # distinguishable to the caller, not silently identical.
        category_result = await db.execute(select(Category).where(Category.id == category_id))
        if category_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category_id}' does not exist.",
            )

        query = select(Shop).where(Shop.category_id == category_id)
        if subcategory_id is not None:
            query = query.where(Shop.subcategory_id == subcategory_id)
        result = await db.execute(query)
        shops = result.scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch shops for category={category_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load shops right now. Please try again.",
        )

    response_data = [ShopResponse.model_validate(s).model_dump() for s in shops]
    if subcategory_id is None:
        await set_cached(cache_key, response_data)

    return response_data


def _top_rated_cache_key(category_id: str | None, limit: int) -> str:
    return f"shops:top_rated:{category_id or 'all'}:{limit}"


# NOTE: this must stay declared BEFORE get_shop_detail's `/shops/{shop_id}`
# below — Starlette matches routes in declaration order, so if `/shops/{shop_id}`
# came first, a request for `/shops/top-rated` would match it with
# shop_id="top-rated" instead of ever reaching this endpoint.
@router.get("/shops/top-rated", response_model=list[ShopResponse])
@limiter.limit("60/minute")
async def get_top_rated_shops(
    request: Request,
    category_id: str | None = Query(None, description="Filter to shops in this category only."),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Top-rated shops across the whole marketplace (or within one category,
    for the category filter chips on the customer app's home screen),
    ordered by rating descending.
    """
    cache_key = _top_rated_cache_key(category_id, limit)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        if category_id is not None:
            category_result = await db.execute(select(Category).where(Category.id == category_id))
            if category_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category '{category_id}' does not exist.",
                )

        query = select(Shop).order_by(Shop.rating.desc()).limit(limit)
        if category_id is not None:
            query = query.where(Shop.category_id == category_id)
        result = await db.execute(query)
        shops = result.scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch top-rated shops (category={category_id}): {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load top-rated shops right now. Please try again.",
        )

    response_data = [ShopResponse.model_validate(s).model_dump() for s in shops]
    # Short-lived cache only (relies on set_cached's default TTL) — shop
    # ratings don't have a dedicated invalidation hook anywhere yet, so this
    # deliberately doesn't try to track every possible category/limit
    # combination for precise invalidation. Fine for a "top rated" list,
    # which isn't expected to be second-by-second fresh anyway.
    await set_cached(cache_key, response_data)

    return response_data


@router.get("/shops/{shop_id}", response_model=ShopResponse)
@limiter.limit("60/minute")
async def get_shop_detail(
    request: Request,
    shop_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    cache_key = _shop_detail_cache_key(shop_id)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        result = await db.execute(select(Shop).where(Shop.id == shop_id))
        shop = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch shop {shop_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load this shop right now. Please try again.",
        )

    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found.")

    response_data = ShopResponse.model_validate(shop).model_dump()
    await set_cached(cache_key, response_data)

    return response_data


@router.post("/shops", response_model=ShopResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_shop(
    request: Request,
    payload: ShopCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin_uid: str = Depends(get_current_admin_uid),
):
    """
    Admin-only for now — creating a shop is an onboarding action (a real
    contract with a real store), not something any user can do. This will
    likely evolve once store_panel_router.py exists (Phase 4) to also allow
    a verified store owner to manage their OWN shop's details — but
    creating the shop record itself, the very first time, stays an admin
    action, matching how you described actually onboarding stores in our
    earlier conversation.
    """
    try:
        category_result = await db.execute(select(Category).where(Category.id == payload.category_id))
        if category_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{payload.category_id}' does not exist.",
            )

        if payload.subcategory_id is not None:
            subcategory_result = await db.execute(
                select(Subcategory).where(Subcategory.id == payload.subcategory_id)
            )
            subcategory = subcategory_result.scalar_one_or_none()
            if subcategory is None or subcategory.category_id != payload.category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Subcategory '{payload.subcategory_id}' does not belong to category '{payload.category_id}'.",
                )

        shop = Shop(
            id=payload.id,
            category_id=payload.category_id,
            subcategory_id=payload.subcategory_id,
            name=payload.name,
            description=payload.description,
            logo_url=payload.logo_url,
            lat=payload.lat,
            lng=payload.lng,
            rating=0.0,
        )
        db.add(shop)
        await db.commit()
        await db.refresh(shop)
    except HTTPException:
        raise
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Shop with id '{payload.id}' already exists.",
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create shop: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create this shop right now. Please try again.",
        )

    # Only the category's shop list is now stale — the new shop's own
    # detail cache doesn't exist yet, so there's nothing to invalidate there.
    await invalidate_cached(_shops_by_category_cache_key(payload.category_id))

    return shop


@router.patch("/shops/{shop_id}", response_model=ShopResponse)
@limiter.limit("20/minute")
async def update_shop(
    request: Request,
    shop_id: str,
    payload: ShopUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin_uid: str = Depends(get_current_admin_uid),
):
    """
    Edits an existing shop's name, description, logo, or location.
    PATCH semantics: only fields actually included in the request body are
    changed — omitted fields keep their current value.
    """
    try:
        result = await db.execute(select(Shop).where(Shop.id == shop_id))
        shop = result.scalar_one_or_none()
        if shop is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found.")

        update_data = payload.model_dump(exclude_unset=True)

        if "subcategory_id" in update_data:
            raw = update_data.pop("subcategory_id")
            if raw == "":
                shop.subcategory_id = None
            else:
                subcategory_result = await db.execute(
                    select(Subcategory).where(Subcategory.id == raw)
                )
                subcategory = subcategory_result.scalar_one_or_none()
                if subcategory is None or subcategory.category_id != shop.category_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Subcategory '{raw}' does not belong to this shop's category.",
                    )
                shop.subcategory_id = raw

        for field, value in update_data.items():
            setattr(shop, field, value)

        await db.commit()
        await db.refresh(shop)
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update shop {shop_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update this shop right now. Please try again.",
        )

    # Both the detail cache and this shop's entry in its category's list
    # are now stale.
    await invalidate_cached(_shop_detail_cache_key(shop_id))
    await invalidate_cached(_shops_by_category_cache_key(shop.category_id))

    return shop