
import { useEffect } from 'react'
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
  Circle,
  useMap
} from 'react-leaflet'

import { RiskBadge } from './RiskBadge'

const RISK_COLORS = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
}

// Automatically move map when location changes
function MapUpdater({ center, zoom }) {
  const map = useMap()

  useEffect(() => {
    if (center && center.length === 2) {
      map.flyTo(center, zoom || 14)
    }
  }, [center, zoom, map])

  return null
}

export default function FloodRiskMap({
  zones = [],
  center = [20.5937, 78.9629],
  zoom = 5,
  userLocation = null
}) {
  const mapCenter = userLocation
    ? [userLocation.lat, userLocation.lon]
    : center

  return (
    <MapContainer
      center={mapCenter}
      zoom={zoom}
      className="w-full h-full"
      style={{ minHeight: '400px' }}
    >
      <MapUpdater center={mapCenter} zoom={zoom} />

      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Flood and heat risk zones */}
      {zones.map(zone => (
        <CircleMarker
          key={zone.zone_id}
          center={[zone.latitude, zone.longitude]}
          radius={Math.max(8, zone.risk_score * 30)}
          pathOptions={{
            fillColor: RISK_COLORS[zone.risk_level] || '#22c55e',
            fillOpacity: 0.7,
            color: RISK_COLORS[zone.risk_level] || '#22c55e',
            weight: 2,
          }}
        >
          <Tooltip permanent={zone.risk_level === 'CRITICAL'}>
            {zone.name}
          </Tooltip>

          <Popup>
            <div className="text-gray-900">
              <p className="font-bold">{zone.name}</p>
              <p className="text-sm text-gray-600">{zone.city}</p>
              <p className="text-sm mt-1">
                Risk: {(zone.risk_score * 100).toFixed(0)}%
              </p>
              <RiskBadge level={zone.risk_level} />
            </div>
          </Popup>
        </CircleMarker>
      ))}

      {/* User's actual current location */}
      {userLocation && (
        <>
          <Circle
            center={[userLocation.lat, userLocation.lon]}
            radius={userLocation.accuracy || 30}
            pathOptions={{
              color: '#2563eb',
              fillColor: '#60a5fa',
              fillOpacity: 0.15,
              weight: 1,
            }}
          />

          <CircleMarker
            center={[userLocation.lat, userLocation.lon]}
            radius={9}
            pathOptions={{
              color: '#ffffff',
              weight: 3,
              fillColor: '#2563eb',
              fillOpacity: 1,
            }}
          >
            <Popup>
              <strong>Your Current Location</strong>
              <br />
              Latitude: {userLocation.lat.toFixed(6)}
              <br />
              Longitude: {userLocation.lon.toFixed(6)}
            </Popup>
          </CircleMarker>
        </>
      )}
    </MapContainer>
  )
}
