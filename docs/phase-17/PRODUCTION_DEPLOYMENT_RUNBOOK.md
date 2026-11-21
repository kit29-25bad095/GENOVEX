# GENOVEX Production Deployment Runbook

**Project:** GENOVEX Clinical Health & Genetic Risk Assessment Platform  
**Target Region:** AWS Middle East (UAE) — `me-central-1` (Dubai)  
**Edge Platform:** Vercel Global Edge Network (`genovex.vercel.app`, `genovex.ae`)  
**Prerequisites:** AWS CLI configured for `me-central-1`, Vercel CLI / Dashboard access, Registrar DNS control  

---

## Pre-Flight Checklist

Before initiating production deployment, confirm:
- [ ] Pre-migration backup verified (`backups/genovex_pre_phase17_migration_20261121_133125.db`).
- [ ] 100% automated local test pass: Pytest (295 passed, 4 skipped), Vitest (48 passed), Playwright (30 passed).
- [ ] Next.js static build verified: `22/22 static pages` compiled without warnings.
- [ ] Production secrets generated: `SECRET_KEY` (64-char hex), RDS master password.

---

## Phase 1: AWS UAE Infrastructure Provisioning (`me-central-1`)

### 1.1 VPC & Subnet Deployment
Deploy the 3-tier VPC with 2 public subnets, 2 private app subnets, and 2 isolated DB subnets across `me-central-1a` and `me-central-1b`.

### 1.2 KMS Customer Managed Key
```bash
aws kms create-key \
    --region me-central-1 \
    --description "GENOVEX Production Sovereign Health Data CMK" \
    --tags TagKey=Project,TagValue=GENOVEX
```

### 1.3 Amazon RDS PostgreSQL 16 Multi-AZ
```bash
aws rds create-db-subnet-group \
    --region me-central-1 \
    --db-subnet-group-name genovex-db-subnets \
    --db-subnet-group-description "Isolated subnets for GENOVEX PostgreSQL" \
    --subnet-ids "subnet-db-az1" "subnet-db-az2"

aws rds create-db-instance \
    --region me-central-1 \
    --db-instance-identifier genovex-prod-db \
    --db-instance-class db.t4g.medium \
    --engine postgres \
    --engine-version 16.3 \
    --multi-az \
    --allocated-storage 50 \
    --storage-type gp3 \
    --storage-encrypted \
    --kms-key-id [CMK_ARN] \
    --db-subnet-group-name genovex-db-subnets \
    --vpc-security-group-ids [SG_RDS_ID] \
    --no-publicly-accessible
```

### 1.4 AWS ECR Container Repository & Image Push
```bash
# 1. Authenticate Docker with AWS ECR in Dubai
aws ecr get-login-password --region me-central-1 | docker login --username AWS --password-stdin [ACCOUNT_ID].dkr.ecr.me-central-1.amazonaws.com

# 2. Create ECR repository
aws ecr create-repository \
    --region me-central-1 \
    --repository-name genovex-backend \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=KMS,kmsKey=[CMK_ARN]

# 3. Build & push production container
docker build -t genovex-backend:latest -f backend/Dockerfile backend/
docker tag genovex-backend:latest [ACCOUNT_ID].dkr.ecr.me-central-1.amazonaws.com/genovex-backend:latest
docker push [ACCOUNT_ID].dkr.ecr.me-central-1.amazonaws.com/genovex-backend:latest
```

### 1.5 Database Migration Execution
From a bastion host or ECS one-off task inside the private application subnet:
```bash
export DATABASE_URL="postgresql+psycopg2://[USER]:[PASS]@[RDS_ENDPOINT]:5432/genovex_prod"
alembic upgrade head
python scripts/migrate_sqlite_to_postgres.py
```

### 1.6 ECS Fargate Service Deployment
Deploy the ECS task definition with minimum 2 tasks across AZ-1a and AZ-1b behind the Application Load Balancer.

---

## Phase 2: Vercel Frontend Configuration & Linking

1. Navigate to **Vercel Dashboard > Project Settings > Environment Variables**.
2. Add:
   - `BACKEND_API_URL` = `https://api.genovex.ae` (Target: Production, Preview)
3. Navigate to **Deployments** and trigger a fresh redeploy to ensure Next.js rewrite rules bind to the live backend URL.

---

## Phase 3: Domain DNS Cutover (`genovex.ae`)

At the `.ae` domain registrar (or authoritative DNS provider):
1. **Apex Record (`genovex.ae`):** Add `A` record pointing to `76.76.21.21` (or `ALIAS` to `cname.vercel-dns.com`).
2. **Subdomain (`www.genovex.ae`):** Add `CNAME` pointing to `cname.vercel-dns.com`.
3. **API Subdomain (`api.genovex.ae`):** Add `CNAME` pointing to the AWS ALB DNS name (e.g. `genovex-alb-xxx.me-central-1.elb.amazonaws.com`).
4. **ACM TLS Validation:** Add the CNAME validation record provided by AWS Certificate Manager for `api.genovex.ae`.

---

## Phase 4: Production Verification Gate

Execute smoke tests outlined in `PRODUCTION_VALIDATION_REPORT.md`:
```bash
# Verify health
curl -I https://api.genovex.ae/health

# Verify Vercel proxy rewrite
curl -I https://genovex.ae/api/health

# Verify frontend response
curl -I https://genovex.ae
```
