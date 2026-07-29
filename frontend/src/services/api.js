import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:9006/api/v1';

export const setAuthData = (data) => localStorage.setItem('auth_data', JSON.stringify(data));
export const getAuthData = () => {
  const raw = localStorage.getItem('auth_data');
  return raw ? JSON.parse(raw) : null;
};
export const clearAuthData = () => localStorage.removeItem('auth_data');
export const getToken = () => getAuthData()?.access_token;

const api = axios.create({ baseURL: API_BASE_URL });
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ─── Auth ────────────────────────────────────────────────────────────────────
export const signup = async (username, password, department) => {
  const res = await api.post('/auth/signup', { username, password, department });
  setAuthData(res.data);
  return res.data;
};

export const login = async (username, password) => {
  const res = await api.post('/auth/login', { username, password });
  setAuthData(res.data);
  return res.data;
};

// ─── Orchestration ────────────────────────────────────────────────────────────
export const orchestrateRequest = async (requestText, threadId = null) => {
  const payload = { request_text: requestText };
  if (threadId) payload.thread_id = threadId;
  const res = await api.post('/orchestrate', payload);
  return res.data;
};

// ─── Approvals ────────────────────────────────────────────────────────────────
export const fetchPendingApprovals = async () => (await api.get('/approvals/pending')).data;
export const fetchMyActions = async () => (await api.get('/approvals/my-actions')).data;
export const fetchAllApprovals = async () => (await api.get('/approvals/all')).data;

export const approvePendingWorkflow = async (threadId, approvedBy) => {
  const res = await api.post('/webhook/approve', { thread_id: threadId, approved_by: approvedBy, decision: 'APPROVED' });
  return res.data;
};

// ─── Workflow history (per user) ──────────────────────────────────────────────
export const fetchMyHistory = async () => (await api.get('/workflows/my-history')).data;

// ─── Metrics (Admin only) ─────────────────────────────────────────────────────
export const fetchMetrics = async () => (await api.get('/workflows/metrics')).data;

// ─── Notifications ────────────────────────────────────────────────────────────
export const fetchNotifications = async (userId) => (await api.get('/notifications', { params: { user_id: userId } })).data;

// ─── User Management (Admin only) ────────────────────────────────────────────
export const fetchAllUsers = async () => (await api.get('/auth/users')).data;
export const updateUserRole = async (username, role) => (await api.patch(`/auth/users/${username}/role`, { role })).data;
export const updateUserDepartment = async (username, department) => (await api.patch(`/auth/users/${username}/department`, { department })).data;
