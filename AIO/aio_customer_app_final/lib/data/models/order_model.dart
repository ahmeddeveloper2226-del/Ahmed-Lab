import 'package:json_annotation/json_annotation.dart';

part 'order_model.g.dart';

@JsonSerializable()
class OrderItemResponse {
  final String id;
  final String product_id;
  final int quantity;
  final double price_at_purchase;
  final double subtotal;

  OrderItemResponse({
    required this.id,
    required this.product_id,
    required this.quantity,
    required this.price_at_purchase,
    required this.subtotal,
  });

  factory OrderItemResponse.fromJson(Map<String, dynamic> json) =>
      _$OrderItemResponseFromJson(json);
  Map<String, dynamic> toJson() => _$OrderItemResponseToJson(this);
}

@JsonSerializable()
class OrderResponse {
  final String id;
  final String checkout_group_id;
  final String shop_id;
  final String? shop_name;
  final double? shop_lat;
  final double? shop_lng;
  final String status;
  final String payment_status;
  final double total;
  final double commission_amount;
  final String? delivery_address;
  final double? delivery_lat;
  final double? delivery_lng;
  final String? driver_name;
  final DateTime created_at;
  final List<OrderItemResponse> items;
  final bool has_review;

  // --- AIO delivery-architecture fields (spec 1.6/1.8/1.9) --------------
  final String? delivery_stage;
  final String? branch_id;
  final String? branch_name;
  final double? branch_lat;
  final double? branch_lng;
  final int? eta_minutes;
  final int? live_eta_minutes;
  final double? delivery_fee;
  final double? road_distance_km;

  OrderResponse({
    required this.id,
    required this.checkout_group_id,
    required this.shop_id,
    this.shop_name,
    this.shop_lat,
    this.shop_lng,
    required this.status,
    required this.payment_status,
    required this.total,
    required this.commission_amount,
    this.delivery_address,
    this.delivery_lat,
    this.delivery_lng,
    this.driver_name,
    required this.created_at,
    required this.items,
    this.has_review = false,
    this.delivery_stage,
    this.branch_id,
    this.branch_name,
    this.branch_lat,
    this.branch_lng,
    this.eta_minutes,
    this.live_eta_minutes,
    this.delivery_fee,
    this.road_distance_km,
  });

  /// Whether this order currently has an assigned driver — the chat/call/
  /// tracking entry points should only show up once this is true.
  bool get hasDriver => driver_name != null;
  bool get isActive => status == 'preparing' || status == 'out_for_delivery';
  bool get canBeReviewed => status == 'delivered' && !has_review;
  /// Best available pickup point for the map — the exact branch fulfilling
  /// this order (spec 1.1/2.4) when one is assigned, otherwise the shop's
  /// own location, unchanged from before branches existed.
  double? get pickupLat => branch_lat ?? shop_lat;
  double? get pickupLng => branch_lng ?? shop_lng;
  String? get pickupName => branch_name ?? shop_name;

  factory OrderResponse.fromJson(Map<String, dynamic> json) =>
      _$OrderResponseFromJson(json);
  Map<String, dynamic> toJson() => _$OrderResponseToJson(this);
}

@JsonSerializable()
class CheckoutRequest {
  final String address_id;
  final Map<String, dynamic> billing_data;
  // Customer's explicit branch choice per branch-aware shop in the cart
  // (shop_id -> branch_id), sourced from the branch delivery-options
  // picker in checkout_screen.dart. Null/omitted for shops the customer
  // didn't get a choice for (single-location shops) — the backend falls
  // back to its existing nearest-branch auto-pick for those.
  final Map<String, String>? branch_selections;

  CheckoutRequest({required this.address_id, required this.billing_data, this.branch_selections});

  factory CheckoutRequest.fromJson(Map<String, dynamic> json) =>
      _$CheckoutRequestFromJson(json);
  Map<String, dynamic> toJson() => _$CheckoutRequestToJson(this);
}

@JsonSerializable()
class CheckoutResponse {
  final String checkout_group_id;
  final String payment_url;
  final double total;

  CheckoutResponse({
    required this.checkout_group_id,
    required this.payment_url,
    required this.total,
  });

  factory CheckoutResponse.fromJson(Map<String, dynamic> json) =>
      _$CheckoutResponseFromJson(json);
  Map<String, dynamic> toJson() => _$CheckoutResponseToJson(this);
}