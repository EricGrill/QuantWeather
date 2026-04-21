/** @type {import('next').NextConfig} */
const path = require("path");

const nextConfig = {
  outputFileTracingRoot: path.join(__dirname),
  async rewrites() {
    return [
      {
        source: "/execution-api/:path*",
        destination: "http://127.0.0.1:8080/:path*"
      }
    ];
  }
};

module.exports = nextConfig;
