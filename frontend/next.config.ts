import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The floating dev badge lands in the corner of every screenshot in docs/img/.
  devIndicators: { buildActivity: false, appIsrStatus: false },
};

export default nextConfig;
