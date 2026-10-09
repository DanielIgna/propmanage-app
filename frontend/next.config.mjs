import path from "node:path";
import { fileURLToPath } from "node:url";
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

// FastAPI backend (Railway). /api and /uploads are proxied same-origin, so cookies and
// CORS behave exactly like the previous Cloudflare worker proxy.
const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8001").replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // The SPA calls `${NEXT_PUBLIC_BACKEND_URL}/api/...`; empty = same origin (via the rewrites below).
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL ?? "",
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
      { source: "/uploads/:path*", destination: `${BACKEND_URL}/uploads/:path*` },
    ];
  },
  images: { unoptimized: true },
  // frontend/ has its own lockfile next to the repo-root one: pin the workspace root.
  turbopack: { root: path.dirname(fileURLToPath(import.meta.url)) },
};

export default nextConfig;

initOpenNextCloudflareForDev();
