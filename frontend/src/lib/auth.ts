// Auth utilities — JWT decode (client-side), cookie management, role config

export const ROLE_CONFIG = {
  radiologist: {
    label: "Radiologist",
    icon: "🩺",
    description: "CT scan review and AI-assisted hemorrhage detection",
    tabs: ["/dashboard", "/dashboard/federated"],
    defaultPath: "/dashboard",
    accent: "#c25b86",
  },
  hospital_operator: {
    label: "Hospital Operator",
    icon: "🏥",
    description: "Patient workflow management and operational oversight",
    tabs: ["/dashboard", "/dashboard/federated", "/dashboard/pacs"],
    defaultPath: "/dashboard",
    accent: "#3b82f6",
  },
  fed_ai_admin: {
    label: "Federated AI Admin",
    icon: "🧠",
    description: "Federated learning rounds, model updates, and AI governance",
    tabs: ["/dashboard/federated", "/dashboard/security", "/dashboard/pacs"],
    defaultPath: "/dashboard/federated",
    accent: "#4c8f6b",
  },
  hospital_it: {
    label: "Hospital IT / Security Admin",
    icon: "🔒",
    description: "PACS integration, PQC security, and infrastructure management",
    tabs: ["/dashboard/security", "/dashboard/pacs"],
    defaultPath: "/dashboard/security",
    accent: "#7c3aed",
  },
  dev: {
    label: "Developer / Creator",
    icon: "⚡",
    description: "Full system access — all modules unlocked",
    tabs: ["/dashboard", "/dashboard/federated", "/dashboard/security", "/dashboard/pacs"],
    defaultPath: "/dashboard",
    accent: "#f59e0b",
  },
} as const;

export type UserRole = keyof typeof ROLE_CONFIG;

export interface AuthPayload {
  role: UserRole;
  exp: number;
  sub: string;
}

const COOKIE_NAME = "qsm_token";

/** Decode JWT payload without verification (client-side only). */
export function decodeJwtPayload(token: string): AuthPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const raw = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(raw)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    );
    const payload = JSON.parse(json);
    if (!payload.role || !payload.exp) return null;
    return payload as AuthPayload;
  } catch {
    return null;
  }
}

/** Read JWT from cookie. Returns null if missing or expired. */
export function getStoredAuth(): { token: string; role: UserRole } | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${COOKIE_NAME}=([^;]+)`));
  if (!match) return null;
  const token = match[1];
  const payload = decodeJwtPayload(token);
  if (!payload) return null;
  if (payload.exp * 1000 < Date.now()) {
    clearAuth();
    return null;
  }
  return { token, role: payload.role };
}

/** Persist JWT in a secure cookie (1 day). */
export function setAuth(token: string): void {
  document.cookie = `${COOKIE_NAME}=${token}; max-age=${60 * 60 * 24}; path=/; SameSite=Strict`;
}

/** Remove auth cookie. */
export function clearAuth(): void {
  document.cookie = `${COOKIE_NAME}=; max-age=0; path=/`;
}

/** Get allowed tabs for a role. */
export function getAllowedTabs(role: UserRole): string[] {
  return ROLE_CONFIG[role].tabs as unknown as string[];
}
