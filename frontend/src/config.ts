export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

import axios from 'axios';

// Intercept requests to add the token from localStorage
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});
