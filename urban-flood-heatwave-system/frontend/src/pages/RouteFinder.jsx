
import { useState } from 'react'
import {
  Navigation,
  AlertTriangle,
  CheckCircle2,
  MapPin,
  LocateFixed,
  Loader2
} from 'lucide-react'

import FloodRiskMap from '../components/FloodRiskMap'
import { routesApi } from '../services/api'
import toast from 'react-hot-toast'

const DEMO_CENTRES = [
  {
    id: 1,
    name: 'BKC Community Hall',
    center_type: 'Community Hall',
    address: 'Bandra Kurla Complex, Mumbai',
    latitude: 19.065,
    longitude: 72.869,
    distance_km: 1.2,
    capacity: 500,
    current_occupancy: 180,
    has_water: true,
    has_medical: true,
    phone: '022-1234-5678'
  },
  {
    id: 2,
    name: 'Dharavi School No. 7',
    center_type: 'School',
    address: 'Dharavi, Mumbai',
    latitude: 19.038,
    longitude: 72.851,
    distance_km: 2.1,
    capacity: 300,
    current_occupancy: 95,
    has_water: true,
    has_medical: false,
    phone: '022-9876-5432'
  },
  {
    id: 3,
    name: 'Sion Hospital OPD Hall',
    center_type: 'Hospital',
    address: 'Sion, Mumbai',
    latitude: 19.040,
    longitude: 72.863,
    distance_km: 3.4,
    capacity: 200,
    current_occupancy: 60,
    has_water: true,
    has_medical: true,
    phone: '022-2222-3333'
  },
]

export default function RouteFinder() {
  const [origin, setOrigin] = useState({ lat: '', lon: '' })
  const [dest, setDest] = useState({ lat: '', lon: '' })
  const [result, setResult] = useState(null)
  const [centres, setCentres] = useState(DEMO_CENTRES)
  const [loading, setLoading] = useState(false)
  const [locating, setLocating] = useState(false)
  const [locationError, setLocationError] = useState('')
  const [userLocation, setUserLocation] = useState(null)
  const [tab, setTab] = useState('route')

  // Get the user's real browser location
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by this browser.')
      toast.error('Location is not supported by this browser')
      return
    }

    setLocating(true)
    setLocationError('')

    navigator.geolocation.getCurrentPosition(
      position => {
        const { latitude, longitude, accuracy } = position.coords

        const location = {
          lat: latitude,
          lon: longitude,
          accuracy: accuracy
        }

        setUserLocation(location)

        setOrigin({
          lat: String(latitude),
          lon: String(longitude)
        })

        setLocating(false)
        toast.success('Your current location detected!')
      },
      error => {
        let message = 'Unable to detect your location.'

        if (error.code === 1) {
          message = 'Location permission denied. Allow location access in browser settings.'
        } else if (error.code === 2) {
          message = 'Location unavailable. Check your device location settings.'
        } else if (error.code === 3) {
          message = 'Location request timed out. Please try again.'
        }

        setLocationError(message)
        setLocating(false)
        toast.error(message)
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0
      }
    )
  }

  const handleRouteSearch = async e => {
    e.preventDefault()

    if (!origin.lat || !origin.lon || !dest.lat || !dest.lon) {
      toast.error('Enter your starting point and destination')
      return
    }

    setLoading(true)

    try {
      const { data } = await routesApi.getSafeRoute({
        origin_lat: origin.lat,
        origin_lon: origin.lon,
        dest_lat: dest.lat,
        dest_lon: dest.lon,
      })

      setResult(data)
    } catch {
      toast.error('Unable to calculate route. Please check the backend connection.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const handleCentreSearch = async () => {
    if (!origin.lat || !origin.lon) {
      toast.error('Detect or enter your location first')
      return
    }

    try {
      const { data } = await routesApi.getCoolingCentres({
        lat: origin.lat,
        lon: origin.lon
      })
      setCentres(data)
    } catch {
      toast.error('Unable to load cooling centres')
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-white">
        Safe Route Finder
      </h1>

      <div className="flex gap-2">
        {['route', 'cooling'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {t === 'route' ? '🗺️ Safe Route' : '❄️ Cooling Centres'}
          </button>
        ))}
      </div>

      {tab === 'route' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <form onSubmit={handleRouteSearch} className="space-y-4">

              <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-3">
                <h2 className="font-semibold text-sm text-white flex items-center gap-2">
                  <MapPin size={14} />
                  Your Location
                </h2>

                <button
                  type="button"
                  onClick={handleGetLocation}
                  disabled={locating}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-semibold text-white"
                >
                  {locating
                    ? <Loader2 size={17} className="animate-spin" />
                    : <LocateFixed size={17} />
                  }
                  {locating ? 'Detecting Location...' : 'Use My Current Location'}
                </button>

                {locationError && (
                  <p className="text-xs text-red-400">
                    {locationError}
                  </p>
                )}

                {userLocation && (
                  <p className="text-xs text-green-400">
                    ✓ Location detected successfully
                    <br />
                    Accuracy: approximately {Math.round(userLocation.accuracy)} metres
                  </p>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <input
                    placeholder="Latitude"
                    value={origin.lat}
                    onChange={e => setOrigin(o => ({ ...o, lat: e.target.value }))}
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />

                  <input
                    placeholder="Longitude"
                    value={origin.lon}
                    onChange={e => setOrigin(o => ({ ...o, lon: e.target.value }))}
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>

              <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-3">
                <h2 className="font-semibold text-sm text-white flex items-center gap-2">
                  <Navigation size={14} />
                  Destination
                </h2>

                <div className="grid grid-cols-2 gap-2">
                  <input
                    placeholder="Latitude"
                    value={dest.lat}
                    onChange={e => setDest(d => ({ ...d, lat: e.target.value }))}
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />

                  <input
                    placeholder="Longitude"
                    value={dest.lon}
                    onChange={e => setDest(d => ({ ...d, lon: e.target.value }))}
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg font-semibold text-white text-sm"
              >
                {loading ? 'Calculating...' : 'Find Safe Route'}
              </button>
            </form>

            {result && (
              <div className={`rounded-xl border p-5 space-y-3 ${
                result.is_safe
                  ? 'bg-green-900/20 border-green-700'
                  : 'bg-red-900/20 border-red-700'
              }`}>
                <div className="flex items-center gap-2">
                  {result.is_safe
                    ? <CheckCircle2 size={20} className="text-green-400" />
                    : <AlertTriangle size={20} className="text-red-400" />
                  }

                  <span className={`font-semibold ${
                    result.is_safe ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {result.is_safe ? 'Route is Safe' : 'Route has Flood Risks!'}
                  </span>
                </div>

                <div className="text-sm text-gray-300 space-y-1">
                  <p>Distance: {(result.distance_m / 1000).toFixed(1)} km</p>
                  <p>Duration: ~{Math.round(result.duration_s / 60)} minutes</p>
                </div>

                {result.flood_warnings?.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-red-400 mb-2">
                      ⚠ Route passes through:
                    </p>

                    {result.flood_warnings.map((w, i) => (
                      <div key={i} className="text-xs bg-red-900/30 rounded-lg px-3 py-2 text-red-300">
                        {w.zone_name} — {w.risk_level} risk
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden" style={{ height: '420px' }}>
            <FloodRiskMap
              zones={[]}
              center={[19.0760, 72.8777]}
              zoom={12}
              userLocation={userLocation}
            />
          </div>
        </div>
      )}

      {tab === 'cooling' && (
        <div className="space-y-4">
          <div className="flex gap-3 flex-wrap">
            <button
              onClick={handleGetLocation}
              disabled={locating}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium text-white"
            >
              {locating ? 'Detecting...' : 'Use My Current Location'}
            </button>

            <input
              placeholder="Your latitude"
              value={origin.lat}
              onChange={e => setOrigin(o => ({ ...o, lat: e.target.value }))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-40"
            />

            <input
              placeholder="Your longitude"
              value={origin.lon}
              onChange={e => setOrigin(o => ({ ...o, lon: e.target.value }))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-40"
            />

            <button
              onClick={handleCentreSearch}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium text-white"
            >
              Find Centres
            </button>
          </div>

          {locationError && (
            <p className="text-sm text-red-400">{locationError}</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {centres.map(c => (
              <div key={c.id} className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-white">{c.name}</p>
                    <p className="text-xs text-blue-400">{c.center_type}</p>
                  </div>
                  <span className="text-xs text-gray-400">{c.distance_km} km</span>
                </div>

                <p className="text-xs text-gray-400">{c.address}</p>

                <div className="flex gap-2 flex-wrap">
                  <span className="px-2 py-0.5 bg-blue-900/30 border border-blue-800 rounded text-xs text-blue-300">
                    {c.current_occupancy}/{c.capacity} capacity
                  </span>

                  {c.has_water && (
                    <span className="px-2 py-0.5 bg-cyan-900/30 border border-cyan-800 rounded text-xs text-cyan-300">
                      💧 Water
                    </span>
                  )}

                  {c.has_medical && (
                    <span className="px-2 py-0.5 bg-green-900/30 border border-green-800 rounded text-xs text-green-300">
                      🏥 Medical
                    </span>
                  )}
                </div>

                {c.phone && (
                  <p className="text-xs text-gray-400">📞 {c.phone}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
