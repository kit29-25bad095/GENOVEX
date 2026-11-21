# GENOVEX — PHASE 17: DOMAIN AND DNS CONFIGURATION
## Authoritative DNS Routing, TLS Termination & SSL Certificate Management

### 1. Domain Portfolio Overview

The intended production infrastructure for GENOVEX utilizes a sovereign `.ae` country-code top-level domain (ccTLD) managed under the auspices of the UAE Telecommunications and Digital Government Regulatory Authority (TDRA).

| Domain Name | Primary Role | Hosting Provider | Target Ingress / Endpoint | Protocol & Port |
|---|---|---|---|:---:|
| `genovex.ae` | Apex Domain (Brand Root) | DNS Registrar / Cloudflare | HTTP 301 Permanent Redirect to `www.genovex.ae` | HTTPS (443) |
| `www.genovex.ae` | Primary Web Application | Vercel Enterprise / Global Edge | Vercel CNAME `cname.vercel-dns.com` | HTTPS (443) |
| `app.genovex.ae` | Legacy / Alternate UI Alias | Vercel Enterprise | Alias to `www.genovex.ae` | HTTPS (443) |
| `api.genovex.ae` | Sovereign Backend API Gateway | AWS UAE (`me-central-1` Dubai) | AWS Application Load Balancer (ALB) | HTTPS (443) |

---

### 2. DNS Zone Records Specification

> [!IMPORTANT]
> **GO-LIVE RULE:** DNS records must be configured in coordination with the project owner and verified using DNS lookup tools (`dig`, `nslookup`) prior to switching production traffic.

```
;; =============================================================================
;; GENOVEX.AE PRODUCTION DNS ZONE SPECIFICATION
;; =============================================================================

; 1. Apex Domain Configuration (Root)
@                   IN  A           76.76.21.21          ; Vercel Apex Anycast IP
@                   IN  AAAA        2600:1f18:...        ; Vercel IPv6 Edge
@                   IN  TXT         "vercel-verification=..." ; Domain Verification

; 2. Web Application Frontend (Canonical Host)
www                 IN  CNAME       cname.vercel-dns.com. ; Vercel Edge Network
app                 IN  CNAME       cname.vercel-dns.com. ; Alias to Web App

; 3. Sovereign Backend API Gateway (AWS UAE Region me-central-1)
api                 IN  CNAME       genovex-alb-prod-1234.me-central-1.elb.amazonaws.com.

; 4. CAA (Certificate Authority Authorization) Policy
@                   IN  CAA 0 issue "letsencrypt.org"
@                   IN  CAA 0 issue "amazon.com"
@                   IN  CAA 0 issuewild "amazon.com"
@                   IN  CAA 0 iodef "mailto:security@genovex.ae"

; 5. Healthcare Email Protection Records (Anti-Phishing / Anti-Spoofing)
@                   IN  TXT         "v=spf1 include:_spf.google.com ~all"
_dmarc              IN  TXT         "v=DMARC1; p=reject; rua=mailto:dmarc@genovex.ae; aspf=s;"
google._domainkey   IN  TXT         "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ..."
```

---

### 3. SSL / TLS Certificate Lifecycle Management

#### 3.1 Frontend (`www.genovex.ae` & `app.genovex.ae`)
- **Certificate Authority:** Let's Encrypt / DigiCert via Vercel Edge Automated Certificates.
- **Key Type:** ECDSA P-256 (preferred for lower TLS handshake latency) or RSA 2048-bit.
- **Renewal Mechanism:** Fully automated 60-day renewal cycle managed by Vercel Edge.
- **HSTS Header:**
  `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`

#### 3.2 Backend API Gateway (`api.genovex.ae`)
- **Certificate Authority:** AWS Certificate Manager (ACM) in region `me-central-1` (Dubai).
- **Validation Method:** DNS validation via automatic CNAME record addition in Route 53 / Cloudflare.
- **Renewal Mechanism:** Fully managed automated annual re-issuance by AWS ACM with zero operational downtime.
- **Minimum Protocol Enforced:** TLS 1.2 minimum; TLS 1.3 preferred. Deprecated TLS 1.0, 1.1, and SSLv3 disabled at ALB listener.

---

### 4. HTTP to HTTPS Redirection & Canonical Host Normalization

To prevent session hijacking, man-in-the-middle interception, and search index duplication, the following redirects are enforced at the network edge:

1. **HTTP -> HTTPS Upgrade:**
   Any request to `http://genovex.ae/*` or `http://www.genovex.ae/*` on Port 80 immediately returns **HTTP 301 Moved Permanently** redirecting to `https://www.genovex.ae/*`.
2. **Apex to Canonical Subdomain:**
   Any request to `https://genovex.ae/*` immediately returns **HTTP 301** redirecting to `https://www.genovex.ae/*`.
3. **Strict Origin Isolation:**
   `https://api.genovex.ae` accepts only API-formatted requests (`/api/v1/*`, `/health/*`) and enforces CORS restrictions matching only `https://www.genovex.ae`.

---

### 5. Domain Expiration, Registrar & UAE Regulatory Requirements

- **Registrar:** Approved UAE `.ae` Registrar (e.g., AE Server, Etisalat, du, Amazon Route 53 Partner).
- **Renewal Policy:** Set to **Auto-Renew with Multi-Year Registration (3+ Years)** to prevent accidental domain expiration of healthcare navigation services.
- **Administrative Contact:** Dedicated corporate email (`domains@genovex.ae`), protected by multi-factor authentication (FIDO2 WebAuthn).
- **Registry Lock:** Enable TDRA Registry Lock to protect critical healthcare domains against unauthorized DNS hijacking or registrar transfers.
