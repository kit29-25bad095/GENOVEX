from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import SessionLocal, Base, engine
from app.core.security import User, RoleEnum, get_password_hash
from app.models.medical_content import (
    MedicalCategory, MedicalReference, MedicalCondition, 
    ConditionContent, ContentVersion, ClinicalReviewRecord,
    PublicationStatus, EvidenceClassification
)
from app.services.medical_content_service import MedicalContentService

def seed_database(db: Session):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # 0. Seed System Users if not present
    if not db.query(User).first():
        print("Seeding GENOVEX System Users & Roles...")
        superadmin = User(
            email="superadmin@genovex.health",
            hashed_password=get_password_hash("SuperAdmin@2026"),
            full_name="Dr. Mansoor Al-Ketbi",
            role=RoleEnum.SUPERADMIN,
            credentials_summary="Chief Medical Officer & UAE Health Informatics Lead"
        )
        clinician = User(
            email="clinician@genovex.health",
            hashed_password=get_password_hash("Clinician@2026"),
            full_name="Dr. Tarek Al-Mansoor",
            role=RoleEnum.CLINICIAN,
            credentials_summary="Consultant Andrologist / DHA-P-00129"
        )
        admin = User(
            email="admin@genovex.health",
            hashed_password=get_password_hash("Admin@2026"),
            full_name="Sarah Jenkins",
            role=RoleEnum.ADMIN,
            credentials_summary="Clinical Content Operations Lead"
        )
        patient = User(
            email="patient@genovex.health",
            hashed_password=get_password_hash("Patient@2026"),
            full_name="Rashid Al-Nuaimi",
            role=RoleEnum.PATIENT,
            credentials_summary="Registered Health Seeker"
        )
        db.add_all([superadmin, clinician, admin, patient])
        db.commit()

    # Check if content already seeded
    if db.query(MedicalCategory).first():
        print("Database already seeded with categories and conditions.")
        return

    print("Seeding GENOVEX Medical Content System...")

    # 1. Seed Categories
    cat_scrotal = MedicalCategory(
        slug="scrotal-vascular",
        name_en="Scrotal & Vascular Pathology",
        name_ar="أمراض كيس الصفن والأوعية الدموية",
        description_en="Conditions affecting scrotal venous drainage, testicular temperature regulation and parenchymal perfusion.",
        description_ar="الحالات التي تؤثر على التصريف الوريدي للصفن، وتنظيم حرارة الخصية وتروية النسيج الخصوي.",
        display_order=1
    )
    cat_endocrine = MedicalCategory(
        slug="endocrine-hormonal",
        name_en="Endocrine & Hormonal Disorders",
        name_ar="اضطرابات الغدد الصماء والهرمونات",
        description_en="Dysfunctions of the hypothalamic-pituitary-gonadal (HPG) axis governing testosterone and spermatogenesis.",
        description_ar="اختلالات المحور الوطائي النخامي التناسلي المنظم لهرمون التستوستيرون وتكوين الحيوانات المنوية.",
        display_order=2
    )
    cat_genetic = MedicalCategory(
        slug="genetic-chromosomal",
        name_en="Genetic & Chromosomal Anomalies",
        name_ar="التشوهات الجينية والصبغية",
        description_en="Karyotypic abnormalities, Y-chromosome microdeletions and single-gene mutations affecting testicular development.",
        description_ar="الاضطرابات الصبغية، الحذف الدقيق للكروموسوم Y والطفرات الجينية التي تؤثر على تطور الخصية.",
        display_order=3
    )
    cat_obstructive = MedicalCategory(
        slug="obstructive-ductal",
        name_en="Obstructive & Ductal Pathology",
        name_ar="أمراض الانسداد والقنوات التناسلية",
        description_en="Physical or functional blockages along the epididymis, vas deferens or ejaculatory ducts.",
        description_ar="الانسدادات الميكانيكية أو الوظيفية على طول البربخ، الأسهر، أو القنوات الدافقة.",
        display_order=4
    )
    cat_congenital = MedicalCategory(
        slug="congenital-developmental",
        name_en="Congenital & Developmental Conditions",
        name_ar="الحالات الخلقية والتطورية",
        description_en="Anomalies of testicular descent and embryonic urogenital tract differentiation.",
        description_ar="تشوهات هبوط الخصية وتمايز الجهاز البولي التناسلي الجنيني.",
        display_order=5
    )

    db.add_all([cat_scrotal, cat_endocrine, cat_genetic, cat_obstructive, cat_congenital])
    db.flush()

    # 2. Seed Medical References
    ref_eau = MedicalReference(
        title="EAU Guidelines on Sexual and Reproductive Health: Male Infertility",
        authors="Minhas S, Bettocchi C, Boeri L, et al.",
        journal_or_publisher="European Association of Urology Guidelines Office",
        publication_year=2024,
        doi_or_url="https://uroweb.org/guidelines/sexual-and-reproductive-health",
        guideline_body="EAU",
        evidence_classification=EvidenceClassification.GUIDELINE_CONSENSUS.value
    )
    ref_aua = MedicalReference(
        title="Diagnosis and Treatment of Infertility in Men: AUA/ASRM Guideline",
        authors="Schlegel PN, Sigman M, Collura B, et al.",
        journal_or_publisher="Journal of Urology & Fertility and Sterility",
        publication_year=2021,
        doi_or_url="https://doi.org/10.1097/JU.0000000000001521",
        guideline_body="AUA / ASRM",
        evidence_classification=EvidenceClassification.LEVEL_1A.value
    )
    ref_who = MedicalReference(
        title="WHO Laboratory Manual for the Examination and Processing of Human Semen (6th Edition)",
        authors="World Health Organization Reproductive Health and Research Group",
        journal_or_publisher="World Health Organization",
        publication_year=2021,
        doi_or_url="https://www.who.int/publications/i/item/9789240030787",
        guideline_body="WHO",
        evidence_classification=EvidenceClassification.GUIDELINE_CONSENSUS.value
    )

    db.add_all([ref_eau, ref_aua, ref_who])
    db.flush()

    # 3. Condition 1: Varicocele (PUBLISHED)
    c1 = MedicalCondition(
        slug="varicocele",
        category_id=cat_scrotal.id,
        organs_involved=["Testes", "Pampiniform Venous Plexus", "Internal Spermatic Vein", "Scrotum"],
        evidence_classification="Level 1A",
        publication_status=PublicationStatus.PUBLISHED,
        current_version=2,
        last_reviewed_at=datetime(2026, 10, 15, 10, 30, tzinfo=timezone.utc),
        clinical_reviewer="Dr. Tarek Al-Mansoor (Consultant Urologist & Andrologist, DHA Licensed)"
    )
    c1.references = [ref_eau, ref_aua]
    db.add(c1)
    db.flush()

    c1_en = ConditionContent(
        condition_id=c1.id,
        language="en",
        name="Varicocele",
        short_description="Abnormal dilation and tortuosity of the pampiniform venous plexus within the scrotum, frequently causing progressive decline in sperm production.",
        detailed_explanation="Varicocele represents the most common surgically correctable cause of primary and secondary male factor reproductive impairment. Occurring in roughly 15% of the adult male population and up to 40% of men presenting with primary fertility challenges, varicoceles arise predominantly on the left hemiscrotum due to venous insertion angle into the left renal vein. Over time, persistent venous reflux creates localized hyperthermia and oxidative stress.",
        biological_mechanism="Incompetence or absence of venous valves in the internal spermatic vein allows retrograde pooling of warm core body blood. This elevates testicular temperature by 1.5°C to 2.5°C above the ideal physiologic thermoregulatory threshold (34°C). The resulting heat stress disrupts Sertoli and Leydig cell metabolism, increases reactive oxygen species (ROS), accelerates germ cell apoptosis, and produces substantial sperm DNA fragmentation.",
        causes_and_risk_factors="Anatomic factors: Insertion of left internal spermatic vein at a right angle into the left renal vein, absence of anti-reflux venous valves, 'nutcracker' compression between aorta and superior mesenteric artery. Risk exacerbators: Prolonged standing, chronic strenuous intra-abdominal pressure, and genetic predisposition to vascular connective tissue laxity.",
        possible_symptoms="Often completely asymptomatic. When symptoms occur: Dull, aching scrotal heaviness or dragging discomfort exacerbated by physical exertion or standing; palpable 'bag of worms' sensation above the testicle; or visible testicular size asymmetry (hypotrophy).",
        silent_asymptomatic_presentation="CRITICAL CLINICAL NOTICE: Up to 80% of clinical varicoceles produce NO noticeable pain or physical discomfort whatsoever. Men often discover the condition solely upon unexpected semen analysis abnormalities or during routine medical examination.",
        clinical_significance="Uncorrected grade II or III varicoceles can lead to progressive testicular volume loss and progressive deterioration of all semen parameters (oligoasthenoteratozoospermia) and elevated sperm DNA fragmentation indices.",
        diagnostic_investigations="High-resolution scrotal Doppler ultrasonography with Valsalva maneuver (venous diameter > 3.0 mm and reflux > 2 seconds); physical examination in both supine and upright positions; serial semen analysis (WHO 6th ed.); hormonal profiling (total testosterone, LH, FSH).",
        clinical_next_steps="Consultation with a verified Reproductive Urologist or Andrologist. Microsurgical subinguinal varicocelectomy is recommended when clinical varicocele is accompanied by abnormal semen parameters and fertility desire."
    )
    c1_ar = ConditionContent(
        condition_id=c1.id,
        language="ar",
        name="دوالي الخصية (Varicocele)",
        short_description="تمدد وتوسع غير طبيعي في الأوردة المنوية داخل كيس الصفن، يُعد من أكثر أسباب تراجع إنتاج الحيوانات المنوية شيوعاً وقابلية للعلاج.",
        detailed_explanation="تعتبر دوالي الخصية السبب الأكثر شيوعاً القابل للتصحيح الجراحي لتأخر الإنجاب لدى الرجال. تحدث لدى حوالي 15٪ من عموم الرجال وتصل إلى 40٪ من الرجال الذين يراجعون لتقييم الخصوبة الأولية. تنشأ غالباً في الجانب الأيسر بسبب زاوية تصريف الوريد المنوي الأيسر داخل الوريد الكلوي. يؤدي الارتجاع الوريدي المستمر إلى ارتفاع حرارة الخصية وزيادة الإجهاد التأكسدي.",
        biological_mechanism="قصور أو غياب الصمامات في الوريد المنوي الداخلي يؤدي لركود الدم الوريدي وارتفاع درجة حرارة الخصية بنحو 1.5 إلى 2.5 درجة مئوية فوق المعدل الطبيعي (34 مئوية). يؤدي هذا الإجهاد الحراري لاختلال وظائف خلايا سيرتولي وليديج، وزيادة الجذور الحرة التفاعلية (ROS)، وتكسر المادة الوراثية للحيوانات المنوية (DNA Fragmentation).",
        causes_and_risk_factors="عوامل تشريحية: صب الوريد المنوي الأيسر بزاوية قائمة في الوريد الكلوي، غياب الصمامات الوريدية، متلازمة كسارة البندق الوعائية. عوامل مفاقمة: الوقوف لفترات طويلة، الإجهاد البدني المزمن، وضعف مرونة الأنسجة الوعائية.",
        possible_symptoms="غالباً لا توجد أي أعراض على الإطلاق. في حال ظهورها: ثقل أو ألم خفيف مستمر في كيس الصفن يزداد مع الوقوف أو بذل الجهد؛ ملمس يشبه 'كيس الديدان' فوق الخصية؛ أو ضمور ملحوظ في حجم الخصية.",
        silent_asymptomatic_presentation="تنبيه سريري هام: ما يصل إلى 80٪ من حالات دوالي الخصية السريرية صامتة تماماً ولا تسبب أي ألم أو انزعاج، ويتم اكتشافها صدفة عبر فحص السائل المنوي أو الفحص السريري الروتيني.",
        clinical_significance="قد تؤدي دوالي الخصية غير المعالجة من الدرجة الثانية أو الثالثة إلى ضمور تدريجي في حجم الخصية وتراجع مستمر في مؤشرات السائل المنوي (العدد، الحركة والتشوهات) وزيادة تكسر الحمض النووي.",
        diagnostic_investigations="فحص الموجات فوق الصوتية الملونة (دوبلر) للصفن مع مناورة فالسالفا (قطر وريدي > 3.0 مم مع ارتجاع > 2 ثانية)، الفحص السريري وقوفاً واستلقاءً، تحليل السائل المنوي وفق معايير منظمة الصحة العالمية، وفحص الهرمونات (التستوستيرون، LH، FSH).",
        clinical_next_steps="استشارة استشاري جراحة المسالك البولية والتناسلية وأمراض الذكورة. يوصى بالجراحة الميكروسكوبية لدوالي الخصية عند وجود دوالي سريرية مصحوبة بتأثر مؤشرات السائل المنوي."
    )
    db.add_all([c1_en, c1_ar])
    db.flush()

    # V1 and V2 snapshots
    v1_c1 = ContentVersion(
        condition_id=c1.id,
        version_number=1,
        snapshot_data=MedicalContentService._create_snapshot(c1),
        change_summary="Initial clinical synthesis and translation",
        created_by="Dr. Tarek Al-Mansoor"
    )
    v2_c1 = ContentVersion(
        condition_id=c1.id,
        version_number=2,
        snapshot_data=MedicalContentService._create_snapshot(c1),
        change_summary="Updated ultrasound diagnostic thresholds per EAU 2024 guidelines",
        created_by="Dr. Tarek Al-Mansoor"
    )
    db.add_all([v1_c1, v2_c1])

    # 4. Condition 2: Hypogonadotropic Hypogonadism (PUBLISHED)
    c2 = MedicalCondition(
        slug="hypogonadotropic-hypogonadism",
        category_id=cat_endocrine.id,
        organs_involved=["Hypothalamus", "Pituitary Gland", "Testes", "Leydig Cells"],
        evidence_classification="Level 1A",
        publication_status=PublicationStatus.PUBLISHED,
        current_version=1,
        last_reviewed_at=datetime(2026, 9, 20, 14, 0, tzinfo=timezone.utc),
        clinical_reviewer="Dr. Fatima Al-Hashimi (Reproductive Endocrinologist, DOH Licensed)"
    )
    c2.references = [ref_eau, ref_who]
    db.add(c2)
    db.flush()

    c2_en = ConditionContent(
        condition_id=c2.id,
        language="en",
        name="Hypogonadotropic Hypogonadism (Secondary Hypogonadism)",
        short_description="Central endocrine dysfunction characterized by deficient pituitary secretion of LH and FSH, causing low testosterone and severely impaired spermatogenesis.",
        detailed_explanation="Secondary or hypogonadotropic hypogonadism occurs when the hypothalamus fails to pulse gonadotropin-releasing hormone (GnRH) or the anterior pituitary fails to secrete luteinizing hormone (LH) and follicle-stimulating hormone (FSH). Because the testes lack hormonal stimulation, testosterone synthesis halts and germ cell maturation arrests, resulting in severe oligospermia or azoospermia.",
        biological_mechanism="Lacking LH stimulation, Leydig cells cannot synthesize testosterone. Simultaneously, lacking FSH stimulation, Sertoli cells cannot nourish developing spermatids. Unlike primary testicular failure where LH and FSH are elevated, secondary hypogonadism shows inappropriately low or normal gonadotropins despite profoundly depressed systemic testosterone levels.",
        causes_and_risk_factors="Congenital (Kallmann syndrome, ANOS1 mutations, idiopathic hypogonadotrophic hypogonadism); Acquired: Pituitary micro/macroadenomas, hyperprolactinemia, history of anabolic-androgenic steroid (AAS) abuse, severe metabolic syndrome, obesity, chronic opioid therapy, or hemochromatosis.",
        possible_symptoms="Subtle reduced libido, erectile dysfunction, decreased spontaneous morning erections, chronic physical fatigue, mood changes, loss of muscle mass, or delayed secondary sexual characteristics.",
        silent_asymptomatic_presentation="Subclinical presentations frequently lack obvious physical signs. In young athletic men with prior steroid exposure, the only apparent indicator may be completely normal physical appearance paired with zero sperm count (azoospermia) on testing.",
        clinical_significance="Highly significant because it is one of the few forms of profound male infertility that is often completely reversible with targeted gonadotropin therapy (hCG + rFSH) or GnRH pulsatile pump therapy.",
        diagnostic_investigations="Fasting early morning (8:00 AM) total and free testosterone (repeated on 2 separate occasions); serum LH and FSH; serum prolactin; thyroid panel (TSH); pituitary magnetic resonance imaging (MRI) with contrast if severe deficiency or visual changes are present.",
        clinical_next_steps="Formal consultation with an Endocrinologist and Reproductive Urologist. Discontinuation of exogenous androgens or opioids under medical supervision; initiation of gonadotropin therapy when fertility is desired."
    )
    c2_ar = ConditionContent(
        condition_id=c2.id,
        language="ar",
        name="قصور الغدد التناسلية الثانوي (Hypogonadotropic Hypogonadism)",
        short_description="اختلال هرموني مركزي ناتج عن نقص إفراز هرموني LH و FSH من الغدة النخامية، مما يؤدي لانخفاض التستوستيرون وتوقف إنتاج الحيوانات المنوية.",
        detailed_explanation="يحدث قصور الغدد التناسلية المركزي أو الثانوي عندما يفشل الوطاء في إفراز الهرمون المطلق لموجهة الغدد التناسلية (GnRH) أو تفشل الغدة النخامية في إفراز هرموني LH و FSH. لعدم وجود التحفيز الهرموني للخصيتين، يتوقف إنتاج هرمون الذكورة وتتوقف نضوج الحيوانات المنوية، مما يؤدي لقلة شديدة أو انعدام الحيوانات المنوية في السائل المنوي.",
        biological_mechanism="في غياب هرمون LH، تفشل خلايا ليديج في تصنيع هرمون التستوستيرون. وفي غياب هرمون FSH، لا تستطيع خلايا سيرتولي تغذية وتطوير الحيوانات المنوية. على عكس القصور الأولي، تكون مستويات LH و FSH منخفضة أو طبيعية بشكل غير ملائم رغم الانخفاض الشديد لهرمون الذكورة.",
        causes_and_risk_factors="أسباب خلقية (متلازمة كالمان، طفرات ANOS1)؛ أسباب مكتسبة: أورام الغدة النخامية الغدية، ارتفاع هرمون الحليب (البرولاكتين)، الاستخدام السابق للمنشطات الستيرويدية لبناء الأجسام، متلازمة الأيض الشديدة، والسمنة المفرطة.",
        possible_symptoms="انخفاض الرغبة الجنسية، ضعف الانتصاب، قلة الانتصاب الصباحي، الإرهاق الجسدي المزمن، تقلبات المزاج، وتراجع الكتلة العضلية.",
        silent_asymptomatic_presentation="في كثير من الحالات، خاصة لدى الشباب والرياضيين الذين استخدموا منشطات سابقة، قد يبدو المظهر الخارجي طبيعياً تماماً بينما يكون عدد الحيوانات المنوية صفراً (انعدام النطاف) دون أي ألم سريري.",
        clinical_significance="يتميز هذا الاضطراب بأنه من الحالات النادرة لعقم الرجال الحاد القابل للعلاج والشفاء التام بواسطة العلاج الهرموني الموجه (hCG + FSH).",
        diagnostic_investigations="فحص هرمون التستوستيرون الكلي والحر صباحاً على مرتين منفصلتين؛ قياس LH و FSH؛ هرمون الحليب (البرولاكتين)؛ وظائف الغدة الدرقية؛ ورنين مغناطيسي للغدة النخامية (MRI) عند الحاجة.",
        clinical_next_steps="مراجعة استشاري الغدد الصماء واستشاري طب الذكورة والتناسل. إيقاف أي مركبات هرمونية خارجية تحت إشراف طبي والبدء في العلاج التعويضي بموجهات الغدد التناسلية لتحفيز إنتاج الحيوانات المنوية."
    )
    db.add_all([c2_en, c2_ar])
    db.flush()

    v1_c2 = ContentVersion(
        condition_id=c2.id,
        version_number=1,
        snapshot_data=MedicalContentService._create_snapshot(c2),
        change_summary="Initial clinical documentation and bilingual translation",
        created_by="Dr. Fatima Al-Hashimi"
    )
    db.add(v1_c2)

    # 5. Condition 3: Klinefelter Syndrome (PUBLISHED)
    c3 = MedicalCondition(
        slug="klinefelter-syndrome",
        category_id=cat_genetic.id,
        organs_involved=["Testes", "Seminiferous Tubules", "Leydig Cells"],
        evidence_classification="Level 1A",
        publication_status=PublicationStatus.PUBLISHED,
        current_version=1,
        last_reviewed_at=datetime(2026, 8, 10, 11, 0, tzinfo=timezone.utc),
        clinical_reviewer="Dr. Omar Al-Zaabi (Clinical Geneticist, MOHAP Licensed)"
    )
    c3.references = [ref_eau, ref_aua]
    db.add(c3)
    db.flush()

    c3_en = ConditionContent(
        condition_id=c3.id,
        language="en",
        name="Klinefelter Syndrome (47,XXY)",
        short_description="A sex chromosomal genetic variation where a male carries an additional X chromosome, leading to testicular dysgenesis, primary hypogonadism and azoospermia.",
        detailed_explanation="Klinefelter syndrome is the most prevalent genetic etiology of non-obstructive azoospermia, occurring in approximately 1 in 600 live male births. Most men are born with a 47,XXY constitution due to maternal or paternal meiotic nondisjunction. Progressive fibrosis and hyalinization of seminiferous tubules occur during puberty, leaving microorchidism and extensive germ cell depletion.",
        biological_mechanism="The presence of the extra X chromosome causes accelerated loss of germ cells during perinatal life and puberty. Extensive hyalinization obliterates seminiferous tubules while Leydig cell clusters exhibit hyperplasia and functional impairment, precipitating elevated gonadotropins (high FSH and LH) and low-normal or frankly low testosterone.",
        causes_and_risk_factors="Random meiotic nondisjunction event during parental gametogenesis. Not inherited from family history in the conventional sense; maternal age > 35 is an associated risk factor.",
        possible_symptoms="Small, firm testicles (< 4 mL volume), gynecomastia (enlarged breast tissue), tall stature with relatively long limbs (eunuchoid proportions), reduced facial and body hair, and metabolic predisposition to diabetes.",
        silent_asymptomatic_presentation="Up to 60-70% of men with Klinefelter syndrome remain UNDIAGNOSED throughout their lifetime due to mild, unnoticeable phenotype variations, often discovering the condition only upon fertility evaluation.",
        clinical_significance="Despite primary testicular failure and azoospermia, microdissection testicular sperm extraction (micro-TESE) can successfully retrieve viable sperm in approximately 45-50% of adult men with 47,XXY for intracytoplasmic sperm injection (ICSI).",
        diagnostic_investigations="Peripheral blood karyotype (cytogenetic analysis) with analysis of minimum 20-30 metaphase cells; serum FSH, LH, and total testosterone; bone mineral density (DEXA scan) to monitor osteopenia.",
        clinical_next_steps="Consultation with a Clinical Geneticist and Andrologist specialized in micro-TESE. Discussion of fertility preservation/sperm retrieval prior to testosterone replacement therapy initiation."
    )
    c3_ar = ConditionContent(
        condition_id=c3.id,
        language="ar",
        name="متلازمة كلاينفلتر (47,XXY)",
        short_description="اضطراب صبغي وراثي ناتج عن وجود كروموسوم X إضافي لدى الذكر، مما يسبب خلل تكوين الخصية وقصوراً أولياً في وظائفها وانعدام النطاف.",
        detailed_explanation="تعد متلازمة كلاينفلتر السبب الوراثي الأكثر شيوعاً لانعدام الحيوانات المنوية غير الانسدادي، حيث تصيب حوالي 1 من كل 600 ولادة ذكور. يمتلك المصاب التركيب الصبغي 47,XXY بسبب عدم انفصال الكروموسومات أثناء الانقسام المنصف. خلال سن البلوغ، يحدث تليف تدريجي في الأنابيب المنوية للخصية وتراجع شديد في الخلايا الجرثومية المنتجة للحيوانات المنوية.",
        biological_mechanism="يتسبب كروموسوم X الإضافي في فقدان متسارع للخلايا الجرثومية. تتليف الأنابيب المنوية وتتراجع وظيفة خلايا ليديج، مما ينتج عنه ارتفاع كبير في الهرمونات المنشطة (ارتفاع شديد في FSH و LH) مع انخفاض التستوستيرون.",
        causes_and_risk_factors="خلل عشوائي في انفصال الكروموسومات أثناء تكوين الأمشاج لدى أحد الوالدين. ليست حالة وراثية متوارثة عائلياً بالمعنى التقليدي، وترتبط بزيادة عمر الأم.",
        possible_symptoms="صغر وصلابة حجم الخصيتين (< 4 مل)، التثدي (تضخم الثدي)، طول القامة مع طول نسبي في الأطراف، قلة شعر الوجه والجسد، وقابلية أيضية لاضطرابات السكر.",
        silent_asymptomatic_presentation="ما يصل إلى 60-70٪ من المصابين بمتلازمة كلاينفلتر لا يتم تشخيصهم طوال حياتهم بسبب التباين الكبير في الأعراض وخفتها، ويكتشف معظمهم الحالة صدفة عند إجراء فحوصات الإنجاب.",
        clinical_significance="على الرغم من انعدام الحيوانات المنوية في القذف، فإن الجراحة الميكروسكوبية لاستخلاص الحيوانات المنوية من الخصية (micro-TESE) تنجح في استخراج حيوانات منوية قابلة للتلقيح المجهري لدى 45-50٪ من المصابين.",
        diagnostic_investigations="فحص النمط النووي الوراثي للدم (Karyotyping)؛ قياس هرمونات الغدة النخامية (FSH و LH) وهرمون التستوستيرون؛ وفحص كثافة العظام (DEXA) للكشف عن هشاشة العظام.",
        clinical_next_steps="استشارة استشاري الوراثة السريرية واستشاري أمراض الذكورة المتخصص في المسح المجهري للخصية. تقييم فرص استخلاص الحيوانات المنوية بالتنسيق مع مركز إخصاب مرخص."
    )
    db.add_all([c3_en, c3_ar])
    db.flush()

    v1_c3 = ContentVersion(
        condition_id=c3.id,
        version_number=1,
        snapshot_data=MedicalContentService._create_snapshot(c3),
        change_summary="Initial clinical genetic entry",
        created_by="Dr. Omar Al-Zaabi"
    )
    db.add(v1_c3)

    # 6. Condition 4: Obstructive Azoospermia (PENDING_REVIEW - demonstration item for review workflow)
    c4 = MedicalCondition(
        slug="obstructive-azoospermia-cbavd",
        category_id=cat_obstructive.id,
        organs_involved=["Vas Deferens", "Epididymis", "Seminal Vesicles"],
        evidence_classification="Level 2A",
        publication_status=PublicationStatus.PENDING_REVIEW,
        current_version=1,
        clinical_reviewer=None
    )
    c4.references = [ref_eau, ref_who]
    db.add(c4)
    db.flush()

    c4_en = ConditionContent(
        condition_id=c4.id,
        language="en",
        name="Congenital Bilateral Absence of the Vas Deferens (CBAVD)",
        short_description="An obstructive condition where both sperm transport ducts fail to develop properly, strongly linked to CFTR cystic fibrosis gene mutations.",
        detailed_explanation="CBAVD accounts for approximately 1-2% of male infertility cases and up to 6% of obstructive azoospermia. In this condition, testicular spermatogenesis is completely intact, but sperm cannot exit into the ejaculate due to absent vas deferens and atrophic seminal vesicles.",
        biological_mechanism="Mutations in the CFTR gene impair chloride and bicarbonate transport across developing epithelial cells in the wolffian duct, resulting in ductal plugging and failure of vas deferens elongation during early fetal organogenesis.",
        causes_and_risk_factors="Compound heterozygosity or homozygous mutations in the CFTR gene (cystic fibrosis transmembrane conductance regulator).",
        possible_symptoms="Typically zero symptoms. Men possess normal virilization, normal libido, and normal erection.",
        silent_asymptomatic_presentation="Strictly silent. Physical exam reveals non-palpable vas deferens bilaterally, and semen analysis demonstrates low volume (< 1.5 mL), acidic pH (< 7.2), and azoospermia.",
        clinical_significance="High clinical and genetic importance: Both the patient and female partner MUST undergo CFTR genetic screening before assisted reproduction to assess cystic fibrosis risk in offspring.",
        diagnostic_investigations="Targeted CFTR gene sequencing; transrectal ultrasound (TRUS) demonstrating seminal vesicle absence or hypoplasia; semen pH and fructose testing; physical palpation of the spermatic cord.",
        clinical_next_steps="Genetic counseling, percutaneous epididymal sperm aspiration (PESA) or testicular biopsy (TESA) for ICSI."
    )
    c4_ar = ConditionContent(
        condition_id=c4.id,
        language="ar",
        name="الغياب الخلقي الثنائي للأسهر (CBAVD)",
        short_description="حالة انسداد خلقي لا تتطور فيها القنوات المنوية الناقلة على الجانبين، وترتبط ارتباطاً وثيقاً بطفرات جين التليف الكيسي (CFTR).",
        detailed_explanation="يمثل الغياب الخلقي للأسهر حوالي 1-2٪ من حالات عقم الرجال وما يصل إلى 6٪ من حالات انعدام الحيوانات المنوية الانسدادي. في هذه الحالة، يكون إنتاج الحيوانات المنوية داخل الخصية سليماً تماماً، لكنها لا تستطيع الخروج مع السائل المنوي لعدم وجود القنوات الناقلة.",
        biological_mechanism="تؤدي طفرات جين CFTR إلى اختلال نقل أيونات الكلوريد والبيكربونات في الخلايا الظهارية لقناة وولف الجنينية، مما يسبب انسدادها وفشل تكوين الوعاء الناقل والحويصلات المنوية.",
        causes_and_risk_factors="طفرات جينية في جين CFTR (منظم موصلية التليف الكيسي عبر الغشاء).",
        possible_symptoms="لا توجد أي أعراض عضوية؛ الخصائص الذكورية والانتصاب والرغبة الجنسية طبيعية تماماً.",
        silent_asymptomatic_presentation="حالة صامتة تماماً. يظهر الفحص السريري غياب الأسهر عند الجس، ويظهر تحليل السائل المنوي حجماً منخفضاً (< 1.5 مل) وحموضة مرتفعة (pH < 7.2) مع انعدام تام للحيوانات المنوية.",
        clinical_significance="أهمية وراثية وسريرية بالغة: يجب إجراء الفحص الجيني للزوجين قبل الشروع في الإخصاب لتفادي ولادة أطفال مصابين بمرض التليف الكيسي.",
        diagnostic_investigations="الفحص الجيني لتسلسل طفرات CFTR، السونار عبر الشرج (TRUS) لفحص الحويصلات المنوية، فحص حموضة وسكر الفركتوز في السائل المنوي، والفحص السريري للحبيل المنوي.",
        clinical_next_steps="استشارة وراثية متخصصة، وسحب الحيوانات المنوية من البربخ (PESA) أو الخصية (TESA) لاستخدامها في الحقن المجهري."
    )
    db.add_all([c4_en, c4_ar])
    db.flush()

    v1_c4 = ContentVersion(
        condition_id=c4.id,
        version_number=1,
        snapshot_data=MedicalContentService._create_snapshot(c4),
        change_summary="Draft submission for clinical genetic review",
        created_by="Dr. Omar Al-Zaabi"
    )
    db.add(v1_c4)

    # 7. Condition 5: Cryptorchidism (DRAFT - demonstration item for editing & draft workflow)
    c5 = MedicalCondition(
        slug="cryptorchidism",
        category_id=cat_congenital.id,
        organs_involved=["Testes", "Inguinal Canal", "Abdomen"],
        evidence_classification="Level 1A",
        publication_status=PublicationStatus.DRAFT,
        current_version=1,
        clinical_reviewer=None
    )
    c5.references = [ref_eau, ref_who]
    db.add(c5)
    db.flush()

    c5_en = ConditionContent(
        condition_id=c5.id,
        language="en",
        name="Cryptorchidism (Undescended Testis)",
        short_description="Failure of one or both testes to descend into the scrotum during fetal development, leading to long-term risk of germ cell impairment and malignancy.",
        detailed_explanation="Cryptorchidism is the most frequent congenital anomaly of male genitalia, observed in 1-4% of full-term and up to 30% of premature male infants. While most spontaneously descend by 3-6 months of life, persistent cryptorchidism causes progressive degeneration of germ cells when the testicle remains exposed to higher abdominal temperatures.",
        biological_mechanism="Exposure to normal intra-abdominal temperature (37°C) instead of the cooler scrotal environment (33-34°C) causes progressive loss of Type A dark spermatogonia, impairing transformation into mature sperm-producing stem cells.",
        causes_and_risk_factors="Prematurity, low birth weight, maternal smoking or endocrine disruptor exposure, anatomical barriers (short spermatic vessels, patent processus vaginalis).",
        possible_symptoms="In adult men: Empty scrotal sac on one or both sides, history of childhood orchiopexy, or palpable nodule in the inguinal canal.",
        silent_asymptomatic_presentation="Adult men who underwent childhood orchiopexy may believe their reproductive health is fully normalized, unaware that unilateral cryptorchidism reduces fertility by 30% and bilateral cryptorchidism by up to 70%.",
        clinical_significance="Significantly elevated risk of both infertility and testicular germ cell tumors (seminoma/non-seminoma).",
        diagnostic_investigations="High-resolution ultrasound / MRI of the pelvis and inguinal canal; physical examination; serial semen analysis; annual testicular self-examination counseling.",
        clinical_next_steps="Urology referral for testicular assessment, semen analysis, and testicular cancer surveillance protocols."
    )
    c5_ar = ConditionContent(
        condition_id=c5.id,
        language="ar",
        name="الخصية المعلقة / غير النازلة (Cryptorchidism)",
        short_description="فشل إحدى الخصيتين أو كلتيهما في النزول إلى كيس الصفن أثناء التطور الجنيني، مما يرفع احتمالية تراجع الخصوبة ومخاطر الأورام الخصوية.",
        detailed_explanation="تعد الخصية المعلقة من أكثر التشوهات التناسلية الخلقية شيوعاً لدى الذكور (1-4٪ من المواليد مكتملي النمو). بالرغم من هبوط بعضها تلقائياً في الأشهر الأولى، فإن بقاء الخصية معلقة يعرضها لدرجة حرارة البطن المرتفعة، مما يتسبب في تنكس تدريجي للخلايا الجرثومية.",
        biological_mechanism="تعرض الخصية لدرجة حرارة البطن (37 مئوية) بدلاً من حرارة الصفن المناسبة (33-34 مئوية) يؤدي لتلف الخلايا الجذعية المنتجة للنطاف (Type A Spermatogonia) وتراجع قدرتها على التمايز.",
        causes_and_risk_factors="الولادة المبكرة، نقص وزن الولادة، التعرض للملوثات الهرمونية أثناء الحمل، قصر الأوعية المنوية خلقياً.",
        possible_symptoms="لدى البالغين: خلو كيس الصفن من إحدى الخصيتين، أو وجود ندبة جراحية سابقة لعملية تثبيت الخصية في الطفولة.",
        silent_asymptomatic_presentation="قد يعتقد الرجل الذي أجرى جراحة تثبيت الخصية في طفولته أن خصوبته طبيعية تماماً، بينما تشير الدراسات إلى تأثر الخصوبة بنسبة 30٪ في الحالات الأحادية و 70٪ في الحالات الثنائية دون ظهور أعراض حالية.",
        clinical_significance="ارتفاع ملحوظ في احتمالية ضعف السائل المنوي بالإضافة لارتفاع خطر الإصابة بأورام الخصية مقارنة بعموم الرجال.",
        diagnostic_investigations="فحص السونار أو الرنين المغناطيسي للحوض والمنطقة الإربية، فحص السائل المنوي الشامل، وتدريب المريض على الفحص الذاتي الدوري للخصية.",
        clinical_next_steps="المتابعة مع استشاري المسالك البولية والتناسلية لإجراء تقييم شامل للسائل المنوي ومتابعة دورية لسلامة النسيج الخصوي."
    )
    db.add_all([c5_en, c5_ar])
    db.flush()

    v1_c5 = ContentVersion(
        condition_id=c5.id,
        version_number=1,
        snapshot_data=MedicalContentService._create_snapshot(c5),
        change_summary="Initial clinical draft entry",
        created_by="Administrator"
    )
    db.add(v1_c5)

    db.commit()
    print("GENOVEX Medical Content System successfully seeded!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
