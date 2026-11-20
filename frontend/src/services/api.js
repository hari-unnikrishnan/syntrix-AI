import axios from "axios";

export const API_CONFIGURATION_MESSAGE =
  "Django backend is not configured for this deployment. Set the GitHub Actions repository variable VITE_API_URL to the deployed HTTPS API URL ending in /api, then rebuild.";

export function resolveApiBaseUrl(configuredUrl, isDevelopment) {
  const trimmedUrl = configuredUrl?.trim();
  return trimmedUrl || (isDevelopment ? "http://127.0.0.1:8000/api" : "");
}

export const API_BASE_URL = resolveApiBaseUrl(
  import.meta.env.VITE_API_URL,
  import.meta.env.DEV,
);

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (!API_BASE_URL) {
    return Promise.reject(new Error(API_CONFIGURATION_MESSAGE));
  }

  const token = sessionStorage.getItem("syntrix-token");
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

export const authApi = {
  login: (credentials) => api.post("/auth/login/", credentials),
  register: (details) => api.post("/auth/register/", details),
  logout: () => api.post("/auth/logout/"),
  me: () => api.get("/auth/me/"),
  profile: () => api.get("/auth/profile/"),
  updateProfile: (details) => api.patch("/auth/profile/", details),
};

export const workspaceApi = {
  health: () => api.get("/health/"),
  adminDatabase: (params) => api.get("/admin/database/", { params }),
  databaseDashboard: () => api.get("/database/"),
  databaseUsers: (params) => api.get("/database/users/", { params }),
  databaseConversations: (params) =>
    api.get("/database/conversations/", { params }),
  settings: () => api.get("/settings/"),
  updateSettings: (settings) => api.patch("/settings/", settings),
  conversations: () => api.get("/conversations/"),
  conversation: (id) => api.get(`/conversations/${id}/`),
  deleteConversation: (id) => api.delete(`/conversations/${id}/`),
  documents: () => api.get("/documents/"),
  uploadDocument: (file, conversationId) => {
    const form = new FormData();
    form.append("file", file);
    if (conversationId) form.append("conversation", String(conversationId));
    return api.post("/documents/", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  deleteDocument: (id) => api.delete(`/documents/${id}/`),
  usageSummary: () => api.get("/usage/"),
  sendMessage: (message, conversationId) =>
    api.post("/chat/", {
      message,
      ...(conversationId ? { conversation_id: conversationId } : {}),
    }),
};

export default api;
