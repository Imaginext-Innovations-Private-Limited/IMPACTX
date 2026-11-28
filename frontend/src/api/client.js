import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export const commodityApi = {
  getTicker: (state, district, locationName, lat, lon) => api.get('/commodities/ticker', {
    params: {
      ...(state ? { state } : {}),
      ...(district ? { district } : {}),
      ...(locationName ? { location_name: locationName } : {}),
      ...(lat != null ? { lat } : {}),
      ...(lon != null ? { lon } : {}),
    },
  }),
  getAll: (category, state, district, locationName, lat, lon) => api.get('/commodities/', {
    params: {
      ...(category ? { category } : {}),
      ...(state ? { state } : {}),
      ...(district ? { district } : {}),
      ...(locationName ? { location_name: locationName } : {}),
      ...(lat != null ? { lat } : {}),
      ...(lon != null ? { lon } : {}),
    },
  }),
  simulateTick: (id) => api.post(`/commodities/${id}/simulate-tick`),
}

export const weatherApi = {
  getLocations: (state, district) => api.get('/weather/locations', {
    params: {
      ...(state ? { state } : {}),
      ...(district ? { district } : {}),
    },
  }),
  getForecast: (lat, lon, locationName, state, language) => api.get('/weather/forecast', {
    params: {
      lat: lat ?? 12.9716,
      lon: lon ?? 77.5946,
      location_name: locationName ?? 'Bengaluru',
      ...(state ? { state } : {}),
      ...(language ? { language } : {}),
    },
  }),
}

export const marketApi = {
  getList: (state, district, locationName, lat, lon) => api.get('/markets/commodities/list', {
    params: {
      ...(state ? { state } : {}),
      ...(district ? { district } : {}),
      ...(locationName ? { location_name: locationName } : {}),
      ...(lat != null ? { lat } : {}),
      ...(lon != null ? { lon } : {}),
    },
  }),
  getCommodityAnalytics: (commodityName, state, district, locationName, lat, lon, language) =>
    api.get(`/markets/${encodeURIComponent(commodityName)}`, {
      params: {
        ...(state ? { state } : {}),
        ...(district ? { district } : {}),
        ...(locationName ? { location_name: locationName } : {}),
        ...(lat != null ? { lat } : {}),
        ...(lon != null ? { lon } : {}),
        ...(language ? { language } : {}),
      },
    }),
}

export const newsApi = {
  getCategories: () => api.get('/news/categories'),
  getArticles: (categoryId, search) =>
    api.get('/news/', { params: { category_id: categoryId || undefined, search: search || undefined } }),
  getArticle: (id) => api.get(`/news/${id}`),
}

export const dairyApi = {
  getOverview: (loc = {}, signal) =>
    api.get('/dairy/', { params: loc, signal }),
  getAdvisory: (loc = {}, signal) =>
    api.get('/dairy/advisory', { params: loc, signal }),
  getProcurementRates: (milkType, loc = {}, signal) =>
    api.get('/dairy/procurement-rates', {
      params: { ...(milkType ? { milk_type: milkType } : {}), ...loc },
      signal,
    }),
  calculatePayout: (data) => api.post('/dairy/calculate-payout', data),
  getBreeds: (tempC, animalType, loc = {}, signal) =>
    api.get('/dairy/breeds', {
      params: { temp_c: tempC, animal_type: animalType, ...loc },
      signal,
    }),
  getFeedPlans: (animalType, stage, loc = {}, signal) =>
    api.get('/dairy/feed-plans', {
      params: { animal_type: animalType, stage, ...loc },
      signal,
    }),
  getBreedingGuide: (damBreed, loc = {}, signal) =>
    api.get('/dairy/breeding-guide', {
      params: { ...(damBreed ? { dam_breed: damBreed } : {}), ...loc },
      signal,
    }),
  getDiseaseAdvisor: (symptom, loc = {}, signal) =>
    api.get('/dairy/disease-advisor', {
      params: { ...(symptom ? { symptom } : {}), ...loc },
      signal,
    }),
  getCattleMarket: (loc = {}, signal) =>
    api.get('/dairy/cattle-market', { params: loc, signal }),
  getDoctors: (doctorType, search, signal) =>
    api.get('/dairy/doctors', {
      params: {
        doctor_type: doctorType || undefined,
        search: search || undefined,
      },
      signal,
    }),
  createDoctor: (data) => api.post('/dairy/doctors', data),
  getCattle: ({ breed, animal_type, min_price, max_price, sort_by } = {}, signal) =>
    api.get('/dairy/cattle', {
      params: {
        breed: breed || undefined,
        animal_type: animal_type || undefined,
        min_price: min_price !== '' && min_price != null ? min_price : undefined,
        max_price: max_price !== '' && max_price != null ? max_price : undefined,
        sort_by: sort_by || undefined,
      },
      signal,
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

export const schemesApi = {
  getSchemes: ({ state, district, location_name, category = 'all', language = 'en-IN' } = {}, signal) =>
    api.get('/schemes/', {
      params: {
        ...(state ? { state } : {}),
        ...(district ? { district } : {}),
        ...(location_name ? { location_name } : {}),
        category,
        language,
      },
      signal,
    }),
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
