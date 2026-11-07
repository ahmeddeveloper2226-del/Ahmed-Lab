from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from .config import settings

# The engine is the actual connection pool to Postgres — created once, reused
# for the whole lifetime of the app.
engine = create_async_engine(settings.database_url, echo=False, future=True)

# Factory for creating new database sessions (one per request).
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Every SQLAlchemy model in models/ inherits from this Base, which is how
# SQLAlchemy knows what tables exist and how to create/migrate them.
Base = declarative_base()


async def get_db():
    """
    FastAPI dependency — yields a fresh DB session per request and always
    closes it afterward, even if the request raised an error.
    Used like: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        yield session