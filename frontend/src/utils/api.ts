import axios, { AxiosInstance, AxiosError } from 'axios';
import { ApiResponse } from '../types/common';

/**
 * API utilities and configuration
 */

// Create axios instance with base configuration
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add timestamp to prevent caching for GET requests
    if (config.method === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now(),
      };
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    const errorMessage = getErrorMessage(error);
    console.error('API Error:', errorMessage, error);
    return Promise.reject(new Error(errorMessage));
  }
);

export function getErrorMessage(error: AxiosError): string {
  if (error.response?.data) {
    const data = error.response.data as any;
    if (typeof data === 'string') return data;
    if (data.detail) return data.detail;
    if (data.error) return data.error;
    if (data.message) return data.message;
  }
  
  if (error.message) return error.message;
  return 'An unexpected error occurred';
}

export function createApiResponse<T>(data: T, success: boolean = true): ApiResponse<T> {
  return {
    success,
    data,
  };
}

export function createErrorResponse(error: string): ApiResponse {
  return {
    success: false,
    error,
  };
}

// Health check function
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await api.get('/health');
    return response.status === 200;
  } catch {
    return false;
  }
}

export default api;