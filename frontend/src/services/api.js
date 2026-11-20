import axios from "axios";

const localApiUrl = import.meta.env.DEV ? "http://127.0.0.1:8000/api" : "";

export const API_BASE_URL = import.meta.env.VITE_API_URL || localApiUrl;

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
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
