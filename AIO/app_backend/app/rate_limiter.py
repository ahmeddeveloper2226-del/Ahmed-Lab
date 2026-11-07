from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings

# Defined in its own module (not in main.py) specifically so router files can
# import it directly without creating a circular import with main.py, which
# itself needs to import the routers to mount them.
#
# storage_uri points at the same Redis instance the rest of the app already
# uses (see redis_client.py) instead of slowapi's default in-memory counters.
# In-memory counters are per-process: run more than one uvicorn/gunicorn
# worker (or more than one container behind a load balancer) and each one
# keeps its own separate count, so a "10/minute" limit silently becomes
# "10/minute PER WORKER" — e.g. 4 workers turns it into an effective
# 40/minute. Backing it with Redis makes the counter shared and the limit
# actually mean what it says, regardless of how many processes are running.
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)