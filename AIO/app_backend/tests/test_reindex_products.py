"""
Tests for tasks/reindex_products.py. Run with: pytest
"""
from unittest.mock import AsyncMock, MagicMock

from app.models.product import Product
from app.models.shop import Shop
from app.tasks import reindex_products


def _fake_scalars_result(items):
    scalars = MagicMock()
    scalars.all.return_value = items
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


async def test_reindex_skips_products_whose_shop_no_longer_exists(monkeypatch):
    orphaned_product = Product(id="p1", shop_id="deleted-shop", name="Ghost", price=10.0, stock_quantity=1)

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalars_result([]),  # no shops
        _fake_scalars_result([orphaned_product]),
    ]

    fake_session_cm = AsyncMock()
    fake_session_cm.__aenter__.return_value = fake_db

    monkeypatch.setattr(reindex_products, "AsyncSessionLocal", MagicMock(return_value=fake_session_cm))
    monkeypatch.setattr(reindex_products, "ensure_products_index_exists", AsyncMock())
    index_mock = AsyncMock()
    monkeypatch.setattr(reindex_products, "index_product", index_mock)

    await reindex_products.reindex_all_products()

    index_mock.assert_not_called()


async def test_reindex_indexes_every_product_with_its_shop(monkeypatch):
    shop = Shop(id="s1", category_id="c1", name="Koshary El Tahrir", rating=4.7)
    product = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=5)

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalars_result([shop]),
        _fake_scalars_result([product]),
    ]

    fake_session_cm = AsyncMock()
    fake_session_cm.__aenter__.return_value = fake_db

    monkeypatch.setattr(reindex_products, "AsyncSessionLocal", MagicMock(return_value=fake_session_cm))
    monkeypatch.setattr(reindex_products, "ensure_products_index_exists", AsyncMock())
    index_mock = AsyncMock()
    monkeypatch.setattr(reindex_products, "index_product", index_mock)

    await reindex_products.reindex_all_products()

    index_mock.assert_called_once_with(product, shop)


async def test_reindex_continues_after_one_product_fails(monkeypatch):
    shop = Shop(id="s1", category_id="c1", name="Koshary El Tahrir", rating=4.7)
    product_a = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=5)
    product_b = Product(id="p2", shop_id="s1", name="Foul", price=25.0, stock_quantity=5)

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalars_result([shop]),
        _fake_scalars_result([product_a, product_b]),
    ]

    fake_session_cm = AsyncMock()
    fake_session_cm.__aenter__.return_value = fake_db

    monkeypatch.setattr(reindex_products, "AsyncSessionLocal", MagicMock(return_value=fake_session_cm))
    monkeypatch.setattr(reindex_products, "ensure_products_index_exists", AsyncMock())

    index_mock = AsyncMock(side_effect=[Exception("ES write failed"), None])
    monkeypatch.setattr(reindex_products, "index_product", index_mock)

    await reindex_products.reindex_all_products()

    assert index_mock.call_count == 2