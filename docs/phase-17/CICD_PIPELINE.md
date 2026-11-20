# GENOVEX — Continuous Integration and Continuous Deployment (CI/CD)

## 1. Pipeline Overview

The GENOVEX CI/CD pipeline is implemented using **GitHub Actions** (`.github/workflows/deploy.yml`) to enforce automated code quality checks, security vulnerability scanning, automated testing, container builds, and controlled promotion across environments.

```
 [ Feature Branch PR ]
          │
          ▼
 ┌──────────────────────────────────────────────┐
 │ Job 1: Lint & Code Style                     │
 │ - Python: Flake8, Black                      │
 │ - Frontend: ESLint, TypeScript Check         │
 └──────────────────────┬───────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────┐
 │ Job 2: Backend Automated Tests (Pytest)      │
 │ - Clinical Rule Engine Tests                 │
 │ - Questionnaire & Medical Content Tests      │
 │ - Phase 18 Maintenance & Audit Tests         │
 └──────────────────────┬───────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────┐
 │ Job 3: Frontend Tests & Next.js Build        │
 │ - Vitest Component Tests                     │
 │ - Next.js Standalone Build Compilation       │
 └──────────────────────┬───────────────────────┘
                        ▼
                 [ PR Merge to main ]
                        │
                        ▼
 ┌──────────────────────────────────────────────┐
 │ Job 4: Build & Scan Docker Images            │
 │ - Multi-stage Backend Image Build            │
 │ - Multi-stage Frontend Standalone Build      │
 │ - Trivy Container Vulnerability Scan         │
 └──────────────────────┬───────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────┐
 │ Job 5: Deploy to Staging                     │
 │ - Push to Staging ECS Cluster (me-central-1) │
 │ - Execute Automated Health Verification      │
 └──────────────────────┬───────────────────────┘
                        │
            [ Semantic Version Tag (v*.*.*) ]
                        │
                        ▼
 ┌──────────────────────────────────────────────┐
 │ Job 6: Manual Approval Gate (Production)     │
 │ - Requires Clinical Lead & Lead DevOps Signoff│
 └──────────────────────┬───────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────┐
 │ Job 7: Deploy to Production (Sovereign Cloud)│
 │ - Rolling Zero-Downtime ECS Update           │
 │ - Smoke Test against /health/ready           │
 └──────────────────────────────────────────────┘
```

---

## 2. Pipeline Job Specifications

### 2.1 Job 1: Lint & Code Style
- **Triggers:** All pull requests and pushes to `main`.
- **Python Check:** `flake8 backend` for syntax/import errors, `black --check` for formatting consistency.
- **Node Check:** `npm run lint` and `npm run typecheck` across all React components and App Router pages.

### 2.2 Job 2: Backend Test Suite
- **Environment:** Ubuntu Latest with Python 3.11.
- **Dependencies:** Installed via `pip install -r backend/requirements.txt`.
- **Test Command:**
  ```bash
  export PYTHONPATH=backend
  export ENVIRONMENT=development
  export SECRET_KEY=test-ci-cd-secure-dummy-key-for-automated-verification
  pytest backend/tests -v --tb=short
  ```
- **Failing Criteria:** Any test failure in clinical rules, medical content versioning, questionnaire validation, or authentication immediately blocks the pipeline.

### 2.3 Job 3: Frontend Tests & Build
- **Environment:** Ubuntu Latest with Node.js 20.
- **Test Command:** `npm test` (executes Vitest component suite).
- **Build Verification:** `npm run build` with `NEXT_TELEMETRY_DISABLED=1` to ensure standalone Next.js compilation succeeds with zero bundle errors.

### 2.4 Job 4: Container Build & Vulnerability Scan
- Uses `docker/build-push-action@v5` to compile both `frontend/Dockerfile` and `backend/Dockerfile`.
- Tags images with Git commit SHA and branch reference.
- Enforces container security scanning to catch CVEs in underlying base images (Alpine / Debian slim).

### 2.5 Job 5: Staging Continuous Deployment
- Runs automatically when changes merge to `main`.
- Updates the AWS ECS Staging service via rolling update.
- Executes automated synthetic health checks: verifies `GET /health/ready` returns HTTP 200.

### 2.6 Job 6 & 7: Production Release Gate & Deployment
- **Trigger:** Only executed when a signed semantic release tag (e.g. `v1.0.0`) is pushed.
- **Approval Gate:** Configured via GitHub Environments with required reviewers:
  - Minimum 1 Senior DevOps Engineer approval.
  - Minimum 1 Clinical Software Specialist approval.
- **Zero-Downtime Rollout:** ECS Fargate deploys updated tasks, verifies target health for 30 seconds, then drains previous tasks gracefully.

---

## 3. GitHub Secrets & Variables Configuration

| Secret / Variable Name | Environment | Purpose |
| :--- | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | Repository Secret | IAM deployment user for AWS me-central-1 |
| `AWS_SECRET_ACCESS_KEY` | Repository Secret | IAM deployment credential |
| `AWS_REGION` | Repository Variable | Set to `me-central-1` |
| `STAGING_CLUSTER_NAME` | Environment Secret | ECS Staging cluster identifier |
| `PRODUCTION_CLUSTER_NAME`| Environment Secret | ECS Production cluster identifier |
| `PROD_SECRET_KEY` | Environment Secret | Production JWT cryptographic secret key |
| `AI_API_KEY` | Environment Secret | Google Gemini / OpenAI production API key |
