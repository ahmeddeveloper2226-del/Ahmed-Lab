"""
Admin-only endpoints for managing drivers (the "admin panel" backend).

This is backend-only, as requested — there's no admin website UI here, just
the REST API a local admin panel (admin_panel/index.html) calls. Endpoints
are protected by a simple shared password check (see
dependencies.verify_admin_panel_secret) — deliberately not Firebase auth,
appropriate for a single local admin, not for a publicly-exposed multi-user
panel.

Why drivers are created here instead of a self-serve signup:
Per the product decision, every driver is onboarded after an in-person
interview, and the admin creates their account on the spot. There is no
public "become a driver" endpoint — that's intentional, not an oversight.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from firebase_admin import auth as firebase_auth
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from ..dependencies import get_db_session, verify_admin_panel_secret
from ..models.category import Category
from ..models.driver import Driver
from ..models.order import Order, OrderStatus
from ..models.product import Product
from ..models.shop import Shop
from ..models.subcategory import Subcategory
from ..models.user import User
from ..services.cache_service import invalidate_cached
from ..services.password_service import hash_password
from ..services.search_service import delete_product_from_index, index_product
from ..schemas.admin_schemas import (
    AdminCategoryResponse,
    AdminOrderResponse,
    AdminProductCreateRequest,
    AdminProductUpdateRequest,
    AdminShopCreateRequest,
    AdminShopResponse,
    AdminShopUpdateRequest,
    AdminSubcategoryResponse,
    CreateDriverRequest,
    DriverAdminResponse,
    UpdateDriverActiveRequest,
)
from ..schemas.product_schemas import ProductResponse

router = APIRouter()
logger = logging.getLogger("wasla.admin")

_ACTIVE_STATUSES = (OrderStatus.preparing, OrderStatus.out_for_delivery)


# ---------------------------------------------------------------------------
# POST /admin/drivers — onboard a new driver
# ---------------------------------------------------------------------------

@router.post("/drivers", response_model=DriverAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_driver(
    payload: CreateDriverRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    """
    Creates a driver account: a Firebase user (phone number only, no
    password — this account is never meant to sign in via Firebase's own
    phone-OTP flow, only via POST /driver/auth/login), the role="driver"
    custom claim, and the linked Postgres User + Driver rows.
    """
    # Check for an existing account with this phone number up front, so we
    # fail with a clean 409 instead of a partially-created Firebase user
    # followed by a Postgres unique-constraint crash.
    existing = await db.execute(select(User).where(User.phone_number == payload.phone_number))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists.",
        )

    try:
        firebase_user = firebase_auth.create_user(
            phone_number=payload.phone_number,
            display_name=payload.full_name,
        )
    except firebase_auth.PhoneNumberAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A Firebase account with this phone number already exists.",
        )
    except Exception as exc:
        logger.error("Firebase user creation failed for phone=%s: %s", payload.phone_number, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create the driver's account right now. Please try again.",
        )

    try:
        firebase_auth.set_custom_user_claims(firebase_user.uid, {"role": "driver"})
    except Exception as exc:
        logger.error("Failed to set driver claim for uid=%s: %s", firebase_user.uid, exc)
        # Roll back the Firebase user so we don't leave an orphaned,
        # claim-less account behind.
        try:
            firebase_auth.delete_user(firebase_user.uid)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not finish setting up the driver's account. Please try again.",
        )

    try:
        user = User(
            id=firebase_user.uid,
            full_name=payload.full_name,
            phone_number=payload.phone_number,
        )
        db.add(user)
        await db.flush()

        driver = Driver(id=str(uuid.uuid4()), user_id=user.id, is_active=True, is_available=False)
        db.add(driver)

        await db.commit()
        await db.refresh(user)
        await db.refresh(driver)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists.",
        )
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("DB error creating driver for phone=%s: %s", payload.phone_number, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save the driver's account. Please try again.",
        )

    logger.info("Admin created driver uid=%s phone=%s", user.id, payload.phone_number)

    return DriverAdminResponse(
        driver_id=driver.id,
        user_id=user.id,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=driver.is_active,
        is_available=driver.is_available,
        current_lat=driver.current_lat,
        current_lng=driver.current_lng,
        active_order_count=0,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# GET /admin/drivers — list all drivers
# ---------------------------------------------------------------------------

@router.get("/drivers", response_model=list[DriverAdminResponse])
async def list_drivers(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    result = await db.execute(select(Driver, User).join(User, Driver.user_id == User.id))
    rows = result.all()

    # Batch-count active orders per driver rather than N+1 querying per row.
    driver_ids = [d.id for d, _ in rows]
    counts: dict[str, int] = {}
    if driver_ids:
        count_result = await db.execute(
            select(Order.driver_id, func.count(Order.id))
            .where(Order.driver_id.in_(driver_ids), Order.status.in_(_ACTIVE_STATUSES))
            .group_by(Order.driver_id)
        )
        counts = dict(count_result.all())

    return [
        DriverAdminResponse(
            driver_id=driver.id,
            user_id=user.id,
            full_name=user.full_name,
            phone_number=user.phone_number,
            is_active=driver.is_active,
            is_available=driver.is_available,
            current_lat=driver.current_lat,
            current_lng=driver.current_lng,
            active_order_count=counts.get(driver.id, 0),
            created_at=user.created_at,
        )
        for driver, user in rows
    ]


# ---------------------------------------------------------------------------
# PATCH /admin/drivers/{driver_id}/active — activate/deactivate a driver
# ---------------------------------------------------------------------------

@router.patch("/drivers/{driver_id}/active", response_model=DriverAdminResponse)
async def set_driver_active(
    driver_id: str,
    payload: UpdateDriverActiveRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    """
    Deactivating a driver blocks them from logging in or accepting new
    orders (see dependencies.get_current_driver and driver_auth_router.py),
    but deliberately does NOT touch any order already assigned to them —
    those must be completed or manually reassigned separately.
    """
    result = await db.execute(select(Driver, User).join(User, Driver.user_id == User.id).where(Driver.id == driver_id))
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found.")

    driver, user = row
    driver.is_active = payload.is_active
    if not payload.is_active:
        driver.is_available = False

    try:
        await db.commit()
        await db.refresh(driver)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("DB error updating driver active state id=%s: %s", driver_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not update driver.")

    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.driver_id == driver.id, Order.status.in_(_ACTIVE_STATUSES))
    )
    active_count = count_result.scalar_one()

    logger.info("Admin set driver=%s is_active=%s", driver_id, payload.is_active)

    return DriverAdminResponse(
        driver_id=driver.id,
        user_id=user.id,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=driver.is_active,
        is_available=driver.is_available,
        current_lat=driver.current_lat,
        current_lng=driver.current_lng,
        active_order_count=active_count,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# GET /admin/orders — platform-wide order overview
# ---------------------------------------------------------------------------

@router.get("/orders", response_model=list[AdminOrderResponse])
async def list_all_orders(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    """
    Platform-wide order visibility for the admin panel — every order,
    across every shop, not scoped to any one store or driver (contrast with
    store_panel_router.get_incoming_orders, which is deliberately scoped to
    the calling store owner's own shop only).

    Supports filtering by status and simple offset pagination — this is an
    operations/oversight view, not meant to replace the customer's own
    order-history endpoint.
    """
    DriverUser = aliased(User)

    query = (
        select(Order, Shop, User, Driver, DriverUser)
        .join(Shop, Order.shop_id == Shop.id)
        .join(User, Order.user_id == User.id)
        .outerjoin(Driver, Order.driver_id == Driver.id)
        .outerjoin(DriverUser, Driver.user_id == DriverUser.id)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status_filter is not None:
        query = query.where(Order.status == status_filter)

    try:
        result = await db.execute(query)
        rows = result.all()
    except SQLAlchemyError as exc:
        logger.error("Failed to list orders for admin overview: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load orders right now. Please try again.",
        )

    return [
        AdminOrderResponse(
            id=order.id,
            checkout_group_id=order.checkout_group_id,
            shop_id=order.shop_id,
            shop_name=shop.name,
            customer_name=customer.full_name,
            driver_name=driver_user.full_name if driver_user else None,
            status=order.status.value,
            payment_status=order.payment_status.value,
            total=float(order.total),
            commission_amount=float(order.commission_amount),
            created_at=order.created_at,
        )
        for order, shop, customer, driver, driver_user in rows
    ]


# ---------------------------------------------------------------------------
# Store panel (store_panel/index.html) — shops, products, categories
# ---------------------------------------------------------------------------
# Deliberately separate from shops_router.py / products_router.py's own
# admin-gated endpoints (those require Firebase's role="admin" claim). These
# exist so the same simple local password (verify_admin_panel_secret) used
# for driver management also covers shop/product management, keeping every
# local-operator tool behind one consistent, simple gate — while leaving the
# customer-facing GET endpoints in shops_router.py/products_router.py
# untouched, since those correctly require a real customer login.

@router.get("/categories", response_model=list[AdminCategoryResponse])
async def list_categories_for_admin(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    result = await db.execute(select(Category))
    return list(result.scalars().all())


@router.get("/categories/{category_id}/subcategories", response_model=list[AdminSubcategoryResponse])
async def list_subcategories_for_admin(
    category_id: str,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    """Feeds the store-panel's subcategory dropdown, which repopulates
    whenever the category dropdown changes (see index.html)."""
    result = await db.execute(
        select(Subcategory)
        .where(Subcategory.category_id == category_id)
        .order_by(Subcategory.sort_order.asc())
    )
    return list(result.scalars().all())


@router.get("/shops", response_model=list[AdminShopResponse])
async def list_shops_for_admin(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    result = await db.execute(
        select(Shop, Category).join(Category, Shop.category_id == Category.id)
    )
    rows = result.all()

    shop_ids = [s.id for s, _ in rows]
    counts: dict[str, int] = {}
    if shop_ids:
        count_result = await db.execute(
            select(Product.shop_id, func.count(Product.id))
            .where(Product.shop_id.in_(shop_ids))
            .group_by(Product.shop_id)
        )
        counts = dict(count_result.all())

    subcategory_ids = [s.subcategory_id for s, _ in rows if s.subcategory_id]
    subcategory_names: dict[str, str] = {}
    if subcategory_ids:
        sub_result = await db.execute(
            select(Subcategory).where(Subcategory.id.in_(subcategory_ids))
        )
        subcategory_names = {sub.id: sub.name for sub in sub_result.scalars().all()}

    return [
        AdminShopResponse(
            id=shop.id,
            category_id=shop.category_id,
            category_name=category.name,
            subcategory_id=shop.subcategory_id,
            subcategory_name=subcategory_names.get(shop.subcategory_id) if shop.subcategory_id else None,
            name=shop.name,
            description=shop.description,
            logo_url=shop.logo_url,
            rating=shop.rating,
            lat=shop.lat,
            lng=shop.lng,
            product_count=counts.get(shop.id, 0),
        )
        for shop, category in rows
    ]


async def _validate_subcategory(db: AsyncSession, subcategory_id: str | None, category_id: str) -> Subcategory | None:
    """Shared by create/update: a subcategory must belong to the shop's
    own category — prevents an "electronics" shop ending up tagged
    "بيتزا" through a stale dropdown or a hand-crafted request."""
    if subcategory_id is None:
        return None
    result = await db.execute(select(Subcategory).where(Subcategory.id == subcategory_id))
    subcategory = result.scalar_one_or_none()
    if subcategory is None or subcategory.category_id != category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subcategory '{subcategory_id}' does not belong to category '{category_id}'.",
        )
    return subcategory


@router.post("/shops", response_model=AdminShopResponse, status_code=status.HTTP_201_CREATED)
async def create_shop_for_admin(
    payload: AdminShopCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    try:
        category_result = await db.execute(select(Category).where(Category.id == payload.category_id))
        category = category_result.scalar_one_or_none()
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

        subcategory = await _validate_subcategory(db, payload.subcategory_id, payload.category_id)

        shop = Shop(
            id=str(uuid.uuid4()),
            category_id=payload.category_id,
            subcategory_id=payload.subcategory_id,
            name=payload.name,
            description=payload.description,
            logo_url=payload.logo_url,
            lat=payload.lat,
            lng=payload.lng,
            rating=0.0,
            password_hash=hash_password(payload.password),
        )
        db.add(shop)
        await db.commit()
        await db.refresh(shop)
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to create shop: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create this store right now. Please try again.",
        )

    await invalidate_cached(f"shops:by_category:{shop.category_id}")

    return AdminShopResponse(
        id=shop.id, category_id=shop.category_id, category_name=category.name,
        subcategory_id=shop.subcategory_id, subcategory_name=subcategory.name if subcategory else None,
        name=shop.name, description=shop.description, logo_url=shop.logo_url,
        rating=shop.rating, lat=shop.lat, lng=shop.lng, product_count=0,
    )


@router.patch("/shops/{shop_id}", response_model=AdminShopResponse)
async def update_shop_for_admin(
    shop_id: str,
    payload: AdminShopUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    result = await db.execute(
        select(Shop, Category).join(Category, Shop.category_id == Category.id).where(Shop.id == shop_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    shop, category = row

    update_data = payload.model_dump(exclude_unset=True)

    # Rehash rather than assign directly — "password" isn't a real Shop
    # column (password_hash is), so it must be popped before the generic
    # setattr loop below or that loop would crash on a nonexistent attribute.
    if "password" in update_data:
        raw_password = update_data.pop("password")
        if raw_password:
            shop.password_hash = hash_password(raw_password)

    # "" means "clear it" (there's no other way to distinguish "omitted" from
    # "explicitly set to null" in a PATCH body) — anything else must be a
    # real subcategory belonging to this shop's category.
    if "subcategory_id" in update_data:
        raw = update_data.pop("subcategory_id")
        if raw == "" or raw is None:
            shop.subcategory_id = None
        else:
            await _validate_subcategory(db, raw, shop.category_id)
            shop.subcategory_id = raw

    for field, value in update_data.items():
        setattr(shop, field, value)

    try:
        await db.commit()
        await db.refresh(shop)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to update shop=%s: %s", shop_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not update this store.")

    await invalidate_cached(f"shops:detail:{shop.id}")
    await invalidate_cached(f"shops:by_category:{shop.category_id}")

    count_result = await db.execute(select(func.count(Product.id)).where(Product.shop_id == shop.id))
    product_count = count_result.scalar_one()

    subcategory_name = None
    if shop.subcategory_id:
        sub_result = await db.execute(select(Subcategory).where(Subcategory.id == shop.subcategory_id))
        sub = sub_result.scalar_one_or_none()
        subcategory_name = sub.name if sub else None

    return AdminShopResponse(
        id=shop.id, category_id=shop.category_id, category_name=category.name,
        subcategory_id=shop.subcategory_id, subcategory_name=subcategory_name,
        name=shop.name, description=shop.description, logo_url=shop.logo_url,
        rating=shop.rating, lat=shop.lat, lng=shop.lng, product_count=product_count,
    )


@router.delete("/shops/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shop_for_admin(
    shop_id: str,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    """
    Hard-deletes a store. Requires its products to be deleted first (clear,
    actionable error rather than a raw FK violation) and is blocked with 409
    if the store has any order history — Order.shop_id has no ON DELETE
    cascade on purpose, so past orders remain intact even after a store
    closes. There is no way to delete a store with order history through
    this panel; that's intentional — deactivate it in the customer-facing
    listing instead of erasing its record.
    """
    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")

    count_result = await db.execute(select(func.count(Product.id)).where(Product.shop_id == shop_id))
    product_count = count_result.scalar_one()
    if product_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This store still has {product_count} product(s). Delete them first.",
        )

    category_id = shop.category_id
    try:
        await db.delete(shop)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This store has order history and cannot be deleted.",
        )
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to delete shop=%s: %s", shop_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not delete this store.")

    await invalidate_cached(f"shops:detail:{shop_id}")
    await invalidate_cached(f"shops:by_category:{category_id}")


@router.get("/shops/{shop_id}/products", response_model=list[ProductResponse])
async def list_products_for_admin(
    shop_id: str,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    result = await db.execute(select(Product).where(Product.shop_id == shop_id))
    return [ProductResponse.from_product(p) for p in result.scalars().all()]


@router.post("/shops/{shop_id}/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product_for_admin(
    shop_id: str,
    payload: AdminProductCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    shop_result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = shop_result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")

    try:
        await _validate_subcategory(db, payload.subcategory_id, shop.category_id)

        product = Product(
            id=str(uuid.uuid4()),
            shop_id=shop_id,
            subcategory_id=payload.subcategory_id,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
            price=payload.price,
            sale_price=payload.sale_price,
            stock_quantity=payload.stock_quantity,
            attributes=payload.attributes,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create this product.")
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to create product for shop=%s: %s", shop_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not create this product.")

    await invalidate_cached(f"products:by_shop:{shop_id}")
    await index_product(product, shop)

    return ProductResponse.from_product(product)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product_for_admin(
    product_id: str,
    payload: AdminProductUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    result = await db.execute(
        select(Product, Shop).join(Shop, Product.shop_id == Shop.id).where(Product.id == product_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    product, shop = row

    update_data = payload.model_dump(exclude_unset=True)

    if "subcategory_id" in update_data:
        raw = update_data.pop("subcategory_id")
        if raw == "" or raw is None:
            product.subcategory_id = None
        else:
            await _validate_subcategory(db, raw, shop.category_id)
            product.subcategory_id = raw

    for field, value in update_data.items():
        setattr(product, field, value)

    try:
        await db.commit()
        await db.refresh(product)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to update product=%s: %s", product_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not update this product.")

    await invalidate_cached(f"products:by_shop:{product.shop_id}")
    await invalidate_cached(f"products:detail:{product.id}")
    await index_product(product, shop)

    return ProductResponse.from_product(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_for_admin(
    product_id: str,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_admin_panel_secret),
):
    """
    Hard-deletes a product. Blocked with 409 if the product has ever been
    ordered — OrderItem.product_id has no ON DELETE cascade on purpose, so
    that historical orders always show what was actually bought even after
    a product is discontinued. For a product with order history, set
    stock_quantity to 0 (PATCH) instead of deleting it.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    shop_id = product.shop_id
    try:
        await db.delete(product)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product has order history and cannot be deleted. "
                "Set its stock to 0 instead to hide it from customers."
            ),
        )
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to delete product=%s: %s", product_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not delete this product.")

    await invalidate_cached(f"products:by_shop:{shop_id}")
    await invalidate_cached(f"products:detail:{product_id}")
    await delete_product_from_index(product_id)