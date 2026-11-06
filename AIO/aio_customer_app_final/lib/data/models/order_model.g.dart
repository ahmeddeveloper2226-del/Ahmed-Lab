// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'order_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

OrderItemResponse _$OrderItemResponseFromJson(Map<String, dynamic> json) =>
    OrderItemResponse(
      id: json['id'] as String,
      product_id: json['product_id'] as String,
      quantity: (json['quantity'] as num).toInt(),
      price_at_purchase: (json['price_at_purchase'] as num).toDouble(),
      subtotal: (json['subtotal'] as num).toDouble(),
    );

Map<String, dynamic> _$OrderItemResponseToJson(OrderItemResponse instance) =>
    <String, dynamic>{
      'id': instance.id,
      'product_id': instance.product_id,
      'quantity': instance.quantity,
      'price_at_purchase': instance.price_at_purchase,
      'subtotal': instance.subtotal,
    };

OrderResponse _$OrderResponseFromJson(Map<String, dynamic> json) =>
    OrderResponse(
      id: json['id'] as String,
      checkout_group_id: json['checkout_group_id'] as String,
      shop_id: json['shop_id'] as String,
      shop_name: json['shop_name'] as String?,
      shop_lat: (json['shop_lat'] as num?)?.toDouble(),
      shop_lng: (json['shop_lng'] as num?)?.toDouble(),
      status: json['status'] as String,
      payment_status: json['payment_status'] as String,
      total: (json['total'] as num).toDouble(),
      commission_amount: (json['commission_amount'] as num).toDouble(),
      delivery_address: json['delivery_address'] as String?,
      delivery_lat: (json['delivery_lat'] as num?)?.toDouble(),
      delivery_lng: (json['delivery_lng'] as num?)?.toDouble(),
      driver_name: json['driver_name'] as String?,
      created_at: DateTime.parse(json['created_at'] as String),
      items: (json['items'] as List<dynamic>)
          .map((e) => OrderItemResponse.fromJson(e as Map<String, dynamic>))
          .toList(),
      has_review: json['has_review'] as bool? ?? false,
      delivery_stage: json['delivery_stage'] as String?,
      branch_id: json['branch_id'] as String?,
      branch_name: json['branch_name'] as String?,
      branch_lat: (json['branch_lat'] as num?)?.toDouble(),
      branch_lng: (json['branch_lng'] as num?)?.toDouble(),
      eta_minutes: (json['eta_minutes'] as num?)?.toInt(),
      live_eta_minutes: (json['live_eta_minutes'] as num?)?.toInt(),
      delivery_fee: (json['delivery_fee'] as num?)?.toDouble(),
      road_distance_km: (json['road_distance_km'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$OrderResponseToJson(OrderResponse instance) =>
    <String, dynamic>{
      'id': instance.id,
      'checkout_group_id': instance.checkout_group_id,
      'shop_id': instance.shop_id,
      'shop_name': instance.shop_name,
      'shop_lat': instance.shop_lat,
      'shop_lng': instance.shop_lng,
      'status': instance.status,
      'payment_status': instance.payment_status,
      'total': instance.total,
      'commission_amount': instance.commission_amount,
      'delivery_address': instance.delivery_address,
      'delivery_lat': instance.delivery_lat,
      'delivery_lng': instance.delivery_lng,
      'driver_name': instance.driver_name,
      'created_at': instance.created_at.toIso8601String(),
      'items': instance.items,
      'has_review': instance.has_review,
      'delivery_stage': instance.delivery_stage,
      'branch_id': instance.branch_id,
      'branch_name': instance.branch_name,
      'branch_lat': instance.branch_lat,
      'branch_lng': instance.branch_lng,
      'eta_minutes': instance.eta_minutes,
      'live_eta_minutes': instance.live_eta_minutes,
      'delivery_fee': instance.delivery_fee,
      'road_distance_km': instance.road_distance_km,
    };

CheckoutRequest _$CheckoutRequestFromJson(Map<String, dynamic> json) =>
    CheckoutRequest(
      address_id: json['address_id'] as String,
      billing_data: json['billing_data'] as Map<String, dynamic>,
      branch_selections: (json['branch_selections'] as Map<String, dynamic>?)
          ?.map((k, e) => MapEntry(k, e as String)),
    );

Map<String, dynamic> _$CheckoutRequestToJson(CheckoutRequest instance) =>
    <String, dynamic>{
      'address_id': instance.address_id,
      'billing_data': instance.billing_data,
      if (instance.branch_selections != null)
        'branch_selections': instance.branch_selections,
    };

CheckoutResponse _$CheckoutResponseFromJson(Map<String, dynamic> json) =>
    CheckoutResponse(
      checkout_group_id: json['checkout_group_id'] as String,
      payment_url: json['payment_url'] as String,
      total: (json['total'] as num).toDouble(),
    );

Map<String, dynamic> _$CheckoutResponseToJson(CheckoutResponse instance) =>
    <String, dynamic>{
      'checkout_group_id': instance.checkout_group_id,
      'payment_url': instance.payment_url,
      'total': instance.total,
    };