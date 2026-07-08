/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  images: {
    unoptimized: true,
  },
  /* We can add PWA workbox configurations here if desired */
};

module.exports = nextConfig;
