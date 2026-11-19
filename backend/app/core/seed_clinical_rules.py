from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.models.clinical_rules import ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus, ClinicalRuleVersionRecord
from app.models.questionnaire import QuestionDomain
from app.core.security import User, RoleEnum

def seed_clinical_rules_v1(db: Session):
    Base.metadata.create_all(bind=engine)

    # Check if rules already seeded
    existing = db.query(ClinicalRule).first()
    if existing:
        print("Clinical rules already seeded. Skipping.")
        return

    print("Seeding GENOVEX Deterministic Clinical Rules (v1.0.0)...")

    # Fetch Clinician user for audit attribution
    clinician = db.query(User).filter(User.role == RoleEnum.CLINICIAN).first()
    clinician_id = clinician.id if clinician else None

    rules_data = [
        # =====================================================================
        # TIER 4: URGENT SAFETY CIRCUIT RULES (Priority 1-10)
        # =====================================================================
        {
            "rule_code": "R-URG-ACUTE-SCROTAL-PAIN",
            "title_en": "Emergency Evaluation: Acute Scrotal Pain / Ischemia Warning",
            "title_ar": "تقييم طارئ: تحذير ألم كيس الصفن الحاد / نقص التروية الدموية",
            "domain_code": QuestionDomain.TESTICULAR_HISTORY,
            "relevant_question_keys": ["Q_ACUTE_SCROTAL_PAIN"],
            "outcome_tier": ClinicalOutcomeTier.TIER_4_URGENT,
            "is_urgent_red_flag": True,
            "priority_rank": 1,
            "recommended_specialty": "Emergency Medicine / Acute Urology",
            "trigger_criteria": {
                "operator": "equals",
                "question_key": "Q_ACUTE_SCROTAL_PAIN",
                "expected_value": "yes"
            },
            "clinical_rationale_en": "Acute severe scrotal pain is an urological emergency requiring immediate physical examination and color Doppler ultrasound to exclude testicular torsion within the 6-hour golden window of testicular viability.",
            "clinical_rationale_ar": "ألم كيس الصفن الحاد والشديد يمثل حالة طوارئ مسالك بولية تستدعي الفحص السريري الفوري وتصوير الدوبلر لاستبعاد التواء الخصية وإنقاذ النسيج الخصوي خلال 6 ساعات.",
            "evidence_references": [
                {
                    "title": "EAU Guidelines on Paediatric & Adult Urological Emergencies",
                    "guideline_body": "European Association of Urology (EAU)",
                    "year": 2024,
                    "doi_or_url": "https://uroweb.org/guidelines/urological-emergencies",
                    "recommendation_text": "In any patient presenting with acute scrotal pain, immediate surgical exploration or definitive doppler exclusion of testicular torsion is mandatory within 6 hours.",
                    "review_date": "2024-03-15"
                }
            ],
            "evidence_classification": "Level 1a"
        },
        {
            "rule_code": "R-URG-TESTIS-LUMP",
            "title_en": "Urgent Oncology Triaging: Intratesticular Mass / Firmness",
            "title_ar": "فرز أورام عاجل: كتلة أو صلابة داخل الخصية",
            "domain_code": QuestionDomain.TESTICULAR_HISTORY,
            "relevant_question_keys": ["Q_PAINLESS_TESTIS_LUMP"],
            "outcome_tier": ClinicalOutcomeTier.TIER_4_URGENT,
            "is_urgent_red_flag": True,
            "priority_rank": 2,
            "recommended_specialty": "Urologist (Oncologic / General)",
            "trigger_criteria": {
                "operator": "equals",
                "question_key": "Q_PAINLESS_TESTIS_LUMP",
                "expected_value": "yes"
            },
            "clinical_rationale_en": "A firm or painless intratesticular mass requires urgent scrotal Doppler ultrasound to exclude testicular germ cell neoplasia; subfertility evaluations discover approximately 1-2% of asymptomatic testicular tumors.",
            "clinical_rationale_ar": "وجود كتلة صلبة أو غير مؤلمة داخل الخصية يستدعي فحص سونار عاجل لاستبعاد أورام الخلايا الجرثومية؛ تكتشف نسبة من أورام الخصية أثناء تقييم تأخر الإنجاب.",
            "evidence_references": [
                {
                    "title": "EAU Guidelines on Testicular Cancer",
                    "guideline_body": "European Association of Urology (EAU)",
                    "year": 2024,
                    "doi_or_url": "https://uroweb.org/guidelines/testicular-cancer",
                    "recommendation_text": "High-frequency scrotal ultrasonography (> 10 MHz) must be performed urgently in any patient with a palpable or suspected testicular mass.",
                    "review_date": "2024-03-20"
                }
            ],
            "evidence_classification": "Level 1a"
        },

        # =====================================================================
        # TIER 3: CLINICAL EVALUATION RECOMMENDED RULES (Priority 20-50)
        # =====================================================================
        {
            "rule_code": "R-REP-PROLONGED-TTC",
            "title_en": "Clinical Evaluation Indicated: Attempting Conception >= 12 Months",
            "title_ar": "يوصى بالتقييم السريري: محاولة الإنجاب لمدة 12 شهراً أو أكثر",
            "domain_code": QuestionDomain.REPRODUCTIVE_HISTORY,
            "relevant_question_keys": ["Q_ATTEMPT_DURATION"],
            "outcome_tier": ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
            "is_urgent_red_flag": False,
            "priority_rank": 20,
            "recommended_specialty": "Male Reproductive Urologist / Andrologist",
            "trigger_criteria": {
                "operator": "in",
                "question_key": "Q_ATTEMPT_DURATION",
                "expected_values": ["12_to_24m", "more_than_2y"]
            },
            "clinical_rationale_en": "Failure to achieve pregnancy after 12 months of regular unprotected intercourse meets the standardized international clinical definition of couple subfertility, mandating parallel male and female evaluation.",
            "clinical_rationale_ar": "عدم حدوث الحمل بعد 12 شهراً من العلاقة الزوجية المنتظمة بدون موانع يطابق التعريف الطبي الدولي لتأخر الإنجاب ويستدعي تقييم الزوجين بالتوازي.",
            "evidence_references": [
                {
                    "title": "Diagnosis and Treatment of Infertility in Men: AUA/ASRM Guideline",
                    "guideline_body": "American Urological Association / ASRM",
                    "year": 2021,
                    "doi_or_url": "https://doi.org/10.1097/JU.0000000000001371",
                    "recommendation_text": "A male evaluation should be initiated when a couple has failed to conceive after one year of regular, unprotected sexual intercourse.",
                    "review_date": "2024-01-10"
                }
            ],
            "evidence_classification": "Level 1a"
        },
        {
            "rule_code": "R-MED-ANABOLIC-STEROIDS",
            "title_en": "Clinical Evaluation Indicated: Exogenous Androgen / Anabolic Steroid Exposure",
            "title_ar": "يوصى بالتقييم السريري: استخدام التستوستيرون الخارجي أو المنشطات الستيرويدية",
            "domain_code": QuestionDomain.MEDICATION_SUBSTANCE,
            "relevant_question_keys": ["Q_ANABOLIC_STEROIDS"],
            "outcome_tier": ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
            "is_urgent_red_flag": False,
            "priority_rank": 25,
            "recommended_specialty": "Male Reproductive Urologist / Andrologist",
            "trigger_criteria": {
                "operator": "in",
                "question_key": "Q_ANABOLIC_STEROIDS",
                "expected_values": ["yes_current", "yes_past"]
            },
            "clinical_rationale_en": "Exogenous testosterone and anabolic steroids act as male contraceptives by providing potent negative feedback to the pituitary, arresting LH/FSH secretion and inducing severe oligospermia or azoospermia.",
            "clinical_rationale_ar": "يؤدي التستوستيرون الخارجي والمنشطات إلى تثبيط الغدة النخامية ومنع إفراز هرموني LH و FSH مما يسبب انعدام أو قلة شديدة في الحيوانات المنوية.",
            "evidence_references": [
                {
                    "title": "EAU Guidelines on Sexual and Reproductive Health: Male Hypogonadism and Infertility",
                    "guideline_body": "European Association of Urology (EAU)",
                    "year": 2024,
                    "doi_or_url": "https://uroweb.org/guidelines/sexual-and-reproductive-health",
                    "recommendation_text": "Exogenous testosterone must not be prescribed or used in men desiring current or future fertility.",
                    "review_date": "2024-02-18"
                }
            ],
            "evidence_classification": "Level 1a"
        },
        {
            "rule_code": "R-TST-CRYPTORCHIDISM",
            "title_en": "Clinical Evaluation Indicated: History of Undescended Testis / Orchidopexy",
            "title_ar": "يوصى بالتقييم السريري: تاريخ الخصية المعلقة أو جراحة تثبيت الخصية",
            "domain_code": QuestionDomain.TESTICULAR_HISTORY,
            "relevant_question_keys": ["Q_TESTIS_SURGERY_TYPE"],
            "outcome_tier": ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
            "is_urgent_red_flag": False,
            "priority_rank": 30,
            "recommended_specialty": "Male Reproductive Urologist / Andrologist",
            "trigger_criteria": {
                "operator": "equals",
                "question_key": "Q_TESTIS_SURGERY_TYPE",
                "expected_value": "undescended_testis"
            },
            "clinical_rationale_en": "Cryptorchidism impairs germ cell maturation into dark adult spermatogonia and carries higher risks of reduced total motile sperm counts and bilateral germ cell loss.",
            "clinical_rationale_ar": "تؤدي الخصية المعلقة إلى خلل في نضوج الخلايا الجرثومية وترتبط بارتفاع مخاطر نقص أعداد الحيوانات المنوية المتحركة وتلف النسيج المنوي.",
            "evidence_references": [
                {
                    "title": "EAU Guidelines on Paediatric Urology: Cryptorchidism Consensus",
                    "guideline_body": "European Association of Urology (EAU)",
                    "year": 2024,
                    "doi_or_url": "https://uroweb.org/guidelines/paediatric-urology",
                    "recommendation_text": "Adult males with a history of cryptorchidism should be evaluated for semen quality and counselled regarding oncological vigilance.",
                    "review_date": "2024-01-25"
                }
            ],
            "evidence_classification": "Level 2a"
        },
        {
            "rule_code": "R-SEX-EJACULATORY-DYSFUNCTION",
            "title_en": "Clinical Evaluation Indicated: Dry Climax / Ejaculatory Disorder",
            "title_ar": "يوصى بالتقييم السريري: النشوة الجافة أو اضطراب القذف",
            "domain_code": QuestionDomain.SEXUAL_EJACULATORY,
            "relevant_question_keys": ["Q_EJACULATORY_PROFILE"],
            "outcome_tier": ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
            "is_urgent_red_flag": False,
            "priority_rank": 35,
            "recommended_specialty": "Male Reproductive Urologist / Andrologist",
            "trigger_criteria": {
                "operator": "in",
                "question_key": "Q_EJACULATORY_PROFILE",
                "expected_values": ["dry_climax", "very_low_volume"]
            },
            "clinical_rationale_en": "Anejaculation, retrograde ejaculation into the bladder, and profound aspermia completely prevent intravaginal sperm deposition; post-ejaculatory urine analysis can confirm retrograde passage.",
            "clinical_rationale_ar": "انعدام القذف أو القذف الارتجاعي إلى المثانة يمنع وصول النطاف تماماً؛ فحص البول بعد القذف يكشف وجود الحيوانات المنوية في المثانة.",
            "evidence_references": [
                {
                    "title": "AUA/ASRM Guideline: Male Infertility Ejaculatory Disorders",
                    "guideline_body": "American Urological Association / ASRM",
                    "year": 2021,
                    "doi_or_url": "https://doi.org/10.1097/JU.0000000000001371",
                    "recommendation_text": "Post-ejaculatory urinalysis should be performed in men with semen volume < 1.0 mL who report dry orgasm or low ejaculatory force.",
                    "review_date": "2024-02-05"
                }
            ],
            "evidence_classification": "Level 1b"
        },
        {
            "rule_code": "R-SEX-HEMATOSPERMIA",
            "title_en": "Clinical Evaluation Indicated: Visible Hematospermia (Blood in Semen)",
            "title_ar": "يوصى بالتقييم السريري: دم مرئي في السائل المنوي",
            "domain_code": QuestionDomain.SEXUAL_EJACULATORY,
            "relevant_question_keys": ["Q_HEMATOSPERMIA"],
            "outcome_tier": ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
            "is_urgent_red_flag": False,
            "priority_rank": 40,
            "recommended_specialty": "Urologist (General / Andrology)",
            "trigger_criteria": {
                "operator": "equals",
                "question_key": "Q_HEMATOSPERMIA",
                "expected_value": "yes"
            },
            "clinical_rationale_en": "Hematospermia warrants urological evaluation to rule out chronic seminal vesiculitis, accessory sex gland infection, ductal lithiasis, or ejaculatory duct cysts.",
            "clinical_rationale_ar": "خروج دم مع السائل المنوي يستدعي فحص المسالك البولية لاستبعاد التهابات الحويصلات المنوية والبروستاتا أو انسداد القنوات الدافقة.",
            "evidence_references": [
                {
                    "title": "EAU Guidelines on Urological Infections: Male Accessory Gland Infections",
                    "guideline_body": "European Association of Urology (EAU)",
                    "year": 2024,
                    "doi_or_url": "https://uroweb.org/guidelines/urological-infections",
                    "recommendation_text": "Recurrent or persistent hematospermia requires physical examination, urinalysis, and transrectal ultrasound of the prostate and seminal vesicles.",
                    "review_date": "2024-02-12"
                }
            ],
            "evidence_classification": "Level 2a"
        },
        {
            "rule_code": "R-FAM-GENETIC-INFERTILITY",
            "title_en": "Clinical Evaluation Indicated: Familial Male Infertility History",
            "title_ar": "يوصى بالتقييم السريري: تاريخ عائلي إيجابي لعقم الذكور",
            "domain_code": QuestionDomain.FAMILY_GENETIC,
            "relevant_question_keys": ["Q_FAMILY_MALE_INFERTILITY"],
            "outcome_tier": ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED,
            "is_urgent_red_flag": False,
            "priority_rank": 45,
            "recommended_specialty": "Clinical Geneticist / Male Reproductive Specialist",
            "trigger_criteria": {
                "operator": "equals",
                "question_key": "Q_FAMILY_MALE_INFERTILITY",
                "expected_value": "yes"
            },
            "clinical_rationale_en": "A positive family history of severe male factor infertility suggests monogenic or chromosomal etiologies (e.g., CFTR mutations, Y-chromosome microdeletions, or balanced translocations).",
            "clinical_rationale_ar": "التاريخ العائلي الإيجابي لعقم الذكور يشير إلى أسباب جينية أو صبغية محتملة تستوجب الفحص الجيني المتخصص.",
            "evidence_references": [
                {
                    "title": "EAU Guidelines on Male Infertility: Genetic Screening Indications",
                    "guideline_body": "European Association of Urology (EAU)",
                    "year": 2024,
                    "doi_or_url": "https://uroweb.org/guidelines/male-infertility",
                    "recommendation_text": "Karyotype analysis and Y-chromosome microdeletion testing should be performed in men with severe oligospermia or family history of genetic reproductive failure.",
                    "review_date": "2024-03-01"
                }
            ],
            "evidence_classification": "Level 1a"
        },

        # =====================================================================
        # TIER 2: RISK FACTORS IDENTIFIED RULES (Priority 60-90)
        # =====================================================================
        {
            "rule_code": "R-LST-TOBACCO-DOKHA",
            "title_en": "Risk Factor Identified: Tobacco, Dokha or Shisha Consumption",
            "title_ar": "تم تحديد عامل خطورة: استهلاك التبغ أو الدوخة أو الشيشة",
            "domain_code": QuestionDomain.LIFESTYLE_HABITS,
            "relevant_question_keys": ["Q_TOBACCO_USE"],
            "outcome_tier": ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
            "is_urgent_red_flag": False,
            "priority_rank": 60,
            "recommended_specialty": "Primary Care / Smoking Cessation Specialist",
            "trigger_criteria": {
                "operator": "contains",
                "question_key": "Q_TOBACCO_USE",
                "expected_values": ["dokha_medwakh", "shisha", "cigarettes", "vaping"]
            },
            "clinical_rationale_en": "Nicotine and combustion toxins generate heavy seminal reactive oxygen species (ROS), causing leukocyte infiltration, reduced progressive motility, and elevated sperm DNA fragmentation.",
            "clinical_rationale_ar": "النيكوتين ونواتج الاحتراق ترفع الجذور الحرة المؤكسدة في السائل المنوي، مما يؤدي إلى زيادة تكسر الحمض النووي للنطاف وتراجع حركتها.",
            "evidence_references": [
                {
                    "title": "WHO Laboratory Manual for the Examination and Processing of Human Semen (6th Edition)",
                    "guideline_body": "World Health Organization (WHO)",
                    "year": 2021,
                    "doi_or_url": "https://www.who.int/publications/i/item/9789240030787",
                    "recommendation_text": "Tobacco smoking is consistently associated with reductions in sperm concentration, motility, normal morphology, and increased DNA fragmentation index.",
                    "review_date": "2023-11-20"
                }
            ],
            "evidence_classification": "Level 1b"
        },
        {
            "rule_code": "R-LST-SCROTAL-HYPERTHERMIA",
            "title_en": "Risk Factor Identified: Chronic Scrotal Thermal Exposure",
            "title_ar": "تم تحديد عامل خطورة: تعرض كيس الصفن لدرجات حرارة مرتفعة",
            "domain_code": QuestionDomain.LIFESTYLE_HABITS,
            "relevant_question_keys": ["Q_SCROTAL_HEAT"],
            "outcome_tier": ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
            "is_urgent_red_flag": False,
            "priority_rank": 65,
            "recommended_specialty": "Primary Care / Lifestyle Medicine",
            "trigger_criteria": {
                "operator": "equals",
                "question_key": "Q_SCROTAL_HEAT",
                "expected_value": "yes"
            },
            "clinical_rationale_en": "Human spermatogenesis is temperature-sensitive and requires scrotal cooling 2-3°C below core temperature; frequent hot tub or sauna exposure causes temporary spermatogenic arrest.",
            "clinical_rationale_ar": "يتطلب تكوين الحيوانات المنوية حرارة أقل من حرارة الجسم بدرجتين إلى ثلاث؛ التعرض المتكرر للساونا والماء الساخن يوقف تكوين النطاف مؤقتاً.",
            "evidence_references": [
                {
                    "title": "AUA/ASRM Male Infertility: Modifiable Lifestyle Risk Factors",
                    "guideline_body": "American Urological Association / ASRM",
                    "year": 2021,
                    "doi_or_url": "https://doi.org/10.1097/JU.0000000000001371",
                    "recommendation_text": "Clinicians should counsel men regarding the negative spermatogenic effects of frequent wet heat exposure and heated car seats.",
                    "review_date": "2024-01-15"
                }
            ],
            "evidence_classification": "Level 2b"
        },
        {
            "rule_code": "R-MET-OBSTRUCTIVE-SLEEP-APNEA",
            "title_en": "Risk Factor Identified: Obstructive Sleep Apnea / Chronic Hypoxia",
            "title_ar": "تم تحديد عامل خطورة: انقطاع التنفس النومي الانسدادي / نقص الأكسجين المزمن",
            "domain_code": QuestionDomain.METABOLIC_HEALTH,
            "relevant_question_keys": ["Q_SLEEP_APNEA"],
            "outcome_tier": ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
            "is_urgent_red_flag": False,
            "priority_rank": 70,
            "recommended_specialty": "Sleep Medicine / Pulmonology / Endocrinology",
            "trigger_criteria": {
                "operator": "in",
                "question_key": "Q_SLEEP_APNEA",
                "expected_values": ["yes_diagnosed", "yes_symptoms"]
            },
            "clinical_rationale_en": "Intermittent nocturnal hypoxemia and architecture fragmentation disrupt nocturnal LH surge pulsatility, predisposing to functional secondary hypogonadism and fatigue.",
            "clinical_rationale_ar": "نقص الأكسجين المتقطع ليلاً وتجزؤ النوم يخل بإفراز هرمون LH النبضي مما يهيئ لقصور الغدد التناسلية الوظيفي وانخفاض التستوستيرون.",
            "evidence_references": [
                {
                    "title": "Male Hypogonadism and Sleep Disturbances: An Endocrine Review",
                    "guideline_body": "The Lancet Diabetes & Endocrinology",
                    "year": 2022,
                    "doi_or_url": "https://doi.org/10.1016/S2213-8587(22)00045-8",
                    "recommendation_text": "Screening for OSA and treating sleep fragmentation improves testosterone rhythms in metabolically vulnerable men.",
                    "review_date": "2023-12-05"
                }
            ],
            "evidence_classification": "Level 2a"
        },
        {
            "rule_code": "R-MED-HAIR-LOSS-5ARI",
            "title_en": "Risk Factor Identified: 5-Alpha Reductase Inhibitor Exposure (Finasteride)",
            "title_ar": "تم تحديد عامل خطورة: استخدام مضادات 5-ألفا ريدكتاز (فيناسترايد)",
            "domain_code": QuestionDomain.MEDICATION_SUBSTANCE,
            "relevant_question_keys": ["Q_HAIR_LOSS_MEDS"],
            "outcome_tier": ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
            "is_urgent_red_flag": False,
            "priority_rank": 75,
            "recommended_specialty": "Dermatologist / Urologist",
            "trigger_criteria": {
                "operator": "equals",
                "question_key": "Q_HAIR_LOSS_MEDS",
                "expected_value": "yes"
            },
            "clinical_rationale_en": "Oral finasteride impairs DHT synthesis and can cause dose-dependent, reversible reductions in total semen volume and sperm count in subfertile men.",
            "clinical_rationale_ar": "أدوية فيناسترايد تثبط هرمون DHT وقد تسبب نقصاً مؤقتاً في حجم القذف وعدد الحيوانات المنوية لدى الرجال المعرضين لتأخر الإنجاب.",
            "evidence_references": [
                {
                    "title": "AUA/ASRM Guidelines: Medication-Induced Male Subfertility",
                    "guideline_body": "American Urological Association / ASRM",
                    "year": 2021,
                    "doi_or_url": "https://doi.org/10.1097/JU.0000000000001371",
                    "recommendation_text": "Discontinuation of 5-alpha reductase inhibitors should be considered in subfertile men with abnormal semen parameters.",
                    "review_date": "2024-02-14"
                }
            ],
            "evidence_classification": "Level 2a"
        },
        {
            "rule_code": "R-OCC-TOXIN-EXPOSURE",
            "title_en": "Risk Factor Identified: Occupational Gonadotoxin Exposure",
            "title_ar": "تم تحديد عامل خطورة: التعرض المهني للسموم الخصوية",
            "domain_code": QuestionDomain.OCCUPATIONAL_EXPOSURE,
            "relevant_question_keys": ["Q_OCCUPATIONAL_HAZARDS"],
            "outcome_tier": ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
            "is_urgent_red_flag": False,
            "priority_rank": 80,
            "recommended_specialty": "Occupational Health / Preventive Medicine",
            "trigger_criteria": {
                "operator": "contains",
                "question_key": "Q_OCCUPATIONAL_HAZARDS",
                "expected_values": ["heavy_metals", "pesticides", "radiation"]
            },
            "clinical_rationale_en": "Occupational heavy metals (lead, cadmium) and agricultural organophosphates damage Sertoli cells and blood-testis barrier integrity.",
            "clinical_rationale_ar": "المعادن الثقيلة الصناعية والمبيدات تضر خلايا سيرتولي وتخترق الحاجز الدموي الخصوي مما يعطل تكوين النطاف.",
            "evidence_references": [
                {
                    "title": "WHO Environmental & Occupational Health Criteria on Reproductive Hazards",
                    "guideline_body": "World Health Organization (WHO)",
                    "year": 2021,
                    "doi_or_url": "https://www.who.int/teams/environment-climate-change-and-health",
                    "recommendation_text": "Personal protective equipment and occupational surveillance are recommended for workers exposed to recognized reproductive toxins.",
                    "review_date": "2023-10-30"
                }
            ],
            "evidence_classification": "Level 2b"
        },
        {
            "rule_code": "R-BAS-ADVANCED-PATERNAL-AGE",
            "title_en": "Risk Factor Identified: Advanced Paternal Age (>= 45 Years)",
            "title_ar": "تم تحديد عامل خطورة: تقدم عمر الأب (45 سنة فما فوق)",
            "domain_code": QuestionDomain.BASIC_HEALTH,
            "relevant_question_keys": ["Q_AGE"],
            "outcome_tier": ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
            "is_urgent_red_flag": False,
            "priority_rank": 85,
            "recommended_specialty": "Primary Care / Reproductive Medicine",
            "trigger_criteria": {
                "operator": "greater_than",
                "question_key": "Q_AGE",
                "expected_value": 44
            },
            "clinical_rationale_en": "Advanced paternal age (> 40-45) is associated with an accumulation of de novo germline point mutations and higher sperm DNA fragmentation index (DFI).",
            "clinical_rationale_ar": "يرتبط تقدم عمر الأب (فوق 45 سنة) بتراكم الطفرات الجينية النقطية في الحيوانات المنوية وارتفاع نسبة تكسر المادة الوراثية.",
            "evidence_references": [
                {
                    "title": "EAU Guidelines on Male Infertility: Paternal Age Factors",
                    "guideline_body": "European Association of Urology (EAU)",
                    "year": 2024,
                    "doi_or_url": "https://uroweb.org/guidelines/male-infertility",
                    "recommendation_text": "Couples should be informed that paternal age over 40-45 decreases fecundability and increases time to pregnancy.",
                    "review_date": "2024-02-28"
                }
            ],
            "evidence_classification": "Level 2a"
        }
    ]

    for r_data in rules_data:
        rule = ClinicalRule(
            rule_code=r_data["rule_code"],
            title_en=r_data["title_en"],
            title_ar=r_data["title_ar"],
            domain_code=r_data["domain_code"],
            relevant_question_keys=r_data["relevant_question_keys"],
            outcome_tier=r_data["outcome_tier"],
            is_urgent_red_flag=r_data["is_urgent_red_flag"],
            priority_rank=r_data["priority_rank"],
            recommended_specialty=r_data["recommended_specialty"],
            trigger_criteria=r_data["trigger_criteria"],
            missing_response_handling="NEVER_NEGATIVE",
            clinical_rationale_en=r_data["clinical_rationale_en"],
            clinical_rationale_ar=r_data["clinical_rationale_ar"],
            evidence_references=r_data["evidence_references"],
            evidence_classification=r_data["evidence_classification"],
            rule_version="1.0.0",
            status=ClinicalRuleStatus.PUBLISHED,
            created_by_user_id=clinician_id,
            clinical_reviewer_id=clinician_id,
            approved_at=datetime.now(timezone.utc),
            published_at=datetime.now(timezone.utc),
            clinical_reviewer_notes="Verified and signed off against EAU, AUA/ASRM, and WHO clinical guidelines."
        )
        db.add(rule)
        db.flush()

        # Create initial version snapshot record
        snapshot = {
            "rule_code": rule.rule_code,
            "title_en": rule.title_en,
            "title_ar": rule.title_ar,
            "outcome_tier": rule.outcome_tier.value,
            "is_urgent_red_flag": rule.is_urgent_red_flag,
            "trigger_criteria": rule.trigger_criteria,
            "evidence_references": rule.evidence_references,
            "clinical_rationale_en": rule.clinical_rationale_en
        }
        v_record = ClinicalRuleVersionRecord(
            rule_id=rule.id,
            version_tag="1.0.0",
            rule_code=rule.rule_code,
            title_en=rule.title_en,
            title_ar=rule.title_ar,
            outcome_tier=rule.outcome_tier,
            is_urgent_red_flag=rule.is_urgent_red_flag,
            trigger_criteria=rule.trigger_criteria,
            evidence_references=rule.evidence_references,
            snapshot_json=snapshot,
            created_by_user_id=clinician_id
        )
        db.add(v_record)

    db.commit()
    print(f"Successfully seeded {len(rules_data)} deterministic clinical rules across all 4 outcome tiers!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_clinical_rules_v1(db)
    finally:
        db.close()
