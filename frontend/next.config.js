/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    // Using remotePatterns (not deprecated `domains`) to mitigate
    // Next.js Image Optimizer DoS CVE (fixed pattern: exact host, no wildcards)
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'www.screener.in',
        port: '',
        pathname: '/**',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
