/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // /api/proxy/* is handled by app/api/proxy/[...path]/route.ts with explicit timeout (504 on timeout)
};

export default nextConfig;
