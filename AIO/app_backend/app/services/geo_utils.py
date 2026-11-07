"""Shared geo helpers — used by both driver_router.py (manual accept flow)
and workers/driver_assignment_worker.py (auto-assignment), so both paths
compute distance identically. Previously this was duplicated inline in
driver_router.py only; the worker had no distance-based logic at all."""

import math


def cluster_shops_by_zone(shops, radius_km):
    """
    Groups shop-orders from a single checkout into delivery zones, so shops
    near each other ship as ONE delivery (one driver, one trip) and shops
    far apart ship as separate deliveries.

    `shops` is a list of (order_id, lat, lng) — one entry per shop-order in
    the checkout. Returns a list of clusters, each a list of order_ids.

    Chain clustering: two shops end up in the same zone if there's a CHAIN
    of shops connecting them where each consecutive pair is within
    radius_km — e.g. shop A and shop C can end up together even if A-C
    alone exceeds radius_km, as long as some shop B is within radius_km of
    both. This mirrors how a real delivery zone works (a driver hopping
    A -> B -> C where each hop is short) instead of an arbitrary
    "closest to whichever shop came first" split.

    Union-find over all pairs within radius_km — O(n^2), fine since n is the
    shop count in ONE checkout (realistically single digits).
    """
    n = len(shops)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            _, lat_i, lng_i = shops[i]
            _, lat_j, lng_j = shops[j]
            if haversine_km(lat_i, lng_i, lat_j, lng_j) <= radius_km:
                union(i, j)

    groups = {}
    for i, (order_id, _, _) in enumerate(shops):
        root = find(i)
        groups.setdefault(root, []).append(order_id)

    return list(groups.values())


def centroid(points):
    """Arithmetic-mean centroid — fine at delivery-zone scale (a few km)."""
    lat = sum(p[0] for p in points) / len(points)
    lng = sum(p[1] for p in points) / len(points)
    return lat, lng


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    r = 6371.0  # Earth's radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))