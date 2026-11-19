from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import SessionLocal, Base, engine
from app.models.questionnaire import (
    QuestionnaireVersion, Question, QuestionnaireStatus, 
    QuestionDomain, QuestionType
)
from app.core.security import User, RoleEnum

def seed_questionnaire_v1(db: Session):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # Check if Version 1.0.0 exists
    existing = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.version_tag == "v1.0.0").first()
    if existing:
        print("Questionnaire Version v1.0.0 already exists. Skipping questionnaire seed.")
        return

    print("Seeding GENOVEX 11-Domain Adaptive Questionnaire Engine (v1.0.0)...")

    # Fetch Clinician user for approval
    clinician = db.query(User).filter(User.role == RoleEnum.CLINICIAN).first()

    version = QuestionnaireVersion(
        version_tag="v1.0.0",
        title_en="GENOVEX Comprehensive Male Reproductive Health Questionnaire",
        title_ar="استبيان جينوفيكس الشامل لصحة الرجل الإنجابية",
        status=QuestionnaireStatus.PUBLISHED,
        published_at=datetime.now(timezone.utc),
        clinical_reviewer_id=clinician.id if clinician else None,
        clinical_reviewer_notes="Reviewed and approved according to EAU Male Reproductive Health Guidelines (2024), AUA/ASRM Infertility Standards, and WHO 6th Edition."
    )
    db.add(version)
    db.flush()

    order = 1
    questions_data = [
        # =====================================================================
        # DOMAIN 1: BASIC HEALTH INFORMATION
        # =====================================================================
        {
            "domain_code": QuestionDomain.BASIC_HEALTH,
            "question_key": "Q_AGE",
            "text_en": "What is your current age in years?",
            "text_ar": "ما هو عمرك الحالي بالسنوات؟",
            "help_text_en": "Paternal age over 40-45 is associated with increased sperm DNA fragmentation and time to pregnancy.",
            "help_text_ar": "يرتبط تقدم عمر الأب فوق 40-45 سنة بزيادة تكسر الحمض النووي للنطاف وزيادة فترة انتظار الحمل.",
            "question_type": QuestionType.NUMERIC,
            "options_json": [],
            "clinical_rationale_en": "Age-related reproductive decline (paternal age effect) affects DNA integrity and embryo quality.",
            "clinical_rationale_ar": "تأثير تقدم العمر على جودة المادة الوراثية وتطور الأجنة.",
            "evidence_references": ["EAU Sexual & Reproductive Health Guidelines 2024", "WHO Semen Manual 6th Ed"],
            "display_order": 1,
            "is_urgent_red_flag": False
        },
        {
            "domain_code": QuestionDomain.BASIC_HEALTH,
            "question_key": "Q_BMI_CATEGORY",
            "text_en": "How would you describe your body composition / weight category?",
            "text_ar": "كيف تصف تكوين جسمك / فئة وزنك؟",
            "help_text_en": "Elevated adiposity increases aromatase conversion of testosterone into estradiol.",
            "help_text_ar": "زيادة الأنسجة الدهنية ترفع تحول التستوستيرون إلى إستروجين عبر إنزيم الأروماتاز.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "underweight", "label_en": "Underweight (BMI < 18.5)", "label_ar": "نقص في الوزن (كتلة الجسم < 18.5)", "order": 1},
                {"key": "normal", "label_en": "Normal weight (BMI 18.5 - 24.9)", "label_ar": "وزن طبيعي (كتلة الجسم 18.5 - 24.9)", "order": 2},
                {"key": "overweight", "label_en": "Overweight (BMI 25.0 - 29.9)", "label_ar": "زيادة في الوزن (كتلة الجسم 25.0 - 29.9)", "order": 3},
                {"key": "obese", "label_en": "Obese (BMI >= 30.0)", "label_ar": "سمنة (كتلة الجسم >= 30.0)", "order": 4}
            ],
            "clinical_rationale_en": "Obesity alters the hypothalamic-pituitary-gonadal axis, causing secondary hypogonadism.",
            "clinical_rationale_ar": "تؤدي السمنة إلى اختلال المحور الهرموني للغدد التناسلية.",
            "evidence_references": ["AUA/ASRM Male Infertility Guideline 2021"],
            "display_order": 2,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 2: REPRODUCTIVE HISTORY
        # =====================================================================
        {
            "domain_code": QuestionDomain.REPRODUCTIVE_HISTORY,
            "question_key": "Q_ATTEMPT_DURATION",
            "text_en": "How long have you and your partner been attempting pregnancy without contraception?",
            "text_ar": "كم المدة التي تحاول فيها أنت وشريكتك تحقيق الحمل دون استخدام موانع؟",
            "help_text_en": "Clinical evaluation is formally indicated after 12 months (or 6 months if partner age > 35).",
            "help_text_ar": "يوصى بالتقييم السريري بعد 12 شهراً من المحاولة (أو 6 أشهر إذا كان عمر الزوجة فوق 35).",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "less_than_6m", "label_en": "Less than 6 months", "label_ar": "أقل من 6 أشهر", "order": 1},
                {"key": "6_to_12m", "label_en": "6 to 12 months", "label_ar": "من 6 إلى 12 شهراً", "order": 2},
                {"key": "12_to_24m", "label_en": "1 to 2 years", "label_ar": "من سنة إلى سنتين", "order": 3},
                {"key": "more_than_2y", "label_en": "More than 2 years", "label_ar": "أكثر من سنتين", "order": 4},
                {"key": "not_actively_trying", "label_en": "Not actively trying (Proactive awareness)", "label_ar": "لا نحاول حالياً (توعية استباقية)", "order": 5}
            ],
            "clinical_rationale_en": "Standard definition of infertility per WHO/EAU/AUA requires duration classification.",
            "clinical_rationale_ar": "التعريف الطبي المعياري لتأخر الإنجاب وفق منظمة الصحة العالمية والجمعيات الدولية.",
            "evidence_references": ["WHO Semen Manual 6th Ed", "EAU Guidelines 2024"],
            "display_order": 3,
            "is_urgent_red_flag": False
        },
        {
            "domain_code": QuestionDomain.REPRODUCTIVE_HISTORY,
            "question_key": "Q_PREVIOUS_PATERNITY",
            "text_en": "Have you ever achieved a biological pregnancy (fathered a child) in the past?",
            "text_ar": "هل سبق لك تحقيق حمل بيولوجي (إنجاب طفل) في الماضي؟",
            "help_text_en": "Differentiates primary male factor impairment from secondary (acquired) impairment.",
            "help_text_ar": "يميز بين تأخر الإنجاب الأولي وتأخر الإنجاب الثانوي المكتسب.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes", "label_en": "Yes (Secondary Infertility)", "label_ar": "نعم (تأخر إنجاب ثانوي)", "order": 1},
                {"key": "no", "label_en": "No (Primary Infertility)", "label_ar": "لا (تأخر إنجاب أولي)", "order": 2}
            ],
            "clinical_rationale_en": "Secondary subfertility frequently implicates progressive pathologies such as varicocele or acquired hypogonadism.",
            "clinical_rationale_ar": "تأخر الإنجاب الثانوي يشير غالباً لأسباب تطورية مثل دوالي الخصية أو القصور الهرموني المكتسب.",
            "evidence_references": ["AUA/ASRM Guideline 2021"],
            "display_order": 4,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 3: TESTICULAR HISTORY & URGENT SAFETY PATHWAY
        # =====================================================================
        {
            "domain_code": QuestionDomain.TESTICULAR_HISTORY,
            "question_key": "Q_ACUTE_SCROTAL_PAIN",
            "text_en": "Are you currently experiencing sudden, severe scrotal pain or acute scrotal swelling?",
            "text_ar": "هل تعاني حالياً من ألم مفاجئ وشديد في الخصية أو تورم حاد في كيس الصفن؟",
            "help_text_en": "RED FLAG: Acute scrotal pain may indicate testicular torsion requiring immediate emergency evaluation within 6 hours.",
            "help_text_ar": "علامة خطر حمراء: قد يشير الألم الحاد لالتواء الخصية الذي يتطلب تدخلاً جراحياً طارئاً خلال 6 ساعات.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes", "label_en": "Yes (Acute Pain / Swelling)", "label_ar": "نعم (ألم حاد / تورم مفاجئ)", "order": 1},
                {"key": "no", "label_en": "No", "label_ar": "لا", "order": 2}
            ],
            "clinical_rationale_en": "Immediate emergency safety triaging for acute testicular ischemia/torsion.",
            "clinical_rationale_ar": "فرز طوارئ فوري للاشتباه في التواء الخصية ونقص التروية الدموية الحاد.",
            "evidence_references": ["EAU Paediatric & Adult Urology Emergency Guidelines 2024"],
            "display_order": 5,
            "is_urgent_red_flag": True
        },
        {
            "domain_code": QuestionDomain.TESTICULAR_HISTORY,
            "question_key": "Q_PAINLESS_TESTIS_LUMP",
            "text_en": "Have you noticed any new, firm or painless lump within either testicle?",
            "text_ar": "هل لاحظت أي كتلة صلبة أو غير مؤلمة جديدة داخل إحدى الخصيتين؟",
            "help_text_en": "RED FLAG: A solid painless intratesticular mass requires urgent scrotal ultrasound to rule out testicular neoplasm.",
            "help_text_ar": "علامة خطر حمراء: تتطلب الكتل الصلبة غير المؤلمة فحص سونار عاجل لاستبعاد أورام الخصية.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes", "label_en": "Yes (Noticeable Lump)", "label_ar": "نعم (كتلة ملحوظة)", "order": 1},
                {"key": "no", "label_en": "No", "label_ar": "لا", "order": 2}
            ],
            "clinical_rationale_en": "Urgent oncologic triaging; 10% of testicular cancers present during fertility evaluations.",
            "clinical_rationale_ar": "فرز سريري عاجل للأورام؛ تكتشف نسبة من أورام الخصية صدفة أثناء فحوصات الإنجاب.",
            "evidence_references": ["EAU Testicular Cancer Guidelines 2024"],
            "display_order": 6,
            "is_urgent_red_flag": True
        },
        {
            "domain_code": QuestionDomain.TESTICULAR_HISTORY,
            "question_key": "Q_TESTIS_SURGERY",
            "text_en": "Have you ever had surgery on your testicles, scrotum, or groin area?",
            "text_ar": "هل سبق لك الخضوع لعملية جراحية في الخصيتين، كيس الصفن، أو المنطقة الإربية؟",
            "help_text_en": "Prior surgery may involve orchiopexy, varicocelectomy, or inadvertent vasal injury during hernia repair.",
            "help_text_ar": "تشمل الجراحات السابقة تثبيت الخصية، دوالي الخصية، أو إصابة القناة الناقلة أثناء علاج الفتق.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes", "label_en": "Yes", "label_ar": "نعم", "order": 1},
                {"key": "no", "label_en": "No", "label_ar": "لا", "order": 2}
            ],
            "clinical_rationale_en": "Prior groin/scrotal surgery is a major risk factor for ductal obstruction or testicular atrophy.",
            "clinical_rationale_ar": "جراحات كيس الصفن والمنطقة الإربية تعد عامل خطورة رئيسياً لانسداد القنوات أو ضمور الخصية.",
            "evidence_references": ["EAU Male Infertility Guidelines 2024"],
            "display_order": 7,
            "is_urgent_red_flag": False
        },
        # Conditional follow-up for surgery:
        {
            "domain_code": QuestionDomain.TESTICULAR_HISTORY,
            "question_key": "Q_TESTIS_SURGERY_TYPE",
            "text_en": "What type of scrotal or groin surgery did you undergo?",
            "text_ar": "ما هو نوع العملية الجراحية التي خضعت لها في كيس الصفن أو المنطقة الإربية؟",
            "help_text_en": "Select the surgical procedure documented in your medical records.",
            "help_text_ar": "حدد الإجراء الجراحي المسجل في سجلك الطبي.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "undescended_testis", "label_en": "Undescended Testicle Surgery (Orchidopexy)", "label_ar": "تثبيت الخصية المعلقة (Orchidopexy)", "order": 1},
                {"key": "varicocelectomy", "label_en": "Varicocele Repair (Varicocelectomy)", "label_ar": "عملية دوالي الخصية (Varicocelectomy)", "order": 2},
                {"key": "hernia_repair", "label_en": "Inguinal Hernia Repair", "label_ar": "إصلاح الفتق الإربي", "order": 3},
                {"key": "hydrocele", "label_en": "Hydrocele / Spermatocele Repair", "label_ar": "إزالة القيلة المائية (Hydrocele)", "order": 4},
                {"key": "other_scrotal", "label_en": "Other Scrotal Surgery", "label_ar": "جراحة خصوية أخرى", "order": 5}
            ],
            "clinical_rationale_en": "Identifies specific pathophysiologic mechanism: congenital germ cell loss vs. iatrogenic obstruction.",
            "clinical_rationale_ar": "يحدد الآلية المرضية المحددة: تلف الخلايا الجرثومية الخلقي مقابل الانسداد الجراحي.",
            "evidence_references": ["EAU Guidelines 2024", "AUA Guidelines 2021"],
            "display_order": 8,
            "is_urgent_red_flag": False,
            "conditional_parent_key": "Q_TESTIS_SURGERY",
            "conditional_trigger_values": ["yes"]
        },

        # =====================================================================
        # DOMAIN 4: MEDICAL HISTORY & SYSTEMIC ILLNESS
        # =====================================================================
        {
            "domain_code": QuestionDomain.MEDICAL_HISTORY,
            "question_key": "Q_CHRONIC_DISEASES",
            "text_en": "Have you been diagnosed with any of the following systemic medical conditions?",
            "text_ar": "هل تم تشخيصك بأي من الحالات الطبية المزمنة التالية؟",
            "help_text_en": "Systemic diseases contribute to autonomic neuropathy, endocrine failure, or oxidative testicular stress.",
            "help_text_ar": "تساهم الأمراض الجهازية في اعتلال الأعصاب الذاتي، القصور الهرموني، أو الإجهاد التأكسدي.",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "options_json": [
                {"key": "none", "label_en": "None of these", "label_ar": "لا يوجد أي مما سبق", "order": 1},
                {"key": "diabetes", "label_en": "Diabetes Mellitus (Type 1 or Type 2)", "label_ar": "داء السكري (النوع الأول أو الثاني)", "order": 2},
                {"key": "hypertension", "label_en": "Hypertension (High Blood Pressure)", "label_ar": "ارتفاع ضغط الدم", "order": 3},
                {"key": "renal_disease", "label_en": "Chronic Kidney Disease", "label_ar": "أمراض الكلى المزمنة", "order": 4},
                {"key": "liver_disease", "label_en": "Chronic Liver Disease / Cirrhosis", "label_ar": "أمراض الكبد المزمنة", "order": 5},
                {"key": "childhood_chemo", "label_en": "Prior Chemotherapy or Radiation", "label_ar": "علاج كيماوي أو إشعاعي سابق", "order": 6}
            ],
            "clinical_rationale_en": "Diabetes causes retrograde ejaculation and high sperm DNA fragmentation; chemo causes permanent germ cell depletion.",
            "clinical_rationale_ar": "السكري يسبب القذف الارتجاعي وتكسر الحمض النووي، والعلاج الكيماوي يسبب فقدان الخلايا الجرثومية.",
            "evidence_references": ["EAU Guidelines 2024", "WHO Semen Manual 6th Ed"],
            "display_order": 9,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 5: HORMONAL HEALTH & ENDOCRINE STATUS
        # =====================================================================
        {
            "domain_code": QuestionDomain.HORMONAL_HEALTH,
            "question_key": "Q_HORMONAL_SYMPTOMS",
            "text_en": "Have you noticed any of the following symptoms related to androgen / testosterone deficiency?",
            "text_ar": "هل لاحظت أي من الأعراض التالية المرتبطة بنقص هرمون الذكورة (التستوستيرون)؟",
            "help_text_en": "Select all that apply over the past 6-12 months.",
            "help_text_ar": "اختر كل ما ينطبق عليك خلال الأشهر الستة إلى الاثني عشر الماضية.",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "options_json": [
                {"key": "none", "label_en": "None of these symptoms", "label_ar": "لا توجد أي من هذه الأعراض", "order": 1},
                {"key": "low_libido", "label_en": "Marked reduction in sexual desire / libido", "label_ar": "تراجع ملحوظ في الرغبة الجنسية", "order": 2},
                {"key": "loss_morning_erections", "label_en": "Loss or reduction of spontaneous morning erections", "label_ar": "غياب أو تراجع الانتصاب الصباحي", "order": 3},
                {"key": "gynecomastia", "label_en": "Tender or enlarged breast tissue (Gynecomastia)", "label_ar": "تضخم أو ألم في نسيج الثدي (التثدي)", "order": 4},
                {"key": "chronic_fatigue", "label_en": "Persistent unexplained physical fatigue / mood changes", "label_ar": "إرهاق بدني مزمن غير مبرر وتقلبات مزاجية", "order": 5}
            ],
            "clinical_rationale_en": "Clinical syndromic screen for hypogonadism (primary testicular or secondary pituitary).",
            "clinical_rationale_ar": "فحص سريري متلازمي لقصور الغدد التناسلية وانخفاض التستوستيرون.",
            "evidence_references": ["Endocrine Society Clinical Practice Guidelines on Hypogonadism"],
            "display_order": 10,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 6: METABOLIC HEALTH
        # =====================================================================
        {
            "domain_code": QuestionDomain.METABOLIC_HEALTH,
            "question_key": "Q_SLEEP_APNEA",
            "text_en": "Have you been diagnosed with Obstructive Sleep Apnea (OSA) or do you experience loud chronic snoring with daytime fatigue?",
            "text_ar": "هل تم تشخيصك بانقطاع التنفس الانسدادي أثناء النوم (OSA) أو تعاني من الشخير المزمن مع الإرهاق النهاري؟",
            "help_text_en": "Chronic nocturnal hypoxia impairs deep sleep pulsatile LH secretion, reducing testosterone.",
            "help_text_ar": "نقص الأكسجين الليلي يخل بإفراز هرمون LH النبضي في النوم العميق مما يخفض التستوستيرون.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes_diagnosed", "label_en": "Yes, diagnosed with OSA", "label_ar": "نعم، تم تشخيصي بانقطاع التنفس النومي", "order": 1},
                {"key": "yes_symptoms", "label_en": "Frequent loud snoring and daytime sleepiness", "label_ar": "شخير متكرر مع نعاس نهاري شديد", "order": 2},
                {"key": "no", "label_en": "No", "label_ar": "لا", "order": 3}
            ],
            "clinical_rationale_en": "Sleep fragmentation disrupts the hypothalamic-pituitary-gonadal axis.",
            "clinical_rationale_ar": "تقطع النوم الليلي يربك وظائف المحور الهرموني التناسلي.",
            "evidence_references": ["Lancet Diabetes Endocrinol 2022 on Male Metabolic Hypogonadism"],
            "display_order": 11,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 7: LIFESTYLE & HABITS (UAE SPECIFIC TOBACCO & HEAT)
        # =====================================================================
        {
            "domain_code": QuestionDomain.LIFESTYLE_HABITS,
            "question_key": "Q_TOBACCO_USE",
            "text_en": "Do you currently use tobacco, nicotine or smoking products?",
            "text_ar": "هل تستخدم حالياً أي منتجات تبغ أو تدخين أو نيكوتين؟",
            "help_text_en": "Includes Dokha / Medwakh, Shisha / Hookah, electronic cigarettes, and traditional cigarettes.",
            "help_text_ar": "يشمل ذلك الدوخة / المدواخ، الشيشة، السجائر الإلكترونية، والسجائر التقليدية.",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "options_json": [
                {"key": "none", "label_en": "No tobacco / non-smoker", "label_ar": "غير مدخن / لا أستخدم التبغ", "order": 1},
                {"key": "dokha_medwakh", "label_en": "Dokha / Medwakh (High nicotine pipe)", "label_ar": "دوخة / مدواخ", "order": 2},
                {"key": "shisha", "label_en": "Shisha / Waterpipe", "label_ar": "شيشة", "order": 3},
                {"key": "cigarettes", "label_en": "Traditional Cigarettes", "label_ar": "سجائر تقليدية", "order": 4},
                {"key": "vaping", "label_en": "E-Cigarettes / Vaping", "label_ar": "سجائر إلكترونية / فيب", "order": 5}
            ],
            "clinical_rationale_en": "Combustion products and heavy metals generate severe seminal reactive oxygen species (ROS) and sperm DNA damage.",
            "clinical_rationale_ar": "نواتج احتراق التبغ والمعادن الثقيلة ترفع الإجهاد التأكسدي وتكسر المادة الوراثية للنطاف.",
            "evidence_references": ["WHO Semen Manual 6th Ed", "EAU Guidelines 2024"],
            "display_order": 12,
            "is_urgent_red_flag": False
        },
        {
            "domain_code": QuestionDomain.LIFESTYLE_HABITS,
            "question_key": "Q_SCROTAL_HEAT",
            "text_en": "Do you regularly engage in habits that expose the scrotum to high temperatures?",
            "text_ar": "هل تمارس بانتظام عادات تعرض كيس الصفن لدرجات حرارة مرتفعة؟",
            "help_text_en": "Frequent hot tub / sauna use (> 2 times weekly), laptop rested directly on lap for hours, or heated car seats.",
            "help_text_ar": "الاستخدام المتكرر للساونا / الجاكوزي الحار، وضع الحاسوب المحمول مباشرة على الحجر لساعات، أو مقاعد السيارات المدفأة.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes", "label_en": "Yes, regular high heat exposure", "label_ar": "نعم، تعرض منتظم للحرارة العالية", "order": 1},
                {"key": "no", "label_en": "No", "label_ar": "لا", "order": 2}
            ],
            "clinical_rationale_en": "Human spermatogenesis requires scrotal temperatures 2-3°C below core body temperature.",
            "clinical_rationale_ar": "تكوين الحيوانات المنوية يتطلب حرارة أقل بنحو 2-3 درجات مئوية من حرارة الجسم.",
            "evidence_references": ["AUA/ASRM Guidelines 2021"],
            "display_order": 13,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 8: MEDICATION & SUBSTANCE HISTORY
        # =====================================================================
        {
            "domain_code": QuestionDomain.MEDICATION_SUBSTANCE,
            "question_key": "Q_ANABOLIC_STEROIDS",
            "text_en": "Have you ever used testosterone injections, anabolic steroids, or SARMs for athletic performance or bodybuilding?",
            "text_ar": "هل سبق لك استخدام حقن التستوستيرون، المنشطات الستيرويدية لبناء الأجسام، أو معدلات مستقبلات الأندروجين (SARMs)؟",
            "help_text_en": "CRITICAL RISK: Exogenous androgens shut down pituitary LH and FSH via negative feedback, causing azoospermia.",
            "help_text_ar": "عامل خطورة رئيسي: الهرمونات الخارجية توقف إفراز هرموني LH و FSH من الغدة النخامية مسببة انعدام الحيوانات المنوية.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes_current", "label_en": "Yes, currently using", "label_ar": "نعم، أستخدمها حالياً", "order": 1},
                {"key": "yes_past", "label_en": "Yes, used in the past", "label_ar": "نعم، استخدمتها في الماضي", "order": 2},
                {"key": "no", "label_en": "No, never used", "label_ar": "لا، لم أستخدمها إطلاقاً", "order": 3}
            ],
            "clinical_rationale_en": "Exogenous testosterone is a potent male contraceptive leading to profound testicular suppression.",
            "clinical_rationale_ar": "التستوستيرون الخارجي يثبط الغدة النخامية ويوقف تكوين الحيوانات المنوية تماماً.",
            "evidence_references": ["EAU Male Sexual and Reproductive Health Guidelines 2024"],
            "display_order": 14,
            "is_urgent_red_flag": False
        },
        {
            "domain_code": QuestionDomain.MEDICATION_SUBSTANCE,
            "question_key": "Q_HAIR_LOSS_MEDS",
            "text_en": "Have you taken Finasteride or Dutasteride (oral 5-alpha reductase inhibitors) for hair loss or prostate symptoms?",
            "text_ar": "هل تناولت فيناسترايد أو دوتاستيرايد (مضادات إنزيم 5-ألفا ريدكتاز عن طريق الفم) لعلاج تساقط الشعر؟",
            "help_text_en": "These medications inhibit DHT synthesis and can reversibly reduce semen volume, count, and erectile function.",
            "help_text_ar": "تثبط هذه الأدوية تحول هرمون DHT وقد تسبب تراجعاً مؤقتاً في عدد الحيوانات المنوية وحجم القذف.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes", "label_en": "Yes, current or past use", "label_ar": "نعم، استخدام حالي أو سابق", "order": 1},
                {"key": "no", "label_en": "No", "label_ar": "لا", "order": 2}
            ],
            "clinical_rationale_en": "5-ARI medications cause reversible or prolonged oligospermia and ejaculatory volume reduction in susceptible men.",
            "clinical_rationale_ar": "أدوية 5-ARI قد تسبب قلة النطاف ونقص حجم القذف القابل للتراجع عند التوقف.",
            "evidence_references": ["AUA Male Infertility Guidelines 2021"],
            "display_order": 15,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 9: OCCUPATIONAL & ENVIRONMENTAL EXPOSURE
        # =====================================================================
        {
            "domain_code": QuestionDomain.OCCUPATIONAL_EXPOSURE,
            "question_key": "Q_OCCUPATIONAL_HAZARDS",
            "text_en": "Does your occupation involve regular exposure to any of the following physical or chemical hazards?",
            "text_ar": "هل تتضمن طبيعة عملك التعرض المنتظم لأي من المخاطر الفيزيائية أو الكيميائية التالية؟",
            "help_text_en": "Select all occupational factors that apply to your daily working environment.",
            "help_text_ar": "حدد جميع العوامل المهنية التي تنطبق على بيئة عملك اليومية.",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "options_json": [
                {"key": "none", "label_en": "No hazardous exposures", "label_ar": "لا يوجد تعرض لمخاطر مهنية", "order": 1},
                {"key": "heavy_metals", "label_en": "Heavy metals, welding fumes, or industrial lead", "label_ar": "معادن ثقيلة، أبخرة اللحام، أو الرصاص الصناعي", "order": 2},
                {"key": "pesticides", "label_en": "Agricultural pesticides or organic solvents", "label_ar": "المبيدات الزراعية أو المذيبات العضوية", "order": 3},
                {"key": "commercial_driving", "label_en": "Prolonged commercial driving (> 6 hours sitting daily)", "label_ar": "القيادة المهنية الطويلة (> 6 ساعات جلوس يومياً)", "order": 4},
                {"key": "radiation", "label_en": "Ionizing radiation or nuclear equipment", "label_ar": "إشعاعات مؤينة أو أجهزة نووية", "order": 5}
            ],
            "clinical_rationale_en": "Occupational gonadotoxins impair Sertoli cell function and accelerate germ line DNA mutational burden.",
            "clinical_rationale_ar": "السموم المهنية تعطل وظائف خلايا سيرتولي وترفع معدل الطفرات في الحمض النووي للنطاف.",
            "evidence_references": ["WHO Global Occupational Health Standards", "EAU Guidelines 2024"],
            "display_order": 16,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 10: SEXUAL & EJACULATORY HEALTH
        # =====================================================================
        {
            "domain_code": QuestionDomain.SEXUAL_EJACULATORY,
            "question_key": "Q_EJACULATORY_PROFILE",
            "text_en": "How would you describe your ejaculation during sexual climax?",
            "text_ar": "كيف تصف عملية القذف لديك أثناء النشوة الجنسية؟",
            "help_text_en": "Dry climax (anejaculation or retrograde ejaculation) prevents sperm delivery into the female tract.",
            "help_text_ar": "القذف الجاف (الارتجاع للمثانة أو انعدام القذف) يمنع وصول النطاف للرحم.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "normal", "label_en": "Normal volume and forward projection", "label_ar": "حجم طبيعي وقذف للأمام", "order": 1},
                {"key": "very_low_volume", "label_en": "Very low volume (just a few drops, < 1 mL)", "label_ar": "حجم قليل جداً (بضع قطرات، أقل من 1 مل)", "order": 2},
                {"key": "dry_climax", "label_en": "Dry orgasm (feeling climax but zero fluid comes out)", "label_ar": "نشوة جافة (شعور بالنشوة دون خروج أي سائل)", "order": 3},
                {"key": "painful", "label_en": "Painful ejaculation", "label_ar": "ألم أثناء القذف", "order": 4}
            ],
            "clinical_rationale_en": "Anejaculation and retrograde ejaculation are treatable mechanical/neurological causes of male factor subfertility.",
            "clinical_rationale_ar": "انعدام القذف والقذف الارتجاعي يمثلان أسباباً عصبية أو ميكانيكية قابلة للعلاج.",
            "evidence_references": ["EAU Sexual & Reproductive Health Guidelines 2024"],
            "display_order": 17,
            "is_urgent_red_flag": False
        },
        {
            "domain_code": QuestionDomain.SEXUAL_EJACULATORY,
            "question_key": "Q_HEMATOSPERMIA",
            "text_en": "Have you noticed visible blood (pink, red, or brownish discoloration) in your semen in the last 6 months?",
            "text_ar": "هل لاحظت وجود دم مرئي (لون وردي، أحمر، أو بني داكن) في السائل المنوي خلال الأشهر الستة الماضية؟",
            "help_text_en": "Hematospermia may indicate seminal vesiculitis, accessory gland infection, or ductal stones.",
            "help_text_ar": "خروج دم مع المني قد يشير لالتهاب الحويصلات المنوية أو البروستاتا أو انسداد القنوات.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes", "label_en": "Yes, blood observed", "label_ar": "نعم، لاحظت وجود دم", "order": 1},
                {"key": "no", "label_en": "No", "label_ar": "لا", "order": 2}
            ],
            "clinical_rationale_en": "Clinical indication for urogenital tract evaluation for infectious or obstructive accessory gland pathology.",
            "clinical_rationale_ar": "مؤشر سريري لتقييم التهابات المسالك البولية والتناسلية أو انسداد الغدد الملحقة.",
            "evidence_references": ["EAU Guidelines 2024"],
            "display_order": 18,
            "is_urgent_red_flag": False
        },

        # =====================================================================
        # DOMAIN 11: FAMILY & GENETIC HISTORY
        # =====================================================================
        {
            "domain_code": QuestionDomain.FAMILY_GENETIC,
            "question_key": "Q_FAMILY_MALE_INFERTILITY",
            "text_en": "Is there a known history of severe male infertility or genetic reproductive disorders among your biological brothers or father?",
            "text_ar": "هل يوجد تاريخ معروف لعقم الذكور الشديد أو الاضطرابات الإنجابية الوراثية بين إخوتك الذكور أو والدك؟",
            "help_text_en": "Genetic factors include cystic fibrosis CFTR mutations, Y-chromosome microdeletions, and Kallmann syndrome.",
            "help_text_ar": "تشمل العوامل الجينية طفرات جين التليف الكيسي (CFTR)، حذف الكروموسوم Y، ومتلازمة كالمان.",
            "question_type": QuestionType.SINGLE_CHOICE,
            "options_json": [
                {"key": "yes", "label_en": "Yes, positive family history", "label_ar": "نعم، يوجد تاريخ عائلي إيجابي", "order": 1},
                {"key": "no", "label_en": "No known family history", "label_ar": "لا يوجد تاريخ عائلي معروف", "order": 2}
            ],
            "clinical_rationale_en": "Identifies heritable genetic etiologies warranting karyotyping and CFTR / AZF molecular screening.",
            "clinical_rationale_ar": "يحدد الأسباب الوراثية التي تستدعي الفحص الجيني للكروموسومات وطفرات التليف الكيسي.",
            "evidence_references": ["EAU Male Infertility Guidelines 2024", "AUA Guidelines 2021"],
            "display_order": 19,
            "is_urgent_red_flag": False
        }
    ]

    for q_data in questions_data:
        q = Question(
            version_id=version.id,
            **q_data
        )
        db.add(q)

    db.commit()
    print(f"Successfully seeded {len(questions_data)} clinical questions across all 11 domains for Questionnaire {version.version_tag}!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_questionnaire_v1(db)
    finally:
        db.close()
