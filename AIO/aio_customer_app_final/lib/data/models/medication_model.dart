import 'product_model.dart';

class MedicationCondition {
  final String id;
  final String labelAr;
  final String emoji;

  MedicationCondition({required this.id, required this.labelAr, required this.emoji});

  factory MedicationCondition.fromJson(Map<String, dynamic> json) => MedicationCondition(
        id: json['id'] as String,
        labelAr: json['label_ar'] as String,
        emoji: json['emoji'] as String,
      );

  static List<MedicationCondition> defaults() => [
        MedicationCondition(id: 'diabetes', labelAr: 'السكري', emoji: '💉'),
        MedicationCondition(id: 'high_blood_pressure', labelAr: 'ضغط الدم المرتفع', emoji: '❤️'),
        MedicationCondition(id: 'heart_disease', labelAr: 'أمراض القلب', emoji: '🫀'),
        MedicationCondition(id: 'thyroid', labelAr: 'اضطرابات الغدة الدرقية', emoji: '🦋'),
        MedicationCondition(id: 'high_cholesterol', labelAr: 'ارتفاع الكوليسترول', emoji: '🩸'),
        MedicationCondition(id: 'other', labelAr: 'أخرى', emoji: '💊'),
      ];

  static MedicationCondition byId(String id) {
    final match = defaults().where((c) => c.id == id);
    if (match.isNotEmpty) return match.first;
    // Not one of the predefined conditions — the user typed their own
    // condition name, so show exactly what they wrote instead of
    // collapsing it into the generic "other" label.
    return MedicationCondition(id: id, labelAr: id, emoji: '💊');
  }
}

class MedicationResponse {
  final String id;
  final String? productId;
  final ProductResponse? product;
  final String? pharmacyName;
  final String medicineName;
  final String condition;
  final int packQuantity;
  final double dailyDosage;
  final DateTime lastRefillDate;
  final int reminderDaysBefore;
  final bool isActive;
  final DateTime runOutDate;
  final int daysLeft;
  final bool needsRefillSoon;

  MedicationResponse({
    required this.id,
    this.productId,
    this.product,
    this.pharmacyName,
    required this.medicineName,
    required this.condition,
    required this.packQuantity,
    required this.dailyDosage,
    required this.lastRefillDate,
    required this.reminderDaysBefore,
    required this.isActive,
    required this.runOutDate,
    required this.daysLeft,
    required this.needsRefillSoon,
  });

  factory MedicationResponse.fromJson(Map<String, dynamic> json) => MedicationResponse(
        id: json['id'] as String,
        productId: json['product_id'] as String?,
        product: json['product'] != null ? ProductResponse.fromJson(json['product'] as Map<String, dynamic>) : null,
        pharmacyName: json['pharmacy_name'] as String?,
        medicineName: json['medicine_name'] as String,
        condition: json['condition'] as String,
        packQuantity: (json['pack_quantity'] as num).toInt(),
        dailyDosage: (json['daily_dosage'] as num).toDouble(),
        lastRefillDate: DateTime.parse(json['last_refill_date'] as String),
        reminderDaysBefore: (json['reminder_days_before'] as num).toInt(),
        isActive: json['is_active'] as bool,
        runOutDate: DateTime.parse(json['run_out_date'] as String),
        daysLeft: (json['days_left'] as num).toInt(),
        needsRefillSoon: json['needs_refill_soon'] as bool,
      );
}

class ReorderMedicationResult {
  final bool addedToCart;
  final DateTime newLastRefillDate;
  final DateTime newRunOutDate;
  final String message;

  ReorderMedicationResult({
    required this.addedToCart,
    required this.newLastRefillDate,
    required this.newRunOutDate,
    required this.message,
  });

  factory ReorderMedicationResult.fromJson(Map<String, dynamic> json) => ReorderMedicationResult(
        addedToCart: json['added_to_cart'] as bool,
        newLastRefillDate: DateTime.parse(json['new_last_refill_date'] as String),
        newRunOutDate: DateTime.parse(json['new_run_out_date'] as String),
        message: json['message'] as String,
      );
}
