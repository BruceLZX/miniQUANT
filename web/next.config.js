/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Proxy all /api/* calls to FastAPI backend on :8000
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*"
      }
    ];
  }
};

module.exports = nextConfig;

