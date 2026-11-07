"""
Per-category product attribute schema.

This is the single source of truth describing which extra fields a store
owner fills in when adding a product in a given shop category, and which
of those fields the CUSTOMER gets to choose between in the app before
adding the product to their cart.

Product.attributes (see app/models/product.py) stores whatever the store
owner picked here as a plain JSON dict keyed by `key` below — intentionally
NOT a rigid column-per-field, since attribute needs differ wildly by
category and will keep growing.

This schema is mirrored (not imported directly, since it also has to run
inside the browser-based store panel and inside the Flutter app) in:
  - panels/store_panel/index.html -> CATEGORY_ATTRIBUTE_SCHEMAS (JS)
  - lib/core/constants/product_attributes.dart (Dart)
Keep all three in sync when adding/renaming a field.

Field shape:
  key:              storage key inside Product.attributes
  label_ar:         label shown in the (Arabic) store panel + app
  type:             "text" | "date" | "boolean" | "single_select" |
                     "choices" | "multi_choices"
                       - text/date/boolean/single_select: the STORE sets
                         one value for the product (informational, shown
                         as-is to the customer).
                       - choices: the store picks which options are
                         AVAILABLE for this product (from suggested_options
                         or freely typed ones); the CUSTOMER then picks
                         exactly one of those before adding to cart.
                       - multi_choices: same as choices, but the customer
                         may pick more than one (e.g. food extras).
  customer_selects: whether the app should render this as a picker the
                     shopper interacts with (True) vs. read-only info
                     shown on the product card/detail page (False).
  optional:         whether the store may leave this field empty.
  suggested_options: starter list shown in the store panel; the store can
                      still type a custom option for `choices`/
                      `single_select` fields unless noted otherwise.
"""

CATEGORY_ATTRIBUTE_SCHEMAS: dict[str, list[dict]] = {
    "grocery": [
        {
            "key": "weight",
            "label_ar": "الوزن / الحجم",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: 500 جم، 1 كجم، 1 لتر",
        },
        {
            "key": "expire_date",
            "label_ar": "تاريخ الصلاحية",
            "type": "date",
            "customer_selects": False,
            "optional": True,
        },
    ],
    "clothes": [
        {
            "key": "size",
            "label_ar": "المقاس",
            "type": "choices",
            "customer_selects": True,
            "optional": False,
            "suggested_options": ["XS", "S", "M", "L", "XL", "XXL", "XXXL"],
        },
        {
            "key": "colour",
            "label_ar": "اللون",
            "type": "choices",
            "customer_selects": True,
            "optional": True,
            "suggested_options": ["أسود", "أبيض", "أحمر", "أزرق", "بيج", "رمادي", "كحلي", "بني"],
        },
        {
            "key": "sleeve_type",
            "label_ar": "نوع الكم",
            "type": "choices",
            "customer_selects": True,
            "optional": True,
            "suggested_options": ["كم طويل", "كم قصير", "بدون كم"],
        },
    ],
    # Default choice groups modeled on what Talabat-style food listings
    # commonly offer — the store can delete any group that doesn't apply
    # to a given dish and add its own custom options within each group.
    "food": [
        {
            "key": "size",
            "label_ar": "الحجم",
            "type": "choices",
            "customer_selects": True,
            "optional": True,
            "suggested_options": ["صغير", "وسط", "كبير", "عائلي"],
        },
        {
            "key": "extras",
            "label_ar": "إضافات",
            "type": "multi_choices",
            "customer_selects": True,
            "optional": True,
            "suggested_options": ["جبنة إضافية", "صوص إضافي", "مقرمش إضافي", "بدون بصل", "بدون طماطم", "بدون مخلل"],
        },
        {
            "key": "spice_level",
            "label_ar": "درجة الحرارة",
            "type": "choices",
            "customer_selects": True,
            "optional": True,
            "suggested_options": ["عادي", "حار", "حار جدًا"],
        },
        {
            "key": "drink_choice",
            "label_ar": "اختيار المشروب (لو ضمن الوجبة)",
            "type": "choices",
            "customer_selects": True,
            "optional": True,
            "suggested_options": ["بيبسي", "سفن أب", "ميرندا", "مياه", "بدون مشروب"],
        },
    ],
    "electronics": [
        {
            "key": "company",
            "label_ar": "الشركة المصنعة",
            "type": "single_select",
            "customer_selects": False,
            "optional": False,
            "suggested_options": [
                "Apple", "Samsung", "Xiaomi", "Oppo", "Realme", "Huawei",
                "Anker/Soundcore", "JBL", "Lenovo", "HP", "Dell", "Sony", "أخرى",
            ],
            # Signals to the store panel that it should offer "اجعل هذه
            # الشركة فئة فرعية؟" — wired to the EXISTING subcategory system
            # (see models/subcategory.py) rather than a new mechanism: the
            # panel just pre-fills/creates a Subcategory named after the
            # brand under this shop's category and assigns it, so brand
            # filtering reuses the same pill-chip UI already in the app.
            "can_become_subcategory": True,
        },
        {
            "key": "colour",
            "label_ar": "اللون",
            "type": "choices",
            "customer_selects": True,
            "optional": True,
            "suggested_options": ["أسود", "أبيض", "فضي", "ذهبي", "أزرق", "أحمر", "أخضر"],
        },
        {
            "key": "warranty",
            "label_ar": "الضمان",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: سنة ضمان من الوكيل",
        },
        # --- Comparison spec fields (Compare Before Buying) ---
        # Plain text, store-set, read-only info fields — kept simple on
        # purpose since specs vary wildly by device type (a TV has no RAM
        # figure worth comparing, a laptop's "camera" is irrelevant); the
        # store just leaves whichever ones don't apply blank, and the
        # comparison table (see products_router.py compare endpoint) only
        # renders rows where at least one selected product has a value.
        {
            "key": "processor",
            "label_ar": "المعالج",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: Snapdragon 8 Gen 3",
        },
        {
            "key": "display",
            "label_ar": "الشاشة",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: 6.7 بوصة AMOLED 120Hz",
        },
        {
            "key": "battery",
            "label_ar": "البطارية",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: 5000 مللي أمبير",
        },
        {
            "key": "ram",
            "label_ar": "الرام",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: 8 جيجا",
        },
        {
            "key": "storage",
            "label_ar": "التخزين",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: 256 جيجا",
        },
        {
            "key": "camera",
            "label_ar": "الكاميرا",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: 50 ميجابكسل + 12 ميجابكسل",
        },
    ],
    "pharmacies": [
        {
            "key": "form",
            "label_ar": "شكل الدواء",
            "type": "single_select",
            "customer_selects": False,
            "optional": True,
            "suggested_options": ["أقراص", "شراب", "كريم", "حقن", "قطرة", "مرهم", "بخاخ", "أخرى"],
        },
        {
            "key": "dosage",
            "label_ar": "التركيز / الجرعة",
            "type": "text",
            "customer_selects": False,
            "optional": True,
            "placeholder": "مثال: 500 mg",
        },
        {
            "key": "expire_date",
            "label_ar": "تاريخ الصلاحية",
            "type": "date",
            "customer_selects": False,
            "optional": True,
        },
        {
            "key": "requires_prescription",
            "label_ar": "يتطلب روشتة طبية",
            "type": "boolean",
            "customer_selects": False,
            "optional": True,
        },
    ],
}
