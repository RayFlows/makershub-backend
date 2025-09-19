import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'https://mini.makershub.cn';

const api = axios.create({
  baseURL: `${API_BASE}/admin/api`,
  timeout: 10000,
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('adminToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('adminToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;