from elasticsearch import AsyncElasticsearch

from .config import settings

# Shared Elasticsearch client — used by search_service.py to query products
# and by tasks/reindex_products.py to keep the index in sync with Postgres.
es_client = AsyncElasticsearch(hosts=[settings.elasticsearch_url])


async def check_elasticsearch_connection() -> bool:
    """Called once at startup (see main.py) to fail fast if ES is unreachable."""
    try:
        return await es_client.ping()
    except Exception as e:
        raise RuntimeError(f"Could not connect to Elasticsearch: {e}")