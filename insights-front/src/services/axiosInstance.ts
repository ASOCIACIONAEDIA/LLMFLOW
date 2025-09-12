import axios from 'axios';
import router from '@/router'; // Assuming your router is here
 
const baseURL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
 
const apiClient = axios.create({
  baseURL: baseURL,
});
 
apiClient.interceptors.request.use(
  (config) => {
    const token = sessionStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Log outgoing requests for debugging
    // console.log('Starting Request', config.method?.toUpperCase(), config.url, config.headers);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
 
apiClient.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Prevent infinite loops
      console.error("Axios Interceptor: Received 401 Unauthorized.");
 
      // Clear potentially invalid token and user data
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('user');
      sessionStorage.removeItem('adminToken'); // If you use this
 
      // Redirect to login
      // Check if already on login to prevent redirect loop
      if (router.currentRoute.value.name !== 'login') { // Corrected 'Login' to 'login'
         router.push({ name: 'login' }); // Corrected 'Login' to 'login'
      }
      return Promise.reject(error); // Important to reject after handling
    }
    return Promise.reject(error);
  }
);
 
export default apiClient;
 