const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "finguide_token";

// Token lives in memory only, so a page refresh logs the user out.
localStorage.removeItem(TOKEN_KEY); // clear any old saved login
export const getToken = () => window.__finguideToken || null;
export const setToken = (t) => { window.__finguideToken = t; };
export const clearToken = () => { window.__finguideToken = null; };

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body } = {}) {
  const token = getToken();
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Can't reach the server. Is the backend running?", 0);
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(", ")
      : detail;
    throw new ApiError(msg || `Request failed (${res.status})`, res.status);
  }
  return data;
}

export const signup = (body) => request("/auth/signup", { method: "POST", body });
export const login = (body) => request("/auth/login", { method: "POST", body });
export const fetchMe = () => request("/auth/me");
export const changePassword = (body) => request("/auth/password", { method: "PUT", body });

export async function fetchProfile() {
  try {
    return await request("/profile");
  } catch (e) {
    if (e.status === 404) return null;
    throw e;
  }
}
export const createProfile = (body) => request("/profile", { method: "POST", body });
export const updateProfile = (body) => request("/profile", { method: "PUT", body });
export const updateMe = (body) => request("/auth/me", { method: "PUT", body });
export const fetchSettings = () => request("/settings");
export const saveSettings = (body) => request("/settings", { method: "PUT", body });
export const listConversations = () => request("/conversations");
export const getConversation = (id) => request(`/conversations/${id}`);
export const createConversation = (message) => request("/conversations", { method: "POST", body: { message } });
export const addMessage = (id, message) => request(`/conversations/${id}/messages`, { method: "POST", body: message });
export const renameConversation = (id, title) => request(`/conversations/${id}`, { method: "PUT", body: { title } });
export const deleteConversation = (id) => request(`/conversations/${id}`, { method: "DELETE" });
export const verifySignup = (body) => request("/auth/verify-signup", { method: "POST", body });
export const resendOtp = (body) => request("/auth/resend-otp", { method: "POST", body });
export const forgotPassword = (body) => request("/auth/forgot-password", { method: "POST", body });
export const resetPassword = (body) => request("/auth/reset-password", { method: "POST", body });