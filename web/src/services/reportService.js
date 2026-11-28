
import axios from "axios";


// -----------------------------------------
// AXIOS API CONFIGURATION
// -----------------------------------------

const API = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});


// -----------------------------------------
// AUTHENTICATION HEADERS
// -----------------------------------------

const getAuthHeaders = () => {
  const token = localStorage.getItem("aquawatch_token");

  return {
    Authorization: `Bearer ${token}`,
  };
};


// -----------------------------------------
// 1. UPLOAD POLLUTION PHOTOGRAPH
// -----------------------------------------

export const uploadPhoto = async (photo) => {
  const formData = new FormData();

  formData.append("file", photo);

  const response = await API.post(
    "/reports/upload-photo",
    formData,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


// -----------------------------------------
// 2. ANALYZE PHOTOGRAPH USING YOLO
// -----------------------------------------

export const detectPollution = async (filename) => {
  const response = await API.post(
    `/ai/detect/${encodeURIComponent(filename)}`,
    {},
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


// -----------------------------------------
// 3. CREATE POLLUTION REPORT
// -----------------------------------------

export const createReport = async (reportData) => {
  const response = await API.post(
    "/reports/create",
    reportData,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


// -----------------------------------------
// 4. GET CITIZEN'S REPORTS
// -----------------------------------------

export const getMyReports = async () => {
  const response = await API.get(
    "/reports/my-reports",
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


// -----------------------------------------
// 5. GET ALL REPORTS - ADMIN ONLY
// -----------------------------------------

export const getAllReports = async () => {
  const response = await API.get(
    "/reports/",
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


// -----------------------------------------
// 6. GET MAP REPORTS - CITIZEN AND ADMIN
// -----------------------------------------

export const getMapReports = async () => {
  const response = await API.get(
    "/map/reports",
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


// -----------------------------------------
// 7. GET ADMIN DASHBOARD STATISTICS
// -----------------------------------------

export const getAdminStats = async () => {
  const response = await API.get(
    "/reports/admin/stats",
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


// -----------------------------------------
// 8. UPDATE REPORT STATUS - ADMIN ONLY
// -----------------------------------------

export const updateReportStatus = async (
  reportId,
  newStatus
) => {
  const response = await API.patch(
    `/reports/admin/${encodeURIComponent(reportId)}/status`,
    null,
    {
      params: {
        new_status: newStatus,
      },
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
