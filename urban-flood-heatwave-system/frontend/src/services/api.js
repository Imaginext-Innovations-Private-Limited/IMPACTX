import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 15000,
})

// Flood API
export const floodApi = {
  getZones: (params) => api.get('/flood/zones', { params }),
  getZone: (id) => api.get(`/flood/zones/${id}`),
  predict: (params) => api.get('/flood/predict', { params }),
}

// Heatwave API
export const heatwaveApi = {
  predict: (params) => api.get('/heatwave/predict', { params }),
}

// Alerts API
export const alertsApi = {
  getActive: (params) => api.get('/alerts/', { params }),
  deactivate: (id) => api.delete(`/alerts/${id}`),
}

// Routes API
export const routesApi = {
  getSafeRoute: (params) => api.get('/routes/safe-route', { params }),
  getCoolingCentres: (params) => api.get('/routes/cooling-centres', { params }),
}

// Reports API
export const reportsApi = {
  submit: (formData) => api.post('/reports/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  list: (params) => api.get('/reports/', { params }),
}

export default api
