"""
Tests for order_service.py — the highest-stakes logic in the app so far.
Run with: pytest
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.product import Product
from app.services import order_service


@pytest.fixture(autouse=True)
def _no_branches_by_default(monkeypatch):
    """
    Every test below predates Branch Management and assumes a plain,
    single-location shop — order_service.has_branches would otherwise
    return a truthy MagicMock() by default (since these tests' fake_db
    doesn't distinguish .first() from .scalars()), spuriously routing
    every test through the branch-aware checkout path. Branch-specific
    behavior gets its own dedicated tests in test_branch_service.py and
    test_order_service_branches.py instead of being mixed into these.
    """
    monkeypatch.setattr(order_service.branch_service, "has_branches", AsyncMock(return_value=False))


def _fake_scalars_result(items):
    scalars = MagicMock()
    scalars.all.return_value = items
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


async def test_raises_empty_cart_error_when_cart_is_empty(monkeypatch):
    monkeypatch.setattr(order_service, "get_raw_cart", AsyncMock(return_value={}))
    fake_db = AsyncMock()

    with pytest.raises(order_service.EmptyCartError):
        await order_service.create_orders_from_cart(fake_db, "uid-1", "addr-1")


async def test_raises_insufficient_stock_before_any_writes(monkeypatch):
    product = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=2)

    monkeypatch.setattr(order_service, "get_raw_cart", AsyncMock(return_value={"p1": 5}))

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([product])

    with pytest.raises(order_service.InsufficientStockError) as exc_info:
        await order_service.create_orders_from_cart(fake_db, "uid-1", "addr-1")

    assert exc_info.value.shortages == [{"product_id": "p1", "requested": 5, "available": 2}]
    # Critical: no order/order-item was ever added, and the transaction was
    # rolled back, not committed — the whole point of checking BEFORE writing.
    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_called()
    fake_db.rollback.assert_called_once()


async def test_splits_cart_into_one_order_per_shop_with_correct_commission(monkeypatch):
    product_a = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=10)
    product_b = Product(id="p2", shop_id="s2", name="Foul", price=25.0, stock_quantity=10)

    monkeypatch.setattr(
        order_service, "get_raw_cart", AsyncMock(return_value={"p1": 2, "p2": 3})
    )
    monkeypatch.setattr(order_service, "clear_cart", AsyncMock())

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([product_a, product_b])

    result = await order_service.create_orders_from_cart(fake_db, "uid-1", "addr-1")

    assert len(result.orders) == 2

    shop_ids = {order.shop_id for order in result.orders}
    assert shop_ids == {"s1", "s2"}

    order_s1 = next(o for o in result.orders if o.shop_id == "s1")
    order_s2 = next(o for o in result.orders if o.shop_id == "s2")

    # p1: 45.0 * 2 = 90.0, commission at default 15% = 13.5
    assert order_s1.total == 90.0
    assert order_s1.commission_amount == 13.5

    # p2: 25.0 * 3 = 75.0, commission at 15% = 11.25
    assert order_s2.total == 75.0
    assert order_s2.commission_amount == 11.25

    assert result.total == 165.0

    # Both orders share the same checkout_group_id
    assert order_s1.checkout_group_id == order_s2.checkout_group_id == result.checkout_group_id

    # Stock was actually decremented, in-memory, on the locked product objects
    assert product_a.stock_quantity == 8
    assert product_b.stock_quantity == 7

    fake_db.commit.assert_called_once()


async def test_price_at_purchase_is_captured_not_a_live_reference(monkeypatch):
    product = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=10)

    monkeypatch.setattr(order_service, "get_raw_cart", AsyncMock(return_value={"p1": 1}))
    monkeypatch.setattr(order_service, "clear_cart", AsyncMock())

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([product])

    await order_service.create_orders_from_cart(fake_db, "uid-1", "addr-1")

    # Find the OrderItem that was added to the session
    order_item_calls = [
        call.args[0] for call in fake_db.add.call_args_list
        if hasattr(call.args[0], "price_at_purchase")
    ]
    assert len(order_item_calls) == 1
    assert order_item_calls[0].price_at_purchase == 45.0

    # Now change the product's live price AFTER the order was created —
    # the already-created OrderItem must be unaffected.
    product.price = 999.0
    assert order_item_calls[0].price_at_purchase == 45.0


async def test_cart_is_cleared_only_after_successful_commit(monkeypatch):
    product = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=10)

    monkeypatch.setattr(order_service, "get_raw_cart", AsyncMock(return_value={"p1": 1}))
    clear_cart_mock = AsyncMock()
    monkeypatch.setattr(order_service, "clear_cart", clear_cart_mock)

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([product])

    await order_service.create_orders_from_cart(fake_db, "uid-1", "addr-1")

    fake_db.commit.assert_called_once()
    clear_cart_mock.assert_called_once_with("uid-1")


async def test_cart_not_cleared_if_commit_fails(monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    product = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=10)

    monkeypatch.setattr(order_service, "get_raw_cart", AsyncMock(return_value={"p1": 1}))
    clear_cart_mock = AsyncMock()
    monkeypatch.setattr(order_service, "clear_cart", clear_cart_mock)

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([product])
    fake_db.commit.side_effect = SQLAlchemyError("db connection lost")

    with pytest.raises(SQLAlchemyError):
        await order_service.create_orders_from_cart(fake_db, "uid-1", "addr-1")

    fake_db.rollback.assert_called_once()
    # The cart must NOT be cleared if the order was never actually saved —
    # otherwise the customer loses their cart for nothing.
    clear_cart_mock.assert_not_called()