/** Texts, type names and colours for the Geography map (kept apart from the drawing code). */

export const UI = {
  ar: {
    title: "خريطة العالم التفاعلية", hint: "اسحب للتحريك • قرّب بالعجلة أو بإصبعين • اضغط على أي معلم لمعرفة اسمه",
    search: "ابحث عن دولة أو نهر أو جبل…", noResults: "لا توجد نتائج", close: "إغلاق", reset: "إعادة الضبط", layers: "الطبقات", quiz: "اختبرني",
    globe: "كرة أرضية", flat: "خريطة مسطحة", fullscreen: "ملء الشاشة", colorMode: "تلوين الدول", byContinent: "حسب القارة", political: "سياسي",
    all: "العالم", loading: "جارٍ تحميل الخريطة…", failed: "تعذر تحميل بيانات الخريطة", zoomIn: "تكبير", zoomOut: "تصغير",
    alsoHere: "أيضًا في هذا الموضع", population: "السكان", area: "المساحة", capital: "العاصمة", continent: "القارة", region: "الإقليم", neighbors: "الدول المجاورة",
    borders: "تُطل عليه", passes: "يمر عبر", length: "الطول", elevation: "الارتفاع", countriesHere: "يقع في", areaApprox: "كم²", km: "كم", meters: "م", belowSea: "تحت سطح البحر",
    million: "مليون", billion: "مليار", thousand: "ألف", noNeighbors: "جزيرة / بلا حدود برية",
    quizFind: "أين تجد:", quizScore: "الدرجة", quizSkip: "تخطي", quizStop: "إنهاء", quizOk: "أحسنت! ✔", quizNo: "هذا هو:", quizTry: "جرّب مرة أخرى", quizDone: "انتهى الاختبار",
    quizAgain: "اختبار جديد", quizOf: "من", quizPick: "اختر نوع الأسئلة", quizCapitalOf: "أين تقع الدولة التي عاصمتها:",
    qc: { countries: "دول العالم", arab: "الدول العربية", capitals: "العواصم", water: "البحار والمحيطات", rivers: "الأنهار", land: "الجبال والهضاب والصحاري", peaks: "قمم الجبال" },
    attribution: "بيانات الخريطة: Natural Earth (ملكية عامة) — الحدود تعرض الوضع الفعلي وفق مصدر البيانات",
    layer: { countries: "الدول", borders: "الحدود", graticule: "خطوط الطول والعرض", water: "البحار والمحيطات", rivers: "الأنهار والقنوات", lakes: "البحيرات",
      mountains: "الجبال", plateaus: "الهضاب", deserts: "الصحاري", lowlands: "السهول والأحواض والوديان", peninsulas: "أشباه الجزر والبرازخ", peaks: "القمم والمنخفضات", cities: "العواصم والمدن" },
    lines: { eq: "خط الاستواء", cancer: "مدار السرطان", capricorn: "مدار الجدي", arctic: "الدائرة القطبية الشمالية", antarctic: "الدائرة القطبية الجنوبية", pm: "خط غرينتش", idl: "خط تغيير التاريخ" },
  },
  en: {
    title: "Interactive World Map", hint: "Drag to pan • scroll or pinch to zoom • click anything to learn its name",
    search: "Search a country, river, mountain…", noResults: "No results", close: "Close", reset: "Reset view", layers: "Layers", quiz: "Quiz me",
    globe: "Globe", flat: "Flat map", fullscreen: "Fullscreen", colorMode: "Country colours", byContinent: "By continent", political: "Political",
    all: "World", loading: "Loading the map…", failed: "Couldn't load the map data", zoomIn: "Zoom in", zoomOut: "Zoom out",
    alsoHere: "Also at this spot", population: "Population", area: "Area", capital: "Capital", continent: "Continent", region: "Region", neighbors: "Neighbouring countries",
    borders: "Borders", passes: "Flows through", length: "Length", elevation: "Elevation", countriesHere: "Located in", areaApprox: "km²", km: "km", meters: "m", belowSea: "below sea level",
    million: "million", billion: "billion", thousand: "thousand", noNeighbors: "Island / no land borders",
    quizFind: "Find:", quizScore: "Score", quizSkip: "Skip", quizStop: "Stop", quizOk: "Nice! ✔", quizNo: "That's", quizTry: "Try again", quizDone: "Quiz finished",
    quizAgain: "New quiz", quizOf: "of", quizPick: "Choose what to be asked", quizCapitalOf: "Where is the country whose capital is:",
    qc: { countries: "World countries", arab: "Arab countries", capitals: "Capitals", water: "Seas & oceans", rivers: "Rivers", land: "Mountains, plateaus, deserts", peaks: "Peaks" },
    attribution: "Map data: Natural Earth (public domain) — borders show the de-facto situation per the data source",
    layer: { countries: "Countries", borders: "Borders", graticule: "Lat / long lines", water: "Seas & oceans", rivers: "Rivers & canals", lakes: "Lakes",
      mountains: "Mountains", plateaus: "Plateaus", deserts: "Deserts", lowlands: "Plains, basins, valleys", peninsulas: "Peninsulas & isthmuses", peaks: "Peaks & depressions", cities: "Capitals & cities" },
    lines: { eq: "Equator", cancer: "Tropic of Cancer", capricorn: "Tropic of Capricorn", arctic: "Arctic Circle", antarctic: "Antarctic Circle", pm: "Prime Meridian", idl: "Date Line" },
  },
};

export const TYPE = {
  ar: { ocean: "محيط", sea: "بحر", bay: "خليج", gulf: "خليج", strait: "مضيق", channel: "ممر مائي", sound: "مدخل بحري", reef: "حيد مرجاني", river: "نهر", canal: "قناة مائية",
    lake: "بحيرة", mountain: "جبال / سلسلة جبلية", plateau: "هضبة", desert: "صحراء", plain: "سهل", basin: "حوض", delta: "دلتا", peninsula: "شبه جزيرة", valley: "وادي / أخدود",
    isthmus: "برزخ", peak: "قمة جبل", depression: "منخفض", pass: "ممر جبلي", city: "مدينة", capital: "عاصمة", country: "دولة" },
  en: { ocean: "Ocean", sea: "Sea", bay: "Bay", gulf: "Gulf", strait: "Strait", channel: "Channel", sound: "Sound", reef: "Reef", river: "River", canal: "Canal",
    lake: "Lake", mountain: "Mountain range", plateau: "Plateau", desert: "Desert", plain: "Plain", basin: "Basin", delta: "Delta", peninsula: "Peninsula", valley: "Valley / rift",
    isthmus: "Isthmus", peak: "Peak", depression: "Depression", pass: "Mountain pass", city: "City", capital: "Capital", country: "Country" },
};

export const CONT = {
  ar: ["أفريقيا", "آسيا", "أوروبا", "أمريكا الشمالية", "أمريكا الجنوبية", "أوقيانوسيا", "القارة القطبية الجنوبية", "جزر المحيطات"],
  en: ["Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Antarctica", "Ocean islands"],
};
export const SUB_AR = {
  "Eastern Africa": "شرق أفريقيا", "Western Asia": "غرب آسيا", "South-Eastern Asia": "جنوب شرق آسيا", "South America": "أمريكا الجنوبية", "Southern Europe": "جنوب أوروبا",
  Melanesia: "ميلانيزيا", "Central Asia": "وسط آسيا", Micronesia: "ميكرونيزيا", Caribbean: "الكاريبي", Polynesia: "بولينيزيا", "Northern America": "أمريكا الشمالية",
  "Seven seas (open ocean)": "جزر المحيطات", "Western Africa": "غرب أفريقيا", "Northern Europe": "شمال أوروبا", "Eastern Europe": "شرق أوروبا", "Northern Africa": "شمال أفريقيا",
  "Eastern Asia": "شرق آسيا", "Western Europe": "غرب أوروبا", "Southern Africa": "جنوب أفريقيا", "Southern Asia": "جنوب آسيا", "Middle Africa": "وسط أفريقيا",
  "Central America": "أمريكا الوسطى", "Australia and New Zealand": "أستراليا ونيوزيلندا", Antarctica: "القارة القطبية الجنوبية",
};

/** continent shortcuts: [x0, y0, x1, y1] in lon/lat */
export const CONT_BOX = [
  [-19, -35, 52, 38], [26, -11, 146, 70], [-25, 34, 46, 72], [-170, 7, -50, 74], [-82, -56, -34, 13], [110, -48, 180, -5], [-180, -90, 180, -62],
];

export const ARAB = new Set(["DZA", "BHR", "COM", "DJI", "EGY", "IRQ", "JOR", "KWT", "LBN", "LBY", "MRT", "MAR", "OMN", "PSE", "QAT", "SAU", "SOM", "SDN", "SYR", "TUN", "ARE", "YEM"]);

/** which layer toggle controls which kind of feature */
export const LAYER_OF = { country: "countries", water: "water", river: "rivers", lake: "lakes", mountain: "mountains", plateau: "plateaus", desert: "deserts",
  plain: "lowlands", basin: "lowlands", delta: "lowlands", valley: "lowlands", peninsula: "peninsulas", isthmus: "peninsulas", peak: "peaks", city: "cities" };

export const LAYER_SWATCH = { countries: "#f2c46d", borders: "#7c8a99", graticule: "#8aa7bd", water: "#3b9be0", rivers: "#2d7fd3", lakes: "#5cb7ec", mountains: "#8d6e63", plateaus: "#d19a3f",
  deserts: "#e3c46b", lowlands: "#8bc34a", peninsulas: "#b07cc6", peaks: "#6d4c41", cities: "#e8505b" };

/** region overlay colours */
export const REGION_STYLE = {
  mountain: { fill: "#8d6e63", a: 0.4, stroke: "#6d4c41", pattern: "mount" },
  plateau: { fill: "#d19a3f", a: 0.42, stroke: "#b07d2a", pattern: "lines" },
  desert: { fill: "#e3c46b", a: 0.5, stroke: "#c9a43f", pattern: "dots" },
  plain: { fill: "#8bc34a", a: 0.3, stroke: "#6aa02e" }, basin: { fill: "#26a69a", a: 0.3, stroke: "#1e857b" }, delta: { fill: "#26c6a2", a: 0.45, stroke: "#139877" },
  valley: { fill: "#a1887f", a: 0.38, stroke: "#7d6760" }, peninsula: { fill: "#b07cc6", a: 0.24, stroke: "#8f5fa6" }, isthmus: { fill: "#b07cc6", a: 0.3, stroke: "#8f5fa6" },
};

const CONT_LIGHT = ["#f5cf86", "#f2a7a0", "#c3b1ea", "#93d0aa", "#8fcfe0", "#f6b6cf", "#e6edf2", "#dfe6ea"];
const CONT_DARK = ["#8a6a2c", "#8d4b52", "#5d4b92", "#2f7d57", "#2d7d96", "#8a4766", "#6f7f8c", "#52606b"];
const POL_LIGHT = ["#f5cf86", "#f2a7a0", "#c3b1ea", "#93d0aa", "#8fcfe0", "#f6b6cf", "#d8e3a0"];
const POL_DARK = ["#8a6a2c", "#8d4b52", "#5d4b92", "#2f7d57", "#2d7d96", "#8a4766", "#68763a"];
export const palette = (dark, mode) => (mode === "political" ? (dark ? POL_DARK : POL_LIGHT) : dark ? CONT_DARK : CONT_LIGHT);

export const THEME = {
  light: { ocean: ["#dff1fb", "#bfe0f3"], land: "#f5cf86", border: "#ffffff", coast: "#6b8497", text: "#23323f", halo: "rgba(255,255,255,.85)", water: "#2b7fc2", waterText: "#2a6fa8", river: "#2f86d6", lake: "#9ad1f2", grat: "rgba(60,100,140,.20)", line: "rgba(214,80,60,.65)", space: "#0b1a24" },
  dark: { ocean: ["#0f3347", "#0a2433"], land: "#8a6a2c", border: "#08202c", coast: "#9bbbd0", text: "#e6f1f7", halo: "rgba(5,18,26,.85)", water: "#79c2ff", waterText: "#8fcfff", river: "#5ab4ff", lake: "#1d5f86", grat: "rgba(140,190,230,.16)", line: "rgba(255,140,110,.7)", space: "#03090e" },
};
