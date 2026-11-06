// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'product_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ProductResponse _$ProductResponseFromJson(Map<String, dynamic> json) =>
    ProductResponse(
      id: json['id'] as String,
      shop_id: json['shop_id'] as String,
      subcategory_id: json['subcategory_id'] as String?,
      name: json['name'] as String,
      price: (json['price'] as num).toDouble(),
      sale_price: (json['sale_price'] as num?)?.toDouble(),
      stock_quantity: (json['stock_quantity'] as num).toInt(),
      in_stock: json['in_stock'] as bool? ?? false,
      is_on_sale: json['is_on_sale'] as bool? ?? false,
      discount_percent: (json['discount_percent'] as num?)?.toInt(),
      image_url: json['image_url'] as String?,
      attributes: json['attributes'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$ProductResponseToJson(ProductResponse instance) =>
    <String, dynamic>{
      'id': instance.id,
      'shop_id': instance.shop_id,
      'subcategory_id': instance.subcategory_id,
      'name': instance.name,
      'price': instance.price,
      'sale_price': instance.sale_price,
      'stock_quantity': instance.stock_quantity,
      'in_stock': instance.in_stock,
      'is_on_sale': instance.is_on_sale,
      'discount_percent': instance.discount_percent,
      'image_url': instance.image_url,
      'attributes': instance.attributes,
    };

ProductCreateRequest _$ProductCreateRequestFromJson(
  Map<String, dynamic> json,
) => ProductCreateRequest(
  id: json['id'] as String,
  name: json['name'] as String,
  price: (json['price'] as num).toDouble(),
  sale_price: (json['sale_price'] as num?)?.toDouble(),
  stock_quantity: (json['stock_quantity'] as num?)?.toInt() ?? 0,
);

Map<String, dynamic> _$ProductCreateRequestToJson(
  ProductCreateRequest instance,
) => <String, dynamic>{
  'id': instance.id,
  'name': instance.name,
  'price': instance.price,
  'sale_price': instance.sale_price,
  'stock_quantity': instance.stock_quantity,
};

ProductSearchResult _$ProductSearchResultFromJson(Map<String, dynamic> json) =>
    ProductSearchResult(
      id: json['id'] as String,
      shop_id: json['shop_id'] as String,
      shop_name: json['shop_name'] as String,
      category_id: json['category_id'] as String,
      name: json['name'] as String,
      price: (json['price'] as num).toDouble(),
      stock_quantity: (json['stock_quantity'] as num).toInt(),
      in_stock: json['in_stock'] as bool,
      image_url: json['image_url'] as String?,
    );

Map<String, dynamic> _$ProductSearchResultToJson(
  ProductSearchResult instance,
) => <String, dynamic>{
  'id': instance.id,
  'shop_id': instance.shop_id,
  'shop_name': instance.shop_name,
  'category_id': instance.category_id,
  'name': instance.name,
  'price': instance.price,
  'stock_quantity': instance.stock_quantity,
  'in_stock': instance.in_stock,
  'image_url': instance.image_url,
};