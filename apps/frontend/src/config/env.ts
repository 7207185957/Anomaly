const trimSlash = (value: string) => value.replace(/\/+$/, "");

export const env = {
  apiBaseUrl: trimSlash(
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:9001/api/v1",
  ),
  demoMode: process.env.NEXT_PUBLIC_DEMO_MODE === "true",
  demoUsername: process.env.NEXT_PUBLIC_DEMO_USERNAME || "demo",
  demoPassword: process.env.NEXT_PUBLIC_DEMO_PASSWORD || "demo123",
};

