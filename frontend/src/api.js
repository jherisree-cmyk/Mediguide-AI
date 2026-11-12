// Small wrapper around fetch for the FastAPI backend.
// `credentials: "include"` sends the httpOnly session cookie; JavaScript never sees the token.

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, body) {
  const res = await fetch(path, {
    method,
    credentials: "include",
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }
  if (!res.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || res.statusText;
    throw new ApiError(res.status, message);
  }
  return data;
}

export const api = {
  meta: () => request("GET", "/api/meta"),
  me: () => request("GET", "/api/auth/me"),
  register: (email, password, language, display_name) =>
    request("POST", "/api/auth/register", { email, password, language, display_name: display_name || null }),
  login: (email, password) => request("POST", "/api/auth/login", { email, password }),
  logout: () => request("POST", "/api/auth/logout"),
  updateProfile: (profile) => request("PUT", "/api/auth/me", profile),
  deleteAccount: () => request("DELETE", "/api/auth/me"),
  preview: (payload) => request("POST", "/api/assess/preview", payload),
  assess: (payload) => request("POST", "/api/assess", payload),
  answer: (id, answers, followup_token) => request("POST", `/api/assess/${id}/answers`, { answers, followup_token }),
  history: () => request("GET", "/api/history"),
  historyItem: (id) => request("GET", `/api/history/${id}`),
  deleteHistoryItem: (id) => request("DELETE", `/api/history/${id}`),
  deleteHistory: () => request("DELETE", "/api/history"),
  adminStats: () => request("GET", "/api/admin/stats"),
};
