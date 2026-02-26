/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // /api/proxy/* is handled by app/api/proxy/[...path]/route.ts with explicit timeout (504 on timeout)
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: "/api/proxy/api/v1/:path*" },
    ];
  },
};

export default nextConfig;
