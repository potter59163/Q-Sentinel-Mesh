export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("qsentinel_token");
}

export function setToken(token: string): void {
  localStorage.setItem("qsentinel_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("qsentinel_token");
}

export function isTokenValid(): boolean {
  const token = getToken();
  if (!token) return false;
  try {
    const [, payload] = token.split(".");
    const decoded = JSON.parse(atob(payload));
    return decoded.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}
