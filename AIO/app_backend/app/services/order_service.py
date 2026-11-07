import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.order import Order, OrderItem, OrderStatus, PaymentStatus
from ..models.product import Product
from ..models.branch import Branch, BranchStock
from ..models.address import Address
from ..models.delivery import DeliveryStage
from .cart_service import clear_cart, get_raw_cart
from . import branch_service
from . import delivery_service

logger = logging.getLogger("wasla.orders")


class EmptyCartError(Exception):
    pass


class InsufficientStockError(Exception):
    def __init__(self, shortages: list[dict]):
        # shortages: [{"product_id": ..., "requested": ..., "available": ...}]
        self.shortages = shortages
        super().__init__("Insufficient stock for one or more items")


class OrderCreationResult:
    def __init__(self, checkout_group_id: str, orders: list[Order], total: float):
        self.checkout_group_id = checkout_group_id
        self.orders = orders
        self.total = total


async def create_orders_from_cart(
    db: AsyncSession,
    uid: str,
    address_id: str,
    branch_selections: dict[str, str] | None = None,
) -> OrderCreationResult:
    """
    The core money-handling function of the whole app. Turns the user's
    cart into one Order row per shop, atomically.

    Correctness guarantees this function is specifically designed around:

    1. STOCK RACE CONDITIONS: uses SELECT ... FOR UPDATE to lock the
       relevant Product rows for the duration of this transaction. Without
       this, two customers checking out the last unit of the same product
       at nearly the same moment could BOTH pass a naive "is there enough
       stock?" check before either one's decrement is applied — a classic,
       real race condition, not a theoretical one. Locking the rows makes
       the second transaction wait for the first to finish (and see its
       already-decremented stock) before proceeding.

    2. ATOMICITY: order creation, order-item creation, and stock
       decrements all happen in ONE transaction. If anything fails partway
       (a database error, a constraint violation), the entire transaction
       rolls back — there is no possible state where stock was decremented
       but no order exists, or vice versa.

    3. PRICE INTEGRITY: price_at_purchase is captured from the product's
       CURRENT price at checkout time and stored on the OrderItem — never
       a live reference to Product.price. If the shop changes prices
       tomorrow, this order's historical record is untouched.

    4. COMMISSION: computed and stored explicitly per order at creation
       time, from settings.commission_rate — not recomputed later, so a
       future change to the commission rate never silently alters
       historical orders.

    Raises EmptyCartError if the cart has nothing in it, or
    InsufficientStockError (with full shortage details) if ANY item in the
    cart can no longer be fully fulfilled — the whole checkout fails
    together rather than silently fulfilling some items and not others.
    """
    raw_cart = await get_raw_cart(uid)
    if not raw_cart:
        raise EmptyCartError()

    product_ids = list(raw_cart.keys())

    try:
        result = await db.execute(
            select(Product).where(Product.id.in_(product_ids)).with_for_update()
        )
        products = {p.id: p for p in result.scalars().all()}

        items_by_shop: dict[str, list[tuple[Product, int]]] = {}
        for product_id, quantity in raw_cart.items():
            product = products.get(product_id)
            if product is None:
                continue
            items_by_shop.setdefault(product.shop_id, []).append((product, quantity))

        # Branch-aware shops (see branch_service.py) check/decrement stock
        # at the BRANCH level instead of Product.stock_quantity — a shop
        # with zero branches skips all of this and behaves exactly as
        # before. Delivery address lat/lng is the reference point for
        # "nearest branch," since that's where the order needs to reach.
        address_lat, address_lng = None, None
        if any([await branch_service.has_branches(db, shop_id) for shop_id in items_by_shop]):
            addr_result = await db.execute(select(Address).where(Address.id == address_id))
            address = addr_result.scalar_one_or_none()
            address_lat = address.lat if address else None
            address_lng = address.lng if address else None

        shortages = []
        branch_assignment: dict[str, str | None] = {}  # shop_id -> branch_id
        branch_stock_locks: dict[str, BranchStock] = {}  # (branch_id, product_id) key -> locked row

        for shop_id, items in items_by_shop.items():
            shop_has_branches = await branch_service.has_branches(db, shop_id)

            if not shop_has_branches:
                for product, quantity in items:
                    if product.stock_quantity < quantity:
                        shortages.append(
                            {"product_id": product.id, "requested": quantity, "available": product.stock_quantity}
                        )
                branch_assignment[shop_id] = None
                continue

            # Branch-aware shop. If the customer explicitly picked a branch
            # for this shop (spec 1.1 — via GET .../branches/delivery-options),
            # honor that choice as-is: AIO is city-wide, so an explicit pick
            # is never second-guessed or overridden for being "too far"
            # (spec 1.2). Otherwise fall back to the previous automatic
            # nearest-fulfilling-branch behavior, unchanged.
            requirements = {p.id: qty for p, qty in items}
            chosen_branch_id = (branch_selections or {}).get(shop_id)
            if chosen_branch_id is not None:
                valid_branch_ids = {b.id for b in await branch_service.list_branches(db, shop_id)}
                if chosen_branch_id not in valid_branch_ids:
                    # Selected branch doesn't belong to (or isn't active
                    # for) this shop — don't silently substitute another
                    # branch; treat as a shortage so checkout fails loudly
                    # with a clear reason instead of fulfilling from a
                    # branch the customer didn't choose.
                    chosen_branch_id = None
                    for product, quantity in items:
                        shortages.append(
                            {"product_id": product.id, "requested": quantity, "available": 0}
                        )
                    continue
            elif address_lat is not None and address_lng is not None:
                chosen_branch_id = await branch_service.find_fulfilling_branch(
                    db, shop_id, requirements, address_lat, address_lng
                )
                if chosen_branch_id is None:
                    chosen_branch_id = await branch_service.nearest_branch_fallback(
                        db, shop_id, address_lat, address_lng
                    )
            if chosen_branch_id is None:
                # No usable branch location data at all — treat like a
                # shortage rather than silently picking a random branch.
                for product, quantity in items:
                    shortages.append(
                        {"product_id": product.id, "requested": quantity, "available": 0}
                    )
                continue

            branch_assignment[shop_id] = chosen_branch_id

            branch_stock_result = await db.execute(
                select(BranchStock)
                .where(BranchStock.branch_id == chosen_branch_id)
                .where(BranchStock.product_id.in_([p.id for p, _ in items]))
                .with_for_update()
            )
            branch_stocks = {bs.product_id: bs for bs in branch_stock_result.scalars().all()}

            for product, quantity in items:
                bs = branch_stocks.get(product.id)
                available = bs.stock_quantity if bs else 0
                if available < quantity:
                    shortages.append(
                        {"product_id": product.id, "requested": quantity, "available": available}
                    )
                elif bs is not None:
                    branch_stock_locks[f"{chosen_branch_id}:{product.id}"] = bs

        if shortages:
            raise InsufficientStockError(shortages)

        checkout_group_id = str(uuid.uuid4())
        created_orders: list[Order] = []

        # Branches selected for this checkout, needed to compute each
        # order's delivery snapshot (spec 1.6) below.
        branch_lookup: dict[str, Branch] = {}
        chosen_ids = [bid for bid in branch_assignment.values() if bid is not None]
        if chosen_ids:
            branches_result = await db.execute(select(Branch).where(Branch.id.in_(chosen_ids)))
            branch_lookup = {b.id: b for b in branches_result.scalars().all()}

        for shop_id, items in items_by_shop.items():
            subtotal = sum(float(product.price) * quantity for product, quantity in items)
            commission_amount = round(subtotal * settings.commission_rate, 2)
            chosen_branch_id = branch_assignment.get(shop_id)

            # Delivery snapshot (spec 1.6): captured NOW so historical
            # orders stay consistent even if branch data or pricing rules
            # change later. Only computed when we have both a branch and
            # the customer's coordinates — shops without branches keep
            # these fields null, exactly as before this feature existed.
            road_distance_km = eta_minutes = delivery_fee = None
            branch = branch_lookup.get(chosen_branch_id) if chosen_branch_id else None
            if branch is not None and address_lat is not None and address_lng is not None:
                eta_minutes, road_distance_km = delivery_service.estimate_checkout_eta_minutes(
                    branch_prep_minutes=15,
                    branch_lat=branch.lat,
                    branch_lng=branch.lng,
                    customer_lat=address_lat,
                    customer_lng=address_lng,
                )
                delivery_fee = delivery_service.calculate_delivery_fee(road_distance_km)

            order = Order(
                id=str(uuid.uuid4()),
                checkout_group_id=checkout_group_id,
                user_id=uid,
                shop_id=shop_id,
                branch_id=chosen_branch_id,
                status=OrderStatus.pending,
                payment_status=PaymentStatus.pending,
                total=round(subtotal, 2),
                commission_amount=commission_amount,
                delivery_address_id=address_id,
                # Stock for this order was already validated above (that's
                # why we got this far without raising InsufficientStockError),
                # so branch-assigned orders start one step further along
                # than a bare order_created.
                delivery_stage=DeliveryStage.inventory_validated if chosen_branch_id else DeliveryStage.order_created,
                road_distance_km=road_distance_km,
                eta_minutes=eta_minutes,
                delivery_fee=delivery_fee,
            )
            db.add(order)

            for product, quantity in items:
                db.add(
                    OrderItem(
                        id=str(uuid.uuid4()),
                        order_id=order.id,
                        product_id=product.id,
                        quantity=quantity,
                        price_at_purchase=float(product.price),
                    )
                )
                if chosen_branch_id is not None:
                    bs = branch_stock_locks.get(f"{chosen_branch_id}:{product.id}")
                    if bs is not None:
                        bs.stock_quantity -= quantity
                else:
                    product.stock_quantity -= quantity

            created_orders.append(order)

        await db.commit()

        for order in created_orders:
            await db.refresh(order)

    except (EmptyCartError, InsufficientStockError):
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create orders from cart for uid={uid}: {e}")
        raise

    await clear_cart(uid)

    total = round(sum(order.total for order in created_orders), 2)
    return OrderCreationResult(checkout_group_id=checkout_group_id, orders=created_orders, total=total)