import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.toString() || "http://127.0.0.1:9010";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000
});

