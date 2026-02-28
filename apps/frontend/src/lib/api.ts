import axios from "axios";

import { env } from "@/config/env";
import { clearAccessToken, getAccessToken } from "@/lib/auth";

export const api = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 60000,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      clearAccessToken();
    }
    return Promise.reject(err);
  },
);

