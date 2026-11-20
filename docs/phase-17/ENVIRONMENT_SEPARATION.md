# GENOVEX — Environment Separation Strategy

## 1. Principles of Environment Isolation

To ensure clinical safety, patient data confidentiality, and system stability, GENOVEX enforces strict separation across three isolated environments:

```
┌─────────────────────────────────┐
│     DEVELOPMENT (Sandbox)       │
│  - SQLite Local Instance        │
│  - Mock AI Provider             │
│  - Simulated Persona Auth ON    │
│  - DEBUG = True                 │
│  - Localhost CORS Allowed       │
└────────────────┬────────────────┘
                 │ Automated CI / Feature PR
                 ▼
┌─────────────────────────────────┐
│       STAGING (Validation)      │
│  - Isolated Staging DB          │
│  - Synthetic Clinical Cases     │
│  - Simulated Persona Auth OFF   │
│  - DEBUG = False                │
│  - Staging HTTPS CORS Only      │
└────────────────┬────────────────┘
                 │ Manual Clinical & Security Gate
                 ▼
┌─────────────────────────────────┐
│      PRODUCTION (Live UAE)      │
│  - Multi-AZ Encrypted DB        │
│  - Real Clinical Consultations  │
│  - Simulated Persona Auth OFF   │
│  - DEBUG = False (Hard-Failing) │
│  - Zero Hardcoded Secrets       │
└─────────────────────────────────┘
```

---

## 2. Environment Comparison Matrix

| Attribute | Development (`development`) | Staging (`staging`) | Production (`production`) |
| :--- | :--- | :--- | :--- |
| **Primary Domain** | `http://localhost:3000` | `https://staging.genovex.ae` | `https://genovex.ae` |
| **API Domain** | `http://127.0.0.1:8000` | `https://staging.genovex.ae/api` | `https://genovex.ae/api` |
| **`ENVIRONMENT`** | `"development"` | `"staging"` | `"production"` |
| **`DEBUG` Flag** | `True` | `False` | `False` *(Startup rejects `True`)* |
| **`SECRET_KEY`** | Default dev key permitted | Random 64-char key | Vault-injected 64-char key *(Default key causes crash)* |
| **`ALLOW_SIMULATED_AUTH`** | `True` *(Developer persona switcher)* | `False` *(Banned)* | `False` *(Banned)* |
| **CORS Origins** | `localhost:3000`, `127.0.0.1:3000` | Strict staging HTTPS origins | Strict production HTTPS origins |
| **AI Provider** | `mock` (Offline deterministic) | `mock` / sandbox API | `gemini` / production API with circuit breaker |
| **Database Instance** | `./genovex.db` | `/app/data/genovex_staging.db` | Dedicated persistent volume / RDS PostgreSQL |
| **Database Content** | Seeded dummy questions & test users | Seeded baseline + synthetic clinical suites | Authoritative clinical rules + patient records |
| **Log Level** | `DEBUG` / `INFO` | `INFO` | `INFO` / `WARNING` (Structured JSON) |
| **HSTS Preload** | Disabled | Enabled (1 year) | Enabled (`max-age=63072000; includeSubDomains; preload`) |

---

## 3. Strict Fail-Closed Safeguards in Code

The GENOVEX codebase embeds runtime safeguards directly in `backend/app/core/config.py` that actively prevent accidental deployment of misconfigured applications:

```python
is_production = (
    self.ENVIRONMENT.lower() == "production" 
    or os.getenv("VERCEL_ENV", "").lower() == "production"
)
if is_production:
    # 1. Reject default developer secrets
    if self.SECRET_KEY == "genovex-secure-secret-key-uae-2026":
        raise ValueError("CRITICAL SECURITY ERROR: SECRET_KEY must be explicitly set to a cryptographically secure random value in production!")
    
    # 2. Reject debug mode in production
    if self.DEBUG:
        raise ValueError("CRITICAL SECURITY ERROR: DEBUG must be False in production!")
```

In addition:
- `get_allowed_cors_origins()` strictly rejects `localhost` or wildcards (`*`) whenever `ENVIRONMENT == "production"` or `ENVIRONMENT == "staging"`.
- If an unknown or malformed environment setting is detected, CORS fails closed by only allowing explicitly validated HTTPS origins.

---

## 4. Secret Management & Injection Guidelines

### Zero Committed Secrets Policy
1. No `.env`, `.env.staging`, or `.env.production` files containing live credentials may ever be committed to the Git repository.
2. The root `.gitignore` strictly excludes `.env` and `.env.*` while keeping `.env*.example` tracking templates.

### Cloud Secret Injection
- **Staging & Production:**
  Secrets must be injected as container environment variables at runtime via:
  - **AWS Systems Manager Parameter Store** (SecureString with KMS)
  - **AWS Secrets Manager** (`/genovex/production/backend` & `/genovex/production/frontend`)
  - **GitHub Actions Secrets** (used exclusively for deployment automation tokens)

---

## 5. Synthetic Data Isolation for Staging

Under UAE Health Data Law No. 2 of 2019:
- **No live patient data or real assessment responses from production may ever be copied or replicated to staging or development environments.**
- Staging verification must rely exclusively on synthetic assessment profiles (e.g., standard male factor infertility risk scenarios, varicocele profiles, anabolic steroid hypogonadism mock cases).
- Automated test suites verify that test runner databases run in temporary memory (`sqlite:///:memory:`) or dedicated test files (`test_*.db`) that are wiped after execution.
