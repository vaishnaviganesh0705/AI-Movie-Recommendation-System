import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {

    const token =
      localStorage.getItem("access_token") || localStorage.getItem("token");

    if (token) {

      config.headers.Authorization =
        `Bearer ${token}`;

    }

    return config;
  },

  (error) => {
    return Promise.reject(error);
  }
);


api.interceptors.response.use(

  (response) => response,

  (error) => {

    console.error(
      "API Error:",
      error.response?.status,
      error.response?.data
    );

    return Promise.reject(error);
  }

);


export default api;