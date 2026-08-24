// src/api/axiosClient.ts
import axios from "axios";

const axiosClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  // withCredentials: true,
});

// Interceptor request
axiosClient.interceptors.request.use(
  (config) => {
    // Gắn token nếu có
    const token =
      typeof window !== "undefined"
        ? sessionStorage.getItem("access_token")
        : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Nếu body là FormData => để axios tự set multipart/form-data
    if (config.data instanceof FormData) {
      // KHÔNG set Content-Type ở đây,
      // để axios tự thêm boundary phù hợp
    } else {
      // Nếu không phải FormData => gửi JSON
      config.headers["Content-Type"] = "application/json";
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor response
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      console.warn("Unauthorized - Có thể token hết hạn");
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
