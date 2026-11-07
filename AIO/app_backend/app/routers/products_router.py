import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_admin_uid, get_current_user_id, get_db_session
from ..models.product import Product
from ..models.shop import Shop
from ..rate_limiter import limiter
from ..schemas.product_schemas import (
    CompleteLookAddToCartRequest,
    CompleteLookResponse,
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from ..services.cache_service import get_cached, invalidate_cached, set_cached
from ..services.cart_service import add_product_to_raw_cart, build_cart_response, get_raw_cart, save_raw_cart
from ..services.complete_look_service import get_complete_look
from ..services.search_service import index_product

logger = logging.getLogger("wasla.products")

router = APIRouter()


def _products_by_shop_cache_key(shop_id: str) -> str:
    return f"products:by_shop:{shop_id}"


def _product_detail_cache_key(product_id: str) -> str:
    return f"products:detail:{product_id}"


# ─────────────────────────────────────────────────────────────────────────
# Stock is deliberately kept OUT of every cached product payload.
#
# Everything else about a product (name, price, images, attributes...) only
# changes when a store owner edits their catalog — that's rare, so caching
# it for minutes is safe and is what gets the 9s → ~100ms win. Stock moves
# every time *anyone* places an order, so caching it would mean showing a
# sold-out item as buyable (or vice versa) for up to DEFAULT_TTL_SECONDS.
# That's not a staleness we can accept for something that decides whether
# a customer can actually check out.
#
# So: cache the static payload, and always read stock_quantity fresh from
# Postgres (a single indexed column, effectively free) on every request,
# merging the two right before responding. Cache hit or miss, stock is
# always current.
# ─────────────────────────────────────────────────────────────────────────


def _product_static_payload(product: Product) -> dict:
    """Everything about a product EXCEPT its live stock. Safe to cache."""
    price = float(product.price)
    sale_price = float(product.sale_price) if product.sale_price is not None else None
    is_on_sale = sale_price is not None and sale_price < price
    discount_percent = round((1 - (sale_price / price)) * 100) if is_on_sale and price > 0 else None

    return {
        "id": product.id,
        "shop_id": product.shop_id,
        "subcategory_id": product.subcategory_id,
        "name": product.name,
        "description": product.description,
        "image_url": product.image_url,
        "price": price,
        "sale_price": sale_price,
        "is_on_sale": is_on_sale,
        "discount_percent": discount_percent,
        "attributes": product.attributes,
    }


def _with_live_stock(static_payload: dict, stock_quantity: int) -> dict:
    """Merges a (possibly cached) static payload with freshly-read stock."""
    return {
        **static_payload,
        "stock_quantity": stock_quantity,
        "in_stock": stock_quantity > 0,
    }


async def _live_stock_by_id(db: AsyncSession, product_ids: list[str]) -> dict[str, int]:
    """Single cheap query for just the stock column, keyed by product id.
    Products no longer found (deleted since the static payload was cached)
    simply aren't in the result — callers default those to 0/out-of-stock."""
    if not product_ids:
        return {}
    result = await db.execute(select(Product.id, Product.stock_quantity).where(Product.id.in_(product_ids)))
    return dict(result.all())


@router.get("/shops/{shop_id}/products", response_model=list[ProductResponse])
@limiter.limit("60/minute")
async def get_products_for_shop(
    request: Request,
    shop_id: str,
    subcategory_id: str | None = Query(None, description="Filter to products tagged with this subcategory."),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Cached — but only the static part of each product (name/price/images/
    attributes/etc). stock_quantity and in_stock are never stored in the
    cache; they're read fresh from Postgres on every request and merged in
    right before responding, so this endpoint is fast AND stock is never
    stale (see the block above _product_static_payload for why).
    """
    cache_key = _products_by_shop_cache_key(shop_id)
    if subcategory_id is None:
        cached_static = await get_cached(cache_key)
        if cached_static is not None:
            try:
                stock_by_id = await _live_stock_by_id(db, [p["id"] for p in cached_static])
            except SQLAlchemyError as e:
                logger.error(f"Failed to fetch live stock for shop={shop_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not load products right now. Please try again.",
                )
            return [_with_live_stock(p, stock_by_id.get(p["id"], 0)) for p in cached_static]

    try:
        shop_result = await db.execute(select(Shop).where(Shop.id == shop_id))
        if shop_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop '{shop_id}' does not exist.",
            )

        query = select(Product).where(Product.shop_id == shop_id).where(Product.is_active.is_(True))
        if subcategory_id is not None:
            query = query.where(Product.subcategory_id == subcategory_id)
        result = await db.execute(query)
        products = result.scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch products for shop={shop_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load products right now. Please try again.",
        )

    static_payloads = [_product_static_payload(p) for p in products]
    if subcategory_id is None:
        await set_cached(cache_key, static_payloads)

    return [_with_live_stock(sp, p.stock_quantity) for sp, p in zip(static_payloads, products)]


def _fast_picks_cache_key(limit: int) -> str:
    return f"products:fast_picks:all:{limit}"


# NOTE: must stay declared BEFORE `/products/{product_id}` below — routes
# are matched in declaration order, so if `{product_id}` came first a
# request for `/products/fast-picks` would match it with
# product_id="fast-picks" instead of ever reaching this endpoint (same
# ordering trap documented in shops_router.py for `/shops/top-rated`).
@router.get("/products/fast-picks", response_model=list[ProductResponse])
@limiter.limit("60/minute")
async def get_fast_picks(
    request: Request,
    limit: int = Query(30, ge=1, le=60),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    AIO Fast Picks — discounted products across every shop and category,
    for the "exploit stagnant inventory" rail on the home screen. A
    product only qualifies once a store owner sets a sale_price lower than
    its price (see store_panel_router.py); this endpoint never guesses at
    a discount itself.
    """
    cache_key = _fast_picks_cache_key(limit)
    cached_static = await get_cached(cache_key)
    if cached_static is not None:
        try:
            stock_by_id = await _live_stock_by_id(db, [p["id"] for p in cached_static])
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch live stock for fast picks: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not load Fast Picks right now. Please try again.",
            )
        return [_with_live_stock(p, stock_by_id.get(p["id"], 0)) for p in cached_static]

    try:
        query = (
            select(Product)
            .where(Product.sale_price.is_not(None))
            .where(Product.is_active.is_(True))
            .where(Product.sale_price < Product.price)
            .order_by(Product.id.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        products = result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch fast picks: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load Fast Picks right now. Please try again.",
        )

    static_payloads = [_product_static_payload(p) for p in products]
    # Short cache only (relies on set_cached's default TTL) — same
    # reasoning as top-rated shops: no dedicated invalidation hook for
    # "some sale_price somewhere changed," and a Fast Picks rail doesn't
    # need second-by-second freshness on WHICH items are on sale. Stock
    # itself still isn't cached, so "in stock" is always live regardless.
    await set_cached(cache_key, static_payloads)

    return [_with_live_stock(sp, p.stock_quantity) for sp, p in zip(static_payloads, products)]


# NOTE: must stay above `/products/{product_id}` for the same routing-order
# reason as `/products/fast-picks` above — otherwise FastAPI would treat
# "compare" as a product_id path parameter and this would never be reached.
@router.get("/products/compare", response_model=list[ProductResponse])
@limiter.limit("30/minute")
async def compare_products(
    request: Request,
    ids: str = Query(..., description="Comma-separated product ids, 2 to 4"),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    'Compare Before Buying' (Electronics-exclusive in the app, but not
    restricted here — plain side-by-side product lookup). Takes 2-4
    product ids and returns their full ProductResponse (including
    `attributes`, which is where processor/display/battery/ram/storage/
    camera live — see constants/product_attributes.py) so the client can
    render a spec table. Order of the response follows the order ids were
    requested in, not insertion order, so columns don't jump around.
    """
    product_ids = [p.strip() for p in ids.split(",") if p.strip()]
    if len(product_ids) < 2 or len(product_ids) > 4:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "قارن بين 2 إلى 4 منتجات فقط.")

    try:
        result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products_by_id = {p.id: p for p in result.scalars().all()}
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch products for comparison: {e}")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل المقارنة الآن.")

    missing = [pid for pid in product_ids if pid not in products_by_id]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "بعض المنتجات المطلوب مقارنتها لم تعد متوفرة.")

    return [ProductResponse.from_product(products_by_id[pid]) for pid in product_ids]


@router.get("/products/{product_id}", response_model=ProductResponse)
@limiter.limit("60/minute")
async def get_product_detail(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    cache_key = _product_detail_cache_key(product_id)
    cached_static = await get_cached(cache_key)
    if cached_static is not None:
        try:
            stock_result = await db.execute(select(Product.stock_quantity).where(Product.id == product_id))
            stock_quantity = stock_result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch live stock for product {product_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not load this product right now. Please try again.",
            )
        # stock_quantity is None only if the product was deleted after this
        # cache entry was written — fall through to a normal DB fetch below
        # so that case still correctly 404s instead of serving a ghost.
        if stock_quantity is not None:
            await analytics_service.record_product_view(cached_static["shop_id"])
            return _with_live_stock(cached_static, stock_quantity)

    try:
        result = await db.execute(select(Product).where(Product.id == product_id).where(Product.is_active.is_(True)))
        product = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load this product right now. Please try again.",
        )

    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    static_payload = _product_static_payload(product)
    await set_cached(cache_key, static_payload)

    await analytics_service.record_product_view(product.shop_id)
    return _with_live_stock(static_payload, product.stock_quantity)


@router.get("/products/{product_id}/complete-look", response_model=CompleteLookResponse)
@limiter.limit("60/minute")
async def complete_the_look(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Clothes-exclusive outfit recommendations (pants/shoes/bags/watches/
    accessories) for the product being viewed. Returns an empty list for
    non-clothes products or clothes items with nothing in stock to
    complete the look with — the caller (Flutter) simply doesn't render
    the section when suggestions come back empty.
    """
    suggestions = await get_complete_look(db, product_id)
    return CompleteLookResponse(product_id=product_id, suggestions=suggestions)


@router.post("/products/complete-look/add-to-cart")
@limiter.limit("15/minute")
async def add_complete_look_to_cart(
    request: Request,
    payload: CompleteLookAddToCartRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    'Add the complete outfit to your cart with a single tap' — adds one
    unit of each given product id, skipping anything that went out of
    stock between the suggestion being shown and this tap, and returns
    the resulting cart plus which ids (if any) were skipped so the UI can
    say exactly what did/didn't make it in.
    """
    try:
        result = await db.execute(select(Product).where(Product.id.in_(payload.product_ids)))
        products = {p.id: p for p in result.scalars().all()}
    except SQLAlchemyError as e:
        logger.error(f"Failed to load products for complete-look add-to-cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذرت إضافة الأصناف الآن. حاول مرة أخرى.",
        )

    raw_cart = await get_raw_cart(uid)
    added_ids, skipped_ids = [], []
    for product_id in payload.product_ids:
        product = products.get(product_id)
        if product is None or product.stock_quantity < 1:
            skipped_ids.append(product_id)
            continue
        add_product_to_raw_cart(raw_cart, product, 1)
        added_ids.append(product.id)

    await save_raw_cart(uid, raw_cart)
    cart = await build_cart_response(db, uid, raw_cart)

    return {
        "cart": cart,
        "added_ids": added_ids,
        "skipped_ids": skipped_ids,
    }


@router.post(
    "/shops/{shop_id}/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def create_product(
    request: Request,
    shop_id: str,
    payload: ProductCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin_uid: str = Depends(get_current_admin_uid),
):
    """
    Admin-only for now, matching shop creation — real store-owner-scoped
    product management (a shop managing only ITS OWN products) belongs in
    store_panel_router.py (Phase 4), with its own role check, once that
    role actually exists. Building a half version of that permission model
    here would be worse than being explicit that it's deferred.
    """
    try:
        shop_result = await db.execute(select(Shop).where(Shop.id == shop_id))
        shop = shop_result.scalar_one_or_none()
        if shop is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shop '{shop_id}' does not exist.",
            )

        product = Product(
            id=payload.id,
            shop_id=shop_id,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
            price=payload.price,
            sale_price=payload.sale_price,
            stock_quantity=payload.stock_quantity,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
    except HTTPException:
        raise
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with id '{payload.id}' already exists.",
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create product for shop={shop_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create this product right now. Please try again.",
        )

    await invalidate_cached(_products_by_shop_cache_key(shop_id))

    # Postgres is the real source of truth and already has this product
    # committed at this point — indexing into Elasticsearch is best-effort
    # for search visibility, never allowed to fail the actual creation.
    await index_product(product, shop)

    return ProductResponse.from_product(product)


@router.patch("/products/{product_id}", response_model=ProductResponse)
@limiter.limit("20/minute")
async def update_product(
    request: Request,
    product_id: str,
    payload: ProductUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin_uid: str = Depends(get_current_admin_uid),
):
    """
    Edits an existing product's name, description, image, price, or stock.
    PATCH semantics: only fields actually included in the request body are
    changed. Admin-only here, matching create_product — store-owner-scoped
    editing of their OWN products lives in store_panel_router.py instead.
    """
    try:
        result = await db.execute(
            select(Product, Shop).join(Shop, Product.shop_id == Shop.id).where(Product.id == product_id)
        )
        row = result.first()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
        product, shop = row

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        await db.commit()
        await db.refresh(product)
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update this product right now. Please try again.",
        )

    await invalidate_cached(_product_detail_cache_key(product_id))
    await invalidate_cached(_products_by_shop_cache_key(product.shop_id))
    await index_product(product, shop)

    return ProductResponse.from_product(product)

# ─────────────────────────────────────────────────────────────────────────────
#  Branches — see app/services/branch_service.py. A shop with no branches
#  simply returns an empty list here; the Flutter app treats that as "this
#  shop is single-location," same as before branches existed at all.
# ─────────────────────────────────────────────────────────────────────────────
from ..services import branch_service  # noqa: E402
from ..services import analytics_service  # noqa: E402


@router.get("/products/{product_id}/branches")
async def get_product_branches(
    product_id: str,
    lat: float | None = None,
    lng: float | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Every branch of this product's shop, each showing whether/how much
    stock it has of THIS product — sorted nearest-with-stock first when
    lat/lng is provided. Backs both 'preview all branches' and the
    'nearest branch has it' highlight on the product detail screen.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    return await branch_service.list_branches_with_product_stock(db, product.shop_id, product_id, lat, lng)


@router.get("/shops/{shop_id}/branches/delivery-options")
async def get_branch_delivery_options(
    shop_id: str,
    lat: float,
    lng: float,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Every eligible branch for this shop, city-wide, each with its own ETA
    and delivery fee (spec sections 1.1-1.4). lat/lng is the CUSTOMER's
    location — required, since ETA/fee are meaningless without it. This is
    what the Customer App calls to let the customer actually choose a
    branch, distinct from get_product_branches above which is about stock,
    not delivery economics.

    A shop with zero branches returns an empty list — the app falls back
    to its existing single-location checkout flow, unaffected.
    """
    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found.")

    return await branch_service.list_eligible_branches_with_delivery_quote(db, shop_id, lat, lng)
