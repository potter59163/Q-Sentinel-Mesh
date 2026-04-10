import axios from "axios";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60_000,
});

export default api;
