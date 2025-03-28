import axios from 'axios';

// http://127.0.0.1:8000/
// https://trip-planner-backend-azure.vercel.app/api

// Base url
const API_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add authentication token if needed
api.interceptors.request.use((config) => {
  const tokenString = localStorage.getItem('tokens');
  if (tokenString) {
    const tokenData = JSON.parse(tokenString); // Parse the JSON string
    const accessToken = tokenData.access_token; // Access the access_token property
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
  } 
  return config;
});

// Authentication Endpoints
export const signup = (userData) => api.post('/auth/users/', userData);
export const login = (credentials) => api.post('/auth/login/', credentials);

// Location Endpoints
export const geocodeAddress = (address) => api.post('/locations/geocode/', { address });

// Trip Endpoints
export const createTrip = (tripData) => api.post('/trips/', tripData);
export const getTrips = (params = {}) => api.get('/trips/', { params }); // List all trips
export const getTripDetails = (tripId) => api.get(`/trips/${tripId}/`);
export const generateLogs = (tripId) =>
  api.post(`/trips/${tripId}/generate_logs/`);
export const calculateRoute = (tripId) =>
  api.post(`/trips/${tripId}/calculate_route/`);

// Route Endpoints
export const getRoutes = (params = {}) => api.get('/routes/', { params });

// Waypoint Endpoints
export const getWaypoints = (params = {}) => api.get('/waypoints/', { params });

// Log Entry Endpoints
export const getLogEntries = (params = {}) => api.get('/log-entries/', { params });

// Daily Log Endpoints
export const getDailyLogs = (params = {}) => api.get('/daily-logs/', { params });






export default api;
