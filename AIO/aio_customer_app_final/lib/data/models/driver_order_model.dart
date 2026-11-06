import 'delivery_stage.dart';
export 'delivery_stage.dart';

class DriverOrderItem {
  final String productId;
  final int quantity;
  final double priceAtPurchase;

  DriverOrderItem({
    required this.productId,
    required this.quantity,
    required this.priceAtPurchase,
  });

  factory DriverOrderItem.fromJson(Map<String, dynamic> json) => DriverOrderItem(
        productId: json['product_id'],
        quantity: json['quantity'],
        priceAtPurchase: (json['price_at_purchase'] as num).toDouble(),
      );
}

class DriverOrderModel {
  final String id;
  final String checkoutGroupId;
  // All orders sharing this ID are part of the SAME delivery offer — one
  // driver, one trip, possibly several shops. Null only for orders created
  // before this field existed.
  final String? deliveryGroupId;
  final String shopId;
  final String shopName;
  final String? customerName;
  final double? shopLat;
  final double? shopLng;
  final String status;
  final String paymentStatus;
  final double total;
  final String? deliveryAddress;
  final double? deliveryLat;
  final double? deliveryLng;
  final double? distanceKm;
  final List<DriverOrderItem> items;
  final DateTime createdAt;

  // --- AIO delivery-architecture fields --------------------------------
  final DeliveryStage? deliveryStage;
  // The EXACT branch fulfilling this order (spec 2.4) — the driver's
  // real first destination, which may differ from the shop's own
  // address for shops with multiple branches. Null for shops with no
  // branches, in which case shopLat/shopLng above is the pickup point,
  // unchanged from before this feature existed.
  final String? branchId;
  final String? branchName;
  final double? branchLat;
  final double? branchLng;
  final String? branchAddress;
  final String? branchPhone;
  final int? etaMinutes;
  final int? liveEtaMinutes;
  final double? deliveryFee;
  final double? roadDistanceKm;

  /// Pickup location for this order — the branch if one is assigned,
  /// otherwise the shop's own location (today's behavior, unchanged).
  double? get pickupLat => branchLat ?? shopLat;
  double? get pickupLng => branchLng ?? shopLng;
  String get pickupName => branchName ?? shopName;

  DriverOrderModel({
    required this.id,
    required this.checkoutGroupId,
    required this.deliveryGroupId,
    required this.shopId,
    required this.shopName,
    required this.customerName,
    required this.shopLat,
    required this.shopLng,
    required this.status,
    required this.paymentStatus,
    required this.total,
    required this.deliveryAddress,
    required this.deliveryLat,
    required this.deliveryLng,
    required this.distanceKm,
    required this.items,
    required this.createdAt,
    this.deliveryStage,
    this.branchId,
    this.branchName,
    this.branchLat,
    this.branchLng,
    this.branchAddress,
    this.branchPhone,
    this.etaMinutes,
    this.liveEtaMinutes,
    this.deliveryFee,
    this.roadDistanceKm,
  });

  factory DriverOrderModel.fromJson(Map<String, dynamic> json) => DriverOrderModel(
        id: json['id'],
        checkoutGroupId: json['checkout_group_id'],
        deliveryGroupId: json['delivery_group_id'],
        shopId: json['shop_id'],
        shopName: json['shop_name'],
        customerName: json['customer_name'],
        shopLat: (json['shop_lat'] as num?)?.toDouble(),
        shopLng: (json['shop_lng'] as num?)?.toDouble(),
        status: json['status'],
        paymentStatus: json['payment_status'],
        total: (json['total'] as num).toDouble(),
        deliveryAddress: json['delivery_address'],
        deliveryLat: (json['delivery_lat'] as num?)?.toDouble(),
        deliveryLng: (json['delivery_lng'] as num?)?.toDouble(),
        distanceKm: (json['distance_km'] as num?)?.toDouble(),
        items: (json['items'] as List).map((e) => DriverOrderItem.fromJson(e)).toList(),
        createdAt: DateTime.parse(json['created_at']),
        deliveryStage: DeliveryStage.fromValue(json['delivery_stage'] as String?),
        branchId: json['branch_id'],
        branchName: json['branch_name'],
        branchLat: (json['branch_lat'] as num?)?.toDouble(),
        branchLng: (json['branch_lng'] as num?)?.toDouble(),
        branchAddress: json['branch_address'],
        branchPhone: json['branch_phone'],
        etaMinutes: (json['eta_minutes'] as num?)?.toInt(),
        liveEtaMinutes: (json['live_eta_minutes'] as num?)?.toInt(),
        deliveryFee: (json['delivery_fee'] as num?)?.toDouble(),
        roadDistanceKm: (json['road_distance_km'] as num?)?.toDouble(),
      );

  /// Whether this order is still awaiting pickup at the shop, vs already
  /// picked up and heading to the customer.
  bool get isHeadingToShop => status == 'preparing';
  bool get isHeadingToCustomer => status == 'out_for_delivery';
}
