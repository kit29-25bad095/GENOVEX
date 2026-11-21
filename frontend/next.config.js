/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: process.env.NEXT_STANDALONE === 'true' ? 'standalone' : undefined,
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()' },
        ],
      },
    ];
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_API_URL;
    if (backendUrl) {
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
    // Only proxy to localhost in local development environment
    if (process.env.NODE_ENV !== 'production' && !process.env.VERCEL) {
      return [
        {
          source: '/api/v1/:path*',
          destination: 'http://127.0.0.1:8000/api/v1/:path*',
        },
        {
          source: '/api/health',
          destination: 'http://127.0.0.1:8000/health',
        },
      ];
    }
    // When running under Vercel serverless without an external backend, proxy to the Python serverless function
    return [
      {
        source: '/api/v1/:path*',
        destination: '/api/index.py',
      },
      {
        source: '/api/health',
        destination: '/api/index.py',
      },
    ];
  },
};

module.exports = nextConfig;
