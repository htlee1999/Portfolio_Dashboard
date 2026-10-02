import path from "node:path";
import type { NextConfig } from "next";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

// Sent with every page and API response.
const securityHeaders = [
  // No framing (clickjacking), plugins, <base> hijacking or off-site form posts. Scripts aren't
  // restricted here: that needs per-request nonces (see Next's Content Security Policy guide).
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  // Keeps password-reset tokens in /reset?token=... from leaking to other sites.
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  // Pin the workspace root to web/ so a lockfile elsewhere in the repo can't confuse Turbopack.
  turbopack: { root: path.resolve(__dirname) },
  // Proxy the FastAPI backend under the same origin so the session cookie is first-party.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
  experimental: {
    // AI assessments and model training can take longer than the 30s default.
    proxyTimeout: 180_000,
  },
};

export default nextConfig;
