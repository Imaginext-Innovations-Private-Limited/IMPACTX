
import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000/api"
});

const getAuthHeaders = () => {
  const token = localStorage.getItem("aquawatch_token");

  return {
    Authorization: `Bearer ${token}`
  };
};

// Existing manual reading functions
export const createWaterReading = async (readingData) => {
  const response = await API.post(
    "/water/readings",
    readingData,
    { headers: getAuthHeaders() }
  );

  return response.data;
};

export const getAllWaterReadings = async () => {
  const response = await API.get(
    "/water/readings",
    { headers: getAuthHeaders() }
  );

  return response.data;
};

export const getMyWaterReadings = async () => {
  const response = await API.get(
    "/water/my-readings",
    { headers: getAuthHeaders() }
  );

  return response.data;
};

// NEW: Get nearby CPCB historical readings
export const getNearbyHistoricalReadings = async (
  latitude,
  longitude,
  radiusKm = 25
) => {
  const response = await API.get(
    "/water/historical/nearby",
    {
      params: {
        latitude,
        longitude,
        radius_km: radiusKm
      },
      headers: getAuthHeaders()
    }
  );

  return response.data;
};
