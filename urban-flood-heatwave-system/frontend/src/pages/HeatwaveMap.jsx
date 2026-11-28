
import { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { RiskBadge } from '../components/RiskBadge'

const CITY_DATA = {
  Mumbai: {
    center: [19.0760, 72.8777],
    zones: [
      { id: 'h1', name: 'Dharavi', lat: 19.040, lon: 72.854, temp: 46.2, risk_level: 'CRITICAL', advice: 'Go to nearest cooling centre immediately' },
      { id: 'h2', name: 'Andheri', lat: 19.113, lon: 72.868, temp: 43.5, risk_level: 'HIGH', advice: 'Avoid outdoor activity 11am–4pm' },
      { id: 'h3', name: 'Kurla', lat: 19.072, lon: 72.880, temp: 44.1, risk_level: 'HIGH', advice: 'Stay hydrated' },
      { id: 'h4', name: 'Worli', lat: 19.017, lon: 72.816, temp: 42.0, risk_level: 'MEDIUM', advice: 'Use fans, keep curtains closed' },
      { id: 'h5', name: 'Bandra', lat: 19.054, lon: 72.841, temp: 40.3, risk_level: 'MEDIUM', advice: 'Stay hydrated' },
    ],
  },

  Bengaluru: {
    center: [12.9716, 77.5946],
    zones: [
      { id: 'b1', name: 'Bellandur', lat: 12.9304, lon: 77.6784, temp: 39.5, risk_level: 'HIGH', advice: 'Avoid outdoor activity during peak afternoon heat' },
      { id: 'b2', name: 'Marathahalli', lat: 12.9591, lon: 77.6974, temp: 38.2, risk_level: 'HIGH', advice: 'Stay hydrated and use shaded routes' },
      { id: 'b3', name: 'Whitefield', lat: 12.9698, lon: 77.7500, temp: 37.4, risk_level: 'MEDIUM', advice: 'Limit prolonged outdoor exposure' },
      { id: 'b4', name: 'Koramangala', lat: 12.9352, lon: 77.6245, temp: 36.8, risk_level: 'MEDIUM', advice: 'Drink water regularly' },
      { id: 'b5', name: 'Hebbal', lat: 13.0358, lon: 77.5970, temp: 38.0, risk_level: 'HIGH', advice: 'Prefer shaded areas when walking' },
      { id: 'b6', name: 'HSR Layout', lat: 12.9116, lon: 77.6389, temp: 36.2, risk_level: 'MEDIUM', advice: 'Stay hydrated' },
    ],
  },
}

const HEAT_COLORS = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
}

export default function HeatwaveMap() {
  const [selectedCity, setSelectedCity] = useState('Mumbai')

  const city = CITY_DATA[selectedCity]
  const heatZones = city.zones

  return (
    <div className="p-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">
            🌡️ Heatwave Risk Map
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Heat index values and urban heat island effects by zone.
          </p>
        </div>

        <select
          value={selectedCity}
          onChange={(e) => setSelectedCity(e.target.value)}
          className="bg-gray-800 text-white border border-gray-700 rounded-lg px-4 py-2"
        >
          <option value="Mumbai">Mumbai</option>
          <option value="Bengaluru">Bengaluru</option>
        </select>
      </div>

      <p className="text-xs text-yellow-400">
        Demo heat-risk values for demonstration only; not live temperature measurements.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div
          className="lg:col-span-3 bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
          style={{ height: '560px' }}
        >
          <MapContainer
            center={city.center}
            zoom={12}
            className="w-full h-full"
            key={selectedCity}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {heatZones.map((z) => (
              <CircleMarker
                key={z.id}
                center={[z.lat, z.lon]}
                radius={Math.max(10, (z.temp - 35) * 3)}
                pathOptions={{
                  fillColor: HEAT_COLORS[z.risk_level],
                  fillOpacity: 0.65,
                  color: HEAT_COLORS[z.risk_level],
                  weight: 2,
                }}
              >
                <Popup>
                  <div>
                    <p className="font-bold">{z.name}</p>
                    <p className="text-sm">
                      Demo feels-like value: {z.temp}°C
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      {z.advice}
                    </p>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        <div className="space-y-2">
          <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
            Heat Index by Zone
          </h2>

          {[...heatZones]
            .sort((a, b) => b.temp - a.temp)
            .map((z) => (
              <div
                key={z.id}
                className="bg-gray-900 rounded-lg border border-gray-800 p-3"
              >
                <p className="text-sm font-medium text-white">{z.name}</p>
                <p className="text-2xl font-bold text-orange-400">
                  {z.temp}°C
                </p>
                <RiskBadge level={z.risk_level} className="mt-1" />
                <p className="text-xs text-gray-500 mt-1">{z.advice}</p>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
