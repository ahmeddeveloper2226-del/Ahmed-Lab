import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key-for-pytest-only")
os.environ.setdefault("ENVIRONMENT", "development")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()