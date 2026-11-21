# GENOVEX Production Environment Variables Specification

**Project:** GENOVEX Clinical Health & Genetic Risk Assessment Platform  
**Target Environments:** Vercel Edge (Frontend) & AWS ECS Fargate / RDS (Backend)  
**Security Standard:** Zero Plaintext Credentials in Repositories or Logs  

---

## 1. Vercel Frontend Environment Variables

Configure these in the Vercel Dashboard under **Project Settings > Environment Variables** (Scope: Production, Preview):

| Variable Name | Required | Example / Target Value | Description & Security Contract |
| :--- | :---: | :--- | :--- |
| `BACKEND_API_URL` | **CRITICAL** | `https://api.genovex.ae` | Used server-side by `next.config.js` to rewrite same-origin `/api/v1/:path*` requests to the deployed AWS backend. Must be an HTTPS endpoint in production. |
| `NEXT_PUBLIC_SITE_URL` | Optional | `https://genovex.ae` | Canonical site URL for metadata, OpenGraph tags, and SEO robots configuration. |
| `NEXT_PUBLIC_API_BASE_URL` | Optional | *(Omit in production)* | When omitted, client-side browsers automatically use same-origin `/api/v1`, avoiding CORS and mixed-content issues. Only set if bypassing Next.js rewrites. |

---

## 2. AWS Backend API Environment Variables (ECS Fargate)

Stored securely in **AWS Secrets Manager** and injected into the ECS Task Definition via parameter store / secrets mapping:

| Variable Name | Required | Example / Target Format | Description & Purpose |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **CRITICAL** | `postgresql+psycopg2://genovex_app:[PASS]@genovex-prod-db.[id].me-central-1.rds.amazonaws.com:5432/genovex_prod` | PostgreSQL 16 connection string with `psycopg2` driver. Injected via AWS Secrets Manager. |
| `ENVIRONMENT` | **CRITICAL** | `production` | Enables production security mode, disables OpenAPI Swagger docs in public routes, enforces strict error redaction. |
| `SECRET_KEY` | **CRITICAL** | `[64-character cryptographically secure hex string]` | Used for HMAC signing of JWT tokens and password reset hashes. Generated via `openssl rand -hex 32`. |
| `CORS_ORIGINS` | **CRITICAL** | `["https://genovex.ae", "https://www.genovex.ae", "https://genovex.vercel.app"]` | JSON list of trusted origins permitted to access backend endpoints directly. |
| `ALLOWED_HOSTS` | **CRITICAL** | `["api.genovex.ae", "localhost"]` | Trusted HTTP `Host` header values to prevent HTTP Host Header Poisoning attacks. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Required | `60` | JWT access token validity period. |
| `TRUST_PROXY_HEADERS` | Required | `True` | Instructs FastAPI / Uvicorn to trust `X-Forwarded-For` and `X-Forwarded-Proto` headers set by AWS ALB. |
| `SMTP_HOST` | Required | `[smtp.provider.ae / in-region endpoint]` | Outbound mail server for forgot-password verification emails. |
| `SMTP_PORT` | Required | `587` | Outbound mail server submission port (STARTTLS). |
| `SMTP_USER` | Required | `noreply@genovex.ae` | Authenticated SMTP username. |
| `SMTP_PASSWORD` | Required | `[secure secret]` | Injected via AWS Secrets Manager. |
| `EMAILS_FROM_EMAIL` | Required | `noreply@genovex.ae` | Envelope sender address for system notifications. |
| `EMAILS_FROM_NAME` | Required | `GENOVEX Health` | Display name for outbound emails. |

---

## 3. Secret Rotation & Key Management Protocol

1. **AWS Secrets Manager:** All database credentials, JWT keys, and SMTP credentials must reside in Secrets Manager in `me-central-1` Dubai.
2. **KMS Encryption:** The Secrets Manager vault is encrypted with a dedicated Customer Managed Key (`genovex-secrets-cmk`).
3. **Least Privilege IAM:** The ECS Task Execution Role (`ecsTaskExecutionRole`) is granted `secretsmanager:GetSecretValue` permission strictly for the specific secret ARNs.
