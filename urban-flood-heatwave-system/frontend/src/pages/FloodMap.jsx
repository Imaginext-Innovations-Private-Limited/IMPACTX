
import { useState } from 'react'
import FloodRiskMap from '../components/FloodRiskMap'
import { RiskBadge } from '../components/RiskBadge'

const CITY_DATA = {
  Mumbai: {
    center: [19.0760, 72.8777],
    zoom: 12,
    zones: [
      { zone_id: 'm1', name: 'Dharavi', city: 'Mumbai', latitude: 19.040, longitude: 72.854, risk_score: 0.82, risk_level: 'CRITICAL', is_flooded: true },
      { zone_id: 'm2', name: 'Kurla', city: 'Mumbai', latitude: 19.072, longitude: 72.880, risk_score: 0.65, risk_level: 'HIGH', is_flooded: false },
      { zone_id: 'm3', name: 'Worli', city: 'Mumbai', latitude: 19.017, longitude: 72.816, risk_score: 0.38, risk_level: 'MEDIUM', is_flooded: false },
      { zone_id: 'm4', name: 'Bandra', city: 'Mumbai', latitude: 19.054, longitude: 72.841, risk_score: 0.15, risk_level: 'LOW', is_flooded: false },
      { zone_id: 'm5', name: 'Andheri', city: 'Mumbai', latitude: 19.113, longitude: 72.868, risk_score: 0.72, risk_level: 'HIGH', is_flooded: false },
    ]
  },

  Bengaluru: {
    center: [12.9716, 77.5946],
    zoom: 12,
    zones: [
      { zone_id: 'b1', name: 'Bellandur', city: 'Bengaluru', latitude: 12.9250, longitude: 77.6760, risk_score: 0.85, risk_level: 'CRITICAL', is_flooded: true },
      { zone_id: 'b2', name: 'Marathahalli', city: 'Bengaluru', latitude: 12.9591, longitude: 77.6974, risk_score: 0.72, risk_level: 'HIGH', is_flooded: false },
      { zone_id: 'b3', name: 'Whitefield', city: 'Bengaluru', latitude: 12.9698, longitude: 77.7500, risk_score: 0.60, risk_level: 'HIGH', is_flooded: false },
      { zone_id: 'b4', name: 'Koramangala', city: 'Bengaluru', latitude: 12.9352, longitude: 77.6245, risk_score: 0.38, risk_level: 'MEDIUM', is_flooded: false },
      { zone_id: 'b5', name: 'Hebbal', city: 'Bengaluru', latitude: 13.0358, longitude: 77.5970, risk_score: 0.20, risk_level: 'LOW', is_flooded: false },
      { zone_id: 'b6', name: 'HSR Layout', city: 'Bengaluru', latitude: 12.9116, longitude: 77.6389, risk_score: 0.45, risk_level: 'MEDIUM', is_flooded: false },
    ]
  }
}

export default function FloodMap() {
  const [selectedCity, setSelectedCity] = useState('Mumbai')

  const city = CITY_DATA[selectedCity]
  const zones = city.zones

  return (
    <div className="p-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Flood Risk Map</h1>
          <p className="text-sm text-gray-400">
            View flood-risk locations by city.
          </p>
        </div>

        <select
          value={selectedCity}
          onChange={e => setSelectedCity(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2"
        >
          <option value="Mumbai">Mumbai</option>
          <option value="Bengaluru">Bengaluru</option>
        </select>
      </div>

      <p className="text-xs text-amber-400">
        Demonstration risk data – not verified live flood reports.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div
          className="lg:col-span-3 bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
          style={{ height: '560px' }}
        >
          <FloodRiskMap
            zones={zones}
            center={city.center}
            zoom={city.zoom}
          />
        </div>

        <div className="space-y-2">
          <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
            {selectedCity} Risk Zones
          </h2>

          {[...zones]
            .sort((a, b) => b.risk_score - a.risk_score)
            .map(z => (
              <div
                key={z.zone_id}
                className="bg-gray-900 rounded-lg border border-gray-800 p-3"
              >
                <p className="text-sm font-medium text-white">{z.name}</p>
                <p className="text-xs text-gray-500 mb-2">
                  Score: {(z.risk_score * 100).toFixed(0)}%
                </p>
                <RiskBadge level={z.risk_level} />

                {z.is_flooded && (
                  <p className="text-xs text-red-400 mt-1 font-medium">
                    Demo flooded status
                  </p>
                )}
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
