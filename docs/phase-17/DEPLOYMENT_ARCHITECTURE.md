# GENOVEX — PHASE 17: DEPLOYMENT ARCHITECTURE
## Hybrid Edge & Sovereign Cloud Topology (AWS UAE me-central-1 Dubai)

### 1. Architectural Strategy: Edge Delivery with Sovereign Health Core

To balance global frontend performance with strict statutory healthcare compliance under **UAE Federal Law No. 2 of 2019 (Health Data Law)**, GENOVEX employs a hybrid decoupled architecture:

1. **Presentation & Static Content Layer (Edge Cloud):**
   - Deployed on Vercel Global Edge Network.
   - Serves pre-rendered Next.js 14 HTML, optimized JavaScript/CSS bundles, static imagery, and public educational pages.
   - **Zero Patient Health Data (PHI) Stored:** Stateless edge; acts purely as a client delivery channel.
2. **Clinical Decision Support & Core API Layer (Sovereign Cloud):**
   - Deployed in the **AWS Middle East (UAE) Region (`me-central-1` Dubai)**.
   - Runs containerized FastAPI backend under Gunicorn/Uvicorn supervisors in a secure Virtual Private Cloud (VPC).
   - Enforces deterministic clinical rules, 11-domain questionnaire processing, red-flag emergency detection, and clinician review workflows.
3. **Data Persistence & Audit Vault (Sovereign Isolated Storage):**
   - **Amazon RDS for PostgreSQL 16 (Multi-AZ in Dubai)**.
   - Hosted within private, non-routable database subnets with strict security groups allowing access ONLY from authorized backend containers.
   - Encrypted at rest via AWS Key Management Service (KMS) with customer-managed keys.

---

### 2. Physical & Logical Topology Diagram

```
                                      [ Patient / Clinician (UAE Ingress) ]
                                                        │
                                            HTTPS (TLS 1.3 / Port 443)
                                                        │
                         ┌──────────────────────────────┴──────────────────────────────┐
                         │                                                             │
                         ▼                                                             ▼
     [ VERCEL GLOBAL EDGE NETWORK ]                                      [ AWS UAE INGRESS (me-central-1) ]
     - www.genovex.ae                                                    - api.genovex.ae
     - Next.js 14 Standalone App Router                                  - AWS Application Load Balancer (ALB)
     - Bilingual English / Arabic (RTL)                                  - AWS WAF (OWASP Top 10 + Rate Limits)
     - Strict Security Headers (CSP, HSTS)                               - TLS 1.3 Termination (ACM Cert)
     - Zero PHI Stored at Edge                                                         │
                         │                                                             │
                         │ Client-Side API Calls                                       ▼
                         │ (via secure bearer token / session)            [ AWS ECS FARGATE (Dubai VPC) ]
                         └──────────────────────────────────────────────> - Private Subnet (No Public IP)
                                                                          - FastAPI 0.115+ (Gunicorn Cluster)
                                                                          - Non-Root Docker Containers
                                                                          - Deterministic Clinical Rule DAG
                                                                          - AI Safety Guardrails & Fallbacks
                                                                                       │
                                                                                       ▼
                                                                          [ AMAZON RDS POSTGRESQL 16 ]
                                                                          - Multi-AZ High Availability
                                                                          - Private Isolated Subnet
                                                                          - Encrypted at Rest (AES-256 KMS)
                                                                          - Point-in-Time Recovery (30 Days)
                                                                                       │
                                                                                       ▼
                                                                          [ SOVEREIGN BACKUP VAULT ]
                                                                          - AWS S3 (me-central-1 Dubai)
                                                                          - Versioning & Object Lock Enabled
                                                                          - Encrypted Daily Automated Backups
```

---

### 3. AWS Middle East (UAE — `me-central-1`) Service Availability Matrix

An assessment was conducted of required AWS services within the Dubai region (`me-central-1`):

| Service Required | Available in `me-central-1`? | Configuration Profile | Alternative / Fallback if Constrained |
|---|:---:|---|---|
| **Amazon VPC & Subnets** | **YES** | Multi-AZ (3 Availability Zones: `me-central-1a`, `1b`, `1c`) | Standard requirement |
| **Application Load Balancer (ALB)** | **YES** | Internet-facing, Dual-stack IPv4/IPv6, ACM TLS 1.3 | Network Load Balancer (NLB) |
| **AWS Fargate (Serverless Containers)** | **YES** | Linux x86_64 / ARM64, 0.5–4 vCPU tasks | Amazon EC2 with ECS Agent |
| **Amazon RDS for PostgreSQL** | **YES** | PostgreSQL 16.x, Multi-AZ replication, gp3 SSD | Aurora PostgreSQL Serverless v2 |
| **AWS KMS (Key Management Service)** | **YES** | Dedicated Customer Managed Keys (CMK) | AWS Managed Keys |
| **AWS Certificate Manager (ACM)** | **YES** | Free automated SSL/TLS certificates for `*.genovex.ae` | Manual Let's Encrypt bot |
| **AWS WAF v2** | **YES** | Regional WAF attached to ALB with rate-based rules | Cloudflare Edge WAF |
| **Amazon S3** | **YES** | Standard S3 bucket with Object Lock for compliance backups | Local attached EBS snapshot |
| **Amazon CloudWatch** | **YES** | Metric alarms, structured log groups, container insights | Datadog agent forwarding |

---

### 4. Containerization Specification

#### Backend Docker Container (`backend/Dockerfile`):
- **Base Image:** `python:3.11-slim` (hardened minimal image, ~140MB).
- **Execution User:** Non-root system user (`appuser:10001`).
- **Process Supervisor:** `gunicorn -c gunicorn_conf.py main:app`.
- **Worker Configuration:**
  - Worker Class: `uvicorn.workers.UvicornWorker`
  - Workers Count: 3 workers per vCPU (auto-calculated)
  - Keep-Alive Timeout: 65 seconds (exceeds ALB 60s idle timeout to prevent 502 bad gateways)
  - Max Requests / Jitter: 1,000 requests with 10% jitter to prevent memory leaks

#### Frontend Docker Container (`frontend/Dockerfile`):
- **Base Image:** `node:20-alpine` (multi-stage build).
- **Output:** Next.js `standalone` mode (reducing image size to ~160MB).
- **User:** Non-root `nextjs:nodejs`.
- **Port:** 3000.

---

### 5. Network Isolation & Security Group Rules

```
[Internet]
    │ HTTPS (443)
    ▼
[Security Group: sg-genovex-alb]
- Inbound:  TCP 443 from 0.0.0.0/0 (Internet)
- Outbound: TCP 8000 to sg-genovex-ecs
    │ TCP 8000
    ▼
[Security Group: sg-genovex-ecs]
- Inbound:  TCP 8000 strictly from sg-genovex-alb
- Outbound: TCP 5432 to sg-genovex-rds
- Outbound: TCP 443 to AWS Services (via VPC Endpoints)
    │ TCP 5432
    ▼
[Security Group: sg-genovex-rds]
- Inbound:  TCP 5432 strictly from sg-genovex-ecs
- Outbound: None (Strictly non-routable)
```
