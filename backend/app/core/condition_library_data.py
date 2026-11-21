"""
GENOVEX Medical Condition Library Data
Authoritative clinical definitions, evidence classifications, references,
and bilingual (EN/AR) structured content for male reproductive health.
Synthesized from peer-reviewed clinical practice guidelines (WHO, EAU, AUA, ASRM, Endocrine Society).
"""

from datetime import datetime, timezone
from typing import List, Dict, Any

CATEGORIES_DATA = [
    {
        "slug": "scrotal-vascular",
        "name_en": "Scrotal & Vascular Pathology",
        "name_ar": "أمراض كيس الصفن والأوعية الدموية",
        "description_en": "Conditions affecting scrotal venous drainage, testicular temperature regulation and parenchymal perfusion.",
        "description_ar": "الحالات التي تؤثر على التصريف الوريدي للصفن، وتنظيم حرارة الخصية وتروية النسيج الخصوي.",
        "display_order": 1
    },
    {
        "slug": "endocrine-hormonal",
        "name_en": "Endocrine & Hormonal Disorders",
        "name_ar": "اضطرابات الغدد الصماء والهرمونات",
        "description_en": "Dysfunctions of the hypothalamic-pituitary-gonadal (HPG) axis governing testosterone and spermatogenesis.",
        "description_ar": "اختلالات المحور الوطائي النخامي التناسلي المنظم لهرمون التستوستيرون وتكوين الحيوانات المنوية.",
        "display_order": 2
    },
    {
        "slug": "genetic-chromosomal",
        "name_en": "Genetic & Chromosomal Anomalies",
        "name_ar": "التشوهات الجينية والصبغية",
        "description_en": "Karyotypic abnormalities, Y-chromosome microdeletions and single-gene mutations affecting testicular development.",
        "description_ar": "الاضطرابات الصبغية، الحذف الدقيق للكروموسوم Y والطفرات الجينية التي تؤثر على تطور الخصية.",
        "display_order": 3
    },
    {
        "slug": "obstructive-ductal",
        "name_en": "Obstructive & Ductal Pathology",
        "name_ar": "أمراض الانسداد والقنوات التناسلية",
        "description_en": "Physical or functional blockages along the epididymis, vas deferens or ejaculatory ducts.",
        "description_ar": "الانسدادات الميكانيكية أو الوظيفية على طول البربخ، الأسهر، أو القنوات الدافقة.",
        "display_order": 4
    },
    {
        "slug": "congenital-developmental",
        "name_en": "Congenital & Developmental Conditions",
        "name_ar": "الحالات الخلقية والتطورية",
        "description_en": "Anomalies of testicular descent and embryonic urogenital tract differentiation.",
        "description_ar": "تشوهات هبوط الخصية وتمايز الجهاز البولي التناسلي الجنيني.",
        "display_order": 5
    }
]

REFERENCES_DATA = [
    {
        "title": "EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
        "authors": "Minhas S, Bettocchi C, Boeri L, et al.",
        "journal_or_publisher": "European Association of Urology Guidelines Office",
        "publication_year": 2024,
        "doi_or_url": "https://uroweb.org/guidelines/sexual-and-reproductive-health",
        "guideline_body": "EAU",
        "evidence_classification": "Clinical Practice Guideline (WHO/AUA/EAU/ASRM)"
    },
    {
        "title": "Diagnosis and Treatment of Infertility in Men: AUA/ASRM Guideline",
        "authors": "Schlegel PN, Sigman M, Collura B, et al.",
        "journal_or_publisher": "Journal of Urology & Fertility and Sterility",
        "publication_year": 2021,
        "doi_or_url": "https://doi.org/10.1097/JU.0000000000001521",
        "guideline_body": "AUA / ASRM",
        "evidence_classification": "Level 1A (Systematic Review of RCTs)"
    },
    {
        "title": "WHO Laboratory Manual for the Examination and Processing of Human Semen (6th Edition)",
        "authors": "World Health Organization Reproductive Health and Research Group",
        "journal_or_publisher": "World Health Organization",
        "publication_year": 2021,
        "doi_or_url": "https://www.who.int/publications/i/item/9789240030787",
        "guideline_body": "WHO",
        "evidence_classification": "Clinical Practice Guideline (WHO/AUA/EAU/ASRM)"
    },
    {
        "title": "EAU Guidelines on Testicular Cancer",
        "authors": "Minhas S, Boeri L, et al.",
        "journal_or_publisher": "European Association of Urology Guidelines Office",
        "publication_year": 2024,
        "doi_or_url": "https://uroweb.org/guidelines/testicular-cancer",
        "guideline_body": "EAU",
        "evidence_classification": "Clinical Practice Guideline (WHO/AUA/EAU/ASRM)"
    },
    {
        "title": "EAU Guidelines on Urological Infections & Epididymitis",
        "authors": "Bonkat G, Bartoletti R, Bruyère F, et al.",
        "journal_or_publisher": "European Association of Urology Guidelines Office",
        "publication_year": 2024,
        "doi_or_url": "https://uroweb.org/guidelines/urological-infections",
        "guideline_body": "EAU",
        "evidence_classification": "Clinical Practice Guideline (WHO/AUA/EAU/ASRM)"
    },
    {
        "title": "Erectile Dysfunction: AUA Guideline",
        "authors": "Burnett AL, Nehra A, Breau RH, et al.",
        "journal_or_publisher": "Journal of Urology",
        "publication_year": 2018,
        "doi_or_url": "https://doi.org/10.1016/j.juro.2018.05.004",
        "guideline_body": "AUA",
        "evidence_classification": "Level 1A (Systematic Review of RCTs)"
    },
    {
        "title": "Testosterone Therapy in Men with Hypogonadism: An Endocrine Society Clinical Practice Guideline",
        "authors": "Bhasin S, Brito JP, Cunningham GR, et al.",
        "journal_or_publisher": "Journal of Clinical Endocrinology & Metabolism",
        "publication_year": 2018,
        "doi_or_url": "https://doi.org/10.1210/jc.2018-00229",
        "guideline_body": "Endocrine Society",
        "evidence_classification": "Clinical Practice Guideline (WHO/AUA/EAU/ASRM)"
    }
]

CONDITIONS_DATA: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # Condition 1: Varicocele (Baseline - PUBLISHED)
    # -------------------------------------------------------------------------
    {
        "slug": "varicocele",
        "category_slug": "scrotal-vascular",
        "organs_involved": ["Testes", "Pampiniform Venous Plexus", "Internal Spermatic Vein", "Scrotum"],
        "evidence_classification": "Level 1A",
        "publication_status": "PUBLISHED",
        "current_version": 2,
        "last_reviewed_at": datetime(2026, 10, 15, 10, 30, tzinfo=timezone.utc),
        "clinical_reviewer": "Dr. Tarek Al-Mansoor (Consultant Urologist & Andrologist, DHA Licensed)",
        "reference_titles": [
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
            "Diagnosis and Treatment of Infertility in Men: AUA/ASRM Guideline"
        ],
        "en": {
            "name": "Varicocele",
            "short_description": "Abnormal dilation and tortuosity of the pampiniform venous plexus within the scrotum, frequently causing progressive decline in sperm production.",
            "detailed_explanation": "Varicocele represents the most common surgically correctable cause of primary and secondary male factor reproductive impairment. Occurring in roughly 15% of the adult male population and up to 40% of men presenting with primary fertility challenges, varicoceles arise predominantly on the left hemiscrotum due to venous insertion angle into the left renal vein. Over time, persistent venous reflux creates localized hyperthermia and oxidative stress.",
            "biological_mechanism": "Incompetence or absence of venous valves in the internal spermatic vein allows retrograde pooling of warm core body blood. This elevates testicular temperature by 1.5°C to 2.5°C above the ideal physiologic thermoregulatory threshold (34°C). The resulting heat stress disrupts Sertoli and Leydig cell metabolism, increases reactive oxygen species (ROS), accelerates germ cell apoptosis, and produces substantial sperm DNA fragmentation.",
            "causes_and_risk_factors": "Anatomic factors: Insertion of left internal spermatic vein at a right angle into the left renal vein, absence of anti-reflux venous valves, 'nutcracker' compression between aorta and superior mesenteric artery. Risk exacerbators: Prolonged standing, chronic strenuous intra-abdominal pressure, and genetic predisposition to vascular connective tissue laxity.",
            "possible_symptoms": "Often completely asymptomatic. When symptoms occur: Dull, aching scrotal heaviness or dragging discomfort exacerbated by physical exertion or standing; palpable 'bag of worms' sensation above the testicle; or visible testicular size asymmetry (hypotrophy).",
            "silent_asymptomatic_presentation": "CRITICAL CLINICAL NOTICE: Up to 80% of clinical varicoceles produce NO noticeable pain or physical discomfort whatsoever. Men often discover the condition solely upon unexpected semen analysis abnormalities or during routine medical examination.",
            "clinical_significance": "Uncorrected grade II or III varicoceles can lead to progressive testicular volume loss and progressive deterioration of all semen parameters (oligoasthenoteratozoospermia) and elevated sperm DNA fragmentation indices.",
            "diagnostic_investigations": "High-resolution scrotal Doppler ultrasonography with Valsalva maneuver (venous diameter > 3.0 mm and reflux > 2 seconds); physical examination in both supine and upright positions; serial semen analysis (WHO 6th ed.); hormonal profiling (total testosterone, LH, FSH).",
            "clinical_next_steps": "Consultation with a verified Reproductive Urologist or Andrologist. Microsurgical subinguinal varicocelectomy is recommended when clinical varicocele is accompanied by abnormal semen parameters and fertility desire."
        },
        "ar": {
            "name": "دوالي الخصية (Varicocele)",
            "short_description": "تمدد وتوسع غير طبيعي في الأوردة المنوية داخل كيس الصفن، يُعد من أكثر أسباب تراجع إنتاج الحيوانات المنوية شيوعاً وقابلية للعلاج.",
            "detailed_explanation": "تعتبر دوالي الخصية السبب الأكثر شيوعاً القابل للتصحيح الجراحي لتأخر الإنجاب لدى الرجال. تحدث لدى حوالي 15٪ من عموم الرجال وتصل إلى 40٪ من الرجال الذين يراجعون لتقييم الخصوبة الأولية. تنشأ غالباً في الجانب الأيسر بسبب زاوية تصريف الوريد المنوي الأيسر داخل الوريد الكلوي. يؤدي الارتجاع الوريدي المستمر إلى ارتفاع حرارة الخصية وزيادة الإجهاد التأكسدي.",
            "biological_mechanism": "قصور أو غياب الصمامات في الوريد المنوي الداخلي يؤدي لركود الدم الوريدي وارتفاع درجة حرارة الخصية بنحو 1.5 إلى 2.5 درجة مئوية فوق المعدل الطبيعي (34 مئوية). يؤدي هذا الإجهاد الحراري لاختلال وظائف خلايا سيرتولي وليديج، وزيادة الجذور الحرة التفاعلية (ROS)، وتكسر المادة الوراثية للحيوانات المنوية (DNA Fragmentation).",
            "causes_and_risk_factors": "عوامل تشريحية: صب الوريد المنوي الأيسر بزاوية قائمة في الوريد الكلوي، غياب الصمامات الوريدية، متلازمة كسارة البندق الوعائية. عوامل مفاقمة: الوقوف لفترات طويلة، الإجهاد البدني المزمن، وضعف مرونة الأنسجة الوعائية.",
            "possible_symptoms": "غالباً لا توجد أي أعراض على الإطلاق. في حال ظهورها: ثقل أو ألم خفيف مستمر في كيس الصفن يزداد مع الوقوف أو بذل الجهد؛ ملمس يشبه 'كيس الديدان' فوق الخصية؛ أو ضمور ملحوظ في حجم الخصية.",
            "silent_asymptomatic_presentation": "تنبيه سريري هام: ما يصل إلى 80٪ من حالات دوالي الخصية السريرية صامتة تماماً ولا تسبب أي ألم أو انزعاج، ويتم اكتشافها صدفة عبر فحص السائل المنوي أو الفحص السريري الروتيني.",
            "clinical_significance": "قد تؤدي دوالي الخصية غير المعالجة من الدرجة الثانية أو الثالثة إلى ضمور تدريجي في حجم الخصية وتراجع مستمر في مؤشرات السائل المنوي (العدد، الحركة والتشوهات) وزيادة تكسر الحمض النووي.",
            "diagnostic_investigations": "فحص الموجات فوق الصوتية الملونة (دوبلر) للصفن مع مناورة فالسالفا (قطر وريدي > 3.0 مم مع ارتجاع > 2 ثانية)، الفحص السريري وقوفاً واستلقاءً، تحليل السائل المنوي وفق معايير منظمة الصحة العالمية، وفحص الهرمونات (التستوستيرون، LH، FSH).",
            "clinical_next_steps": "استشارة استشاري جراحة المسالك البولية والتناسلية وأمراض الذكورة. يوصى بالجراحة الميكروسكوبية لدوالي الخصية عند وجود دوالي سريرية مصحوبة بتأثر مؤشرات السائل المنوي."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 2: Hypogonadotropic Hypogonadism (Baseline - PUBLISHED)
    # -------------------------------------------------------------------------
    {
        "slug": "hypogonadotropic-hypogonadism",
        "category_slug": "endocrine-hormonal",
        "organs_involved": ["Hypothalamus", "Pituitary Gland", "Testes", "Leydig Cells"],
        "evidence_classification": "Level 1A",
        "publication_status": "PUBLISHED",
        "current_version": 1,
        "last_reviewed_at": datetime(2026, 9, 20, 14, 0, tzinfo=timezone.utc),
        "clinical_reviewer": "Dr. Fatima Al-Hashimi (Reproductive Endocrinologist, DOH Licensed)",
        "reference_titles": [
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
            "WHO Laboratory Manual for the Examination and Processing of Human Semen (6th Edition)"
        ],
        "en": {
            "name": "Hypogonadotropic Hypogonadism (Secondary Hypogonadism)",
            "short_description": "Central endocrine dysfunction characterized by deficient pituitary secretion of LH and FSH, causing low testosterone and severely impaired spermatogenesis.",
            "detailed_explanation": "Secondary or hypogonadotropic hypogonadism occurs when the hypothalamus fails to pulse gonadotropin-releasing hormone (GnRH) or the anterior pituitary fails to secrete luteinizing hormone (LH) and follicle-stimulating hormone (FSH). Because the testes lack hormonal stimulation, testosterone synthesis halts and germ cell maturation arrests, resulting in severe oligospermia or azoospermia.",
            "biological_mechanism": "Lacking LH stimulation, Leydig cells cannot synthesize testosterone. Simultaneously, lacking FSH stimulation, Sertoli cells cannot nourish developing spermatids. Unlike primary testicular failure where LH and FSH are elevated, secondary hypogonadism shows inappropriately low or normal gonadotropins despite profoundly depressed systemic testosterone levels.",
            "causes_and_risk_factors": "Congenital (Kallmann syndrome, ANOS1 mutations, idiopathic hypogonadotrophic hypogonadism); Acquired: Pituitary micro/macroadenomas, hyperprolactinemia, history of anabolic-androgenic steroid (AAS) abuse, severe metabolic syndrome, obesity, chronic opioid therapy, or hemochromatosis.",
            "possible_symptoms": "Subtle reduced libido, erectile dysfunction, decreased spontaneous morning erections, chronic physical fatigue, mood changes, loss of muscle mass, or delayed secondary sexual characteristics.",
            "silent_asymptomatic_presentation": "Subclinical presentations frequently lack obvious physical signs. In young athletic men with prior steroid exposure, the only apparent indicator may be completely normal physical appearance paired with zero sperm count (azoospermia) on testing.",
            "clinical_significance": "Highly significant because it is one of the few forms of profound male infertility that is often completely reversible with targeted gonadotropin therapy (hCG + rFSH) or GnRH pulsatile pump therapy.",
            "diagnostic_investigations": "Fasting early morning (8:00 AM) total and free testosterone (repeated on 2 separate occasions); serum LH and FSH; serum prolactin; thyroid panel (TSH); pituitary magnetic resonance imaging (MRI) with contrast if severe deficiency or visual changes are present.",
            "clinical_next_steps": "Formal consultation with an Endocrinologist and Reproductive Urologist. Discontinuation of exogenous androgens or opioids under medical supervision; initiation of gonadotropin therapy when fertility is desired."
        },
        "ar": {
            "name": "قصور الغدد التناسلية الثانوي (Hypogonadotropic Hypogonadism)",
            "short_description": "اختلال هرموني مركزي ناتج عن نقص إفراز هرموني LH و FSH من الغدة النخامية، مما يؤدي لانخفاض التستوستيرون وتوقف إنتاج الحيوانات المنوية.",
            "detailed_explanation": "يحدث قصور الغدد التناسلية المركزي أو الثانوي عندما يفشل الوطاء في إفراز الهرمون المطلق لموجهة الغدد التناسلية (GnRH) أو تفشل الغدة النخامية في إفراز هرموني LH و FSH. لعدم وجود التحفيز الهرموني للخصيتين، يتوقف إنتاج هرمون الذكورة وتتوقف نضوج الحيوانات المنوية، مما يؤدي لقلة شديدة أو انعدام الحيوانات المنوية في السائل المنوي.",
            "biological_mechanism": "في غياب هرمون LH، تفشل خلايا ليديج في تصنيع هرمون التستوستيرون. وفي غياب هرمون FSH، لا تستطيع خلايا سيرتولي تغذية وتطوير الحيوانات المنوية. على عكس القصور الأولي، تكون مستويات LH و FSH منخفضة أو طبيعية بشكل غير ملائم رغم الانخفاض الشديد لهرمون الذكورة.",
            "causes_and_risk_factors": "أسباب خلقية (متلازمة كالمان، طفرات ANOS1)؛ أسباب مكتسبة: أورام الغدة النخامية الغدية، ارتفاع هرمون الحليب (البرولاكتين)، الاستخدام السابق للمنشطات الستيرويدية لبناء الأجسام، متلازمة الأيض الشديدة، والسمنة المفرطة.",
            "possible_symptoms": "انخفاض الرغبة الجنسية، ضعف الانتصاب، قلة الانتصاب الصباحي، الإرهاق الجسدي المزمن، تقلبات المزاج، وتراجع الكتلة العضلية.",
            "silent_asymptomatic_presentation": "في كثير من الحالات، خاصة لدى الشباب والرياضيين الذين استخدموا منشطات سابقة، قد يبدو المظهر الخارجي طبيعياً تماماً بينما يكون عدد الحيوانات المنوية صفراً (انعدام النطاف) دون أي ألم سريري.",
            "clinical_significance": "يتميز هذا الاضطراب بأنه من الحالات النادرة لعقم الرجال الحاد القابل للعلاج والشفاء التام بواسطة العلاج الهرموني الموجه (hCG + FSH).",
            "diagnostic_investigations": "فحص هرمون التستوستيرون الكلي والحر صباحاً على مرتين منفصلتين؛ قياس LH و FSH؛ هرمون الحليب (البرولاكتين)؛ وظائف الغدة الدرقية؛ ورنين مغناطيسي للغدة النخامية (MRI) عند الحاجة.",
            "clinical_next_steps": "مراجعة استشاري الغدد الصماء واستشاري طب الذكورة والتناسل. إيقاف أي مركبات هرمونية خارجية تحت إشراف طبي والبدء في العلاج التعويضي بموجهات الغدد التناسلية لتحفيز إنتاج الحيوانات المنوية."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 3: Klinefelter Syndrome (Baseline - PUBLISHED)
    # -------------------------------------------------------------------------
    {
        "slug": "klinefelter-syndrome",
        "category_slug": "genetic-chromosomal",
        "organs_involved": ["Testes", "Seminiferous Tubules", "Leydig Cells"],
        "evidence_classification": "Level 1A",
        "publication_status": "PUBLISHED",
        "current_version": 1,
        "last_reviewed_at": datetime(2026, 8, 10, 11, 0, tzinfo=timezone.utc),
        "clinical_reviewer": "Dr. Omar Al-Zaabi (Clinical Geneticist, MOHAP Licensed)",
        "reference_titles": [
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
            "Diagnosis and Treatment of Infertility in Men: AUA/ASRM Guideline"
        ],
        "en": {
            "name": "Klinefelter Syndrome (47,XXY)",
            "short_description": "A sex chromosomal genetic variation where a male carries an additional X chromosome, leading to testicular dysgenesis, primary hypogonadism and azoospermia.",
            "detailed_explanation": "Klinefelter syndrome is the most prevalent genetic etiology of non-obstructive azoospermia, occurring in approximately 1 in 600 live male births. Most men are born with a 47,XXY constitution due to maternal or paternal meiotic nondisjunction. Progressive fibrosis and hyalinization of seminiferous tubules occur during puberty, leaving microorchidism and extensive germ cell depletion.",
            "biological_mechanism": "The presence of the extra X chromosome causes accelerated loss of germ cells during perinatal life and puberty. Extensive hyalinization obliterates seminiferous tubules while Leydig cell clusters exhibit hyperplasia and functional impairment, precipitating elevated gonadotropins (high FSH and LH) and low-normal or frankly low testosterone.",
            "causes_and_risk_factors": "Random meiotic nondisjunction event during parental gametogenesis. Not inherited from family history in the conventional sense; maternal age > 35 is an associated risk factor.",
            "possible_symptoms": "Small, firm testicles (< 4 mL volume), gynecomastia (enlarged breast tissue), tall stature with relatively long limbs (eunuchoid proportions), reduced facial and body hair, and metabolic predisposition to diabetes.",
            "silent_asymptomatic_presentation": "Up to 60-70% of men with Klinefelter syndrome remain UNDIAGNOSED throughout their lifetime due to mild, unnoticeable phenotype variations, often discovering the condition only upon fertility evaluation.",
            "clinical_significance": "Despite primary testicular failure and azoospermia, microdissection testicular sperm extraction (micro-TESE) can successfully retrieve viable sperm in approximately 45-50% of adult men with 47,XXY for intracytoplasmic sperm injection (ICSI).",
            "diagnostic_investigations": "Peripheral blood karyotype (cytogenetic analysis) with analysis of minimum 20-30 metaphase cells; serum FSH, LH, and total testosterone; bone mineral density (DEXA scan) to monitor osteopenia.",
            "clinical_next_steps": "Consultation with a Clinical Geneticist and Andrologist specialized in micro-TESE. Discussion of fertility preservation/sperm retrieval prior to testosterone replacement therapy initiation."
        },
        "ar": {
            "name": "متلازمة كلاينفلتر (47,XXY)",
            "short_description": "اضطراب صبغي وراثي ناتج عن وجود كروموسوم X إضافي لدى الذكر، مما يسبب خلل تكوين الخصية وقصوراً أولياً في وظائفها وانعدام النطاف.",
            "detailed_explanation": "تعد متلازمة كلاينفلتر السبب الوراثي الأكثر شيوعاً لانعدام الحيوانات المنوية غير الانسدادي، حيث تصيب حوالي 1 من كل 600 ولادة ذكور. يمتلك المصاب التركيب الصبغي 47,XXY بسبب عدم انفصال الكروموسومات أثناء الانقسام المنصف. خلال سن البلوغ، يحدث تليف تدريجي في الأنابيب المنوية للخصية وتراجع شديد في الخلايا الجرثومية المنتجة للحيوانات المنوية.",
            "biological_mechanism": "يتسبب كروموسوم X الإضافي في فقدان متسارع للخلايا الجرثومية. تتليف الأنابيب المنوية وتتراجع وظيفة خلايا ليديج، مما ينتج عنه ارتفاع كبير في الهرمونات المنشطة (ارتفاع شديد في FSH و LH) مع انخفاض التستوستيرون.",
            "causes_and_risk_factors": "خلل عشوائي في انفصال الكروموسومات أثناء تكوين الأمشاج لدى أحد الوالدين. ليست حالة وراثية متوارثة عائلياً بالمعنى التقليدي، وترتبط بزيادة عمر الأم.",
            "possible_symptoms": "صغر وصلابة حجم الخصيتين (< 4 مل)، التثدي (تضخم الثدي)، طول القامة مع طول نسبي في الأطراف، قلة شعر الوجه والجسد، وقابلية أيضية لاضطرابات السكر.",
            "silent_asymptomatic_presentation": "ما يصل إلى 60-70٪ من المصابين بمتلازمة كلاينفلتر لا يتم تشخيصهم طوال حياتهم بسبب التباين الكبير في الأعراض وخفتها، ويكتشف معظمهم الحالة صدفة عند إجراء فحوصات الإنجاب.",
            "clinical_significance": "على الرغم من انعدام الحيوانات المنوية في القذف، فإن الجراحة الميكروسكوبية لاستخلاص الحيوانات المنوية من الخصية (micro-TESE) تنجح في استخراج حيوانات منوية قابلة للتلقيح المجهري لدى 45-50٪ من المصابين.",
            "diagnostic_investigations": "فحص النمط النووي الوراثي للدم (Karyotyping)؛ قياس هرمونات الغدة النخامية (FSH و LH) وهرمون التستوستيرون؛ وفحص كثافة العظام (DEXA) للكشف عن هشاشة العظام.",
            "clinical_next_steps": "استشارة استشاري الوراثة السريرية واستشاري أمراض الذكورة المتخصص في المسح المجهري للخصية. تقييم فرص استخلاص الحيوانات المنوية بالتنسيق مع مركز إخصاب مرخص."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 4: Obstructive Azoospermia - CBAVD (Baseline - PENDING_REVIEW)
    # -------------------------------------------------------------------------
    {
        "slug": "obstructive-azoospermia-cbavd",
        "category_slug": "obstructive-ductal",
        "organs_involved": ["Vas Deferens", "Epididymis", "Seminal Vesicles"],
        "evidence_classification": "Level 2A",
        "publication_status": "PENDING_REVIEW",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
            "WHO Laboratory Manual for the Examination and Processing of Human Semen (6th Edition)"
        ],
        "en": {
            "name": "Congenital Bilateral Absence of the Vas Deferens (CBAVD)",
            "short_description": "An obstructive condition where both sperm transport ducts fail to develop properly, strongly linked to CFTR cystic fibrosis gene mutations.",
            "detailed_explanation": "CBAVD accounts for approximately 1-2% of male infertility cases and up to 6% of obstructive azoospermia. In this condition, testicular spermatogenesis is completely intact, but sperm cannot exit into the ejaculate due to absent vas deferens and atrophic seminal vesicles.",
            "biological_mechanism": "Mutations in the CFTR gene impair chloride and bicarbonate transport across developing epithelial cells in the wolffian duct, resulting in ductal plugging and failure of vas deferens elongation during early fetal organogenesis.",
            "causes_and_risk_factors": "Compound heterozygosity or homozygous mutations in the CFTR gene (cystic fibrosis transmembrane conductance regulator).",
            "possible_symptoms": "Typically zero symptoms. Men possess normal virilization, normal libido, and normal erection.",
            "silent_asymptomatic_presentation": "Strictly silent. Physical exam reveals non-palpable vas deferens bilaterally, and semen analysis demonstrates low volume (< 1.5 mL), acidic pH (< 7.2), and azoospermia.",
            "clinical_significance": "High clinical and genetic importance: Both the patient and female partner MUST undergo CFTR genetic screening before assisted reproduction to assess cystic fibrosis risk in offspring.",
            "diagnostic_investigations": "Targeted CFTR gene sequencing; transrectal ultrasound (TRUS) demonstrating seminal vesicle absence or hypoplasia; semen pH and fructose testing; physical palpation of the spermatic cord.",
            "clinical_next_steps": "Genetic counseling, percutaneous epididymal sperm aspiration (PESA) or testicular biopsy (TESA) for ICSI."
        },
        "ar": {
            "name": "الغياب الخلقي الثنائي للأسهر (CBAVD)",
            "short_description": "حالة انسداد خلقي لا تتطور فيها القنوات المنوية الناقلة على الجانبين، وترتبط ارتباطاً وثيقاً بطفرات جين التليف الكيسي (CFTR).",
            "detailed_explanation": "يمثل الغياب الخلقي للأسهر حوالي 1-2٪ من حالات عقم الرجال وما يصل إلى 6٪ من حالات انعدام الحيوانات المنوية الانسدادي. في هذه الحالة، يكون إنتاج الحيوانات المنوية داخل الخصية سليماً تماماً، لكنها لا تستطيع الخروج مع السائل المنوي لعدم وجود القنوات الناقلة.",
            "biological_mechanism": "تؤدي طفرات جين CFTR إلى اختلال نقل أيونات الكلوريد والبيكربونات في الخلايا الظهارية لقناة وولف الجنينية، مما يسبب انسدادها وفشل تكوين الوعاء الناقل والحويصلات المنوية.",
            "causes_and_risk_factors": "طفرات جينية في جين CFTR (منظم موصلية التليف الكيسي عبر الغشاء).",
            "possible_symptoms": "لا توجد أي أعراض عضوية؛ الخصائص الذكورية والانتصاب والرغبة الجنسية طبيعية تماماً.",
            "silent_asymptomatic_presentation": "حالة صامتة تماماً. يظهر الفحص السريري غياب الأسهر عند الجس، ويظهر تحليل السائل المنوي حجماً منخفضاً (< 1.5 مل) وحموضة مرتفعة (pH < 7.2) مع انعدام تام للحيوانات المنوية.",
            "clinical_significance": "أهمية وراثية وسريرية بالغة: يجب إجراء الفحص الجيني للزوجين قبل الشروع في الإخصاب لتفادي ولادة أطفال مصابين بمرض التليف الكيسي.",
            "diagnostic_investigations": "الفحص الجيني لتسلسل طفرات CFTR، السونار عبر الشرج (TRUS) لفحص الحويصلات المنوية، فحص حموضة وسكر الفركتوز في السائل المنوي، والفحص السريري للحبيل المنوي.",
            "clinical_next_steps": "استشارة وراثية متخصصة، وسحب الحيوانات المنوية من البربخ (PESA) أو الخصية (TESA) لاستخدامها في الحقن المجهري."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 5: Cryptorchidism (Baseline - DRAFT)
    # -------------------------------------------------------------------------
    {
        "slug": "cryptorchidism",
        "category_slug": "congenital-developmental",
        "organs_involved": ["Testes", "Inguinal Canal", "Abdomen"],
        "evidence_classification": "Level 1A",
        "publication_status": "DRAFT",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
            "WHO Laboratory Manual for the Examination and Processing of Human Semen (6th Edition)"
        ],
        "en": {
            "name": "Cryptorchidism (Undescended Testis)",
            "short_description": "Failure of one or both testes to descend into the scrotum during fetal development, leading to long-term risk of germ cell impairment and malignancy.",
            "detailed_explanation": "Cryptorchidism is the most frequent congenital anomaly of male genitalia, observed in 1-4% of full-term and up to 30% of premature male infants. While most spontaneously descend by 3-6 months of life, persistent cryptorchidism causes progressive degeneration of germ cells when the testicle remains exposed to higher abdominal temperatures.",
            "biological_mechanism": "Exposure to normal intra-abdominal temperature (37°C) instead of the cooler scrotal environment (33-34°C) causes progressive loss of Type A dark spermatogonia, impairing transformation into mature sperm-producing stem cells.",
            "causes_and_risk_factors": "Prematurity, low birth weight, maternal smoking or endocrine disruptor exposure, anatomical barriers (short spermatic vessels, patent processus vaginalis).",
            "possible_symptoms": "In adult men: Empty scrotal sac on one or both sides, history of childhood orchiopexy, or palpable nodule in the inguinal canal.",
            "silent_asymptomatic_presentation": "Adult men who underwent childhood orchiopexy may believe their reproductive health is fully normalized, unaware that unilateral cryptorchidism reduces fertility by 30% and bilateral cryptorchidism by up to 70%.",
            "clinical_significance": "Significantly elevated risk of both infertility and testicular germ cell tumors (seminoma/non-seminoma).",
            "diagnostic_investigations": "High-resolution ultrasound / MRI of the pelvis and inguinal canal; physical examination; serial semen analysis; annual testicular self-examination counseling.",
            "clinical_next_steps": "Urology referral for testicular assessment, semen analysis, and testicular cancer surveillance protocols."
        },
        "ar": {
            "name": "الخصية المعلقة / غير النازلة (Cryptorchidism)",
            "short_description": "فشل إحدى الخصيتين أو كلتيهما في النزول إلى كيس الصفن أثناء التطور الجنيني، مما يرفع احتمالية تراجع الخصوبة ومخاطر الأورام الخصوية.",
            "detailed_explanation": "تعد الخصية المعلقة من أكثر التشوهات التناسلية الخلقية شيوعاً لدى الذكور (1-4٪ من المواليد مكتملي النمو). بالرغم من هبوط بعضها تلقائياً في الأشهر الأولى، فإن بقاء الخصية معلقة يعرضها لدرجة حرارة البطن المرتفعة، مما يتسبب في تنكس تدريجي للخلايا الجرثومية.",
            "biological_mechanism": "تعرض الخصية لدرجة حرارة البطن (37 مئوية) بدلاً من حرارة الصفن المناسبة (33-34 مئوية) يؤدي لتلف الخلايا الجذعية المنتجة للنطاف (Type A Spermatogonia) وتراجع قدرتها على التمايز.",
            "causes_and_risk_factors": "الولادة المبكرة، نقص وزن الولادة، التعرض للملوثات الهرمونية أثناء الحمل، قصر الأوعية المنوية خلقياً.",
            "possible_symptoms": "لدى البالغين: خلو كيس الصفن من إحدى الخصيتين، أو وجود ندبة جراحية سابقة لعملية تثبيت الخصية في الطفولة.",
            "silent_asymptomatic_presentation": "قد يعتقد الرجل الذي أجرى جراحة تثبيت الخصية في طفولته أن خصوبته طبيعية تماماً، بينما تشير الدراسات إلى تأثر الخصوبة بنسبة 30٪ في الحالات الأحادية و 70٪ في الحالات الثنائية دون ظهور أعراض حالية.",
            "clinical_significance": "ارتفاع ملحوظ في احتمالية ضعف السائل المنوي بالإضافة لارتفاع خطر الإصابة بأورام الخصية مقارنة بعموم الرجال.",
            "diagnostic_investigations": "فحص السونار أو الرنين المغناطيسي للحوض والمنطقة الإربية، فحص السائل المنوي الشامل، وتدريب المريض على الفحص الذاتي الدوري للخصية.",
            "clinical_next_steps": "المتابعة مع استشاري المسالك البولية والتناسلية لإجراء تقييم شامل للسائل المنوي ومتابعة دورية لسلامة النسيج الخصوي."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 6: Testicular Torsion (EXPANSION - PENDING_REVIEW)
    # -------------------------------------------------------------------------
    {
        "slug": "testicular-torsion",
        "category_slug": "scrotal-vascular",
        "organs_involved": ["Testes", "Spermatic Cord", "Tunica Vaginalis", "Scrotum"],
        "evidence_classification": "Level 1A",
        "publication_status": "PENDING_REVIEW",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
            "EAU Guidelines on Urological Infections & Epididymitis"
        ],
        "en": {
            "name": "Testicular Torsion (Acute Spermatic Cord Twisting)",
            "short_description": "An acute urological emergency caused by axial rotation of the spermatic cord, producing sudden testicular ischemia and necrosis if not surgically treated within 4-6 hours.",
            "detailed_explanation": "Testicular torsion represents a critical urological emergency in which the mobile testis rotates along the axis of the spermatic cord, immediately obstructing venous outflow and rapidly progressing to arterial hypoperfusion and parenchymal infarction. Peak incidence occurs during early adolescence (12-18 years), although men of any age can be affected. Emergency surgical exploration and detorsion within 4 to 6 hours is paramount to salvage testicular tissue and preserve future endocrine and spermatogenic capacity.",
            "biological_mechanism": "Congenital 'bell-clapper' deformity (abnormally high investment of the tunica vaginalis over the spermatic cord) grants excessive rotational mobility. When twisting occurs (typically 180° to 720°), immediate venous occlusion causes profound venous hypertension, interstitial edema, microvascular thrombosis, and secondary arterial ischemia. Irreversible germ cell apoptosis and permanent Sertoli/Leydig cell loss commence after 4 to 6 hours of warm ischemia.",
            "causes_and_risk_factors": "Congenital bell-clapper anatomical variant; rapid pubertal testicular enlargement; vigorous physical exercise or direct scrotal trauma; sudden temperature changes inducing hyperactive cremasteric reflex contraction; previous episodes of transient intermittent torsion.",
            "possible_symptoms": "Sudden onset of severe, excruciating unilateral scrotal pain; high-riding, transversely oriented testis; progressive scrotal swelling, warmth, and erythema; nausea and vomiting; lower abdominal or ipsilateral groin pain; completely absent ipsilateral cremasteric reflex.",
            "silent_asymptomatic_presentation": "CRITICAL CLINICAL NOTICE: Acute testicular torsion is NEVER painless. However, intermittent testicular torsion manifests as recurrent, self-resolving episodes of sudden scrotal pain that mimic epididymitis or trauma before progressing to complete, irreversible cord strangulation.",
            "clinical_significance": "TIME-CRITICAL EMERGENCY: Testicular salvage rates exceed 90% if surgical detorsion is accomplished within 6 hours of symptom onset, declining sharply to under 50% at 12 hours and under 10% after 24 hours. Testicular loss causes permanent reduction in reproductive capacity and can trigger auto-immunogenic anti-sperm antibodies compromising the contralateral testis.",
            "diagnostic_investigations": "Immediate emergency clinical assessment (absent cremasteric reflex, high-riding transverse testis). Emergency high-resolution scrotal color Doppler ultrasonography (demonstrating absent or decreased parenchymal arterial flow). CRITICAL: Diagnostic imaging must NEVER delay emergency surgical exploration when clinical suspicion is high.",
            "clinical_next_steps": "EMERGENCY DEPARTMENT ADMISSION: Immediate surgical exploration, detorsion, and bilateral orchiopexy (surgical fixation of both the affected and contralateral testicles) by an on-call Urologist."
        },
        "ar": {
            "name": "انفتال الخصية / التواء الخصية (Testicular Torsion)",
            "short_description": "حالة طوارئ جراحية حادة تنتج عن التواء الحبل المنوي وانقطاع التروية الدموية عن الخصية، مما يستوجب التدخل الجراحي العاجل خلال 4-6 ساعات لإنقاذها.",
            "detailed_explanation": "يحدث انفتال الخصية عند دوران الخصية حول محور الحبل المنوي، مما يؤدي لانسداد الأوردة والشرايين المغذية للخصية وتوقف تدفق الدم. تعد الحالة أكثر شيوعاً لدى المراهقين والشباب (12-18 عاماً)، وتعتبر حالة طوارئ جراحية قصوى تستدعي التدخل الفوري لإنقاذ أنسجة الخصية والحفاظ على القدرة الإنجابية وإنتاج هرمون التستوستيرون.",
            "biological_mechanism": "وجود تشوه تشريحي خلقي ('تشوه لسان الجرس') يمنح الخصية حركة مفرطة. يؤدي التواء الحبل المنوي (180 إلى 720 درجة) لانسداد وريدي متبوع باحتقان شديد ونقص تروية شرياني، مما يسبب نقص أكسجين حاد في الخلايا الجرثومية وبدء موتها المبرمج خلال 4 إلى 6 ساعات.",
            "causes_and_risk_factors": "تشوه لسان الجرس الخلقي، النمو السريع للخصية خلال البلوغ، المجهود البدني الشديد أو الرضوض الصفنية، الانقباض المفاجئ لعضلة المشمرة بسبب البرودة، ووجود نوبات سابقة من الالتواء المتقطع المؤقت.",
            "possible_symptoms": "ألم حاد ومفاجئ وشديد جداً في كيس الصفن في جانب واحد؛ ارتفاع الخصية وتغير وضعيتها إلى الوضع الأفقي؛ تورم واحمرار سريع في كيس الصفن؛ غثيان وقيء؛ ألم في أسفل البطن؛ وغياب المنعكس المشمراني في الجانب المصاب.",
            "silent_asymptomatic_presentation": "تنبيه سريري حاسم: لا يكون انفتال الخصية الحاد صامتاً أبداً بل يتسم بألم مبرح. ولكن في حالات الالتواء المتقطع، قد يعاني المريض من نوبات ألم متكررة تزول تلقائياً، مما قد يؤدي لتشخيص خاطئ قبل حدوث الالتواء الكامل الدائم.",
            "clinical_significance": "عامل الوقت حاسم لإنقاذ الخصية: تبلغ نسبة إنقاذ الخصية أكثر من 90٪ إذا أجريت الجراحة خلال 6 ساعات، وتنخفض إلى أقل من 50٪ بعد 12 ساعة وأقل من 10٪ بعد 24 ساعة. يؤدي التأخر لضمور الخصية وتكون أجسام مضادة للحيوانات المنوية تؤثر على الخصية الأخرى.",
            "diagnostic_investigations": "الفحص السريري العاجل (غياب المنعكس المشمراني ووضعية الخصية الأفقية)؛ سونار دوبلر الملون الطارئ للصفن لتقييم التروية الدموية الشريانية. تحذير سريري: لا يجوز تأخير الجراحة الاستكشافية لإجراء الفحوصات التصويرية عند الاشتباه السريري القوي.",
            "clinical_next_steps": "التوجه فوراً لقسم الطوارئ في أقرب مستشفى: إجراء استكشاف جراحي عاجل، فك الالتواء وتثبيت الخصيتين جراحياً (Bilateral Orchiopexy) بواسطة استشاري جراحة المسالك البولية المناوب."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 7: Testicular Cancer & Masses (EXPANSION - PENDING_REVIEW)
    # -------------------------------------------------------------------------
    {
        "slug": "testicular-mass-cancer",
        "category_slug": "congenital-developmental",
        "organs_involved": ["Testes", "Seminiferous Tubules", "Retroperitoneal Lymph Nodes", "Scrotum"],
        "evidence_classification": "Level 1A",
        "publication_status": "PENDING_REVIEW",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "EAU Guidelines on Testicular Cancer",
            "Diagnosis and Treatment of Infertility in Men: AUA/ASRM Guideline"
        ],
        "en": {
            "name": "Testicular Tumors & Intratesticular Masses",
            "short_description": "Solid neoplasms arising within the testicular parenchyma, predominantly germ cell tumors, representing the most frequent malignancy in young men aged 15-40.",
            "detailed_explanation": "Testicular cancer represents the most common solid organ malignancy diagnosed in men between the ages of 15 and 40. Predominantly comprising germ cell tumors (seminomas and non-seminomatous germ cell tumors), testicular neoplasms usually present as a painless, firm intratesticular lump. Early detection through regular testicular self-examination enables early intervention, resulting in overall cure rates exceeding 95%.",
            "biological_mechanism": "Malignant transformation of primordial germ cells arrests normal spermatogenesis, typically preceded by germ cell neoplasia in situ (GCNIS). Abnormal chromosomal alterations (principally isochromosome 12p amplification) drive unrestrained cellular proliferation, architectural disorganization of seminiferous tubules, and eventual lymphatic or hematogenous dissemination.",
            "causes_and_risk_factors": "History of cryptorchidism (undescended testis, 4-8x elevated risk); prior personal history of testicular tumor in contralateral testicle; first-degree family history (father or brother); testicular dysgenesis syndrome (subfertility, hypospadias, microorchidism); Klinefelter syndrome.",
            "possible_symptoms": "Discrete, firm, non-tender or painless lump within either testicle; painless diffuse testicular enlargement; sensation of heaviness or dragging discomfort in the scrotum; dull ache in the lower abdomen, groin, or back (in retroperitoneal spread); gynecomastia (from beta-hCG secretion).",
            "silent_asymptomatic_presentation": "CRITICAL CLINICAL NOTICE: Up to 90% of testicular tumors present completely WITHOUT PAIN. Men frequently notice an incidental hard knot while showering or during routine examination, mistakenly assuming that the absence of pain indicates a harmless finding.",
            "clinical_significance": "HIGH ONCOLOGICAL IMPORTANCE: Extremely high cure rate (>95%) when diagnosed at clinical stage I, but untreated tumors can progress rapidly with retroperitoneal and distant visceral metastases. Sperm banking prior to orchiectomy and gonadotoxic oncological treatment is mandatory to preserve biological paternity.",
            "diagnostic_investigations": "High-resolution scrotal Doppler ultrasonography (solid hypoechoic intratesticular mass); serum tumor markers prior to orchiectomy: alpha-fetoprotein (AFP), beta-human chorionic gonadotropin (beta-hCG), and lactate dehydrogenase (LDH); contrast-enhanced CT of chest, abdomen, and pelvis for staging.",
            "clinical_next_steps": "URGENT UROLOGIC ONCOLOGY REFERRAL: Immediate consultation with a Urologist; counseling and urgent sperm cryopreservation; radical inguinal orchiectomy (trans-scrotal biopsy is strictly contraindicated)."
        },
        "ar": {
            "name": "أورام وكتل الخصية (Testicular Tumors & Masses)",
            "short_description": "أورام صلبة تنشأ داخل نسيج الخصية، معظمها أورام خلايا جرثومية، وتعد أكثر الأورام الخبيثة شيوعاً لدى الرجال بين 15 و 40 عاماً.",
            "detailed_explanation": "تعد أورام الخصية أكثر الأورام الصلبة شيوعاً لدى الشباب في سن الإنجاب (15-40 عاماً). تنقسم معظم هذه الأورام إلى أورام منوية (Seminoma) وغير منوية (Non-Seminoma)، وتظهر عادة ككتلة صلبة غير مؤلمة داخل الخصية. بفضل التشخيص المبكر عبر الفحص الذاتي المنتظم والعلاجات الحديثة، تتجاوز معدلات الشفاء التام 95٪.",
            "biological_mechanism": "تحول سرطاني في الخلايا الجرثومية الأولية يسبقه غالباً ورم الخلايا الجرثومية الموضعي (GCNIS). تؤدي الطفرات الوراثية وتضخيم الكروموسوم 12p إلى انقسام خلوي غير منضبط وتخريب لبنية الأنابيب المنوية، مع قابلية الانتشار اللمفاوي عبر العقد خلف البريتوان.",
            "causes_and_risk_factors": "تاريخ سابق للإصابة بالخصية المعلقة (يرفع الخطر بمقدار 4-8 أضعاف)، إصابة سابقة في الخصية المقابلة، وجود تاريخ عائلي من الدرجة الأولى (أب أو أخ)، متلازمة خلل تكوين الخصية، وعقم الرجال.",
            "possible_symptoms": "كتلة صلبة غير مؤلمة أو عقدة واضحة داخل نسيج إحدى الخصيتين؛ تضخم غير مؤلم في حجم الخصية؛ شعور بثقل أو سحب مستمر في كيس الصفن؛ ألم خفيف في أسفل البطن أو الظهر؛ وأحياناً تضخم الثديين (نتيجة إفراز هرمون hCG).",
            "silent_asymptomatic_presentation": "تنبيه سريري هام: ما يصل إلى 90٪ من أورام الخصية تظهر دون أي ألم سريري على الإطلاق، ويكتشفها الرجل صدفة أثناء الاستحمام أو الفحص الذاتي، ويظن خطأً أن غياب الألم يعني سلامة الكتلة.",
            "clinical_significance": "أهمية ورمية بالغة: معدلات الشفاء ممتازة (>95٪) عند الاكتشاف المبكر في المرحلة الأولى، بينما يؤدي الإهمال لانتشار الورم في البطن والرئتين. يجب إجراء التجميد الوقائي للحيوانات المنوية قبل استئصال الخصية لحفظ الخصوبة.",
            "diagnostic_investigations": "فحص السونار عالي الدقة للصفن لتمييز الكتل الصلبة من الأكياس؛ قياس دلالات الأورام في الدم (AFP، beta-hCG، LDH) قبل الجراحة؛ والأشعة المقطعية للصدر والبطن والحوض لتحديد مرحلة المرض.",
            "clinical_next_steps": "استشارة عاجلة مع استشاري جراحة أورام المسالك البولية: تجميد السائل المنوي لحفظ الخصوبة، يليه استئصال الخصية الجراحي عبر المنطقة الإربية (يُحظر تماماً أخذ خزعة عبر كيس الصفن)."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 8: Acute & Chronic Epididymo-Orchitis (EXPANSION - PENDING_REVIEW)
    # -------------------------------------------------------------------------
    {
        "slug": "acute-epididymo-orchitis",
        "category_slug": "obstructive-ductal",
        "organs_involved": ["Epididymis", "Testes", "Vas Deferens", "Scrotum"],
        "evidence_classification": "Level 1A",
        "publication_status": "PENDING_REVIEW",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "EAU Guidelines on Urological Infections & Epididymitis",
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility"
        ],
        "en": {
            "name": "Epididymo-Orchitis (Epididymal & Testicular Infection)",
            "short_description": "Acute or chronic infectious inflammation of the epididymis and testicle, frequently caused by ascending urethral pathogens and risking ductal scarring.",
            "detailed_explanation": "Epididymitis and epididymo-orchitis involve acute bacterial, viral, or non-infectious inflammatory destruction of the epididymal tubules and testicular parenchyma. In sexually active men under 35, ascending infection with sexually transmitted organisms (Chlamydia trachomatis, Neisseria gonorrhoeae) predominates, while in older men or following catheterization, coliform enteric bacteria (Escherichia coli) are typical.",
            "biological_mechanism": "Pathogens ascend retrogradely from the urethra through the ejaculatory ducts and vas deferens into the epididymal lumen. Marked neutrophilic infiltration causes mucosal edema, luminal occlusion, microabscesses, and parenchymal swelling. Chronic unresolved inflammation precipitates fibroblast proliferation, ductal fibrosis, and potential complete mechanical obstruction of sperm transit.",
            "causes_and_risk_factors": "Sexually transmitted infections (unprotected intercourse, multiple sexual partners); urinary tract infections or bladder outlet obstruction; indwelling urinary catheters or recent urological instrumentation; strenuous physical exertion with a full bladder causing retrograde urine reflux.",
            "possible_symptoms": "Gradual onset of localized scrotal pain (usually beginning along the posterior testicle); significant scrotal swelling, warmth, and skin redness; dysuria (painful urination) or urinary frequency; urethral discharge; fever or chills; reactive inflammatory hydrocele.",
            "silent_asymptomatic_presentation": "Subacute or chronic chlamydial epididymitis can present with only mild, fluctuating scrotal discomfort or low-grade aching that is ignored for months, silently resulting in bilateral epididymal tubule fibrosis and secondary obstructive azoospermia.",
            "clinical_significance": "Severe acute infection can lead to testicular abscess, parenchymal necrosis, or testicular atrophy. Long-term post-inflammatory scarring of the epididymal transit system is a leading etiology of acquired obstructive azoospermia and severe subfertility.",
            "diagnostic_investigations": "First-void urine nucleic acid amplification testing (NAAT) for Chlamydia trachomatis and Neisseria gonorrhoeae; mid-stream urine analysis and culture; high-resolution scrotal Doppler ultrasonography (demonstrating epididymal hypervascularity and ruling out testicular torsion).",
            "clinical_next_steps": "Prompt medical evaluation by a Urologist or Primary Care Physician: targeted empirical antibiotic therapy; partner notification and treatment; scrotal elevation and anti-inflammatory support; follow-up ultrasound if symptoms do not improve within 72 hours."
        },
        "ar": {
            "name": "التهاب البربخ والخصية (Epididymo-Orchitis)",
            "short_description": "التهاب جرثومي أو مناعي حاد يصيب البربخ وأنسجة الخصية، ينتج غالباً عن عدوى صاعدة من مجرى البول وقد يسبب انسداداً وتليفاً في القنوات المنوية.",
            "detailed_explanation": "يحدث التهاب البربخ والخصية نتيجة صعود الميكروبات من مجرى البول إلى القنوات المنوية. لدى الشباب النشطين جنسياً تحت سن 35، تعد العدوى المنقولة جنسياً (كالكلاميديا والسيلان) السبب الرئيسي، بينما تشيع بكتيريا المسالك البولية المعوية (مثل الإشريكية القولونية) لدى الأكبر سناً أو بعد القسطرة البولية.",
            "biological_mechanism": "صعود الجراثيم العكسي من الإحليل عبر الأسهر إلى قنوات البربخ يثير استجابة التهابية حادة، وتجمع الخلايا المناعية والوذمة، مما يسبب انسداداً ميكانيكياً في تجويف البربخ وتكون خراجات مجهرية وتليفاً لاحقاً قد يعيق مرور الحيوانات المنوية.",
            "causes_and_risk_factors": "العدوى المنقولة جنسياً، التهابات المسالك البولية وتضخم البروستاتا، القساطر البولية أو الإجراءات الجراحية للمسالك، وممارسة المجهود البدني مع امتلاء المثانة مما يسبب ارتجاع البول في الأسهر.",
            "possible_symptoms": "ألم تدريجي يتزايد في كيس الصفن (يبدأ غالباً خلف الخصية)؛ تورم واحمرار وسخونة في الصفن؛ حرقان وصعوبة في التبول؛ إفرازات إحليلية؛ حمى وقشعريرة؛ وتجمع مائي التهابي حول الخصية.",
            "silent_asymptomatic_presentation": "تنبيه سريري: قد تتطور عدوى الكلاميديا المزمنة بصورة صامتة وخفية دون أعراض حادة، وتكتفي بألم بسيط متقطع يتجاهله المريض، مما يؤدي لتليف تدريجي في البربخ وانسداد دائم للحيوانات المنوية.",
            "clinical_significance": "قد يؤدي الالتهاب الحاد الشديد لتكون خراج خصوي أو تلف في أنسجة الخصية، بينما يعد التليف والانسداد المزمن للبربخ من أبرز أسباب العقم الانسدادي المكتسب لدى الرجال.",
            "diagnostic_investigations": "فحص البول التراكمي الدقيق (NAAT) للكشف عن الكلاميديا والسيلان؛ زراعة البول وفحص الإفرازات؛ وفحص دوبلر الملون للصفن لتأكيد زيادة التروية الدموية ونفي انفتال الخصية بشكل قاطع.",
            "clinical_next_steps": "مراجعة فورية لطبيب المسالك البولية أو الرعاية الأولية: البدء الفوري بالمضادات الحيوية المناسبة؛ علاج الشريك لتفادي عودة العدوى؛ رفع كيس الصفن ومسكنات الالتهاب؛ ومتابعة سريرية بعد 72 ساعة."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 9: Hydrocele & Spermatocele (EXPANSION - PENDING_REVIEW)
    # -------------------------------------------------------------------------
    {
        "slug": "hydrocele-spermatocele",
        "category_slug": "scrotal-vascular",
        "organs_involved": ["Scrotum", "Tunica Vaginalis", "Epididymis"],
        "evidence_classification": "Level 2A",
        "publication_status": "PENDING_REVIEW",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
            "Diagnosis and Treatment of Infertility in Men: AUA/ASRM Guideline"
        ],
        "en": {
            "name": "Hydrocele & Spermatocele (Scrotal Fluid Collections)",
            "short_description": "Benign fluid collections within the tunica vaginalis (hydrocele) or a retention cyst of the epididymal head (spermatocele) producing painless scrotal enlargement.",
            "detailed_explanation": "A hydrocele represents an abnormal accumulation of serous fluid between the parietal and visceral layers of the tunica vaginalis surrounding the testis. A spermatocele is a benign, smooth retention cyst arising from the efferent ductules of the epididymal head, filled with milky fluid containing non-viable spermatozoa. Both conditions present as smooth, non-tender scrotal swelling and must be evaluated to exclude underlying pathology.",
            "biological_mechanism": "In communicating hydroceles, persistence of a patent processus vaginalis allows peritoneal fluid to flow into the scrotum. In non-communicating adult hydroceles, an imbalance between fluid production and lymphatic/venous reabsorption by the tunica vaginalis leads to progressive fluid accumulation. Spermatoceles arise from focal dilatation of efferent ductules secondary to partial obstruction or trauma.",
            "causes_and_risk_factors": "Patent processus vaginalis (congenital); prior scrotal or groin surgery (varicocelectomy lymphatic disruption, inguinal hernia repair); scrotal trauma; resolving epididymo-orchitis; chronic filarial lymphatic obstruction.",
            "possible_symptoms": "Painless, gradual, progressive enlargement of the hemiscrotum; sensation of scrotal heaviness or physical dragging; visible scrotal asymmetry; palpable distinct soft lump above and behind the testicle (spermatocele); positive transillumination test.",
            "silent_asymptomatic_presentation": "Virtually all hydroceles and spermatoceles develop slowly and painlessly over months to years. Men often ignore the swelling until significant physical bulk impairs daily activities, athletic performance, or clothing comfort.",
            "clinical_significance": "While hydroceles and spermatoceles are fundamentally benign and rarely impair intrinsic spermatogenesis, large tense collections can cause physical discomfort and secondary testicular temperature elevation. CRITICAL: A secondary 'reactive' hydrocele can mask an underlying testicular tumor or inflammatory mass.",
            "diagnostic_investigations": "Physical examination including scrotal transillumination (clear fluid glows translucent); high-resolution scrotal ultrasonography (essential to confirm simple anechoic fluid and verify that the underlying testicular parenchyma is completely normal and tumor-free).",
            "clinical_next_steps": "Consultation with a Urologist: Active surveillance for small, asymptomatic collections; surgical hydrocelectomy or spermatocelectomy if swelling causes significant physical symptoms or cosmetic distress (aspiration with sclerotherapy is generally avoided in reproductive-aged men)."
        },
        "ar": {
            "name": "القيلة المائية والقيلة المنوية (Hydrocele & Spermatocele)",
            "short_description": "تجمعات سائلية حميدة داخل أغشية الخصية (القيلة المائية) أو كيس احتباسي منوي في رأس البربخ (القيلة المنوية) يسبب تضخماً غير مؤلم في الصفن.",
            "detailed_explanation": "القيلة المائية هي تجمع غير طبيعي لسائل مصلي بين طبقات الغلالة الغمدية المحيطة بالخصية، بينما القيلة المنوية هي كيس حميد ينشأ من قنوات رأس البربخ ويحتوي على سائل حليبي به حيوانات منوية. كلاهما يظهر على شكل تضخم رخو غير مؤلم في كيس الصفن، ويجب فحصهما بدقة لنفي وجود أي مسببات باطنية كامنة.",
            "biological_mechanism": "تحدث القيلة المتصلة بسبب بقاء القناة الصفاقية الجنينية مفتوحة مما يسمح بنزول سائل البطن للصفن، بينما تنتج القيلة غير المتصلة لدى البالغين عن اختلال توازن إفراز وامتصاص السوائل عبر الأوعية اللمفاوية للغلالة. تنشأ القيلة المنوية من انسداد أو توسع موضعي في القنوات الصادرة للبربخ.",
            "causes_and_risk_factors": "بقاء الناتئ المهبلي مفتوحاً خلقياً، جراحات سابقة في الصفن والإربية (مثل جراحة الدوالي أو الفتق الإربي)، الرضوض المباشرة، الالتهابات السابقة في البربخ، والانسدادات اللمفاوية.",
            "possible_symptoms": "تضخم تدريجي غير مؤلم في كيس الصفن؛ شعور بثقل أو سحب ميكانيكي لأسفل؛ عدم تناظر ملحوظ في الصفن؛ كتلة دائرية ملساء منفصلة فوق الخصية (القيلة المنوية)؛ وإضاءة موجبة عند تسليط الضوء على الصفن (Transillumination).",
            "silent_asymptomatic_presentation": "تتطور القيلة المائية والمنوية ببطء شديد وبشكل صامت دون ألم على مدار أشهر أو سنوات، وقد لا يلاحظها المريض إلا عند زيادة حجمها لدرجة تؤثر على المظهر أو راحة المشي وارتداء الملابس.",
            "clinical_significance": "تعد هذه التجمعات حميدة ولا تؤثر بذاتها على إنتاج الحيوانات المنوية، ولكن التجمعات الكبيرة قد ترفع حرارة الخصية. تنبيه سريري هام: قد تتكون القيلة المائية كرد فعل ثانوي لإخفاء ورم خصوي كامن تحت السائل.",
            "diagnostic_investigations": "الفحص السريري واختبار نفاذية الضوء؛ فحص السونار عالي الدقة للصفن للتأكد من طبيعة السائل والتأكد القاطع من سلامة نسيج الخصية الداخلي من أي أورام.",
            "clinical_next_steps": "استشارة استشاري المسالك البولية: الملاحظة والمتابعة للحالات البسيطة الخالية من الأعراض؛ إجراء جراحة تصريف واستئصال كيس القيلة (Hydrocelectomy) في حال كبر الحجم أو الإزعاج الشديد (يُفضل تجنب الشفط بالإبرة للرجال في سن الإنجاب)."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 10: Male Factor Infertility (EXPANSION - PENDING_REVIEW)
    # -------------------------------------------------------------------------
    {
        "slug": "male-factor-infertility",
        "category_slug": "congenital-developmental",
        "organs_involved": ["Testes", "Seminiferous Tubules", "Epididymis", "Spermatozoa"],
        "evidence_classification": "Level 1A",
        "publication_status": "PENDING_REVIEW",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "WHO Laboratory Manual for the Examination and Processing of Human Semen (6th Edition)",
            "Diagnosis and Treatment of Infertility in Men: AUA/ASRM Guideline",
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility"
        ],
        "en": {
            "name": "Male Factor Infertility (Idiopathic & Primary Spermatogenic Impairment)",
            "short_description": "Inability to achieve clinical pregnancy after 12 months of regular unprotected intercourse due to semen parameter abnormalities or functional sperm deficits.",
            "detailed_explanation": "Male factor infertility contributes solely or co-contributes in approximately 50% of all couples experiencing delayed conception globally. Manifesting as oligozoospermia (low sperm count), asthenozoospermia (poor motility), teratozoospermia (abnormal morphology), or azoospermia (absence of sperm), male subfertility frequently occurs without obvious physical signs, reflecting multifactorial genetic, environmental, and testicular microenvironmental disruptions.",
            "biological_mechanism": "Impaired spermatogenesis arises from defective spermatogonial stem cell self-renewal, meiotic arrest, elevated reactive oxygen species (ROS) inducing sperm membrane lipid peroxidation, or elevated sperm DNA fragmentation indices. This compromises sperm transport, acrosome reaction, oocyte fertilization, and early embryonic developmental competence.",
            "causes_and_risk_factors": "Idiopathic etiology (30-40% of cases); advanced paternal age (>40); lifestyle factors (tobacco, shisha/dokha, obesity, metabolic syndrome); chronic scrotal hyperthermia; environmental endocrine disruptors; gonadotoxin exposures; uncorrected clinical varicocele; previous infections.",
            "possible_symptoms": "Strictly silent in the vast majority of cases. Men typically have completely normal sexual drive, normal penile erections, normal volume of ejaculate, and no physical testicular discomfort.",
            "silent_asymptomatic_presentation": "CRITICAL CLINICAL NOTICE: Over 90% of men with male factor infertility experience zero physical symptoms. The diagnosis is discovered exclusively through formal semen analysis following months or years of unsuccessful pregnancy attempts.",
            "clinical_significance": "Beyond delayed paternity, male infertility serves as an early biological window into overall male health. Subfertile men have significantly higher lifetime risks of cardiovascular disease, metabolic syndrome, osteoporosis, and testicular malignancy.",
            "diagnostic_investigations": "Comprehensive semen analysis performed according to WHO 6th Edition criteria (minimum of 2 independent samples collected 2-4 weeks apart); hormonal profile (early morning total testosterone, FSH, LH, prolactin); scrotal Doppler ultrasound; sperm DNA fragmentation testing (DFI); genetic screening (karyotype and Y-chromosome microdeletion) if sperm concentration < 5 million/mL.",
            "clinical_next_steps": "Comprehensive evaluation by a fellowship-trained Male Reproductive Urologist / Andrologist; lifestyle modification and antioxidant therapy; targeted assisted reproductive technology (IUI, IVF, ICSI) coordinated with a licensed fertility center."
        },
        "ar": {
            "name": "عقم الرجال الأولي وغير المفسر (Male Factor Infertility)",
            "short_description": "تأخر الإنجاب بعد 12 شهراً من العلاقة الزوجية المنتظمة دون موانع ناتج عن تراجع عدد أو حركة أو تشوهات الحيوانات المنوية أو خلل وظائفها.",
            "detailed_explanation": "يسهم العامل الذكوري منفرداً أو مشتركاً في حوالي 50٪ من إجمالي حالات تأخر الإنجاب لدى الأزواج. يظهر الخلل في صورة قلة الحيوانات المنوية (Oligozoospermia)، ضعف الحركة (Asthenozoospermia)، زيادة التشوهات (Teratozoospermia)، أو انعدام النطاف (Azoospermia)، وغالباً ما يحدث دون أي أعراض جسدية ظاهرة.",
            "biological_mechanism": "اختلال عملية تكوين الحيوانات المنوية ناتج عن توقف الانقسام المنصف، أو زيادة الإجهاد التأكسدي والجذور الحرة (ROS) المؤدية لتلف غشاء الحيوان المنوي وتكسر الحمض النووي (DNA Fragmentation)، مما يعيق تخصيب البويضة وانقسام الجنين.",
            "causes_and_risk_factors": "أسباب مجهولة وغير مفسرة (30-40٪)، تقدم عمر الأب (>40 عاماً)، التدخين والمدواخ، السمنة ومتلازمة الأيض، التعرض للحرارة المفرطة، الملوثات الكيميائية، ودوالي الخصية غير المشخصة.",
            "possible_symptoms": "حالة صامتة تماماً في الغالبية الساحقة من الرجال؛ الرغبة الجنسية والانتصاب والقذف والمظهر الخارجي طبيعية تماماً دون أي ألم.",
            "silent_asymptomatic_presentation": "تنبيه سريري هام: أكثر من 90٪ من حالات عقم الرجال تكون صامتة سريرياً ولا تسبب أي أعراض جسدية، ويتم اكتشافها حصرياً عبر فحص السائل المنوي بعد محاولات إنجاب غير ناجحة.",
            "clinical_significance": "تعد خصوبة الرجل مؤشراً حيوياً على صحته العامة؛ حيث أثبتت الدراسات أن الرجال الذين يعانون من تراجع مؤشرات السائل المنوي معرضون بنسب أعلى لأمراض القلب والسكري واضطرابات العظام وأورام الخصية مستقبلاً.",
            "diagnostic_investigations": "تحليل السائل المنوي الشامل مرتين منفصلتين وفق معايير منظمة الصحة العالمية (الإصدار السادس)؛ فحص الهرمونات صباحاً (التستوستيرون، FSH، LH، البرولاكتين)؛ دوبلر الصفن؛ فحص تكسر الحمض النووي؛ والفحص الجيني للكروموسومات وكروموسوم Y إذا قل العدد عن 5 ملايين/مل.",
            "clinical_next_steps": "مراجعة استشاري طب وجراحة الذكورة وتأخر الإنجاب؛ تعديل نمط الحياة والتغذية؛ واستخدام تقنيات الإخصاب المساعد المتقدمة (الحقن المجهري ICSI) بالتنسيق مع مركز إخصاب مرخص."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 11: Erectile Dysfunction (EXPANSION - PENDING_REVIEW)
    # -------------------------------------------------------------------------
    {
        "slug": "erectile-dysfunction",
        "category_slug": "endocrine-hormonal",
        "organs_involved": ["Penis", "Cavernous Arteries", "Corpora Cavernosa", "Endothelium"],
        "evidence_classification": "Level 1A",
        "publication_status": "PENDING_REVIEW",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "Erectile Dysfunction: AUA Guideline",
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility"
        ],
        "en": {
            "name": "Erectile Dysfunction (Vascular & Endocrine Impairment)",
            "short_description": "Persistent or recurrent inability to attain and/or maintain an erection sufficient for satisfactory sexual performance, with major reproductive implications.",
            "detailed_explanation": "Erectile dysfunction (ED) is defined as the consistent or recurrent inability to achieve or sustain a penile erection of sufficient rigidity for satisfactory sexual intercourse. Affecting over 30% of adult men to varying degrees, ED directly impairs natural conception and serves as an independent herald of systemic endothelial and cardiovascular disease.",
            "biological_mechanism": "Normal erection relies on nitric oxide (NO) release from cavernous non-adrenergic non-cholinergic (NANC) nerves and endothelial cells, activating guanylate cyclase and elevating cyclic GMP (cGMP) to relax cavernous smooth muscle. Endothelial dysfunction, androgen deficiency, arterial stenosis, or cavernosal veno-occlusive dysfunction disrupts this pathway, preventing adequate intracavernosal blood trapping.",
            "causes_and_risk_factors": "Atherosclerotic cardiovascular disease; diabetes mellitus (diabetic microangiopathy and neuropathy); hypertension; hypogonadism (low testosterone); medications (antihypertensives, 5-alpha reductase inhibitors such as finasteride, SSRIs); smoking; chronic psychogenic performance anxiety or depression.",
            "possible_symptoms": "Difficulty achieving full penile erection; reduced penile rigidity inadequate for penetration; rapid loss of erection prior to ejaculation; progressive reduction or absence of spontaneous nocturnal and early-morning erections.",
            "silent_asymptomatic_presentation": "Men often experience a gradual, insidious decline in erectile firmness over several years, initially attributing it to routine fatigue or stress, unaware that it reflects underlying systemic vascular microangiopathy.",
            "clinical_significance": "CRITICAL CARDIOVASCULAR WINDOW: Because penile helicine arteries measure 1-2 mm while coronary arteries measure 3-4 mm, atherosclerotic erectile dysfunction typically precedes coronary artery disease and acute myocardial infarction by 2 to 5 years ('artery size hypothesis').",
            "diagnostic_investigations": "Comprehensive cardiovascular risk evaluation (fasting blood glucose, HbA1c, lipid profile); fasting morning total and free testosterone; validated IIEF-5 assessment score; penile duplex Doppler ultrasonography with intracavernosal vasoactive injection when indicated.",
            "clinical_next_steps": "Evaluation by an Andrologist / Urologist and Primary Care / Cardiology: Lifestyle modification, management of cardiovascular risk factors; first-line oral phosphodiesterase type 5 (PDE5) inhibitors (tadalafil, sildenafil); hormonal optimization; vacuum devices or penile prostheses for refractory disease."
        },
        "ar": {
            "name": "ضعف الانتصاب (Erectile Dysfunction)",
            "short_description": "عدم القدرة المستمرة أو المتكررة على تحقيق أو الحفاظ على انتصاب كافٍ لإتمام العلاقة الزوجية، مما يؤثر مباشرة على الإنجاب والصحة العامة.",
            "detailed_explanation": "يُعرف ضعف الانتصاب بأنه عدم القدرة المتكررة على الوصول إلى انتصاب صلب أو الحفاظ عليه بما يكفي لإتمام اللقاء الجنسي. يصيب أكثر من 30٪ من الرجال بدرجات متفاوتة، ويعيق الإنجاب الطبيعي، كما يعتبر مؤشراً مبكراً ومستقلاً على صحة الشرايين والجهاز الدوري.",
            "biological_mechanism": "يعتمد الانتصاب الفسيولوجي على إفراز أكسيد النيتريك (NO) من بطانة الأوعية الدموية والأعصاب، مما يرفع مركب cGMP ويرخي عضلات الأجسام الكهفية ليتدفق الدم داخل القضيب. يؤدي اعتلال بطانة الأوعية أو نقص التستوستيرون أو التصلب الشرياني إلى فشل استرخاء العضلات وتسرب الدم الوريدي.",
            "causes_and_risk_factors": "تصلب الشرايين وأمراض القلب، مرض السكري، ارتفاع ضغط الدم والكوليسترول، نقص هرمون التستوستيرون، الأدوية (مضادات الضغط، أدوية تساقط الشعر مثل فيناسترايد، ومضادات الاكتئاب)، التدخين، والضغوط النفسية.",
            "possible_symptoms": "صعوبة في بدء الانتصاب؛ قلة صلابة القضيب بما يعيق الإيلاج؛ ارتخاء القضيب السريع قبل القذف؛ وتراجع أو غياب الانتصاب الصباحي التلقائي.",
            "silent_asymptomatic_presentation": "يتطور الضعف الوعائي تدريجياً على مدار سنوات، وغالباً ما يعزوه المريض للإرهاق اليومي دون إدراك أنه قد يكون علامة إنذار أولى على ضيق الشرايين الدقيقة في الجسم.",
            "clinical_significance": "مؤشر حيوي لسلامة القلب: نظراً لأن قطر شرايين القضيب (1-2 مم) أصغر من شرايين القلب التاجية (3-4 مم)، فإن ضعف الانتصاب يسبق حدوث الجلطات القلبية وأمراض الشرايين التاجية بـ 2 إلى 5 سنوات.",
            "diagnostic_investigations": "فحص عوامل خطورة القلب والأوعية (السكر التراكمي HbA1c، دهون الدم الكاملة)؛ فحص هرمون التستوستيرون الصباحي؛ استبيان IIEF-5 الدولي؛ وأشعة دوبلر الملونة لشرايين القضيب عند الحاجة.",
            "clinical_next_steps": "استشارة استشاري أمراض الذكورة والمسالك البولية وطبيب القلب: معالجة عوامل الخطورة الوعائية؛ استخدام مثبطات فوسفو داي إستراز-5 الفموية (مثل تادالافيل، سيلدينافيل)؛ وتنظيم الهرمونات."
        }
    },

    # -------------------------------------------------------------------------
    # Condition 12: Testosterone Deficiency Syndrome (EXPANSION - PENDING_REVIEW)
    # -------------------------------------------------------------------------
    {
        "slug": "testosterone-deficiency-syndrome",
        "category_slug": "endocrine-hormonal",
        "organs_involved": ["Testes", "Leydig Cells", "Hypothalamus", "Pituitary Gland"],
        "evidence_classification": "Level 1A",
        "publication_status": "PENDING_REVIEW",
        "current_version": 1,
        "clinical_reviewer": None,
        "reference_titles": [
            "Testosterone Therapy in Men with Hypogonadism: An Endocrine Society Clinical Practice Guideline",
            "EAU Guidelines on Sexual and Reproductive Health: Male Infertility"
        ],
        "en": {
            "name": "Testosterone Deficiency Syndrome (Male Hypogonadism)",
            "short_description": "A clinical and biochemical syndrome characterized by deficient androgen levels paired with reduced libido, fatigue, erectile dysfunction and impaired vitality.",
            "detailed_explanation": "Testosterone Deficiency Syndrome (TDS), also termed Late-Onset Hypogonadism or primary androgen deficiency, is a systemic disorder characterized by consistently low serum testosterone combined with clinical symptoms of androgen depletion. Arising from primary testicular Leydig cell failure, combined testicular and hypothalamic-pituitary senescence, or severe metabolic syndrome, TDS profoundly impairs sexual health, energy, and overall quality of life.",
            "biological_mechanism": "Decreased Leydig cell mass, impaired steroidogenic enzyme expression (CYP11A1, 3beta-HSD, CYP17A1), or excessive peripheral aromatization of androgens to estrogens in visceral adipose tissue depresses circulating free and total testosterone levels. This impairs androgen receptor activation across reproductive tissues, skeletal muscle, bone, and central neurocognitive centers.",
            "causes_and_risk_factors": "Visceral obesity and metabolic syndrome; type 2 diabetes mellitus; aging; chronic systemic illness; prior testicular trauma, mumps orchitis, or bilateral cryptorchidism; obstructive sleep apnea; chronic psychological stress.",
            "possible_symptoms": "Reduced sexual desire (libido); erectile dysfunction and reduced morning erections; persistent physical exhaustion and diminished vigor; loss of lean muscle mass and increased abdominal fat; mood changes, irritability, or depressive symptoms; impaired memory and concentration.",
            "silent_asymptomatic_presentation": "The onset of testosterone deficiency is typically insidious and progressive. Many men accept chronic low energy, fatigue, and diminishing sex drive as inevitable consequences of aging or work stress, delaying medical evaluation for years.",
            "clinical_significance": "CRITICAL FERTILITY AND METABOLIC HAZARD: Testosterone deficiency accelerates metabolic syndrome, visceral adiposity, and osteoporosis. CRITICAL WARNING: Exogenous testosterone therapy (TRT) suppresses LH/FSH and halts spermatogenesis, causing azoospermia; men seeking fertility must NEVER receive testosterone injections or gels.",
            "diagnostic_investigations": "Fasting morning (8:00–10:00 AM) serum total testosterone repeated on at least 2 separate occasions; serum free or bioavailable testosterone; serum LH and FSH (to differentiate primary testicular failure from central secondary hypogonadism); serum prolactin; complete metabolic and lipid panel.",
            "clinical_next_steps": "Consultation with a Consultant Andrologist or Endocrinologist: Weight loss and lifestyle optimization; for men desiring fertility: off-label gonadotropin therapy (hCG, rFSH) or SERMs (clomiphene citrate); for men with completed families: supervised testosterone replacement therapy (TRT)."
        },
        "ar": {
            "name": "متلازمة نقص التستوستيرون وقصور الذكورة (Testosterone Deficiency Syndrome)",
            "short_description": "متلازمة سريرية ومخبرية تتسم بنقص هرمون الذكورة مصحوباً بانخفاض الرغبة الجنسية، والإرهاق المستمر، وضعف الانتصاب وتراجع الحيوية.",
            "detailed_explanation": "تعتبر متلازمة نقص هرمون التستوستيرون (قصور الغدد التناسلية الأولي أو المتأخر) اضطراباً جهازياً يتميز بانخفاض مستويات هرمون الذكورة في الدم مع ظهور أعراض سريرية واضحة. ينتج عن قصور في خلايا ليديج بالخصية، أو الشيخوخة الفسيولوجية، أو متلازمة الأيض والسمنة المفرطة، مما ينعكس سلباً على الصحة الجنسية والبدنية والنفسية.",
            "biological_mechanism": "تراجع عدد وكفاءة خلايا ليديج بالخصية أو زيادة تحول التستوستيرون إلى إستروجين بواسطة إنزيم الأروماتاز في الدهون الحشوية يؤدي لانخفاض هرمون الذكورة الحر، مما يضعف ارتباطه بمستقبلات الأندروجين في العضلات والعظام والدماغ والأعضاء التناسلية.",
            "causes_and_risk_factors": "السمنة المفرطة وتراكم الدهون الحشوية، مرض السكري من النوع الثاني، التقدم في العمر، الأمراض المزمنة، إصابات الخصية أو التهابها الفيروسي السابق (النكاف)، وانقطاع التنفس الانسدادي أثناء النوم.",
            "possible_symptoms": "انخفاض الرغبة الجنسية؛ ضعف الانتصاب وقلة الانتصاب الصباحي؛ الشعور المستمر بالإرهاق والخمول البدني؛ تراجع الكتلة العضلية وزيادة دهون البطن؛ تقلبات المزاج والاكتئاب؛ وضعف التركيز والذاكرة.",
            "silent_asymptomatic_presentation": "يتسلل نقص التستوستيرون ببطء شديد على مدار سنوات، ويعتقد كثير من الرجال خطأً أن تراجع طاقتهم ورغبتهم الجنسية أمر طبيعي ناتج عن ضغوط العمل أو التقدم في السن دون إدراك وجود سبب هرموني قابل للعلاج.",
            "clinical_significance": "تحذير سريري حاسم للخصوبة: يرتبط نقص التستوستيرون بهشاشة العظام وأمراض القلب. تحذير هام: يُحظر إعطاء حقن أو دهانات التستوستيرون التعويضية للرجل الراغب في الإنجاب، لأنها توقف إفراز هرمونات النخامية وتؤدي لانعدام تام للحيوانات المنوية.",
            "diagnostic_investigations": "فحص هرمون التستوستيرون الكلي والحر صباحاً (8-10 صباحاً) على مرتين منفصلتين؛ قياس هرموني LH و FSH (للتمييز بين القصور الأولي في الخصية والقصور الثانوي في النخامية)؛ هرمون الحليب (البرولاكتين)؛ وفحص السكر والدهون.",
            "clinical_next_steps": "استشارة استشاري أمراض الذكورة أو استشاري الغدد الصماء: تخفيف الوزن وتعديل نمط الحياة؛ للراغبين بالإنجاب: استخدام محفزات الخصية مثل hCG أو الكلوميفين؛ للرجال الذين لا يرغبون بالإنجاب: العلاج التعويضي بهرمون التستوستيرون (TRT) تحت إشراف دقيق."
        }
    }
]
