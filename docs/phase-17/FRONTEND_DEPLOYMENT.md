# GENOVEX — Frontend Deployment Specification

## 1. Architecture & Build Configuration

The GENOVEX frontend is built on **Next.js 14** using the App Router, React 18, TypeScript, and Tailwind CSS. It provides bilingual English and Arabic interfaces with full Right-to-Left (RTL) support.

### 1.1 Next.js Standalone Build Optimization
In `frontend/next.config.js`, the production output is configured as `standalone`:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  poweredByHeader: false,
  // ...
};
```

**Benefits of Standalone Build:**
- Bundles only the necessary `node_modules` required for production runtime, shrinking the container footprint from >800MB to ~150MB.
- Generates a standalone Node server entry point at `.next/standalone/server.js`.
- Eliminates devDependencies and extraneous build tooling in the production container image.

---

## 2. Security Headers & Reverse Proxy Rewrites

### 2.1 Security Headers
The following HTTP response headers are injected at the Next.js edge for all routes (`/:path*`):

| Header | Production Setting | Rationale |
| :--- | :--- | :--- |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Enforces HTTPS strictly for 2 years across all subdomains. |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing attacks. |
| `X-Frame-Options` | `DENY` | Prevents clickjacking and framing of medical assessment pages. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits leakage of sensitive URL query parameters across origins. |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), interest-cohort=()` | Disables invasive browser APIs and FLoC tracking. |
| `X-DNS-Prefetch-Control`| `on` | Optimizes external DNS prefetching while maintaining security. |

### 2.2 Dynamic API Rewrites
To avoid CORS issues and facilitate containerized or CDN routing:
```javascript
async rewrites() {
  const backendUrl = process.env.BACKEND_API_URL || 'http://127.0.0.1:8000';
  return [
    {
      source: '/api/v1/:path*',
      destination: `${backendUrl.replace(/\/$/, '')}/api/v1/:path*`,
    },
    {
      source: '/api/health',
      destination: `${backendUrl.replace(/\/$/, '')}/health`,
    },
  ];
}
```

---

## 3. Container Specification (`frontend/Dockerfile`)

The container employs a 3-stage multi-stage build on Alpine Linux:

1. **Stage 1 (`deps`):**
   - Base: `node:20-alpine`
   - Installs build tools and executes `npm ci` with caching.
2. **Stage 2 (`builder`):**
   - Copies source files and compiles Next.js pages, CSS, and TypeScript types.
   - Outputs `.next/standalone` and `.next/static`.
3. **Stage 3 (`runner`):**
   - Minimal Node 20 runtime.
   - Non-root user: `nextjs:nodejs` (UID/GID 1001).
   - Copies only standalone artifacts and static public assets.
   - Exposes port 3000.
   - Healthcheck: Executes lightweight HTTP probe via `wget --spider http://127.0.0.1:3000/`.

---

## 4. Local Build & Run Instructions

```bash
# 1. Build the production Docker image locally
docker build -t genovex-frontend:latest ./frontend

# 2. Run the standalone container
docker run -d \
  -p 3000:3000 \
  -e BACKEND_API_URL="http://host.docker.internal:8000" \
  -e NEXT_PUBLIC_SITE_URL="http://localhost:3000" \
  --name genovex-frontend-app \
  genovex-frontend:latest

# 3. Verify health status
docker inspect --format='{{json .State.Health.Status}}' genovex-frontend-app
```

---

## 5. Zero-Downtime Deployment in Production

When deploying new frontend releases:
1. The new image is tagged with the Git commit SHA (e.g., `genovex-frontend:a1b2c3d`).
2. AWS ECS Fargate initiates a rolling update:
   - Spawns new container tasks alongside existing ones.
   - Application Load Balancer routes traffic only after the container passes health checks for 30 consecutive seconds.
   - Once healthy, old container tasks receive `SIGTERM`, wait for active connections to drain (graceful timeout: 30s), and terminate cleanly.
3. Static assets (`.next/static/*`) are uploaded to an S3/CloudFront CDN bucket with immutable cache headers (`Cache-Control: public, max-age=31536000, immutable`), ensuring users on active sessions experience no missing asset errors during deployments.
