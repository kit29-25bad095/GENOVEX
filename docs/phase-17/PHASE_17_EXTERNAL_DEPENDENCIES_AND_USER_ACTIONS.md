# GENOVEX Phase 17: External Dependencies & User Actions Catalog

**Project:** GENOVEX Clinical Health & Genetic Risk Assessment Platform  
**Target Environment:** AWS UAE (`me-central-1` Dubai), Vercel, `.ae` Registrar  
**Document Purpose:** Exhaustive specification of all external prerequisites, credentials, domain ownership actions, and regulatory approvals required to transition GENOVEX from repository readiness to live production.  

---

## 1. Cloud Infrastructure & Service Credentials (AWS)

To provision and run the production backend in Dubai (`me-central-1`), the following infrastructure access is required:

| # | Item | Responsible Party | Description & Scope |
| :-: | :--- | :--- | :--- |
| **1.1** | **AWS IAM Access / CLI Credentials** | Cloud Admin / User | IAM user or role with permissions for ECS, ECR, RDS, VPC, KMS, Secrets Manager, and CloudWatch in region `me-central-1` (Dubai). |
| **1.2** | **Amazon RDS PostgreSQL 16 Provisioning** | DevOps / User | Provision a Multi-AZ `db.t4g.medium` instance in `me-central-1` with 50GB gp3 KMS-encrypted storage. Provide connection endpoint. |
| **1.3** | **AWS KMS Customer Managed Key (CMK)** | Cloud Admin / User | Provision a dedicated CMK in `me-central-1` for database storage encryption and Secrets Manager vault encryption. |
| **1.4** | **AWS Certificate Manager (ACM) Certificate** | DevOps / User | Request a public TLS certificate for `api.genovex.ae` in `me-central-1` and complete the DNS CNAME validation challenge. |
| **1.5** | **AWS Secrets Manager Secret Injection** | Cloud Admin / User | Store production secrets (`SECRET_KEY`, `DATABASE_URL`, `SMTP_PASSWORD`) in AWS Secrets Manager under ARN referenced by ECS task execution role. |

---

## 2. Frontend Platform Configuration (Vercel)

| # | Item | Responsible Party | Description & Scope |
| :-: | :--- | :--- | :--- |
| **2.1** | **Vercel Project Environment Variable** | Vercel Owner / User | In Vercel Project Settings for `genovex`, add `BACKEND_API_URL=https://api.genovex.ae` (Scopes: Production, Preview). |
| **2.2** | **Vercel Project Redeploy** | Vercel Owner / User | Trigger a production redeployment to ensure server-side rewrites bind to the live AWS ALB endpoint. |
| **2.3** | **Vercel Custom Domains Binding** | Vercel Owner / User | Add custom domains `genovex.ae` and `www.genovex.ae` in Vercel Dashboard and configure redirect preference. |

---

## 3. Domain Registrar & DNS Cutover (`genovex.ae`)

At the `.ae` Domain Registrar (aeDA / TDRA accredited registrar):

| # | Host / Record | Type | Target / Value | Notes |
| :-: | :--- | :---: | :--- | :--- |
| **3.1** | `genovex.ae` (Apex) | `A` | `76.76.21.21` | Points apex domain to Vercel Anycast edge network. (Or `ALIAS` / `ANAME` to `cname.vercel-dns.com` if registrar supports flattening). |
| **3.2** | `www.genovex.ae` | `CNAME` | `cname.vercel-dns.com.` | Subdomain pointing to Vercel CDN. |
| **3.3** | `api.genovex.ae` | `CNAME` | `[ALB_DNS_NAME].me-central-1.elb.amazonaws.com.` | Subdomain pointing to AWS Dubai Application Load Balancer. |
| **3.4** | `_acm-challenge.api` | `CNAME` | `_[VALIDATION_STRING].acm-validations.aws.` | Automated DNS validation challenge issued by AWS ACM for `api.genovex.ae`. |

---

## 4. Outbound Email Infrastructure (SMTP)

| # | Item | Responsible Party | Description & Scope |
| :-: | :--- | :--- | :--- |
| **4.1** | **In-Region Sovereign SMTP Provider** | Operations / User | Provide an authenticated SMTP relay service located within the UAE (or self-hosted Postfix container in `me-central-1`) to dispatch forgot-password emails without cross-border transit of patient email addresses. |
| **4.2** | **SPF, DKIM, DMARC Records** | DNS Admin / User | Configure DNS TXT records for `genovex.ae` to authenticate outbound emails and guarantee delivery to patient inboxes. |

---

## 5. Regulatory, Compliance & Legal Readiness

Before offering the service to UAE patients and clinicians, the following formal reviews must be completed:

| # | Prerequisite Area | Regulatory Context | Status | Required Evidence |
| :-: | :--- | :--- | :---: | :--- |
| **5.1** | **UAE Legal Counsel Review** | UAE PDPL / Civil Code | **PENDING** | Written review of Terms of Service, Licensing, and medical disclaimers by licensed UAE legal counsel. |
| **5.2** | **Privacy Policy & Patient Consent** | UAE PDPL (Decree-Law 45/2021) | **PENDING** | Formal legal sign-off on Three-Tier Consent model and patient rights (access, rectification, erasure). |
| **5.3** | **Health Data Residency Assessment** | UAE Health Data Law (No. 2/2019) | **PENDING** | Comprehensive audit of data flows confirming that all health records, responses, and audit logs remain strictly within the UAE. |
| **5.4** | **Data Retention & Deletion Policy** | UAE Health Data Law (No. 2/2019) | **PENDING** | Policy defining mandatory medical record retention periods (e.g. 5-25 years depending on emirate) and secure disposal protocols. |
| **5.5** | **Medical Device / SaMD Classification** | MOHAP / DoH / DHA Guidelines | **PENDING** | Formal regulatory assessment determining whether the risk identification algorithm is classified as Software as a Medical Device (SaMD) or clinical decision support wellness tool. |
| **5.6** | **Health Authority Approvals** | MOHAP / DoH / DHA | **PENDING** | Official written approval or exemption certificate from UAE Ministry of Health and Prevention (MOHAP) and Dubai Health Authority (DHA). |

> [!WARNING]
> Do NOT claim regulatory approval, non-diagnostic classification, or complete legal compliance until formal written documentation from licensed legal counsel and relevant UAE health authorities is physically executed.
