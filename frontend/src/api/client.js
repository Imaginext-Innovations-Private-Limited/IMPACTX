import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export const commodityApi = {
  getTicker: () => api.get('/commodities/ticker'),
  getAll: (category) => api.get('/commodities/', { params: category ? { category } : {} }),
  simulateTick: (id) => api.post(`/commodities/${id}/simulate-tick`),
}

export const weatherApi = {
  getLocations: () => api.get('/weather/locations'),
  getForecast: (lat, lon, locationName) => api.get('/weather/forecast', {
    params: {
      lat: lat ?? 12.9716,
      lon: lon ?? 77.5946,
      location_name: locationName ?? 'Bengaluru',
    },
  }),
}

export const marketApi = {
  getList: () => api.get('/markets/commodities/list'),
  getCommodityAnalytics: (commodityName) =>
    api.get(`/markets/${encodeURIComponent(commodityName)}`),
}

export const newsApi = {
  getCategories: () => api.get('/news/categories'),
  getArticles: (categoryId, search) =>
    api.get('/news/', { params: { category_id: categoryId || undefined, search: search || undefined } }),
  getArticle: (id) => api.get(`/news/${id}`),
}

export const dairyApi = {
  getProcurementRates: (milkType) =>
    api.get('/dairy/procurement-rates', { params: milkType ? { milk_type: milkType } : {} }),
  calculatePayout: (data) => api.post('/dairy/calculate-payout', data),
  getBreeds: (tempC, animalType) =>
    api.get('/dairy/breeds', { params: { temp_c: tempC, animal_type: animalType } }),
  getFeedPlans: (animalType, stage) =>
    api.get('/dairy/feed-plans', { params: { animal_type: animalType, stage } }),
  getBreedingGuide: (damBreed) =>
    api.get('/dairy/breeding-guide', { params: damBreed ? { dam_breed: damBreed } : {} }),
  getDiseaseAdvisor: (symptom) =>
    api.get('/dairy/disease-advisor', { params: symptom ? { symptom } : {} }),
  getDoctors: (doctorType, search) =>
    api.get('/dairy/doctors', {
      params: {
        doctor_type: doctorType || undefined,
        search: search || undefined,
      },
    }),
  createDoctor: (data) => api.post('/dairy/doctors', data),
  getCattle: ({ breed, animal_type, min_price, max_price, sort_by } = {}) =>
    api.get('/dairy/cattle', {
      params: {
        breed: breed || undefined,
        animal_type: animal_type || undefined,
        min_price: min_price !== '' && min_price != null ? min_price : undefined,
        max_price: max_price !== '' && max_price != null ? max_price : undefined,
        sort_by: sort_by || undefined,
      },
    }),
  createCattle: (data) => api.post('/dairy/cattle', data),
  deleteCattle: (id) => api.delete(`/dairy/cattle/${id}`),
}

export const helpApi = {
  getContacts: (category, search) =>
    api.get('/help/contacts', {
      params: {
        category: category || undefined,
        search: search || undefined,
      },
    }),
  createContact: (data) => api.post('/help/contacts', data),
  deleteContact: (id) => api.delete(`/help/contacts/${id}`),
}

export const livestockPetsApi = {
  getListings: ({ category, min_price, max_price, sort_by } = {}) =>
    api.get('/livestock-pets', {
      params: {
        category: category || undefined,
        min_price: min_price !== '' && min_price != null ? min_price : undefined,
        max_price: max_price !== '' && max_price != null ? max_price : undefined,
        sort_by: sort_by || undefined,
      },
    }),
  createListing: (data) => api.post('/livestock-pets', data),
  deleteListing: (id) => api.delete(`/livestock-pets/${id}`),
}

export const voiceApi = {
  getLanguages: () => api.get('/voice/languages'),
  textQuery: (text, language, keyterms, location = null) => api.post('/voice/text-query', {
    text,
    language,
    keyterms: keyterms || [
      "APMC", "mandi", "paddy", "arecanut", "NPK", "urea",
      "DAP", "fungicide", "blight", "PM-KISAN", "KCC", "acre", "barrel"
    ],
    ...(location?.lat != null ? { lat: location.lat } : {}),
    ...(location?.lon != null ? { lon: location.lon } : {}),
    ...(location?.location_name ? { location_name: location.location_name } : {}),
  }, { timeout: 60000 }),
  voiceQuery: (formData) => api.post('/voice/query', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  }),
}

export const scanApi = {
  getModes: () => api.get('/scan/modes'),
  scan: (formData) => api.post('/scan/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 35000,
  }),
}

export const notificationApi = {
  getAll: (category) => api.get('/notifications/', { params: category ? { category } : {} }),
  getUnreadCount: () => api.get('/notifications/unread-count'),
  markRead: (id) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/mark-all-read'),
  toggleChecklist: (notificationId, docKey, isCompleted) =>
    api.post(`/notifications/${notificationId}/checklist/${docKey}`, { is_completed: isCompleted }),
}

export const whatsappApi = {
  simulate: (payload) => api.post('/whatsapp/simulate', payload),
  verifyWebhook: (params) => api.get('/whatsapp/webhook', { params }),
}

export const financeApi = {
  getLedger: (cropTag, entryType) =>
    api.get('/finance/ledger', { params: { crop_tag: cropTag || undefined, entry_type: entryType || undefined } }),
  addLedgerEntry: (data) => api.post('/finance/ledger', data),
  deleteLedgerEntry: (id) => api.delete(`/finance/ledger/${id}`),
  getProfitComparison: (soilType, tempC) =>
    api.get('/finance/profit-comparison', { params: { soil_type: soilType, temp_c: tempC } }),
  getAdvisory: () => api.get('/finance/advisory'),
  allocateWealth: (data) => api.post('/finance/wealth/allocate', data),
  checkPanLoans: (data) => api.post('/finance/wealth/pan-loans', data),
  addLoan: (data) => api.post('/finance/wealth/loans', data),
  closeLoan: (loanId) => api.patch(`/finance/wealth/loans/${loanId}/close`),
  getInvestPlan: (data) => api.post('/finance/wealth/invest-plan', data),
  calculateReturns: (data) => api.post('/finance/wealth/calculate-returns', data),
}

export default api
