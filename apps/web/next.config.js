/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  basePath: '/AI-Local-Language-Assistant',
  images: {
    unoptimized: true,
  },
  /* We can add PWA workbox configurations here if desired */
};

module.exports = nextConfig;
