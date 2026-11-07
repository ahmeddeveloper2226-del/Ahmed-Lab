"""
The AIO delivery lifecycle — additive to models/order.py's existing
OrderStatus (pending/preparing/out_for_delivery/delivered/cancelled).

WHY A SEPARATE ENUM INSTEAD OF EXTENDING OrderStatus:
OrderStatus already drives payment_webhook_router, store_panel_router, and
the customer-facing order list — all launching soon. Widening it to ~20
values right before launch means re-auditing every `if order.status ==`
across the codebase under time pressure, which is exactly how a delivery
bug ships to production. Instead, DeliveryStage is a parallel, more
granular field (Order.delivery_stage) that tracks the operational
handoff — branch validation, provider selection, driver-to-branch,
pickup, branch-to-customer — while OrderStatus keeps meaning what it
always meant to payment/store code. The two are kept in sync at the
handful of points that matter (see services/delivery_service.py), not
duplicated everywhere.
"""
import enum


class DeliveryStage(enum.Enum):
    order_created = "order_created"
    branch_validated = "branch_validated"
    inventory_validated = "inventory_validated"
    delivery_validated = "delivery_validated"
    fulfillment_selected = "fulfillment_selected"
    provider_selected = "provider_selected"
    driver_assigned = "driver_assigned"
    going_to_branch = "going_to_branch"
    arrived_at_branch = "arrived_at_branch"
    waiting_for_order = "waiting_for_order"
    picked_up = "picked_up"
    in_transit = "in_transit"
    arrived_at_customer = "arrived_at_customer"
    delivered = "delivered"

    # Exception states
    cancelled = "cancelled"
    failed_delivery = "failed_delivery"
    customer_unavailable = "customer_unavailable"
    branch_delay = "branch_delay"
    driver_rejected = "driver_rejected"
    provider_failed = "provider_failed"
    inventory_unavailable = "inventory_unavailable"


# Ordered "happy path" used for two things: (1) validating that a stage
# transition is a legitimate forward step, and (2) letting the Customer
# App render a progress bar without hardcoding the order itself.
DELIVERY_STAGE_HAPPY_PATH: list[DeliveryStage] = [
    DeliveryStage.order_created,
    DeliveryStage.branch_validated,
    DeliveryStage.inventory_validated,
    DeliveryStage.delivery_validated,
    DeliveryStage.fulfillment_selected,
    DeliveryStage.provider_selected,
    DeliveryStage.driver_assigned,
    DeliveryStage.going_to_branch,
    DeliveryStage.arrived_at_branch,
    DeliveryStage.waiting_for_order,
    DeliveryStage.picked_up,
    DeliveryStage.in_transit,
    DeliveryStage.arrived_at_customer,
    DeliveryStage.delivered,
]

# Terminal stages — once here, no further transition is valid (a new
# delivery attempt means a new Order/re-dispatch, not resurrecting this one).
DELIVERY_TERMINAL_STAGES: frozenset[DeliveryStage] = frozenset({
    DeliveryStage.delivered,
    DeliveryStage.cancelled,
})

# Stages a customer, driver, or system-monitor might reasonably recover
# from without cancelling the whole order (e.g. branch_delay can resolve
# back into the happy path; failed_delivery can be retried by re-offering
# to a driver). These are exposed so delivery_service.py's transition
# table doesn't have to be re-derived by hand.
DELIVERY_RECOVERABLE_EXCEPTIONS: frozenset[DeliveryStage] = frozenset({
    DeliveryStage.branch_delay,
    DeliveryStage.driver_rejected,
    DeliveryStage.provider_failed,
    DeliveryStage.customer_unavailable,
})


class DeliveryProvider(enum.Enum):
    """
    Who is physically carrying out this delivery. AIO never operates a
    hub/warehouse — this only decides which fleet's driver picks up from
    the branch, not where the order is fulfilled from.
    """
    aio_driver = "aio_driver"
    store_driver = "store_driver"
    third_party = "third_party"  # 3PL


class DeliveryFailureReason(enum.Enum):
    customer_unavailable = "customer_unavailable"
    wrong_address = "wrong_address"
    customer_refused = "customer_refused"
    driver_issue = "driver_issue"
    other = "other"
