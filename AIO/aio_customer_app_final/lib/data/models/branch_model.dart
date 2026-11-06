class ProductBranch {
  final String branchId;
  final String name;
  final String? address;
  final double lat;
  final double lng;
  final String? phone;
  final int stockQuantity;
  final bool inStock;
  final double? distanceKm;

  ProductBranch({
    required this.branchId,
    required this.name,
    this.address,
    required this.lat,
    required this.lng,
    this.phone,
    required this.stockQuantity,
    required this.inStock,
    this.distanceKm,
  });

  factory ProductBranch.fromJson(Map<String, dynamic> json) => ProductBranch(
        branchId: json['branch_id'] as String,
        name: json['name'] as String,
        address: json['address'] as String?,
        lat: (json['lat'] as num).toDouble(),
        lng: (json['lng'] as num).toDouble(),
        phone: json['phone'] as String?,
        stockQuantity: (json['stock_quantity'] as num).toInt(),
        inStock: json['in_stock'] as bool,
        distanceKm: (json['distance_km'] as num?)?.toDouble(),
      );
}

/// A single branch's delivery quote — from GET /shops/{id}/branches/
/// delivery-options — used when the customer picks WHICH branch fulfills
/// their order (spec: "the customer selects Store -> Branch"), city-wide,
/// with no branch hidden for being far away. Distinct from [ProductBranch]
/// above, which is about per-product STOCK, not delivery economics.
class BranchDeliveryOption {
  final String branchId;
  final String name;
  final String? address;
  final double lat;
  final double lng;
  final String? phone;
  final double roadDistanceKm;
  final int etaMinutes;
  final double deliveryFee;

  BranchDeliveryOption({
    required this.branchId,
    required this.name,
    this.address,
    required this.lat,
    required this.lng,
    this.phone,
    required this.roadDistanceKm,
    required this.etaMinutes,
    required this.deliveryFee,
  });

  factory BranchDeliveryOption.fromJson(Map<String, dynamic> json) => BranchDeliveryOption(
        branchId: json['branch_id'] as String,
        name: json['name'] as String,
        address: json['address'] as String?,
        lat: (json['lat'] as num).toDouble(),
        lng: (json['lng'] as num).toDouble(),
        phone: json['phone'] as String?,
        roadDistanceKm: (json['road_distance_km'] as num).toDouble(),
        etaMinutes: (json['eta_minutes'] as num).toInt(),
        deliveryFee: (json['delivery_fee'] as num).toDouble(),
      );
}
