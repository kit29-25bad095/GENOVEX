from sqlalchemy.orm import Session
from app.models.facility import HealthcareFacility
import enum

class UAEEmirate(str, enum.Enum):
    ABU_DHABI = 'ABU_DHABI'
    DUBAI = 'DUBAI'
    SHARJAH = 'SHARJAH'
    AJMAN = 'AJMAN'
    UMM_AL_QUWAIN = 'UMM_AL_QUWAIN'
    RAS_AL_KHAIMAH = 'RAS_AL_KHAIMAH'
    FUJAIRAH = 'FUJAIRAH'

class UAERegulatoryAuthority(str, enum.Enum):
    DHA = 'DHA'
    DOH = 'DOH'
    MOHAP = 'MOHAP'

class FacilityType(str, enum.Enum):
    TERTIARY_HOSPITAL = 'TERTIARY_HOSPITAL'
    SPECIALIZED_ANDROLOGY_CENTER = 'SPECIALIZED_ANDROLOGY_CENTER'
    FERTILITY_IVF_CENTER = 'FERTILITY_IVF_CENTER'
    GENERAL_HOSPITAL = 'GENERAL_HOSPITAL'

UAE_FACILITIES_SEED = [   {   'address_ar': 'جزيرة المارية، أبوظبي، الإمارات العربية المتحدة',
        'address_en': 'Al Maryah Island, Abu Dhabi, UAE',
        'booking_url': 'https://www.clevelandclinicabudhabi.ae/en/patients-visitors/book-an-appointment',
        'city_ar': 'أبوظبي',
        'city_en': 'Abu Dhabi',
        'emergency_phone': '+971 2 659 0200',
        'emirate': 'ABU_DHABI',
        'facility_type': 'TERTIARY_HOSPITAL',
        'has_24_7_emergency': True,
        'has_andrology_specialist': True,
        'has_micro_tese_capability': True,
        'has_who_semen_analysis_lab': True,
        'insurance_networks': [   'Daman',
                                  'Thiqa',
                                  'NextCare',
                                  'AXA / GIG',
                                  'MedNet',
                                  'Cigna',
                                  'MetLife',
                                  'Sukoon',
                                  'NAS'],
        'is_active': True,
        'is_verified': True,
        'name_ar': 'مستشفى كليفلاند كلينك أبوظبي — مركز صحة الرجل وأمراض '
                   'الذكورة',
        'name_en': 'Cleveland Clinic Abu Dhabi — Male Health & Andrology '
                   'Center',
        'notes_ar': 'مركز تميز معتمد من دائرة الصحة بأبوظبي مع قسم طوارئ '
                    'جراحية بولية على مدار الساعة ومختبرات متقدمة للذكورة.',
        'notes_en': 'DoH-accredited tertiary center of excellence with 24/7 '
                    'urological surgical emergency and advanced microsurgery.',
        'offered_specialties': [   'Male Reproductive Urologist / Andrologist',
                                   'General Urology',
                                   'Reproductive Endocrinology',
                                   'Microsurgical Varicocelectomy',
                                   'Micro-TESE / Sperm Retrieval',
                                   'Genetic Counseling'],
        'phone_number': '+971 800 82223',
        'regulatory_authority': 'DOH',
        'slug': 'cleveland-clinic-abu-dhabi',
        'website_url': 'https://www.clevelandclinicabudhabi.ae'},
    {   'address_ar': 'واحة دبي للسيليكون، دبي، الإمارات العربية المتحدة',
        'address_en': 'Dubai Silicon Oasis, Dubai, UAE',
        'booking_url': 'https://fuh.care/book-appointment',
        'city_ar': 'دبي',
        'city_en': 'Dubai',
        'emergency_phone': '+971 4 414 4499',
        'emirate': 'DUBAI',
        'facility_type': 'TERTIARY_HOSPITAL',
        'has_24_7_emergency': True,
        'has_andrology_specialist': True,
        'has_micro_tese_capability': True,
        'has_who_semen_analysis_lab': True,
        'insurance_networks': [   'NextCare',
                                  'AXA / GIG',
                                  'Daman',
                                  'MetLife',
                                  'Cigna',
                                  'MedNet',
                                  'Neuron',
                                  'Sukoon'],
        'is_active': True,
        'is_verified': True,
        'name_ar': 'مستشفى فقيه الجامعي — قسم صحة الرجل والمسالك البولية',
        'name_en': "Fakeeh University Hospital — Men's Health & Urology "
                   'Department',
        'notes_ar': 'مركز طبي أكاديمي حديث يقدم تقنيات متطورة في جراحة المسالك '
                    'البولية وفحوصات الخصوبة.',
        'notes_en': 'Academic medical center with cutting-edge robotic urology '
                    'and advanced diagnostics.',
        'offered_specialties': [   'Male Reproductive Urologist / Andrologist',
                                   'General Urology',
                                   'Clinical Sexology & Erectile Dysfunction',
                                   'WHO 6th Edition Semen Analysis',
                                   'Color Doppler Scrotal Ultrasound'],
        'phone_number': '+971 4 414 4444',
        'regulatory_authority': 'DHA',
        'slug': 'fakeeh-university-hospital-dubai',
        'website_url': 'https://fuh.care'},
    {   'address_ar': 'البرشاء جنوب 3، طريق أم سقيم، دبي، الإمارات العربية '
                      'المتحدة',
        'address_en': 'Al Barsha South 3, Umm Suqeim Road, Dubai, UAE',
        'booking_url': 'https://www.mediclinic.ae/en/parkview-hospital/book-an-appointment.html',
        'city_ar': 'دبي',
        'city_en': 'Dubai',
        'emergency_phone': '+971 4 445 8888',
        'emirate': 'DUBAI',
        'facility_type': 'TERTIARY_HOSPITAL',
        'has_24_7_emergency': True,
        'has_andrology_specialist': True,
        'has_micro_tese_capability': True,
        'has_who_semen_analysis_lab': True,
        'insurance_networks': [   'Daman',
                                  'NextCare',
                                  'AXA / GIG',
                                  'MedNet',
                                  'Cigna',
                                  'MetLife',
                                  'Sukoon',
                                  'NAS'],
        'is_active': True,
        'is_verified': True,
        'name_ar': 'مستشفى ميديكلينيك بارك فيو — رعاية أمراض الذكورة والمسالك '
                   'البولية',
        'name_en': 'Mediclinic Parkview Hospital — Andrology & Urological Care',
        'notes_ar': 'مستشفى متكامل في جنوب دبي يوفر طوارئ على مدار الساعة '
                    'وكادراً استشارياً في طب الذكورة.',
        'notes_en': 'Leading private hospital in South Dubai with 24/7 adult '
                    'emergency department and full andrology subspecialists.',
        'offered_specialties': [   'Male Reproductive Urologist / Andrologist',
                                   'General Urology',
                                   'Reproductive Endocrinology',
                                   'Microsurgery'],
        'phone_number': '+971 800 1999',
        'regulatory_authority': 'DHA',
        'slug': 'mediclinic-parkview-dubai',
        'website_url': 'https://www.mediclinic.ae'},
    {   'address_ar': 'عود ميثاء، الشارع 19، دبي، الإمارات العربية المتحدة',
        'address_en': 'Oud Metha, 19th Street, Dubai, UAE',
        'booking_url': 'https://www.ahdubai.com/book-appointment',
        'city_ar': 'دبي',
        'city_en': 'Dubai',
        'emergency_phone': '+971 4 377 5555',
        'emirate': 'DUBAI',
        'facility_type': 'TERTIARY_HOSPITAL',
        'has_24_7_emergency': True,
        'has_andrology_specialist': True,
        'has_micro_tese_capability': True,
        'has_who_semen_analysis_lab': True,
        'insurance_networks': [   'NextCare',
                                  'AXA / GIG',
                                  'Daman',
                                  'Cigna',
                                  'MetLife',
                                  'MedNet',
                                  'Sukoon'],
        'is_active': True,
        'is_verified': True,
        'name_ar': 'المستشفى الأمريكي دبي — مركز صحة الرجل والمسالك البولية',
        'name_en': "American Hospital Dubai — Center for Men's Health & "
                   'Urology',
        'notes_ar': 'عضو شبكة مايو كلينك للرعاية مع قسم متميز لأمراض الذكورة '
                    'وحفظ الخصوبة.',
        'notes_en': 'Mayo Clinic Care Network member with premier andrology '
                    'and male fertility preservation services.',
        'offered_specialties': [   'Male Reproductive Urologist / Andrologist',
                                   'General Urology',
                                   'Reproductive Endocrinology',
                                   'Genetic Counseling'],
        'phone_number': '+971 4 377 5500',
        'regulatory_authority': 'DHA',
        'slug': 'american-hospital-dubai',
        'website_url': 'https://www.ahdubai.com'},
    {   'address_ar': 'مدينة محمد بن زايد، حوض 33، أبوظبي، الإمارات العربية '
                      'المتحدة',
        'address_en': 'Mohamed Bin Zayed City, Sector 33, Abu Dhabi, UAE',
        'booking_url': 'https://burjeelmedicalcity.com/book-appointment/',
        'city_ar': 'أبوظبي',
        'city_en': 'Abu Dhabi',
        'emergency_phone': '+971 2 204 4444',
        'emirate': 'ABU_DHABI',
        'facility_type': 'TERTIARY_HOSPITAL',
        'has_24_7_emergency': True,
        'has_andrology_specialist': True,
        'has_micro_tese_capability': True,
        'has_who_semen_analysis_lab': True,
        'insurance_networks': [   'Thiqa',
                                  'Daman',
                                  'NextCare',
                                  'AXA / GIG',
                                  'MedNet',
                                  'NAS',
                                  'Cigna'],
        'is_active': True,
        'is_verified': True,
        'name_ar': 'مدينة برجيل الطبية — الرعاية المتقدمة للمسالك البولية '
                   'والإنجاب',
        'name_en': 'Burjeel Medical City — Advanced Urology & Reproductive '
                   'Care',
        'notes_ar': 'صرح طبي متقدم في مدينة محمد بن زايد يقدم حلولاً متقدمة '
                    'لحالات عقم الرجال والجراحة الميكروسكوبية.',
        'notes_en': 'Flagship quaternary facility in Mohamed Bin Zayed City '
                    'catering to complex cases and fertility surgery.',
        'offered_specialties': [   'Male Reproductive Urologist / Andrologist',
                                   'General Urology',
                                   'Reproductive Endocrinology',
                                   'Genetic Counseling'],
        'phone_number': '+971 800 55',
        'regulatory_authority': 'DOH',
        'slug': 'burjeel-medical-city-abu-dhabi',
        'website_url': 'https://burjeelmedicalcity.com'},
    {   'address_ar': 'البطين، معسكر آل نهيان، أبوظبي، الإمارات العربية '
                      'المتحدة',
        'address_en': 'Al Bateen, Al Nahyan Camp, Abu Dhabi, UAE',
        'booking_url': 'https://hplus.ae/fertility/book-appointment',
        'city_ar': 'أبوظبي',
        'city_en': 'Abu Dhabi',
        'emergency_phone': None,
        'emirate': 'ABU_DHABI',
        'facility_type': 'FERTILITY_IVF_CENTER',
        'has_24_7_emergency': False,
        'has_andrology_specialist': True,
        'has_micro_tese_capability': True,
        'has_who_semen_analysis_lab': True,
        'insurance_networks': [   'Thiqa',
                                  'Daman',
                                  'NextCare',
                                  'AXA / GIG',
                                  'Cigna'],
        'is_active': True,
        'is_verified': True,
        'name_ar': 'مركز هيلث بلس للإخصاب أبوظبي',
        'name_en': 'HealthPlus Fertility Center Abu Dhabi',
        'notes_ar': 'مركز إخصاب متخصص مع مختبر ذكورة معتمد من CAP ومطابق '
                    'لمعايير منظمة الصحة العالمية.',
        'notes_en': 'Dedicated fertility center with CAP-accredited andrology '
                    'laboratory adhering to WHO 6th edition standards.',
        'offered_specialties': [   'Male Reproductive Urologist / Andrologist',
                                   'Reproductive Endocrinology',
                                   'WHO 6th Edition Semen Analysis',
                                   'Genetic Counseling',
                                   'Fertility Preservation'],
        'phone_number': '+971 2 643 3494',
        'regulatory_authority': 'DOH',
        'slug': 'healthplus-fertility-abu-dhabi',
        'website_url': 'https://hplus.ae/fertility/'},
    {   'address_ar': 'مبنى 64، مبنى الرازي، مدينة دبي الطبية، دبي، الإمارات '
                      'العربية المتحدة',
        'address_en': 'Building 64, Al Razi Building, Dubai Healthcare City '
                      '(DHCC), Dubai, UAE',
        'booking_url': 'https://orchid-fertility.com/contact/',
        'city_ar': 'دبي',
        'city_en': 'Dubai',
        'emergency_phone': None,
        'emirate': 'DUBAI',
        'facility_type': 'SPECIALIZED_ANDROLOGY_CENTER',
        'has_24_7_emergency': False,
        'has_andrology_specialist': True,
        'has_micro_tese_capability': True,
        'has_who_semen_analysis_lab': True,
        'insurance_networks': [   'NextCare',
                                  'AXA / GIG',
                                  'MetLife',
                                  'Cigna',
                                  'MedNet'],
        'is_active': True,
        'is_verified': True,
        'name_ar': 'عيادة أوركيد للخصوبة — طب الذكورة والجينات الإنجابية',
        'name_en': 'Orchid Fertility Clinic — Andrology & Reproductive '
                   'Genetics',
        'notes_ar': 'عيادة متخصصة في مدينة دبي الطبية تركز على تشخيص العوامل '
                    'الذكورية والفحوصات الوراثية المتقدمة.',
        'notes_en': 'Specialized reproductive center in Dubai Healthcare City '
                    'focusing on male factor subfertility and genetic '
                    'screening.',
        'offered_specialties': [   'Male Reproductive Urologist / Andrologist',
                                   'Reproductive Endocrinology',
                                   'Genetic Counseling',
                                   'WHO 6th Edition Semen Analysis'],
        'phone_number': '+971 4 437 6222',
        'regulatory_authority': 'DHA',
        'slug': 'orchid-fertility-clinic-dubai',
        'website_url': 'https://orchid-fertility.com'},
    {   'address_ar': 'المدينة الجامعية، الشارقة، الإمارات العربية المتحدة',
        'address_en': 'University City, Sharjah, UAE',
        'booking_url': 'https://www.uhs.ae/appointments',
        'city_ar': 'الشارقة',
        'city_en': 'Sharjah',
        'emergency_phone': '+971 6 505 8888',
        'emirate': 'SHARJAH',
        'facility_type': 'TERTIARY_HOSPITAL',
        'has_24_7_emergency': True,
        'has_andrology_specialist': True,
        'has_micro_tese_capability': False,
        'has_who_semen_analysis_lab': True,
        'insurance_networks': [   'NextCare',
                                  'Daman',
                                  'AXA / GIG',
                                  'MedNet',
                                  'Sharjah Government Employee Network'],
        'is_active': True,
        'is_verified': True,
        'name_ar': 'مستشفى الجامعة بالشارقة — قسم المسالك البولية والصحة '
                   'الإنجابية',
        'name_en': 'University Hospital Sharjah — Urology & Reproductive '
                   'Health',
        'notes_ar': 'مستشفى جامعي رائد في الإمارات الشمالية يقدم خدمات طوارئ '
                    'المسالك البولية وفحوصات الذكورة.',
        'notes_en': 'Premier tertiary hospital in the Northern Emirates with '
                    'full emergency urological and diagnostic services.',
        'offered_specialties': [   'General Urology',
                                   'Male Reproductive Urologist / Andrologist',
                                   'Reproductive Endocrinology',
                                   'Scrotal Doppler Ultrasound'],
        'phone_number': '+971 6 505 8555',
        'regulatory_authority': 'MOHAP',
        'slug': 'university-hospital-sharjah',
        'website_url': 'https://www.uhs.ae'}]

def seed_facilities(db: Session):
    """
    Populates default verified UAE healthcare facilities if not already existing.
    """
    if db.query(HealthcareFacility).first():
        return

    print("Seeding UAE Healthcare Facilities & Andrology Centers...")
    for fac_data in UAE_FACILITIES_SEED:
        facility = HealthcareFacility(**fac_data)
        db.add(facility)
    db.commit()
    print(f"Successfully seeded {len(UAE_FACILITIES_SEED)} UAE Healthcare Facilities.")

seed_facilities_v1 = seed_facilities
