# GENOVEX — Domain, HTTPS, and TLS Specification

## 1. Domain Namespace & DNS Architecture

The authoritative production domain for the platform is registered under the UAE national top-level domain (`.ae`):

| Domain / Subdomain | Target Environment | Purpose | Ingress Target |
| :--- | :--- | :--- | :--- |
| `genovex.ae` | Production | Primary user portal & public landing | Cloudflare Edge -> AWS ALB (Frontend) |
| `www.genovex.ae` | Production | Canonical redirect to `genovex.ae` | Cloudflare Edge 301 Redirect |
| `api.genovex.ae` | Production | Direct REST API & Clinician services | Cloudflare Edge -> AWS ALB (Backend) |
| `staging.genovex.ae` | Staging | Pre-production testing & validation | Cloudflare Edge -> Staging ALB |
| `staging-api.genovex.ae`| Staging | Staging REST API | Cloudflare Edge -> Staging ALB |

---

## 2. DNS Record Configuration

All DNS records are managed via Cloudflare with DNSSEC enabled:

```dns
; Primary Domain Records
genovex.ae.                 300 IN  A      104.21.XX.XX      ; Cloudflare Proxy
genovex.ae.                 300 IN  AAAA   2606:4700:XX::XX  ; Cloudflare Proxy
www.genovex.ae.             300 IN  CNAME  genovex.ae.       ; Cloudflare Proxy

; API Records
api.genovex.ae.             300 IN  CNAME  alb-prod-me-central-1.genovex.ae.

; Staging Records
staging.genovex.ae.         300 IN  CNAME  alb-staging-me-central-1.genovex.ae.

; CAA Records (Restricting Certificate Authorities)
genovex.ae.                 300 IN  CAA    0 issue "letsencrypt.org"
genovex.ae.                 300 IN  CAA    0 issue "amazon.com"
genovex.ae.                 300 IN  CAA    0 issuewild ";"
genovex.ae.                 300 IN  CAA    0 iodef "mailto:security@genovex.ae"

; Healthcare Email Security (SPF, DKIM, DMARC)
genovex.ae.                 300 IN  TXT    "v=spf1 include:_spf.google.com ~all"
_dmarc.genovex.ae.          300 IN  TXT    "v=DMARC1; p=reject; rua=mailto:dmarc-reports@genovex.ae; pct=100; aspf=s; adkim=s"
```

---

## 3. TLS 1.3 / 1.2 Strict Cryptographic Profiles

To safeguard male reproductive health assessments against eavesdropping or downgrade attacks:

1. **Protocol Versions:**
   - **TLS 1.3:** Preferred and default.
   - **TLS 1.2:** Supported as minimum fallback for legacy clinical devices.
   - **TLS 1.0 & 1.1:** Strictly disabled at edge and load balancer levels.
2. **Cipher Suites:**
   - `TLS_AES_128_GCM_SHA256`
   - `TLS_AES_256_GCM_SHA384`
   - `TLS_CHACHA20_POLY1305_SHA256`
   - `ECDHE-ECDSA-AES128-GCM-SHA256`
   - `ECDHE-RSA-AES128-GCM-SHA256`
3. **HTTP Strict Transport Security (HSTS):**
   - Header: `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
   - Submitted to the official Google/Mozilla HSTS Preload list to guarantee browsers never initiate unencrypted plaintext connections.

---

## 4. Edge Web Application Firewall (WAF) & Rate Limiting

### 4.1 WAF Rule Configuration (Cloudflare Edge)
- **Rule 1 — OWASP Core Rule Set:** Enforce strict anomaly score threshold of 25 to mitigate SQL injection, Cross-Site Scripting, and Shellshock attempts.
- **Rule 2 — Geo-Fencing:** Restrict access to internal clinician and admin routes (`/api/v1/clinician/*`, `/api/v1/admin/*`) exclusively to authenticated IP ranges within the UAE and GCC.
- **Rule 3 — Bot Management:** Automatic JS challenge / Managed Challenge for automated scraping attempts against the Public Health Library.

### 4.2 Rate Limiting Directives
- **Authentication Endpoints (`/api/v1/auth/*`):** Max 10 requests per minute per IP. Exceeding triggers a 15-minute HTTP 429 block.
- **Assessment Evaluation (`/api/v1/assessment/evaluate`):** Max 15 requests per minute per IP to prevent computational denial-of-service against the clinical rule engine.
- **General Content Endpoints:** Max 300 requests per minute per IP.
