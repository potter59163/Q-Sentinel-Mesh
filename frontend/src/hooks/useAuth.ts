"use client";
import { useState } from "react";
import api from "@/lib/api";
import { setToken, clearToken, isTokenValid } from "@/lib/auth";

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function login(password: string): Promise<boolean> {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/api/auth/login", { password });
      const token: string = res.data.access_token;
      setToken(token);
      document.cookie = `qsentinel_token=${token}; path=/; max-age=86400; SameSite=Lax`;
      return true;
    } catch {
      setError("รหัสผ่านไม่ถูกต้อง");
      return false;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    clearToken();
    document.cookie = "qsentinel_token=; path=/; max-age=0";
    window.location.href = "/login";
  }

  return { login, logout, loading, error, isAuthenticated: isTokenValid() };
}
