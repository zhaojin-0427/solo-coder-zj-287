import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  res => res.data,
  err => {
    console.error('API Error:', err)
    return Promise.reject(err)
  }
)

export default {
  dashboard: () => api.get('/dashboard/'),
  statistics: (months = 12) => api.get(`/statistics/?months=${months}`),
  paybackPrediction: () => api.get('/payback-prediction/'),
  seedDemo: () => api.post('/seed-demo/'),
  importGeneration: (data) => api.post('/import-generation/', data),
  calculateRevenue: (date) => api.post('/calculate-revenue/', { date }),

  inverters: {
    list: () => api.get('/inverters/'),
    create: (data) => api.post('/inverters/', data),
    update: (id, data) => api.put(`/inverters/${id}/`, data),
    delete: (id) => api.delete(`/inverters/${id}/`),
    fetchData: (id) => api.post(`/inverters/${id}/fetch-data/`),
  },

  panelGroups: {
    list: () => api.get('/panel-groups/'),
    create: (data) => api.post('/panel-groups/', data),
    update: (id, data) => api.put(`/panel-groups/${id}/`, data),
    delete: (id) => api.delete(`/panel-groups/${id}/`),
  },

  dailyGeneration: {
    list: (params) => api.get('/daily-generation/', { params }),
    create: (data) => api.post('/daily-generation/', data),
  },

  householdUsage: {
    list: (params) => api.get('/household-usage/', { params }),
    create: (data) => api.post('/household-usage/', data),
  },

  electricityPrices: {
    list: () => api.get('/electricity-prices/'),
    create: (data) => api.post('/electricity-prices/', data),
  },

  revenueRecords: {
    list: (params) => api.get('/revenue-records/', { params }),
  },

  healthDiagnosis: {
    list: (params) => api.get('/health-diagnosis/', { params }),
    markHandled: (id) => api.post(`/health-diagnosis/${id}/mark-handled/`),
  },

  alertSummary: () => api.get('/alert-summary/'),
  generateDiagnosis: (dateFrom, dateTo) => api.post('/generate-diagnosis/', { date_from: dateFrom, date_to: dateTo }),

  storageSummary: () => api.get('/storage-summary/'),
  calculateStorage: (data) => api.post('/calculate-storage/', data),

  storageBatteries: {
    list: () => api.get('/storage-batteries/'),
    create: (data) => api.post('/storage-batteries/', data),
    update: (id, data) => api.put(`/storage-batteries/${id}/`, data),
    delete: (id) => api.delete(`/storage-batteries/${id}/`),
    get: (id) => api.get(`/storage-batteries/${id}/`),
    recalculate: (id, dateFrom, dateTo) => api.post(`/storage-batteries/${id}/recalculate/`, { date_from: dateFrom, date_to: dateTo }),
  },

  storageSchedules: {
    list: (params) => api.get('/storage-schedules/', { params }),
    get: (id) => api.get(`/storage-schedules/${id}/`),
  },
}
