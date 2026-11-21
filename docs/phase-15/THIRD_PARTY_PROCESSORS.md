# GENOVEX — PHASE 15: THIRD-PARTY PROCESSORS, LIBRARIES & SOFTWARE LICENSING
## Software Bill of Materials (SBOM), Open-Source Attribution & UAE Data Flow Mapping

### 1. Executive Summary & Open-Source Governance
GENOVEX leverages vetted, modern open-source foundations and third-party services. In compliance with open-source licensing requirements and healthcare supply-chain security standards, all third-party software components and cloud service integrations are documented, attributed, and analyzed for intellectual property (IP) and privacy implications.

The user-facing intellectual property disclosures are publicly accessible within the platform at `/licensing` and prominently featured on the Privacy Policy at `/privacy`:

```
+------------------------------------------------------------------------------------------------------------------------------------+
|                                                  Intellectual Property & Licensing                                                 |
|                                                  OPEN-SOURCE & THIRD-PARTY SOFTWARE                                                |
+------------------------------------------------------------------------------------------------------------------------------------+
|    [ MIT ]      |    [ MIT ]      |  [ Apache 2.0 ] |  [ PSF License ] |    [ MIT ]      |  [ PostgreSQL Lic. ] |    [ MIT ]      |   [ Service terms ] |
|     React       |    Next.js      |   TypeScript    |      Python      |    FastAPI      |      PostgreSQL      |   Tailwind CSS  |     OpenAI API      |
+------------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2. Software Bill of Materials (SBOM) & Open-Source Licenses

| Component / Library | Version / Layer | License Type | Notice & Attribution Requirement | License Compliance Status | Purpose within GENOVEX |
|---|---|---|---|:---:|---|
| **React** | v18.3.x / Frontend | **MIT License** | Include original copyright & permission notice | **COMPLIANT** | Declarative component UI runtime |
| **Next.js** | v14.2.x / Fullstack | **MIT License** | Include original copyright & permission notice | **COMPLIANT** | Server-side rendering, routing & edge headers |
| **TypeScript** | v5.x / Language | **Apache License 2.0** | Include Apache 2.0 notice & state changes | **COMPLIANT** | Static typing & interface reliability |
| **Python** | v3.14.x / Language | **Python Software Foundation (PSF)** | Include PSF copyright notice | **COMPLIANT** | Core backend language & runtime |
| **FastAPI** | v0.115.x / Backend | **MIT License** | Include original copyright & permission notice | **COMPLIANT** | High-performance asynchronous API framework |
| **PostgreSQL** | v16.x / Database | **PostgreSQL License** | Include PostgreSQL copyright notice | **COMPLIANT** | Primary relational database engine |
| **Tailwind CSS** | v3.4.x / Styling | **MIT License** | Include original copyright & permission notice | **COMPLIANT** | Utility-first responsive design & RTL support |
| **SQLAlchemy** | v2.0.x / ORM | **MIT License** | Include original copyright & permission notice | **COMPLIANT** | Database ORM and query compiler |
| **Pydantic** | v2.x / Schemas | **MIT License** | Include original copyright & permission notice | **COMPLIANT** | Data validation and parsing |
| **Passlib / PBKDF2** | v1.7.x / Security | **BSD License** | Include BSD copyright notice | **COMPLIANT** | NIST-approved password hashing engine |
| **PyJWT** | v2.9.x / Security | **MIT License** | Include original copyright & permission notice | **COMPLIANT** | RFC 7519 JWT encoding and decoding |
| **Lucide Icons** | v0.4x / Icons | **ISC License** | Include ISC copyright notice | **COMPLIANT** | Medical and user interface iconography |

---

### 3. Third-Party Service Providers & Cloud Data Flow Mapping

GENOVEX distinguishes sharply between **internal sovereign data stores** (where patient health data resides) and **external auxiliary cloud services** (which receive zero personal health identifiers).

| Provider / Service | Service Terms & Category | Data Transmitted | UAE Data Residency & Localization Assessment | Zero Data Retention (ZDR) Status |
|---|---|---|---|:---:|
| **OpenAI API** | Service Terms (Commercial API) | Strictly sanitized, non-diagnostic terminology and medical text explanations. **Zero PHI, zero user names, zero emails, zero questionnaire responses.** | Auxiliary educational support only. Input data does not contain patient health identifiers. | **ENFORCED:** OpenAI commercial API terms state API customer data is not used to train models. |
| **Google Gemini API** | Service Terms (Google Cloud AI) | Strictly sanitized educational glossaries and clinical guidance summaries. **Zero patient answers or session tokens.** | Google Cloud UAE Region (`me-central1` / Dammam / Doha regional availability). Zero personal health data transferred. | **ENFORCED:** Google Workspace / Vertex AI ZDR agreement applies. |
| **Vercel** | Edge Hosting Platform | Frontend static assets, compiled JavaScript chunks, and edge reverse proxy rewrites. | Edge CDN caching static content. API calls are reverse-proxied to internal backend API. | **COMPLIANT:** No database records or medical assessments stored on Vercel edge storage. |
| **Managed PostgreSQL (UAE)** | Database Provider (Target) | Encrypted user accounts, assessment snapshots, clinical rules, facility directory, and audit logs. | **MANDATORY UAE LOCALIZATION:** Hosted within AWS UAE (`me-central-1`) or Azure UAE North/Central to comply with UAE Health Data Law Art. 13. | **LOCAL RESIDENCY GUARANTEED** |

---

### 4. Zero Personal Health Information (PHI) Egress Guard

To prevent accidental data leakage to external third-party processors (such as LLM APIs or analytics providers), GENOVEX implements technical controls:

1. **Pre-Transmission Sanitization:**
   Before any prompt is constructed for educational AI services, `AIGuardrails.sanitize_user_input` disarms prompt injection attempts, strips potential base64 payloads, and filters out personal identifiers.
2. **Structural Exclusion of Patient Identifiers:**
   The AI payload builder accepts only approved medical condition strings, glossary keys, or non-diagnostic findings. Parameters representing user ID, session token, phone numbers, or email addresses are strictly rejected at the schema level.
3. **Deterministic Local Fallback:**
   In the event of network disruption or API unavailability, GENOVEX gracefully falls back to the local offline deterministic rule engine. No patient assessment ever stalls or fails due to third-party outages.

---

### 5. Proprietary Intellectual Property Protections

While GENOVEX honors all open-source software licenses, the following assets constitute proprietary intellectual property of GENOVEX:

1. **Deterministic Clinical Rule DAG:** The 20-rule male reproductive health classification matrix, cross-domain inference trees, and multi-condition edge weightings.
2. **11-Domain Adaptive Branching Logic:** The clinical sequencing and conditional skipping algorithm governing questionnaire traversal.
3. **Urgent Red-Flag Triage Circuit:** The immediate 6-hour surgical golden window emergency escalation logic for acute scrotal symptoms.
4. **Bilingual Clinical Glossary & UAE Localization:** The curated English/Arabic medical terminology mappings tailored to Gulf and UAE clinical practice.
