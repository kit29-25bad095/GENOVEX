# GENOVEX
## AI-Assisted Male Reproductive Health Risk Identification & Clinical Navigation Platform

**Domain:** Digital Healthcare / Male Reproductive Health  
**Target Market:** United Arab Emirates (UAE)  
**Languages:** English & Arabic (العربية - RTL)  
**Core Purpose:** Early identification of male reproductive-health risk factors and clinical navigation.

---

### Medical Boundary Notice
**GENOVEX is NOT:**
- An infertility diagnosis application.
- A sperm-quality measurement application.
- A fertility prediction system.
- A replacement for medical professionals.
- A treatment or medication recommendation system.

**GENOVEX IS:**
- A reproductive-health awareness platform.
- An adaptive health questionnaire.
- A clinician-reviewed risk-identification system.
- A transparent rule-based assessment platform.
- A clinical-navigation and referral-support system.

---

## Architecture Overview

1. **Deterministic Clinical Rule Engine (Decoupled):**
   - Independent 4-tier triage system (`No Risk Factors`, `Risk Factors Identified`, `Clinical Evaluation Recommended`, `Urgent Medical Assessment`).
   - Priority deterministic urgent red-flag evaluation.
   - Decoupled from educational content: editing medical descriptions never alters clinical assessment scoring.
2. **Dynamic Medical Content & Dysfunction Management Module (CMS):**
   - Allows authorized administrators and clinical reviewers to add, edit, update, review, publish, archive, and rollback conditions without modifying application source code.
   - Structured around **20 clinical fields** with full English and Arabic (RTL) translations.
   - Version history and one-click rollback snapshot mechanism.
3. **Public Health Library:**
   - Dynamic, responsive user-facing educational library querying published conditions from the database.
   - Real-time bilingual support (`en` / `ar` with RTL layout flipping).
   - Evidence-linked citations to WHO, EAU, and AUA/ASRM clinical guidelines.

---

## Directory Structure

```
GENOVEX/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # Admin CMS & Public Health Library endpoints
│   │   ├── core/                 # Config, Database engine, Seed generator
│   │   ├── models/               # SQLAlchemy models (Conditions, Contents, Versions, Rules)
│   │   ├── schemas/              # Pydantic v2 schemas
│   │   ├── services/             # Pure medical content & review business logic
│   │   └── static/               # Interactive UI templates (Admin CMS & Public Library)
│   ├── tests/                    # Comprehensive Pytest test suite
│   └── main.py                   # FastAPI server entry point
├── requirements.txt              # Python dependencies
├── .gitignore
└── README.md
```

---

## Quickstart

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Node.js & npm (for frontend tooling)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Seeding
Populate initial categories, guidelines, and verified conditions (Varicocele, Hypogonadotropic Hypogonadism, Klinefelter Syndrome, CBAVD, Cryptorchidism):
```bash
python backend/app/core/seed_data.py
```

### 3. Start the Platform Server
```bash
# Set PYTHONPATH to include backend:
export PYTHONPATH="backend"     # Linux / macOS
$env:PYTHONPATH="backend"       # Windows PowerShell

uvicorn main:app --reload --port 8000 --app-dir backend
```

- **Platform Portal:** [http://localhost:8000](http://localhost:8000)
- **Admin Medical Content CMS:** [http://localhost:8000/admin/medical-content](http://localhost:8000/admin/medical-content)
- **Public Health Library:** [http://localhost:8000/health-library](http://localhost:8000/health-library)
- **OpenAPI / Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running Automated Tests
```bash
pytest backend/tests/test_medical_content.py -v
```

---

## License & Compliance

### Healthcare Regulatory & Clinical Alignment
This platform is architected in compliance with:
- **UAE Federal Decree-Law No. 45 of 2021** regarding Personal Data Protection (PDPL)
- **UAE Federal Law No. 2 of 2019** on the Use of ICT in Healthcare (Health Data Law)
- **European Association of Urology (EAU)** Male Infertility Guidelines (2024)
- **WHO Laboratory Manual** for the Examination and Processing of Human Semen (6th Edition)

### Open-Source & Third-Party Software Licenses
GENOVEX incorporates and is built upon industry-standard open-source technologies and third-party services. All copyrights and licenses are acknowledged:

| Software / Runtime | License | Copyright Holder / Organization |
| :--- | :--- | :--- |
| **TypeScript** | **Apache 2.0** | Microsoft Corporation |
| **Python** | **PSF License** | Python Software Foundation |
| **PostgreSQL** | **PostgreSQL Lic.** | PostgreSQL Global Development Group |
| **React** | **MIT** | Meta Platforms, Inc. / React Contributors |
| **Next.js** | **MIT** | Vercel, Inc. |
| **FastAPI** | **MIT** | Sebastián Ramírez |
| **Tailwind CSS** | **MIT** | Tailwind Labs, Inc. |
| **OpenAI API** | **Service terms** | OpenAI, L.L.C. |

For detailed copyright notices, attribution statements, and license references, see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) and the in-app disclosure at `/licensing`.

### Proprietary Clinical Property
The deterministic clinical rule directed acyclic graphs (DAG), 11-domain reproductive health questionnaire logic, and urgent red-flag clinical triage matrices are proprietary intellectual property of GENOVEX © 2026. All rights reserved.
