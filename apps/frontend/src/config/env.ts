const trimSlash = (value: string) => value.replace(/\/+$/, "");

export const env = {
  apiBaseUrl: trimSlash(
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:9001/api/v1",
  ),
};

