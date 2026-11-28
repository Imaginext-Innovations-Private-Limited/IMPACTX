
import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker
} from "react-leaflet";
import { MapPin, Search, LoaderCircle } from "lucide-react";

import "leaflet/dist/leaflet.css";

function LocationSearch({ onSelect }) {
  const [lakeName, setLakeName] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const searchLake = async () => {
    if (!lakeName.trim()) {
      setError("Please enter a lake name.");
      return;
    }

    setLoading(true);
    setError("");
    setResults([]);
    setSelected(null);

    // Clear previous selection in the parent page
    onSelect(null);

    try {
      const searchQuery = lakeName.trim();

      const cacheKey =
        "aquawatch_location_" + searchQuery.toLowerCase();

      let data = [];

      // Check localStorage cache
      const cached = localStorage.getItem(cacheKey);

      if (cached) {
        try {
          const cachedData = JSON.parse(cached);

          if (
            Array.isArray(cachedData) &&
            cachedData.length > 0
          ) {
            data = cachedData;
          }
        } catch {
          localStorage.removeItem(cacheKey);
        }
      }

      // Search OpenStreetMap if cache is empty
      if (data.length === 0) {
        const params = new URLSearchParams({
          q: searchQuery,
          format: "jsonv2",
          limit: "10",
          countrycodes: "in",
          addressdetails: "1"
        });

        const response = await fetch(
          `https://nominatim.openstreetmap.org/search?${params}`,
          {
            headers: {
              "Accept": "application/json",
              "Accept-Language": "en"
            }
          }
        );

        if (!response.ok) {
          throw new Error(
            "Location service is temporarily unavailable. Please try again."
          );
        }

        data = await response.json();

        // Save only successful search results
        if (data.length > 0) {
          localStorage.setItem(
            cacheKey,
            JSON.stringify(data)
          );
        }
      }

      if (!data || data.length === 0) {
        setError(
          "Lake not found. Try: Navalooru Lake, Dharwad, Karnataka."
        );
      } else {
        setResults(data);
      }

    } catch (err) {
      setError(
        err.message || "Unable to find this location."
      );
    } finally {
      setLoading(false);
    }
  };

  const chooseLocation = (place) => {
    const latitude = Number(place.lat);
    const longitude = Number(place.lon);

    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude)
    ) {
      setError("Invalid location coordinates.");
      return;
    }

    const location = {
      lake_name: place.name || lakeName.trim(),
      latitude,
      longitude,
      display_name: place.display_name
    };

    setSelected(location);
    setResults([]);
    setError("");

    // Send selected GPS coordinates to WaterQuality.jsx
    onSelect(location);
  };

  const position = selected
    ? [selected.latitude, selected.longitude]
    : null;

  return (
    <div className="location-search">

      <label htmlFor="lake-search-input">
        Search Lake Location
      </label>

      <div className="location-search-row">

        <input
          id="lake-search-input"
          type="text"
          value={lakeName}
          onChange={(e) => setLakeName(e.target.value)}
          placeholder="Enter lake name, e.g. Navalooru Lake, Dharwad"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              searchLake();
            }
          }}
        />

        <button
          type="button"
          onClick={searchLake}
          disabled={loading}
        >
          {loading ? (
            <LoaderCircle
              size={18}
              className="location-spinner"
            />
          ) : (
            <Search size={18} />
          )}

          {loading ? "Searching..." : "Find Lake"}
        </button>

      </div>

      {error && (
        <p className="location-error">
          {error}
        </p>
      )}

      {results.length > 0 && (
        <div className="location-results">

          <p>Select the correct lake location:</p>

          {results.map((place) => (
            <button
              type="button"
              key={`${place.osm_type}-${place.osm_id}`}
              onClick={() => chooseLocation(place)}
              className="location-result-item"
            >
              <MapPin size={18} />

              <span>
                <strong>
                  {place.name || "Unnamed location"}
                </strong>

                <small>
                  {place.display_name}
                </small>
              </span>
            </button>
          ))}

        </div>
      )}

      {selected && (
        <div className="selected-location">

          <p className="location-success">
            <MapPin size={17} />
            Location selected successfully
          </p>

          <p>{selected.display_name}</p>

          <div className="location-coordinates">
            Latitude: {selected.latitude.toFixed(6)}
            <br />
            Longitude: {selected.longitude.toFixed(6)}
          </div>

          <MapContainer
            key={`${selected.latitude}-${selected.longitude}`}
            center={position}
            zoom={15}
            scrollWheelZoom={true}
            className="location-preview-map"
          >

            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <CircleMarker
              center={position}
              radius={10}
              pathOptions={{
                color: "#0d9488",
                fillColor: "#14b8a6",
                fillOpacity: 0.8
              }}
            />

          </MapContainer>

          <p className="location-map-attribution">
            Map data © OpenStreetMap contributors.
            Location coordinates are approximate.
          </p>

        </div>
      )}

    </div>
  );
}

export default LocationSearch;
