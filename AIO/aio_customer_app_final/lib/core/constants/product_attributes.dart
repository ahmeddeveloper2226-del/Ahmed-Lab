/// Mirrors app/constants/product_attributes.py on the backend (labels and
/// field *types* only — keep in sync when adding/renaming a field there).
///
/// Product.attributes on the wire is a flat `{ key: value }` map:
///   - text / date / single_select / boolean fields: value is the single
///     thing the STORE set (shown read-only on the product page).
///   - choices / multi_choices fields: value is the list of options the
///     STORE made available for this product; the CUSTOMER picks one (or,
///     for multi_choices, more than one) before adding it to the cart.
library;

enum ProductAttributeType { text, date, boolean, singleSelect, choices, multiChoices }

class ProductAttributeMeta {
  final String key;
  final String labelAr;
  final ProductAttributeType type;

  const ProductAttributeMeta(this.key, this.labelAr, this.type);
}

/// Flat lookup by attribute key — a key like "colour" means the same thing
/// (a customer-picked color option) regardless of which category schema it
/// came from, so one shared map is enough for display purposes.
const Map<String, ProductAttributeMeta> kProductAttributeMeta = {
  'weight': ProductAttributeMeta('weight', 'الوزن / الحجم', ProductAttributeType.text),
  'expire_date': ProductAttributeMeta('expire_date', 'تاريخ الصلاحية', ProductAttributeType.date),
  'size': ProductAttributeMeta('size', 'المقاس', ProductAttributeType.choices),
  'colour': ProductAttributeMeta('colour', 'اللون', ProductAttributeType.choices),
  'sleeve_type': ProductAttributeMeta('sleeve_type', 'نوع الكم', ProductAttributeType.choices),
  'extras': ProductAttributeMeta('extras', 'إضافات', ProductAttributeType.multiChoices),
  'spice_level': ProductAttributeMeta('spice_level', 'درجة الحرارة', ProductAttributeType.choices),
  'drink_choice': ProductAttributeMeta('drink_choice', 'اختيار المشروب', ProductAttributeType.choices),
  'company': ProductAttributeMeta('company', 'الشركة المصنعة', ProductAttributeType.singleSelect),
  'warranty': ProductAttributeMeta('warranty', 'الضمان', ProductAttributeType.text),
  // Compare Before Buying spec fields (electronics only) — see
  // app/constants/product_attributes.py for the matching backend schema.
  'processor': ProductAttributeMeta('processor', 'المعالج', ProductAttributeType.text),
  'display': ProductAttributeMeta('display', 'الشاشة', ProductAttributeType.text),
  'battery': ProductAttributeMeta('battery', 'البطارية', ProductAttributeType.text),
  'ram': ProductAttributeMeta('ram', 'الرام', ProductAttributeType.text),
  'storage': ProductAttributeMeta('storage', 'التخزين', ProductAttributeType.text),
  'camera': ProductAttributeMeta('camera', 'الكاميرا', ProductAttributeType.text),
  'form': ProductAttributeMeta('form', 'شكل الدواء', ProductAttributeType.singleSelect),
  'dosage': ProductAttributeMeta('dosage', 'التركيز / الجرعة', ProductAttributeType.text),
  'requires_prescription': ProductAttributeMeta('requires_prescription', 'يتطلب روشتة طبية', ProductAttributeType.boolean),
};

bool isCustomerPickType(ProductAttributeType type) =>
    type == ProductAttributeType.choices || type == ProductAttributeType.multiChoices;
