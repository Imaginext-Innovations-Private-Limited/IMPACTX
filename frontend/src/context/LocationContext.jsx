import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { weatherApi } from '../api/client'

const LocationContext = createContext()

const STORAGE_KEY = 'farmAdvisor_live_location'

export const FALLBACK_DISTRICTS = [
  { id: 'bengaluru', name: 'Bengaluru', district: 'Bengaluru Urban', state: 'Karnataka', lat: 12.9716, lon: 77.5946 },
  { id: 'shivamogga', name: 'Shivamogga', district: 'Shivamogga', state: 'Karnataka', lat: 13.9299, lon: 75.5681 },
  { id: 'davanagere', name: 'Davanagere', district: 'Davanagere', state: 'Karnataka', lat: 14.4644, lon: 75.9218 },
  { id: 'mysuru', name: 'Mysuru', district: 'Mysuru', state: 'Karnataka', lat: 12.2958, lon: 76.6394 },
  { id: 'hassan', name: 'Hassan', district: 'Hassan', state: 'Karnataka', lat: 13.0072, lon: 76.1031 },
  { id: 'belagavi', name: 'Belagavi', district: 'Belagavi', state: 'Karnataka', lat: 15.8497, lon: 74.4977 },
  { id: 'dharwad', name: 'Dharwad', district: 'Dharwad', state: 'Karnataka', lat: 15.4589, lon: 75.0078 },
  { id: 'kalaburagi', name: 'Kalaburagi', district: 'Kalaburagi', state: 'Karnataka', lat: 17.3297, lon: 76.8343 },
  { id: 'mangaluru', name: 'Mangaluru', district: 'Dakshina Kannada', state: 'Karnataka', lat: 12.9141, lon: 74.8560 },
  { id: 'tumakuru', name: 'Tumakuru', district: 'Tumakuru', state: 'Karnataka', lat: 13.3379, lon: 77.1173 },
  { id: 'mandya', name: 'Mandya', district: 'Mandya', state: 'Karnataka', lat: 12.5218, lon: 76.8951 },
  { id: 'chikkamagaluru', name: 'Chikkamagaluru', district: 'Chikkamagaluru', state: 'Karnataka', lat: 13.3161, lon: 75.7720 },
  { id: 'ballari', name: 'Ballari', district: 'Ballari', state: 'Karnataka', lat: 15.1394, lon: 76.9214 },
  { id: 'raichur', name: 'Raichur', district: 'Raichur', state: 'Karnataka', lat: 16.2120, lon: 77.3439 },
  { id: 'kolar', name: 'Kolar', district: 'Kolar', state: 'Karnataka', lat: 13.1362, lon: 78.1291 },
  { id: 'udupi', name: 'Udupi', district: 'Udupi', state: 'Karnataka', lat: 13.3409, lon: 74.7421 },
  { id: 'pune', name: 'Pune', district: 'Pune', state: 'Maharashtra', lat: 18.5204, lon: 73.8567 },
  { id: 'nashik', name: 'Nashik', district: 'Nashik', state: 'Maharashtra', lat: 19.9975, lon: 73.7898 },
  { id: 'coimbatore', name: 'Coimbatore', district: 'Coimbatore', state: 'Tamil Nadu', lat: 11.0168, lon: 76.9558 },
  { id: 'hyderabad', name: 'Hyderabad', district: 'Rangareddy', state: 'Telangana', lat: 17.3850, lon: 78.4867 },
  { id: 'guntur', name: 'Guntur', district: 'Guntur', state: 'Andhra Pradesh', lat: 16.3067, lon: 80.4365 },
  { id: 'thrissur', name: 'Thrissur', district: 'Thrissur', state: 'Kerala', lat: 10.5276, lon: 76.2144 },
  { id: 'lucknow', name: 'Lucknow', district: 'Lucknow', state: 'Uttar Pradesh', lat: 26.8467, lon: 80.9462 },
  { id: 'ludhiana', name: 'Ludhiana', district: 'Ludhiana', state: 'Punjab', lat: 30.9010, lon: 75.8573 },
  { id: 'karnal', name: 'Karnal', district: 'Karnal', state: 'Haryana', lat: 29.6857, lon: 76.9905 },
  { id: 'indore', name: 'Indore', district: 'Indore', state: 'Madhya Pradesh', lat: 22.7196, lon: 75.8577 },
  { id: 'ahmedabad', name: 'Ahmedabad', district: 'Ahmedabad', state: 'Gujarat', lat: 23.0225, lon: 72.5714 },
  { id: 'kolkata', name: 'Kolkata / Hooghly', district: 'Hooghly', state: 'West Bengal', lat: 22.9000, lon: 88.3900 },
  { id: 'jaipur', name: 'Jaipur', district: 'Jaipur', state: 'Rajasthan', lat: 26.9124, lon: 75.7873 },
  { id: 'patna', name: 'Patna', district: 'Patna', state: 'Bihar', lat: 25.5941, lon: 85.1376 },
  { id: 'cuttack', name: 'Cuttack', district: 'Cuttack', state: 'Odisha', lat: 20.4625, lon: 85.8830 },
]

async function reverseGeocodeCoords(lat, lon) {
  const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&zoom=10&addressdetails=1`
  const resp = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!resp.ok) throw new Error(`Nominatim HTTP ${resp.status}`)
  const data = await resp.json()
  const addr = data.address || {}
  const taluk = addr.suburb || addr.village || addr.town || addr.city || addr.county || ''
  const rawDistrict = addr.state_district || addr.county || addr.city || taluk || ''
  const district = rawDistrict.replace(/\s*District$/i, '').trim()
  const state = addr.state || 'Karnataka'
  const parts = []
  if (taluk && taluk.toLowerCase() !== district.toLowerCase()) parts.push(taluk)
  if (district) parts.push(district)
  if (!parts.length && state) parts.push(state)
  const location_name = parts.join(', ') || `${lat.toFixed(4)}, ${lon.toFixed(4)}`
  return { taluk, district: district || taluk, state, location_name }
}

export function LocationProvider({ children }) {
  const [districts, setDistricts] = useState(FALLBACK_DISTRICTS)
  const [location, setLocation] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      const parsed = saved ? JSON.parse(saved) : null
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
    } catch {
      return null
    }
  })
  const [gpsStatus, setGpsStatus] = useState('detecting') // 'detecting' | 'granted' | 'denied' | 'unsupported'
  const [needsManualPicker, setNeedsManualPicker] = useState(false)

  const persistLocation = useCallback((locObj) => {
    setLocation(locObj)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(locObj))
    } catch {
      // ignore storage quota errors
    }
  }, [])

  const detectGpsLocation = useCallback(() => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setGpsStatus('unsupported')
      setNeedsManualPicker(prev => prev || !location)
      return
    }

    setGpsStatus('detecting')
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(6))
        const lon = Number(pos.coords.longitude.toFixed(6))
        setGpsStatus('granted')
        setNeedsManualPicker(false)
        try {
          const geo = await reverseGeocodeCoords(lat, lon)
          persistLocation({
            lat,
            lon,
            taluk: geo.taluk,
            district: geo.district,
            state: geo.state,
            location_name: geo.location_name,
            source: 'gps',
          })
        } catch {
          persistLocation({
            lat,
            lon,
            taluk: '',
            district: '',
            state: '',
            location_name: `${lat.toFixed(3)}, ${lon.toFixed(3)}`,
            source: 'gps',
          })
        }
      },
      () => {
        setGpsStatus('denied')
        // Show manual district picker automatically if user hasn't picked a location yet
        setLocation(curr => {
          if (!curr) setNeedsManualPicker(true)
          return curr
        })
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    )
  }, [location, persistLocation])

  // Fetch district list from backend & request browser GPS on app load
  useEffect(() => {
    weatherApi.getLocations()
      .then(res => {
        if (Array.isArray(res.data) && res.data.length > 0) {
          setDistricts(res.data)
        }
      })
      .catch(() => {})

    detectGpsLocation()
    // Run once on initial mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selectDistrict = useCallback((districtIdOrObj) => {
    const found = typeof districtIdOrObj === 'string'
      ? districts.find(d => d.id === districtIdOrObj || d.name === districtIdOrObj)
      : districtIdOrObj
    if (!found) return
    const distName = found.district || found.name
    persistLocation({
      lat: found.lat,
      lon: found.lon,
      taluk: '',
      district: distName,
      state: found.state || 'Karnataka',
      location_name: found.name || distName,
      source: 'manual',
    })
    setNeedsManualPicker(false)
  }, [districts, persistLocation])

  return (
    <LocationContext.Provider
      value={{
        location,
        gpsStatus,
        districts,
        needsManualPicker,
        setNeedsManualPicker,
        detectGpsLocation,
        selectDistrict,
      }}
    >
      {children}
    </LocationContext.Provider>
  )
}

export function useLocationContext() {
  const ctx = useContext(LocationContext)
  if (!ctx) throw new Error('useLocationContext must be used inside LocationProvider')
  return ctx
}

export const useLocation = useLocationContext
