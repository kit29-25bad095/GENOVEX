# GENOVEX — Hosting Architecture Specification

## 1. Executive Overview

**GENOVEX** is an AI-assisted male reproductive health risk identification and clinical navigation platform tailored specifically for the United Arab Emirates (UAE) healthcare ecosystem. 

Due to the sensitivity of reproductive health information and strict statutory mandates governing medical informatics in the UAE, the hosting topology must strictly comply with:
- **UAE Federal Decree-Law No. 45 of 2021 on Personal Data Protection (PDPL)**
- **UAE Federal Law No. 2 of 2019 on the Use of Information and Communication Technologies in the Health Sector** (Health Data Law)
- **Dubai Health Authority (DHA) Health Data Protection Regulations**
- **Department of Health Abu Dhabi (DoH) Healthcare Information and Cyber Security (HICS) Standards**

Under these frameworks, **all health data, assessment responses, patient audit logs, and medical content must reside within the physical borders of the United Arab Emirates**. Data transfer outside the country is strictly prohibited without explicit statutory exemptions.

---

## 2. Cloud Provider & Regional Topography

### Recommended Primary Infrastructure: AWS UAE Region (`me-central-1` Dubai)
- **Primary Region:** AWS Middle East (UAE) — `me-central-1`
- **Availability Zones:** 3 isolated Availability Zones (`me-central-1a`, `me-central-1b`, `me-central-1c`)
- **Secondary / Disaster Recovery Option:** Microsoft Azure UAE North (Dubai) / UAE Central (Abu Dhabi) for sovereign multi-cloud failover.

```
                                  [ Internet Users / UAE Patients ]
                                                 │
                                                 ▼
                                     [ Cloudflare Edge / WAF ]
                                     - DDoS Protection (L3/4 & L7)
                                     - TLS 1.3 Termination
                                     - HSTS Preload & Edge Caching
                                     - Geo-Fencing & Bot Management
                                                 │
                                                 ▼
                                     [ AWS Application Load Balancer ]
                                     - Multi-AZ (me-central-1a, 1b, 1c)
                                     - ACM Managed TLS Certificate
                                     - Ingress Path Routing
                                        │                      │
                   ┌────────────────────┴──────────┐           │
                   ▼                               ▼           ▼
        / (Next.js SSR/Static)              /api/* & /health   Static Assets (S3)
       [ Frontend Target Group ]      [ Backend Target Group ] [ CloudFront / S3 ]
                   │                               │
                   ▼                               ▼
       [ ECS Fargate (Next.js) ]       [ ECS Fargate (FastAPI) ]
       - 2x tasks minimum (Multi-AZ)   - 2x tasks minimum (Multi-AZ)
       - Auto-scaling (CPU/Memory)     - Gunicorn + Uvicorn Workers
                   │                               │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                 [ AWS Private Subnets (No Public IPs) ]
                 - VPC Peering / Private Endpoints
                 - AWS KMS (Customer Managed Key, UAE)
                 - AWS Secrets Manager / Parameter Store
                                   │
                                   ▼
                     [ Data Persistence Layer ]
           Current (Phase 17/18): Container EBS Persistent Volume (SQLite WAL)
           Target (Phase 14): Amazon RDS for PostgreSQL (Multi-AZ, Encrypted)
                                   │
                                   ▼
                   [ Encrypted S3 Bucket (me-central-1) ]
                   - Automated daily database backups
                   - Write-Once-Read-Many (WORM) audit archives
                   - S3 Glacier Flexible Retrieval lifecycle
```

---

## 3. Component Architecture Breakdown

### 3.1 Edge & Security Perimeter
1. **Cloudflare Enterprise / Business with UAE Edge:**
   - WAF rules blocking OWASP Top 10 vulnerabilities (SQLi, XSS, CSRF, remote code execution).
   - Rate limiting: 120 requests/minute per IP on standard endpoints; 10 requests/minute on authentication and assessment submissions.
   - Geo-blocking capabilities to restrict administration portals to authorized GCC/UAE IP ranges.
   - TLS 1.3 strict encryption with modern cipher suites (`TLS_AES_128_GCM_SHA256`, `TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`).

### 3.2 Ingress & Load Balancing
1. **AWS Application Load Balancer (ALB):**
   - Deployed across 3 public subnets in `me-central-1`.
   - Listens on port 443 (HTTPS) and automatically redirects port 80 (HTTP) with status code 301.
   - Target group routing:
     - Default rule: Routes to `genovex-frontend-tg` (Next.js server on port 3000).
     - Path rule `/api/*` and `/health*`: Routes to `genovex-backend-tg` (FastAPI cluster on port 8000).
   - Health check configuration:
     - Target: `/health/live` (interval: 15s, timeout: 5s, healthy threshold: 2, unhealthy threshold: 3).

### 3.3 Application Compute (AWS ECS on Fargate)
1. **Frontend Service (`genovex-frontend`):**
   - Multi-AZ container deployment using AWS Fargate (serverless container compute).
   - Configuration: 0.5 vCPU, 1 GB RAM per task; minimum 2 tasks, maximum 6 tasks under auto-scaling (scaling threshold: 70% CPU or 75% memory).
   - Zero root access: containers execute as unprivileged `nextjs` user (UID 1001).

2. **Backend Service (`genovex-backend`):**
   - Multi-AZ container deployment using AWS Fargate.
   - Configuration: 1 vCPU, 2 GB RAM per task; minimum 2 tasks, maximum 8 tasks under auto-scaling.
   - Process manager: Gunicorn with `uvicorn.workers.UvicornWorker` (4 concurrent workers per container).
   - Runs as unprivileged `genovex` user (UID 1001).
   - Egress restricted via NAT Gateway; strictly no direct public IP addresses.

### 3.4 Data Persistence & Storage
1. **Database Layer:**
   - **Current Phase 17/18 Deployment:** SQLite 3 in Write-Ahead Logging (`WAL`) mode mounted on an encrypted AWS EBS persistent volume (`gp3`, 3000 IOPS, AES-256 KMS encryption) or attached via AWS EFS with POSIX locking.
   - **Target Phase 14 Architecture:** Amazon RDS for PostgreSQL (Engine 16.x) deployed in Multi-AZ configuration across `me-central-1a` and `me-central-1b`. Storage encrypted with AWS KMS customer-managed key.
2. **Backup Storage:**
   - Amazon S3 bucket located strictly in `me-central-1` (`genovex-prod-backups-me-central-1`).
   - Default encryption: SSE-KMS with customer-managed key.
   - Bucket Versioning enabled; Object Lock enabled in Compliance Mode for audit trails.

---

## 4. Alternative Hosting Options Evaluation

| Option | Pros | Cons | Recommendation for GENOVEX |
| :--- | :--- | :--- | :--- |
| **AWS ECS Fargate (me-central-1)** | • Serverless ops<br>• Fully compliant with UAE PDPL<br>• Zero node management<br>• Native AWS KMS & IAM | • Slightly higher compute unit cost than raw EC2 | **PRIMARY RECOMMENDATION (Best balance of security, compliance, and maintainability)** |
| **Azure Container Apps (UAE North)** | • Strong Microsoft healthcare ecosystem<br>• In-region UAE sovereign hosting | • Slightly different CI/CD toolchain | **SECONDARY ALTERNATIVE (Viable enterprise backup)** |
| **Google Cloud Run (Dammam / Doha)** | • Fast cold starts<br>• Excellent developer ergonomics | • No GCP region inside UAE physical borders as of 2026 (violates Health Data Law) | **REJECTED (Non-compliant with UAE data localization)** |
| **Single Virtual Private Server (VPS)** | • Low initial cost | • Single point of failure<br>• Manual patch management<br>• No automated multi-AZ failover | **REJECTED for Production (Permitted only for temporary dev)** |
| **Pure Serverless (Vercel / Lambda)** | • Zero server maintenance | • Ephemeral storage breaks SQLite WAL persistence<br>• Regional routing may egress data | **REJECTED for Production Database Storage** |

---

## 5. Cost Projections (Production UAE Region)

| Service | Specification | Monthly Estimate (USD) |
| :--- | :--- | :--- |
| AWS ECS Fargate (Backend) | 2 tasks x 1 vCPU, 2 GB RAM | ~$75 |
| AWS ECS Fargate (Frontend) | 2 tasks x 0.5 vCPU, 1 GB RAM | ~$38 |
| Application Load Balancer | 1 Multi-AZ ALB + LCU consumption | ~$28 |
| Amazon EBS / EFS Storage | 50 GB gp3 encrypted volume + backups | ~$12 |
| Amazon S3 (UAE me-central-1) | 100 GB standard + Glacier lifecycle | ~$5 |
| AWS KMS & Secrets Manager | 5 secrets + customer-managed key | ~$8 |
| Cloudflare Business Plan | WAF, DDoS, Edge SSL, UAE edge | ~$200 |
| **Total Estimated Run-Rate** | **High-Availability Sovereign Deployment** | **~$366 / month** |
