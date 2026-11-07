import logging

from ..elasticsearch_client import es_client

logger = logging.getLogger("wasla.search")

PRODUCTS_INDEX = "products"


async def ensure_products_index_exists() -> None:
    """
    Creates the Elasticsearch index with an explicit mapping if it doesn't
    exist yet. Called once at startup (see main.py). Without an explicit
    mapping, Elasticsearch would auto-guess field types from the first
    document indexed — fine for a prototype, a real source of subtle bugs
    in production (e.g. `price` being guessed as `text` instead of `float`
    if the first indexed value ever looked unusual).
    """
    exists = await es_client.indices.exists(index=PRODUCTS_INDEX)
    if exists:
        return

    await es_client.indices.create(
        index=PRODUCTS_INDEX,
        mappings={
            "properties": {
                "shop_id": {"type": "keyword"},
                "shop_name": {"type": "text"},
                "category_id": {"type": "keyword"},
                "name": {"type": "text"},
                "price": {"type": "float"},
                "stock_quantity": {"type": "integer"},
                "in_stock": {"type": "boolean"},
            }
        },
    )
    logger.info(f"Created Elasticsearch index '{PRODUCTS_INDEX}'")


async def index_product(product, shop) -> None:
    """
    Indexes (or re-indexes) one product. Called right after a product is
    created/updated in Postgres.

    Deliberately never raises to the caller on failure — Postgres is the
    real source of truth for products; a transient Elasticsearch hiccup
    should degrade search (a product temporarily not appearing in search
    results) rather than fail the actual product creation, which already
    succeeded in Postgres by the time this runs.
    """
    try:
        await es_client.index(
            index=PRODUCTS_INDEX,
            id=product.id,
            document={
                "shop_id": product.shop_id,
                "shop_name": shop.name,
                "category_id": shop.category_id,
                "name": product.name,
                "price": float(product.price),
                "stock_quantity": product.stock_quantity,
                "in_stock": product.stock_quantity > 0,
            },
        )
    except Exception as e:
        logger.warning(f"Failed to index product {product.id} in Elasticsearch: {e}")


async def delete_product_from_index(product_id: str) -> None:
    try:
        await es_client.delete(index=PRODUCTS_INDEX, id=product_id, ignore=[404])
    except Exception as e:
        logger.warning(f"Failed to remove product {product_id} from Elasticsearch: {e}")


async def search_products(query: str, category_id: str, limit: int = 20) -> list[dict]:
    """
    Searches products by name, scoped to a single category — matching the
    product spec's "search inside any category, across many shops" design.
    """
    try:
        response = await es_client.search(
            index=PRODUCTS_INDEX,
            size=limit,
            query={
                "bool": {
                    "must": [{"match": {"name": {"query": query, "fuzziness": "AUTO"}}}],
                    "filter": [{"term": {"category_id": category_id}}],
                }
            },
        )
    except Exception as e:
        logger.error(f"Elasticsearch query failed for query='{query}' category_id={category_id}: {e}")
        raise

    return [hit["_source"] | {"id": hit["_id"]} for hit in response["hits"]["hits"]]