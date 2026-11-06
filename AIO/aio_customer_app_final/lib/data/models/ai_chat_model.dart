class AiChoiceOption {
  final String optionId;
  final String label;
  final String? detail;

  AiChoiceOption({required this.optionId, required this.label, this.detail});

  factory AiChoiceOption.fromJson(Map<String, dynamic> json) => AiChoiceOption(
        optionId: json['option_id'] as String,
        label: json['label'] as String,
        detail: json['detail'] as String?,
      );
}

class AiCartAddition {
  final String productId;
  final String name;
  final String shopName;
  final int quantity;
  final double price;

  AiCartAddition({
    required this.productId,
    required this.name,
    required this.shopName,
    required this.quantity,
    required this.price,
  });

  factory AiCartAddition.fromJson(Map<String, dynamic> json) => AiCartAddition(
        productId: json['product_id'] as String,
        name: json['name'] as String,
        shopName: json['shop_name'] as String,
        quantity: (json['quantity'] as num).toInt(),
        price: (json['price'] as num).toDouble(),
      );
}

class AiChatResponse {
  final String reply;
  final List<AiChoiceOption>? choices;
  final List<AiCartAddition> cartAdditions;

  AiChatResponse({required this.reply, this.choices, required this.cartAdditions});

  factory AiChatResponse.fromJson(Map<String, dynamic> json) => AiChatResponse(
        reply: json['reply'] as String,
        choices: (json['choices'] as List<dynamic>?)
            ?.map((e) => AiChoiceOption.fromJson(e as Map<String, dynamic>))
            .toList(),
        cartAdditions: (json['cart_additions'] as List<dynamic>? ?? [])
            .map((e) => AiCartAddition.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

/// One bubble in the chat UI — richer than the plain role/content pair the
/// backend deals with (see AiChatMessage there), since the UI also needs to
/// remember which choices/cart-additions were attached to render them
/// inline under the right message, and whether the user already tapped one.
class AiChatEntry {
  final String role; // 'user' | 'assistant'
  final String text;
  final List<AiChoiceOption>? choices;
  final List<AiCartAddition> cartAdditions;
  bool choicesResolved;

  AiChatEntry({
    required this.role,
    required this.text,
    this.choices,
    this.cartAdditions = const [],
    this.choicesResolved = false,
  });
}