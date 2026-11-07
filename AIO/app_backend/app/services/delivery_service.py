"""
The backend brain of the AIO delivery architecture (see the spec doc:
"AIO — New Delivery System Implementation").

This module is the SINGLE place that:
  1. Estimates a road route (distance + travel time) between two points.
  2. Turns that into a customer-facing ETA (checkout-time AND live).
  3. Prices the delivery fee for a given branch/customer pair.
  4. Decides which provider (AIO driver / store driver / 3PL) should carry
     a delivery, given availability and cost.
  5. Validates DeliveryStage transitions, so no router/worker can push an
     order into an invalid stage by hand.

Nothing else in the codebase should reimplement any of these five things —
route/ETA/fee/provider logic living in one importable module (instead of
scattered across driver_router.py, checkout_router.py, order_service.py)
is what makes "recalculate ETA when X changes" (spec 1.3) tractable instead
of a game of find-every-copy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from ..config import settings
from ..models.delivery import (
    DeliveryStage,
    DeliveryProvider,
    DELIVERY_STAGE_HAPPY_PATH,
    DELIVERY_TERMINAL_STAGES,
    DELIVERY_RECOVERABLE_EXCEPTIONS,
)
from .geo_utils import haversine_km

logger = logging.getLogger("wasla.delivery")


# ---------------------------------------------------------------------------
# 1 & 2. Route + ETA estimation
# ---------------------------------------------------------------------------

@dataclass
class RouteEstimate:
    distance_km: float
    travel_minutes: float


def estimate_route(lat1: float, lng1: float, lat2: float, lng2: float) -> RouteEstimate:
    """
    Actual road distance/time between two points.

    Deliberately isolated behind this one function so swapping
    settings.routing_provider from "haversine" to a real road-routing API
    (Google Distance Matrix, OSRM, Mapbox) is a change IN THIS FUNCTION
    ONLY — every caller (ETA calc, fee calc, driver job payload) already
    consumes a RouteEstimate and doesn't care how it was produced.

    The "haversine" branch is NOT real road routing — it's a same-shape
    fallback (straight-line distance * a road-network fudge factor) so the
    rest of the system can be built and tested today. Before launch, this
    should be pointed at a real routing provider; shipping the haversine
    fallback as the ONLY implementation means ETAs will systematically
    undercount actual Cairo travel time, which is worse than no promise.
    """
    if settings.routing_provider == "haversine":
        straight_km = haversine_km(lat1, lng1, lat2, lng2)
        distance_km = round(straight_km * settings.haversine_road_factor, 2)
        travel_minutes = (distance_km / settings.fallback_avg_speed_kmh) * 60.0
        return RouteEstimate(distance_km=distance_km, travel_minutes=round(travel_minutes, 1))

    # Placeholder for real providers — raising rather than silently falling
    # back to haversine, so misconfiguration (a typo'd provider name) is
    # loud in staging instead of quietly shipping wrong ETAs to production.
    raise NotImplementedError(
        f"routing_provider={settings.routing_provider!r} is not wired up yet. "
        f"Implement the Google/OSRM call here and return a RouteEstimate; "
        f"until then set routing_provider='haversine' in config."
    )


def estimate_checkout_eta_minutes(
    *,
    branch_prep_minutes: int,
    branch_lat: float,
    branch_lng: float,
    customer_lat: float,
    customer_lng: float,
) -> tuple[int, float]:
    """
    Pre-checkout ETA for a candidate branch (spec 1.3):

        ETA = branch_prep_time + driver_to_branch + branch_to_customer + pickup_time + safety_buffer

    No driver is assigned yet at this point, so driver→branch uses the
    configured assumption rather than a real driver location — this gets
    replaced by the real figure the moment a driver is actually assigned
    (see recalculate_live_eta below).

    Returns (eta_minutes, road_distance_km) — the distance is branch→customer
    only (what's shown to the customer and used for fee calculation), not
    the driver's current position.
    """
    route = estimate_route(branch_lat, branch_lng, customer_lat, customer_lng)
    total_minutes = (
        branch_prep_minutes
        + settings.assumed_driver_to_branch_minutes
        + route.travel_minutes
        + settings.delivery_safety_buffer_minutes
    )
    return round(total_minutes), route.distance_km


def recalculate_live_eta_minutes(
    *,
    driver_lat: float,
    driver_lng: float,
    destination_lat: float,
    destination_lng: float,
    stage: DeliveryStage,
    branch_prep_minutes: int = 0,
) -> int:
    """
    Dynamic ETA once a driver exists (spec 1.9 / 2.8): recomputed from the
    driver's CURRENT location, not the checkout-time snapshot. Called on
    every driver location ping while stage is one of the "actively en
    route" stages — see tracking_ws_router.py / driver_router.update_location.

    Before pickup, remaining prep time still counts; after pickup it's pure
    travel time to the customer.
    """
    route = estimate_route(driver_lat, driver_lng, destination_lat, destination_lng)
    remaining_prep = branch_prep_minutes if stage in (
        DeliveryStage.driver_assigned,
        DeliveryStage.going_to_branch,
        DeliveryStage.arrived_at_branch,
        DeliveryStage.waiting_for_order,
    ) else 0
    total = remaining_prep + route.travel_minutes + settings.delivery_safety_buffer_minutes
    return round(total)


# ---------------------------------------------------------------------------
# 3. Delivery fee
# ---------------------------------------------------------------------------

def calculate_delivery_fee(road_distance_km: float) -> float:
    """
    base + (per_km * distance), floored at a minimum. See spec 1.4 — this
    is deliberately a simple, transparent formula rather than a black-box
    model, since the fee shown at checkout must exactly match what's
    charged (no surprise re-pricing between quote and payment).
    """
    fee = settings.base_delivery_fee + settings.per_km_delivery_fee * road_distance_km
    return round(max(fee, settings.minimum_delivery_fee), 2)


# ---------------------------------------------------------------------------
# 4. Provider selection
# ---------------------------------------------------------------------------

@dataclass
class ProviderCandidate:
    provider_type: DeliveryProvider
    is_available: bool
    estimated_cost: float
    estimated_minutes: float
    reliability_score: float = 1.0  # 0..1, historical on-time/completion rate


def select_provider(candidates: list[ProviderCandidate]) -> ProviderCandidate | None:
    """
    Picks the best available provider for a delivery (spec 1.7 / "backend
    should select the most appropriate provider according to configurable
    rules"). Only AVAILABLE candidates are considered; ranking is by a
    simple weighted score of cost, speed, and reliability rather than cost
    alone, so a slightly cheaper-but-unreliable 3PL doesn't automatically
    beat a slightly pricier, more reliable AIO driver.

    This is intentionally a pure function over caller-supplied candidates
    — it does NOT query the database itself — so the caller (a router or
    worker) controls what "availability" means for AIO drivers vs. store
    drivers vs. a 3PL API integration, all of which have very different
    real data sources.
    """
    available = [c for c in candidates if c.is_available]
    if not available:
        return None

    def score(c: ProviderCandidate) -> float:
        # Lower cost and lower time are better, so invert them into a
        # 0..1-ish "goodness" before weighting. Guards against division by
        # zero for a free/instant candidate (shouldn't happen, but a bad
        # score is safer than a crash mid-checkout).
        cost_component = 1.0 / (1.0 + max(c.estimated_cost, 0.0))
        time_component = 1.0 / (1.0 + max(c.estimated_minutes, 0.0))
        return (0.4 * cost_component) + (0.3 * time_component) + (0.3 * c.reliability_score)

    return max(available, key=score)


# ---------------------------------------------------------------------------
# 5. Stage transition validation
# ---------------------------------------------------------------------------

def _happy_path_index(stage: DeliveryStage) -> int | None:
    try:
        return DELIVERY_STAGE_HAPPY_PATH.index(stage)
    except ValueError:
        return None


def is_valid_transition(current: DeliveryStage | None, new: DeliveryStage) -> bool:
    """
    Rules:
      - From None (never tracked yet), only order_created is valid.
      - Terminal stages (delivered, cancelled) never transition further.
      - Along the happy path, only forward moves are allowed — no skipping
        backward, but skipping FORWARD is allowed (e.g. a shop with no
        branch-inventory step can jump branch_validated -> delivery_validated)
        since not every order type hits every stage.
      - Any non-terminal stage may move into `cancelled` at any time (a
        customer or ops can cancel mid-flow).
      - The recoverable exceptions (branch_delay, driver_rejected,
        provider_failed, customer_unavailable) may occur from any active
        stage, and may transition back into the NEXT happy-path stage
        after the point they interrupted (i.e. recovering resumes forward,
        it doesn't rewind).
    """
    if current is None:
        return new == DeliveryStage.order_created

    if current in DELIVERY_TERMINAL_STAGES:
        return False

    if new == DeliveryStage.cancelled:
        return True

    if new == DeliveryStage.inventory_unavailable:
        return current in (DeliveryStage.order_created, DeliveryStage.branch_validated)

    if new in DELIVERY_RECOVERABLE_EXCEPTIONS:
        # Can only enter an exception state from an active (non-exception)
        # stage that's actually "in flight" for that kind of problem.
        return current not in DELIVERY_RECOVERABLE_EXCEPTIONS

    current_idx = _happy_path_index(current)
    new_idx = _happy_path_index(new)

    if current_idx is not None and new_idx is not None:
        return new_idx > current_idx

    if current in DELIVERY_RECOVERABLE_EXCEPTIONS and new_idx is not None:
        # Recovering from an exception resumes forward progress.
        return True

    return False


def assert_valid_transition(current: DeliveryStage | None, new: DeliveryStage) -> None:
    if not is_valid_transition(current, new):
        current_label = current.value if current else "None"
        raise ValueError(f"Invalid delivery stage transition: {current_label} -> {new.value}")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
