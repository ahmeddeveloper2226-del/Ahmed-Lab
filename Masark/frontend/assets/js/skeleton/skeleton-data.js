/**
 * Everything the viewer says about bones: names (Arabic / English / Latin),
 * descriptions and the UI strings. Kept separate from the 3D code so the
 * texts are easy to proofread or extend.
 */
const ORD_M = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر", "الحادي عشر", "الثاني عشر"];
const ORD_F = ["الأولى", "الثانية", "الثالثة", "الرابعة", "الخامسة", "السادسة", "السابعة", "الثامنة", "التاسعة", "العاشرة", "الحادية عشرة", "الثانية عشرة"];
const ORD_EN = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th"];
const FINGER_AR = ["الإبهام", "السبابة", "الوسطى", "البنصر", "الخنصر"];
const FINGER_EN = ["thumb", "index finger", "middle finger", "ring finger", "little finger"];
const TOE_AR = ["الكبير (إبهام القدم)", "الثاني", "الثالث", "الرابع", "الخامس (الخنصر)"];
const TOE_EN = ["big toe", "2nd toe", "3rd toe", "4th toe", "little toe"];
const SEG_AR = { proximal: "القريبة", middle: "الوسطى", distal: "البعيدة" };
const SEG_EN = { proximal: "Proximal", middle: "Middle", distal: "Distal" };

export const REGIONS = [
  { id: "head", ar: "الجمجمة", en: "Skull" },
  { id: "spine", ar: "العمود الفقري", en: "Spine" },
  { id: "thorax", ar: "القفص الصدري", en: "Rib cage" },
  { id: "arm", ar: "الذراع واليد", en: "Arm & hand" },
  { id: "pelvis", ar: "الحوض", en: "Pelvis" },
  { id: "leg", ar: "الساق والقدم", en: "Leg & foot" },
];
const TYPE = {
  long: { ar: "عظمة طويلة", en: "Long bone" }, short: { ar: "عظمة قصيرة", en: "Short bone" },
  flat: { ar: "عظمة مسطحة", en: "Flat bone" }, irregular: { ar: "عظمة غير منتظمة", en: "Irregular bone" },
  sesamoid: { ar: "عظمة سمسمانية", en: "Sesamoid bone" },
};
const AXIAL = new Set(["head", "spine", "thorax"]);

/** g = grammatical gender of the Arabic noun (for اليمنى / الأيمن). */
const G = {
  frontal: { ar: "العظم الجبهي", en: "Frontal bone", la: "Os frontale", g: "m", region: "head", type: "flat", quiz: 1,
    d: ["يشكّل الجبهة وسقف تجويفي العينين، ويحمي الجزء الأمامي من المخ.", "Forms the forehead and the roofs of the eye sockets, protecting the front of the brain."] },
  parietal: { ar: "العظم الجداري", en: "Parietal bone", la: "Os parietale", g: "m", region: "head", type: "flat", quiz: 1,
    d: ["عظمتان تشكّلان معظم سقف الجمجمة وجانبيها، وتلتقيان في منتصف الرأس عند الدرز السهمي.", "Two bones forming most of the roof and upper sides of the cranium; they meet at the sagittal suture."] },
  temporal: { ar: "العظم الصدغي", en: "Temporal bone", la: "Os temporale", g: "m", region: "head", type: "irregular", quiz: 1,
    d: ["عظمتان على جانبي الجمجمة تحتويان على أجزاء الأذن الوسطى والداخلية، وفيهما النتوء الخشائي خلف الأذن ومفصل الفك السفلي.", "Two bones on the sides of the skull that house the middle and inner ear, with the mastoid process behind the ear and the jaw joint."] },
  occipital: { ar: "العظم القذالي (المؤخري)", en: "Occipital bone", la: "Os occipitale", g: "m", region: "head", type: "flat", quiz: 1,
    d: ["يشكّل مؤخرة الجمجمة وقاعدتها، وفيه الثقب العظيم الذي يمر منه الحبل الشوكي.", "Forms the back and base of the skull; the large opening (foramen magnum) lets the spinal cord pass through."] },
  sphenoid: { ar: "العظم الوتدي", en: "Sphenoid bone", la: "Os sphenoidale", g: "m", region: "head", type: "irregular",
    d: ["عظم على شكل فراشة يمتد عبر قاعدة الجمجمة، ويظهر جناحاه عند الصدغين، ويربط عظام الجمجمة ببعضها.", "A butterfly-shaped bone across the base of the skull; its wings show at the temples and it links many cranial bones together."] },
  maxilla: { ar: "الفك العلوي", en: "Maxilla (upper jaw)", la: "Maxilla", g: "m", region: "head", type: "irregular", quiz: 1,
    d: ["يحمل الأسنان العليا، ويشكّل سقف الفم وجانبي الأنف وجزءًا من أرضية تجويف العين.", "Holds the upper teeth and forms the roof of the mouth, the sides of the nose and part of the floor of each eye socket."] },
  zygomatic: { ar: "العظم الوجني (عظم الوجنة)", en: "Zygomatic bone (cheekbone)", la: "Os zygomaticum", g: "m", region: "head", type: "irregular", quiz: 1,
    d: ["يشكّل بروز الخد وجزءًا من تجويف العين، ويكوّن مع العظم الصدغي القوس الوجنية.", "Forms the prominence of the cheek and part of the eye socket; with the temporal bone it makes the zygomatic arch."] },
  nasal: { ar: "العظم الأنفي", en: "Nasal bone", la: "Os nasale", g: "m", region: "head", type: "flat",
    d: ["عظمتان صغيرتان تكوّنان جسر الأنف؛ أما باقي الأنف فغضروفي.", "Two small bones that form the bridge of the nose; the rest of the nose is cartilage."] },
  mandible: { ar: "الفك السفلي", en: "Mandible (lower jaw)", la: "Mandibula", g: "m", region: "head", type: "irregular", quiz: 1,
    d: ["العظم الوحيد المتحرك في الجمجمة؛ يحمل الأسنان السفلية ويتمفصل مع العظمين الصدغيين.", "The only movable bone of the skull; it holds the lower teeth and joins the temporal bones at the jaw joints."],
    f: ["هو أكبر عظام الوجه وأقواها.", "It is the largest and strongest bone of the face."] },
  hyoid: { ar: "العظم اللامي", en: "Hyoid bone", la: "Os hyoideum", g: "m", region: "head", type: "irregular", quiz: 1,
    d: ["عظم صغير على شكل حدوة حصان في العنق، يسند اللسان وعضلات البلع.", "A small horseshoe-shaped bone in the neck that supports the tongue and swallowing muscles."],
    f: ["هو العظم الوحيد في الجسم الذي لا يتصل بأي عظم آخر.", "It is the only bone in the body that does not touch another bone."] },
  atlas: { ar: "الفقرة العنقية الأولى (الأطلس)", en: "Atlas (C1)", la: "Atlas", g: "f", region: "spine", type: "irregular", quiz: 1,
    d: ["أول فقرة عنقية؛ تحمل الجمجمة وتسمح بحركة الإيماء (نعم). ليس لها جسم، بل حلقة عظمية.", "The first cervical vertebra; it carries the skull and allows the nodding \"yes\" movement. It has no body, just a bony ring."],
    f: ["سُمّيت على اسم أطلس الذي حمل السماء على كتفيه في الأساطير الإغريقية.", "Named after Atlas, the Greek Titan who held up the sky."] },
  axis: { ar: "الفقرة العنقية الثانية (المحور)", en: "Axis (C2)", la: "Axis", g: "f", region: "spine", type: "irregular", quiz: 1,
    d: ["لها نتوء يشبه السن يسمى «السِّن» يدور حوله الأطلس، فيمكنك تحريك رأسك يمينًا ويسارًا (لا).", "Its tooth-like process (dens) is the pivot the atlas turns on, letting you shake your head \"no\"."] },
  cervical: { ar: "الفقرة العنقية", en: "Cervical vertebra", la: "Vertebra cervicalis", g: "f", region: "spine", type: "irregular", quiz: 1,
    d: ["سبع فقرات عنقية (C1–C7) في العنق تسند الرأس وتحمي الحبل الشوكي وتمنح العنق مرونة كبيرة.", "Seven cervical vertebrae (C1–C7) support the head, protect the spinal cord and make the neck very flexible."],
    f: ["للزرافة وللإنسان العدد نفسه من الفقرات العنقية: سبع فقرات.", "Giraffes and humans both have exactly seven neck vertebrae."] },
  thoracic: { ar: "الفقرة الصدرية", en: "Thoracic vertebra", la: "Vertebra thoracica", g: "f", region: "spine", type: "irregular", quiz: 1,
    d: ["12 فقرة صدرية (T1–T12)؛ تتمفصل كل واحدة منها مع زوج من الأضلاع لتكوين القفص الصدري.", "Twelve thoracic vertebrae (T1–T12); each joins a pair of ribs to form the rib cage."] },
  lumbar: { ar: "الفقرة القطنية", en: "Lumbar vertebra", la: "Vertebra lumbalis", g: "f", region: "spine", type: "irregular", quiz: 1,
    d: ["خمس فقرات قطنية (L1–L5) هي الأكبر والأقوى لأنها تتحمل وزن الجزء العلوي من الجسم.", "Five lumbar vertebrae (L1–L5) are the largest and strongest because they carry the weight of the upper body."] },
  sacrum: { ar: "العجز", en: "Sacrum", la: "Os sacrum", g: "m", region: "pelvis", type: "irregular", quiz: 1,
    d: ["خمس فقرات ملتحمة في عظم مثلث الشكل، يربط العمود الفقري بالحوض ويشكّل جدار الحوض الخلفي.", "Five fused vertebrae forming a triangular bone that links the spine to the pelvis and forms its back wall."] },
  coccyx: { ar: "العصعص", en: "Coccyx (tailbone)", la: "Os coccygis", g: "m", region: "pelvis", type: "irregular", quiz: 1,
    d: ["من ثلاث إلى خمس فقرات صغيرة ملتحمة في نهاية العمود الفقري، وهو أثر لذيل أسلافنا.", "Three to five tiny fused vertebrae at the end of the spine, a remnant of our ancestors' tail."] },
  rib: { ar: "الضلع", en: "Rib", la: "Costa", g: "m", region: "thorax", type: "flat", quiz: 1,
    d: ["12 زوجًا من الأضلاع تحمي القلب والرئتين وتتحرك أثناء التنفس.", "Twelve pairs of ribs protect the heart and lungs and move as you breathe."],
    f: ["الأضلاع 1–7 «حقيقية» تتصل بالقص بغضروف مباشر، و8–10 «كاذبة»، و11–12 «سائبة» لا تتصل بالقص.", "Ribs 1–7 are \"true\" (joined to the sternum by cartilage), 8–10 are \"false\", and 11–12 are \"floating\"."] },
  manubrium: { ar: "مقبض القص", en: "Manubrium", la: "Manubrium sterni", g: "m", region: "thorax", type: "flat", quiz: 1,
    d: ["الجزء العلوي من عظمة القص؛ تتمفصل معه الترقوتان والضلعان الأول والثاني.", "The top part of the breastbone; the collarbones and the first two ribs join it."] },
  sternum_body: { ar: "جسم القص", en: "Body of the sternum", la: "Corpus sterni", g: "m", region: "thorax", type: "flat", quiz: 1,
    d: ["الجزء الأوسط الطويل من عظمة القص، تتصل به غضاريف الأضلاع من الثاني إلى السابع.", "The long middle part of the breastbone; the cartilages of ribs 2–7 attach to it."] },
  xiphoid: { ar: "الناتئ الخنجري", en: "Xiphoid process", la: "Processus xiphoideus", g: "m", region: "thorax", type: "irregular",
    d: ["الطرف السفلي الصغير للقص؛ غضروفي عند الأطفال ويتعظّم مع التقدم في العمر.", "The small lower tip of the sternum; cartilage in children that turns to bone with age."] },
  clavicle: { ar: "الترقوة", en: "Clavicle (collarbone)", la: "Clavicula", g: "f", region: "arm", type: "long", quiz: 1,
    d: ["عظمة على شكل حرف S تربط القص بلوح الكتف، وتبقي الكتف بعيدًا عن القفص الصدري.", "An S-shaped bone linking the sternum to the shoulder blade; it keeps the shoulder away from the rib cage."],
    f: ["الترقوة من أكثر العظام تعرضًا للكسر.", "The clavicle is one of the most commonly broken bones."] },
  scapula: { ar: "لوح الكتف", en: "Scapula (shoulder blade)", la: "Scapula", g: "m", region: "arm", type: "flat", quiz: 1,
    d: ["عظمة مسطحة مثلثة في أعلى الظهر، لها تجويف يستقر فيه رأس عظم العضد، وبروز الأخرم أعلى الكتف.", "A flat triangular bone in the upper back with a socket for the head of the humerus and a ridge (acromion) over the shoulder."] },
  humerus: { ar: "عظم العضد", en: "Humerus", la: "Humerus", g: "m", region: "arm", type: "long", quiz: 1,
    d: ["عظم الذراع العلوي؛ يتمفصل رأسه الكروي مع لوح الكتف، ونهايته السفلى مع عظمتي الساعد عند المرفق.", "The upper-arm bone; its round head fits the shoulder blade and its lower end meets the forearm bones at the elbow."] },
  radius: { ar: "الكعبرة", en: "Radius", la: "Radius", g: "f", region: "arm", type: "long", quiz: 1,
    d: ["عظم الساعد من جهة الإبهام؛ يدور حول الزند ليقلب راحة اليد للأعلى أو للأسفل.", "The forearm bone on the thumb side; it rotates around the ulna to turn the palm up or down."] },
  ulna: { ar: "الزند", en: "Ulna", g: "m", la: "Ulna", region: "arm", type: "long", quiz: 1,
    d: ["عظم الساعد من جهة الخنصر؛ تكوّن نهايته العليا بروز المرفق (الزج).", "The forearm bone on the little-finger side; its upper end forms the point of the elbow (olecranon)."] },
  scaphoid: { ar: "العظم الزورقي (الرسغ)", en: "Scaphoid", la: "Os scaphoideum", g: "m", region: "arm", type: "short", quiz: 1,
    d: ["عظم رسغي على شكل زورق جهة الإبهام، وهو أكثر عظام الرسغ عرضة للكسر.", "A boat-shaped wrist bone on the thumb side; the carpal bone most often broken."] },
  lunate: { ar: "العظم الهلالي", en: "Lunate", la: "Os lunatum", g: "m", region: "arm", type: "short",
    d: ["عظم رسغي على شكل هلال في وسط الصف القريب من الساعد.", "A crescent-shaped wrist bone in the middle of the row nearest the forearm."] },
  triquetrum: { ar: "العظم الهرمي (المثلثي)", en: "Triquetrum", la: "Os triquetrum", g: "m", region: "arm", type: "short",
    d: ["عظم رسغي هرمي الشكل في جهة الخنصر من الصف القريب.", "A pyramid-shaped wrist bone on the little-finger side of the near row."] },
  pisiform: { ar: "العظم الحمصي", en: "Pisiform", la: "Os pisiforme", g: "m", region: "arm", type: "sesamoid",
    d: ["أصغر عظام الرسغ، بحجم حبة البازلاء، ويقع داخل أحد الأوتار.", "The smallest wrist bone, the size of a pea, embedded in a tendon."] },
  trapezium: { ar: "العظم المنحرف الكبير", en: "Trapezium", la: "Os trapezium", g: "m", region: "arm", type: "short",
    d: ["يتمفصل مع مشط الإبهام ويمنح الإبهام حركته الواسعة التي تتيح الإمساك.", "Joins the thumb's metacarpal and gives the thumb its wide, grasping movement."] },
  trapezoid: { ar: "العظم المنحرف الصغير", en: "Trapezoid", la: "Os trapezoideum", g: "m", region: "arm", type: "short",
    d: ["أصغر عظام الصف البعيد في الرسغ، ويتمفصل مع مشط السبابة.", "The smallest bone of the far row of the wrist; it joins the index-finger metacarpal."] },
  capitate: { ar: "العظم الرأسي", en: "Capitate", la: "Os capitatum", g: "m", region: "arm", type: "short",
    d: ["أكبر عظام الرسغ، له رأس مستدير ويقع في مركز الرسغ.", "The largest wrist bone, with a round head, in the centre of the wrist."] },
  hamate: { ar: "العظم الكلابي", en: "Hamate", la: "Os hamatum", g: "m", region: "arm", type: "short",
    d: ["له بروز يشبه الخُطّاف؛ يتمفصل مع مشطي البنصر والخنصر.", "Has a hook-shaped projection and joins the ring- and little-finger metacarpals."] },
  metacarpal: { ar: "عظم المشط", en: "Metacarpal", la: "Os metacarpale", g: "m", region: "arm", type: "long", quiz: 1,
    d: ["خمسة عظام في كل يد تكوّن راحة اليد، وتصل الرسغ بالأصابع.", "Five bones in each hand that form the palm and connect the wrist to the fingers."] },
  phalanx_hand: { ar: "السلامية", en: "Phalanx", la: "Phalanx manus", g: "f", region: "arm", type: "long", quiz: 1,
    d: ["14 سلامية في كل يد: ثلاث لكل إصبع، عدا الإبهام فله اثنتان.", "Fourteen phalanges in each hand: three per finger, except the thumb which has two."] },
  ilium: { ar: "عظم الحرقفة", en: "Ilium", la: "Os ilium", g: "m", region: "pelvis", type: "flat", quiz: 1,
    d: ["أكبر أجزاء عظم الورك وأعلاها؛ نضع أيدينا على حرفه العلوي (عُرف الحرقفة) عند الوقوف.", "The largest, uppermost part of the hip bone; the top edge (iliac crest) is what you rest your hands on."] },
  ischium: { ar: "عظم الإسك", en: "Ischium", la: "Os ischii", g: "m", region: "pelvis", type: "irregular", quiz: 1,
    d: ["الجزء السفلي الخلفي من عظم الورك؛ الحدبة الإسكية هي ما نجلس عليه.", "The lower back part of the hip bone; its tuberosity is what you sit on."] },
  pubis: { ar: "عظم العانة", en: "Pubis", la: "Os pubis", g: "m", region: "pelvis", type: "irregular", quiz: 1,
    d: ["الجزء الأمامي السفلي من عظم الورك؛ يلتقي العظمان العانيان في الأمام عند الارتفاق العاني.", "The front lower part of the hip bone; the two pubic bones meet at the pubic symphysis."],
    f: ["تلتحم الحرقفة والإسك والعانة معًا لتكوين عظم الورك بعد البلوغ، وفيه الحُقّ الذي يستقبل رأس الفخذ.", "Ilium, ischium and pubis fuse into one hip bone after puberty, forming the socket for the femur's head."] },
  femur: { ar: "عظم الفخذ", en: "Femur (thigh bone)", la: "Femur", g: "m", region: "leg", type: "long", quiz: 1,
    d: ["أطول عظام الجسم وأقواها؛ يتمفصل رأسه الكروي مع الحوض عند الورك ونهايته السفلى عند الركبة.", "The longest, strongest bone in the body; its round head fits the pelvis at the hip and its lower end forms the knee."],
    f: ["طول عظم الفخذ يقارب ربع طول الإنسان تقريبًا.", "The femur is roughly a quarter of a person's height."] },
  patella: { ar: "الرضفة (صابونة الركبة)", en: "Patella (kneecap)", la: "Patella", g: "f", region: "leg", type: "sesamoid", quiz: 1,
    d: ["أكبر عظمة سمسمانية في الجسم؛ تحمي مفصل الركبة وتزيد قوة شدّ عضلة الفخذ الأمامية.", "The largest sesamoid bone; it protects the knee joint and increases the pull of the thigh muscle."] },
  tibia: { ar: "الظنبوب (قصبة الساق)", en: "Tibia (shin bone)", la: "Tibia", g: "m", region: "leg", type: "long", quiz: 1,
    d: ["العظم الأكبر في الساق وهو الذي يحمل وزن الجسم؛ يمكن تحسّس حافته الأمامية تحت الجلد.", "The larger leg bone that carries the body's weight; you can feel its front edge under the skin."] },
  fibula: { ar: "الشظية", en: "Fibula", la: "Fibula", g: "f", region: "leg", type: "long", quiz: 1,
    d: ["عظم رفيع بجوار الظنبوب من الخارج، يحمل جزءًا صغيرًا من الوزن ويثبّت مفصل الكاحل.", "A slender bone beside the tibia; it carries little weight but steadies the ankle joint."] },
  talus: { ar: "عظم الكاحل (الحُقّ)", en: "Talus (ankle bone)", la: "Talus", g: "m", region: "leg", type: "short", quiz: 1,
    d: ["يتمفصل مع الظنبوب والشظية لتكوين مفصل الكاحل، وينقل وزن الجسم إلى القدم.", "Joins the tibia and fibula to make the ankle joint and passes body weight into the foot."] },
  calcaneus: { ar: "عظم العقب (الكعب)", en: "Calcaneus (heel bone)", la: "Calcaneus", g: "m", region: "leg", type: "short", quiz: 1,
    d: ["أكبر عظام القدم؛ يشكّل الكعب ويتصل به وتر العرقوب (وتر أخيل).", "The largest foot bone; it forms the heel and the Achilles tendon attaches to it."] },
  navicular: { ar: "العظم الزورقي (القدم)", en: "Navicular", la: "Os naviculare", g: "m", region: "leg", type: "short",
    d: ["عظم على شكل زورق في الجهة الداخلية من القدم، ويسهم في القوس الطولي.", "A boat-shaped bone on the inner side of the foot that helps form the arch."] },
  cuboid: { ar: "العظم النردي (المكعب)", en: "Cuboid", la: "Os cuboideum", g: "m", region: "leg", type: "short",
    d: ["عظم مكعب الشكل في الجهة الخارجية من القدم.", "A cube-shaped bone on the outer side of the foot."] },
  cuneiform: { ar: "العظم الإسفيني", en: "Cuneiform", la: "Os cuneiforme", g: "m", region: "leg", type: "short",
    d: ["ثلاثة عظام إسفينية (الأنسي والمتوسط والوحشي) تصل الزورقي بعظام مشط القدم.", "Three wedge-shaped bones (medial, intermediate, lateral) linking the navicular to the metatarsals."] },
  metatarsal: { ar: "عظم مشط القدم", en: "Metatarsal", la: "Os metatarsale", g: "m", region: "leg", type: "long", quiz: 1,
    d: ["خمسة عظام في كل قدم؛ الأول هو الأسمك لأنه يحمل جزءًا كبيرًا من الوزن عند المشي.", "Five bones in each foot; the first is the thickest because it takes much of your weight when walking."] },
  phalanx_foot: { ar: "السلامية", en: "Phalanx (toe)", la: "Phalanx pedis", g: "f", region: "leg", type: "long", quiz: 1,
    d: ["14 سلامية في كل قدم: لإبهام القدم سلاميتان فقط، وللأصابع الأخرى ثلاث.", "Fourteen toe bones in each foot: the big toe has two, the others three."] },
};

export const GROUPS = G;
export const TOTAL_BONES = 206;

const SIDE = {
  ar: { m: { L: "الأيسر", R: "الأيمن" }, f: { L: "الأيسر → اليسرى", R: "اليمنى" } },
  en: { L: "left", R: "right" },
};
SIDE.ar.f.L = "اليسرى";

/** Primary/secondary names for a bone instance: { ar, en, la }. */
export function boneNames(b) {
  const g = G[b.group];
  const side = b.side === "L" || b.side === "R" ? b.side : null;
  const sAr = side ? " " + SIDE.ar[g.g][side] : "", sEn = side ? ` (${SIDE.en[side]})` : "";
  const n = b.index;
  let ar = g.ar, en = g.en, la = g.la;
  switch (b.group) {
    case "cervical": ar = `الفقرة العنقية ${ORD_F[n - 1]} (C${n})`; en = `Cervical vertebra C${n}`; break;
    case "thoracic": ar = `الفقرة الصدرية ${ORD_F[n - 1]} (T${n})`; en = `Thoracic vertebra T${n}`; break;
    case "lumbar": ar = `الفقرة القطنية ${ORD_F[n - 1]} (L${n})`; en = `Lumbar vertebra L${n}`; break;
    case "rib": ar = `الضلع ${ORD_M[n - 1]}`; en = `${ORD_EN[n - 1]} rib`; break;
    case "metacarpal": ar = `عظم المشط ${ORD_M[n - 1]} (${FINGER_AR[n - 1]})`; en = `Metacarpal ${n} (${FINGER_EN[n - 1]})`; break;
    case "metatarsal": ar = `عظم مشط القدم ${ORD_M[n - 1]}`; en = `Metatarsal ${n} (${TOE_EN[n - 1]})`; break;
    case "cuneiform": ar = `العظم الإسفيني ${["الأنسي", "المتوسط", "الوحشي"][n - 1]}`; en = `${["Medial", "Intermediate", "Lateral"][n - 1]} cuneiform`; break;
    case "phalanx_hand": ar = `السلامية ${SEG_AR[b.seg]} ${b.finger === 1 ? "للإبهام" : "للإصبع " + FINGER_AR[b.finger - 1]}`; en = `${SEG_EN[b.seg]} phalanx of the ${FINGER_EN[b.finger - 1]}`; break;
    case "phalanx_foot": ar = `السلامية ${SEG_AR[b.seg]} للإصبع ${TOE_AR[b.finger - 1]}`; en = `${SEG_EN[b.seg]} phalanx of the ${TOE_EN[b.finger - 1]}`; break;
    default: break;
  }
  if (b.group === "metacarpal" || b.group === "metatarsal" || b.group === "cuneiform" || b.group === "phalanx_hand" || b.group === "phalanx_foot") {
    // sided names read better with the side first for long phrases
  }
  return { ar: ar + sAr, en: en + sEn, la };
}

/** Group-level name (no side / index) used by the quiz. */
export const groupName = (group) => ({ ar: G[group].ar, en: G[group].en });

export function boneInfo(b) {
  const g = G[b.group], n = b.index;
  const badges = [];
  badges.push({ k: "region", ...REGIONS.find((r) => r.id === g.region) });
  badges.push({ k: "type", ...TYPE[g.type] });
  badges.push(AXIAL.has(g.region) ? { ar: "الهيكل المحوري", en: "Axial skeleton" } : { ar: "الهيكل الطرفي", en: "Appendicular skeleton" });
  if (b.group === "rib") badges.push(n <= 7 ? { ar: "ضلع حقيقي", en: "True rib" } : n <= 10 ? { ar: "ضلع كاذب", en: "False rib" } : { ar: "ضلع سائب (عائم)", en: "Floating rib" });
  return { desc: { ar: g.d[0], en: g.d[1] }, fact: g.f ? { ar: g.f[0], en: g.f[1] } : null, badges };
}

export const UI = {
  ar: {
    title: "الهيكل العظمي ثلاثي الأبعاد", hint: "اسحب للتدوير • اقرص للتكبير • اضغط على أي عظمة لمعرفة اسمها",
    all: "الكل", search: "ابحث عن عظمة…", noResults: "لا توجد نتائج", reset: "إعادة الضبط", rotate: "دوران تلقائي", explode: "فك العظام",
    focus: "عزل العظمة", quiz: "اختبرني", fullscreen: "ملء الشاشة", close: "إغلاق", highlightAll: "إبراز كل عظام هذا النوع", highlighting: "إلغاء الإبراز",
    didYouKnow: "هل تعلم؟", loading: "جارٍ تجهيز الهيكل العظمي…", noWebgl: "متصفحك لا يدعم العرض ثلاثي الأبعاد (WebGL).",
    quizFind: "أين تجد:", quizScore: "الدرجة", quizSkip: "تخطي", quizStop: "إنهاء", quizOk: "أحسنت! ✔", quizNo: "هذه:", quizTry: "جرّب مرة أخرى",
    quizDone: "انتهى الاختبار", quizAgain: "اختبار جديد", quizOf: "من", total: "جسم البالغ فيه 206 عظمة — هنا {n} عظمة قابلة للاختيار",
    side: { L: "الجهة اليسرى", R: "الجهة اليمنى", M: "في المنتصف" },
  },
  en: {
    title: "3D Skeleton", hint: "Drag to rotate • pinch to zoom • tap any bone to learn its name",
    all: "All", search: "Search a bone…", noResults: "No results", reset: "Reset view", rotate: "Auto-rotate", explode: "Explode",
    focus: "Isolate bone", quiz: "Quiz me", fullscreen: "Fullscreen", close: "Close", highlightAll: "Highlight all of this kind", highlighting: "Clear highlight",
    didYouKnow: "Did you know?", loading: "Preparing the skeleton…", noWebgl: "Your browser doesn't support 3D (WebGL).",
    quizFind: "Find:", quizScore: "Score", quizSkip: "Skip", quizStop: "Stop", quizOk: "Nice! ✔", quizNo: "That's the", quizTry: "Try again",
    quizDone: "Quiz finished", quizAgain: "New quiz", quizOf: "of", total: "An adult has 206 bones — {n} selectable bones here",
    side: { L: "Left side", R: "Right side", M: "Midline" },
  },
};

export function regionOf(b) { return G[b.group].region; }
export function quizGroups() { return Object.keys(G).filter((k) => G[k].quiz); }

/** normalise Arabic/English text for searching */
export function norm(s) {
  return String(s || "").toLowerCase().replace(/[\u064B-\u065F\u0670]/g, "").replace(/[أإآ]/g, "ا").replace(/ى/g, "ي").replace(/ة/g, "ه").replace(/ـ/g, "");
}
