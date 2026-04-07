// src/lib/api.ts
// Central API client — all backend calls go through here.
// Token is injected automatically on every request via the interceptor.

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ns_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401 — clear stored session and redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("ns_token");
      localStorage.removeItem("ns_profile");
      window.location.href = "/";
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authAPI = {
  signup: (email: string, password: string, full_name: string) =>
    api.post("/auth/signup", { email, password, full_name }),

  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),

  getMe: () => api.get("/auth/me"),

  updateProfile: (data: Record<string, unknown>) =>
    api.put("/auth/profile", data),
};

// ── Health Metrics ────────────────────────────────────────────────────────────

export const metricsAPI = {
  saveManual: (
    metrics: Array<{ metric_type: string; value: number; unit?: string; source?: string }>
  ) => api.post("/metrics/manual", { metrics }),

  extractLab: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/metrics/extract-lab", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  confirmExtracted: (
    confirmed_conditions: string[],
    confirmed_severities: Record<string, string>,
    metrics: Array<{ metric_type: string; value: number; unit?: string }> = []
  ) =>
    api.post("/metrics/confirm-extracted", {
      confirmed_conditions,
      confirmed_severities,
      metrics,
    }),

  getHistory: (metric_type?: string) =>
    api.get("/metrics/history", {
      params: metric_type ? { metric_type } : {},
    }),

  getLatest: () => api.get("/metrics/latest"),
};

// ── Meals ─────────────────────────────────────────────────────────────────────

export const mealsAPI = {
  analyze: (
    food_items: Array<{ name: string; quantity: number }>,
    description?: string,
    image_url?: string
  ) => api.post("/meals/analyze", { food_items, description, image_url }),

  detectImage: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/meals/detect-image", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  getHistory: (limit = 20) =>
    api.get("/meals/history", { params: { limit } }),

  deleteMeal: (id: string) => api.delete(`/meals/${id}`),
};

// ── Foods ─────────────────────────────────────────────────────────────────────

export const foodsAPI = {
  search: (q: string) => api.get("/foods/search", { params: { q } }),
  all:    ()           => api.get("/foods/all"),
};

// ── Diet Plan ─────────────────────────────────────────────────────────────────

export const dietAPI = {
  generate: (food_preference: string, allergies: string[]) =>
    api.post("/diet/generate", { food_preference, allergies }),

  getActive:  () => api.get("/diet/active"),
  getHistory: () => api.get("/diet/history"),
};

// ── Progress ──────────────────────────────────────────────────────────────────

export const progressAPI = {
  getStreak:          () => api.get("/progress/streak"),
  getWeeklyNutrients: () => api.get("/progress/weekly-nutrients"),
  getMonthlySummary:  () => api.get("/progress/monthly-summary"),
};

// ── Bot ───────────────────────────────────────────────────────────────────────

export const botAPI = {
  sendMessage:     (message: string) => api.post("/bot/message", { message }),
  getDailySummary: ()                 => api.get("/bot/daily-summary"),
  getConversation: ()                 => api.get("/bot/conversation"),
};

export default api;