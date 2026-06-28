import axios from 'axios';

const normalizeApiUrl = (value) => {
  const base = (value || 'http://localhost:8000/api').replace(/\/+$/, '');
  return base.endsWith('/api') ? base : `${base}/api`;
};

export const API_URL = normalizeApiUrl(import.meta.env.VITE_API_URL);

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem('access_token', access);

          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        console.log('Token refresh failed, continuing without refresh');
      }
    }

    return Promise.reject(error);
  }
);

// Helper functions
const isAuthenticated = () => {
  return !!localStorage.getItem('access_token');
};

const validateAuth = async () => {
  try {
    const response = await api.get('/auth/user/');
    return response.status === 200;
  } catch {
    return false;
  }
};

const getCurrentUser = async () => {
  try {
    const response = await api.get('/auth/user/');
    return response.data;
  } catch {
    return null;
  }
};

// Auth API
export const authAPI = {
  // Strict username-based login
  login: (credentials) => {
    const { username, password } = credentials || {};
    return api.post('/auth/login/', { username, password }).then(res => res.data);
  },
  register: (userData) => api.post('/auth/register/', userData).then(res => res.data),
  logout: (refreshToken) => api.post('/auth/logout/', { refresh: refreshToken }).then(res => res.data).catch(() => ({})),
  getCurrentUser: () => api.get('/auth/user/'),
  updateProfile: (data) => api.patch('/auth/user/', data),
  isAuthenticated: isAuthenticated,
  validateAuth: validateAuth,
};

// User Profile API
export const profileAPI = {
  get: () => api.get('/auth/user/'),
  getMe: () => api.get('/auth/user/'),
  update: (data) => api.patch('/auth/user/', data),
};

export const billingAPI = {
  getPlans: () => api.get('/billing/plans/').then((res) => res.data),
  getStatus: () => api.get('/billing/status/').then((res) => res.data),
  createCheckoutSession: (plan = 'pro') => api.post('/billing/checkout/', { plan }).then((res) => res.data),
};


// AI Chat API
export const chatAPI = {
  sendMessage: (message, context = {}, sessionId = null) => 
    api.post('/chat/', { message, context, session_id: sessionId }).then(res => res.data),
  getHistory: (limit, sessionId) => 
    api.get('/chat/history/?limit=' + limit + (sessionId ? '&session_id=' + sessionId : '')).then(res => res.data),
  clearHistory: (sessionId) => 
    api.delete('/chat/clear/' + (sessionId ? '?session_id=' + sessionId : '')).then(res => res.data),
  // Chat Sessions
  getSessions: () => api.get('/chat/sessions/', { timeout: 12000 }).then(res => res.data),
  getSession: (sessionId) => api.get('/chat/sessions/' + sessionId + '/').then(res => res.data),
  createSession: (data) => api.post('/chat/sessions/', data).then(res => res.data),
  deleteSession: (sessionId) => api.delete('/chat/sessions/', { data: { session_id: sessionId } }).then(res => res.data),
};

export const analyticsAPI = {
  track: (event, data = {}) =>
    api.post('/analytics/track/', { event, data }).catch(() => {}),
};

export const referralAPI = {
  getInfo: () => api.get('/referral/info/').then((res) => res.data),
};

export const usageAPI = {
  getStats: () => api.get('/usage/stats/').then((res) => res.data),
};

export const textbookAPI = {
  getPdfUrl: (subject) => `${API_URL}/textbooks/${subject}/pdf/`,
  getPages: ({ subject, unit, chapter, title, includeText = false }) =>
    api.get('/textbooks/pages/', {
      params: { subject, unit, chapter, title, include_text: includeText },
    }).then(res => res.data),
};

export default api;
