# GENOVEX Production Cloud Architecture Specification

**Project:** GENOVEX: Male Reproductive Health Risk Identification & Clinical Navigation Platform  
**Target Cloud:** Amazon Web Services (AWS) — UAE Region (`me-central-1`, Dubai)  
**Target Frontend:** Vercel Global Edge Network (`genovex.vercel.app`, `genovex.ae`)  
**Target API:** `https://api.genovex.ae`  
**Regulatory Standards Audited:** UAE Federal Health Data Law (No. 2 of 2019), UAE PDPL (Decree-Law No. 45 of 2021)  
**Document Revision:** 2.0 (Post-Audit Rectification)  

---

## 1. Topological Overview & Trust Boundaries

```
                              [ Internet Patients / Clinicians ]
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
         [ Edge: Vercel Network ]                           [ Direct API Ingress ]
         - genovex.ae (A: 76.76.21.21)                      - api.genovex.ae (CNAME to ALB)
         - www.genovex.ae (CNAME to Vercel)                 - TLS 1.3 Termination (ACM)
         - Next.js Rewrites: /api/v1/* ────────────────┐               │
                                                       │               ▼
                                                       └─────► [ AWS ALB (Dubai) ]
                                                               - Multi-AZ (me-central-1a, 1b)
                                                               - Public Subnets (Port 443)
                                                               - Health check: /health
                                                                       │
                         ┌─────────────────────────────────────────────┘
                         ▼
        ┌────────────────────────────────────────────────────────────────────────┐
        │                 AWS VPC (10.0.0.0/16) — me-central-1 (Dubai)           │
        │                                                                        │
        │  [ Private App Subnets ]                                               │
        │  ┌──────────────────────────────────┐ ┌──────────────────────────────┐ │
        │  │  ECS Fargate Task 1 (AZ-1a)      │ │  ECS Fargate Task 2 (AZ-1b)  │ │
        │  │  - FastAPI (Python 3.11 Slim)    │ │  - FastAPI (Python 3.11 Slim)│ │
        │  │  - Gunicorn + Uvicorn Workers    │ │  - Gunicorn + Uvicorn Workers│ │
        │  │  - In-memory PyMuPDF PDF Engine  │ │  - In-memory PyMuPDF Engine  │ │
        │  └──────────────────┬───────────────┘ └──────────────┬───────────────┘ │
        │                     │                                │                 │
        │                     └────────────────┬───────────────┘                 │
        │                                      │                                 │
        │  [ Isolated Database Subnets — No Internet Access ]                    │
        │  ┌───────────────────────────────────▼───────────────────────────────┐ │
        │  │  Amazon RDS PostgreSQL 16 (Multi-AZ Instance)                     │ │
        │  │  - Primary Instance (me-central-1a)                               │ │
        │  │  - Synchronous Standby Replica (me-central-1b)                    │ │
        │  │  - AES-256 KMS CMK Encrypted Storage                              │ │
        │  │  - Port 5432 Inbound ONLY from sg-ecs-tasks (sslmode=require)     │ │
        │  └───────────────────────────────────────────────────────────────────┘ │
        └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ingress & DNS Configuration Specification

### 2.1 Apex Domain (`genovex.ae`)
- **DNS Constraint (RFC 1034 / 2181):** An apex (root) domain `@` cannot host a standard `CNAME` record because it must coexist with `SOA` and `NS` records. Prescribing an ordinary `CNAME` at `@` is invalid and breaks zone resolution.
- **Provider-Specific Implementation:**
  - **Standard DNS Providers:** Add an `A` record pointing to Vercel's Anycast IP: `76.76.21.21`.
  - **Providers Supporting CNAME Flattening (Route 53, Cloudflare, DNSimple):** Add an `ALIAS` or `ANAME` record pointing to `cname.vercel-dns.com`.

### 2.2 Subdomain (`www.genovex.ae`)
- **Record Type:** `CNAME`
- **Host / Name:** `www`
- **Value / Target:** `cname.vercel-dns.com.`
- **Canonical Routing:** In Vercel Project Domains, configure `genovex.ae` to redirect to `www.genovex.ae` (or vice-versa) to avoid split traffic and dual cookies.

### 2.3 API Subdomain (`api.genovex.ae`)
- **Record Type:**
  - **External DNS Providers:** `CNAME` pointing to the AWS Application Load Balancer DNS name (e.g. `genovex-alb-123456789.me-central-1.elb.amazonaws.com.`).
  - **AWS Route 53:** `A` (Alias) record pointing directly to the ALB resource.
- **TLS Certificate:** AWS Certificate Manager (ACM) validated via DNS CNAME challenge in `me-central-1`.

---

## 3. UAE Data Residency & Sovereignty Audit

### 3.1 Verified Technical Facts
1. **Database & Persistence:** Amazon RDS PostgreSQL 16 is physically provisioned in AWS Dubai (`me-central-1`). All tables, records, patient responses, and credentials remain within UAE geographic boundaries.
2. **Backend Runtime:** AWS ECS Fargate tasks run exclusively on physical hosts in `me-central-1`.
3. **Encryption at Rest:** Managed via AWS KMS Customer Managed Keys (CMK) provisioned in `me-central-1`.
4. **Audit Logs:** Application audit records are written to PostgreSQL table `audit_logs` and streamed to AWS CloudWatch Log Groups residing in `me-central-1`.

### 3.2 Cross-Border Data Flows & Architecture Gaps (Audit Findings)
1. **Vercel Edge Network Proxying:**
   - When users browse `https://genovex.vercel.app` or `https://genovex.ae`, requests are routed to Vercel's Anycast edge network.
   - Next.js rewrites proxy `/api/v1/*` through Vercel serverless functions. These functions may execute in Vercel edge regions outside the UAE (e.g., Frankfurt, Dublin, or US points of presence).
   - *Data Residency Impact:* HTTP headers, authentication tokens, and request bodies traverse Vercel edge compute. While encrypted with TLS in transit, this constitutes cross-border transit of healthcare interaction metadata.
   - *Strict Sovereign Alternative:* Containerize the Next.js frontend using `output: 'standalone'` in `next.config.js` and run it on ECS Fargate inside `me-central-1`, fronted by an ALB or CloudFront distribution with restricted edge logging.
2. **Email Dispatch (SMTP):**
   - Password reset emails require an external SMTP provider. If AWS SES is utilized, note that AWS SES is not natively provisioned in `me-central-1` (commonly provisioned in `eu-west-1` Ireland).
   - *Data Residency Impact:* Email addresses and password reset links would leave the UAE if a foreign SES endpoint is used. A UAE-licensed sovereign relay or in-region Postfix container is required.
3. **AI Summarization Endpoints:**
   - Features integrating the Google Gemini API call external Google Cloud endpoints located in the EU or US.
   - *Data Residency Impact:* Synthetic clinical summaries and terminology queries are transmitted outside the UAE. These features must remain opt-in or masked in production pending healthcare authority approval.

---

## 4. PDF Generation & Storage Architecture

### 4.1 Actual Implementation (In-Memory Streaming)
- **Engine:** PyMuPDF (`fitz` / `pymupdf`) and `qrcode` in `backend/app/services/report_pdf_service.py`.
- **Generation Model:** Stateless, on-demand generation directly from structured `AssessmentReport` database records.
- **Storage Requirement:** **Does NOT require an Amazon S3 bucket.** PDFs are generated in memory and returned directly via binary HTTP response (`Response(content=pdf_bytes, media_type="application/pdf")`).
- **Security & Authorization:**
  - Enforces `ClinicalGovernanceGate.verify_report_access()`.
  - Only authenticated report owners, authorized clinicians, or holders of unexpired, unrevoked share tokens can trigger generation.
  - Generates cryptographic SHA-256 report verification stamps embedded in the document.

---

## 5. Security & Isolation Tiers

- **Public ALB Subnets:** Public subnets (`10.0.1.0/24`, `10.0.2.0/24`) accept inbound 443 with TLS 1.3 only.
- **Private Application Subnets:** ECS Fargate tasks (`10.0.10.0/24`, `10.0.20.0/24`) accept traffic strictly from the ALB security group.
- **Isolated Database Subnets:** PostgreSQL RDS instances (`10.0.100.0/24`, `10.0.200.0/24`) have zero internet routing and accept connections strictly on port 5432 from ECS security groups with `sslmode=require`.
