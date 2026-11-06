/// Mirrors app/models/delivery.py's DeliveryStage on the backend — the
/// granular AIO lifecycle, kept separate from the coarser [DriverOrderModel.status]
/// (pending/preparing/out_for_delivery/delivered/cancelled) for the same
/// reason the backend keeps them separate: status drives payment/store-panel
/// logic; stage drives this app's step-by-step delivery UI.
enum DeliveryStage {
  orderCreated('order_created'),
  branchValidated('branch_validated'),
  inventoryValidated('inventory_validated'),
  deliveryValidated('delivery_validated'),
  fulfillmentSelected('fulfillment_selected'),
  providerSelected('provider_selected'),
  driverAssigned('driver_assigned'),
  goingToBranch('going_to_branch'),
  arrivedAtBranch('arrived_at_branch'),
  waitingForOrder('waiting_for_order'),
  pickedUp('picked_up'),
  inTransit('in_transit'),
  arrivedAtCustomer('arrived_at_customer'),
  delivered('delivered'),
  cancelled('cancelled'),
  failedDelivery('failed_delivery'),
  customerUnavailable('customer_unavailable'),
  branchDelay('branch_delay'),
  driverRejected('driver_rejected'),
  providerFailed('provider_failed'),
  inventoryUnavailable('inventory_unavailable');

  final String value;
  const DeliveryStage(this.value);

  static DeliveryStage? fromValue(String? value) {
    if (value == null) return null;
    for (final stage in DeliveryStage.values) {
      if (stage.value == value) return stage;
    }
    return null;
  }

  /// The stage this order moves to when the driver taps "Next" in the
  /// step-by-step UI, following the happy path from the spec. Null once
  /// there's no further forward step (delivered, or a stage this UI
  /// doesn't drive forward from, like the pre-assignment stages that
  /// happen automatically before a driver ever sees the order).
  DeliveryStage? get nextHappyPathStage => switch (this) {
        DeliveryStage.driverAssigned => DeliveryStage.goingToBranch,
        DeliveryStage.goingToBranch => DeliveryStage.arrivedAtBranch,
        DeliveryStage.arrivedAtBranch => DeliveryStage.waitingForOrder,
        DeliveryStage.waitingForOrder => DeliveryStage.pickedUp,
        DeliveryStage.pickedUp => DeliveryStage.inTransit,
        DeliveryStage.inTransit => DeliveryStage.arrivedAtCustomer,
        DeliveryStage.arrivedAtCustomer => DeliveryStage.delivered,
        _ => null,
      };

  /// Arabic label for the driver app's UI.
  String get arabicLabel => switch (this) {
        DeliveryStage.orderCreated => 'تم إنشاء الطلب',
        DeliveryStage.branchValidated => 'تم تأكيد الفرع',
        DeliveryStage.inventoryValidated => 'تم تأكيد توفر المنتجات',
        DeliveryStage.deliveryValidated => 'تم تأكيد التوصيل',
        DeliveryStage.fulfillmentSelected => 'جاري التجهيز',
        DeliveryStage.providerSelected => 'تم اختيار مزود التوصيل',
        DeliveryStage.driverAssigned => 'تم تعيين السائق',
        DeliveryStage.goingToBranch => 'في الطريق إلى الفرع',
        DeliveryStage.arrivedAtBranch => 'وصل إلى الفرع',
        DeliveryStage.waitingForOrder => 'في انتظار الطلب',
        DeliveryStage.pickedUp => 'تم استلام الطلب',
        DeliveryStage.inTransit => 'في الطريق إلى العميل',
        DeliveryStage.arrivedAtCustomer => 'وصل إلى العميل',
        DeliveryStage.delivered => 'تم التوصيل',
        DeliveryStage.cancelled => 'ملغي',
        DeliveryStage.failedDelivery => 'فشل التوصيل',
        DeliveryStage.customerUnavailable => 'العميل غير متاح',
        DeliveryStage.branchDelay => 'تأخير من الفرع',
        DeliveryStage.driverRejected => 'تم رفض الطلب',
        DeliveryStage.providerFailed => 'فشل مزود التوصيل',
        DeliveryStage.inventoryUnavailable => 'المنتج غير متوفر',
      };
}
