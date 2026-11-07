"""
Periodic job: re-indexes EVERY product from Postgres into Elasticsearch.

WHY THIS EXISTS (this is the honest gap flagged back in search_router.py
and products_router.py): real-time indexing happens on product CREATION
(products_router.py calls index_product() right after creating a row), but
NOT on every possible mutation — most notably, store_panel_router.py's
stock updates DO call index_product() directly (kept in sync deliberately),
but anything else that could ever touch a product outside the normal flow
(a manual database fix, a bug, a future bulk-import tool) would leave
Elasticsearch silently out of sync with Postgres with no automatic
correction. This job is the safety net: run periodically, it guarantees
eventual consistency regardless of how a product got out of sync.

HOW TO RUN IT:
    Manually, once:
        python -m app.tasks.reindex_products

    On a schedule (recommended — e.g. every 15-30 minutes), via cron on
    Linux/your deployment platform:
        */15 * * * * cd /path/to/app_backend && python -m app.tasks.reindex_products

    Or via Cloud Run's built-in Cloud Scheduler once deployed (Phase 5) —
    the script itself doesn't care how it's invoked, it just needs to run
    as a one-shot process periodically.

This is intentionally a full re-index (every product, every run), not an
incremental "what changed since last time" — simpler to reason about
correctly, and product catalogs at this stage are small enough that a full
re-index is cheap. Revisit this if the catalog grows large enough that a
full re-index becomes slow.
"""
import asyncio
import logging

from sqlalchemy import select

from ..database import AsyncSessionLocal
from ..models.product import Product
from ..models.shop import Shop
from ..services.search_service import ensure_products_index_exists, index_product

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("wasla.reindex")


async def reindex_all_products() -> None:
    await ensure_products_index_exists()

    async with AsyncSessionLocal() as db:
        shops_result = await db.execute(select(Shop))
        shops_by_id = {s.id: s for s in shops_result.scalars().all()}

        products_result = await db.execute(select(Product))
        products = products_result.scalars().all()

        success_count = 0
        failure_count = 0

        for product in products:
            shop = shops_by_id.get(product.shop_id)
            if shop is None:
                logger.warning(
                    f"Skipping product {product.id} — its shop {product.shop_id} no longer exists."
                )
                failure_count += 1
                continue

            try:
                await index_product(product, shop)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to reindex product {product.id}: {e}")
                failure_count += 1

        logger.info(
            f"Reindex complete: {success_count} succeeded, {failure_count} failed, "
            f"{len(products)} total products."
        )


if __name__ == "__main__":
    asyncio.run(reindex_all_products())