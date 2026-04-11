import axios from "axios";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60_000,
});

export function getApiErrorMessage(err: unknown) {
  if (typeof err !== "object" || err === null) return "Request failed";
  const maybe = err as {
    message?: string;
    response?: { status?: number; data?: { detail?: string; request_id?: string } };
  };
  const status = maybe.response?.status;
  const detail = maybe.response?.data?.detail;
  const requestId = maybe.response?.data?.request_id;
  const parts = [
    detail || maybe.message || "Request failed",
    status ? `status ${status}` : null,
    requestId ? `req ${requestId}` : null,
  ].filter(Boolean);
  return parts.join(" · ");
}

export async function withRetry<T>(fn: () => Promise<T>, retries = 2, delayMs = 400): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (retries <= 0) throw err;
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    return withRetry(fn, retries - 1, delayMs * 2);
  }
}

export default api;
