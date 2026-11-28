
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate
} from "react-router-dom";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ReportPollution from "./pages/ReportPollution";
import MyReports from "./pages/MyReports";
import LakeMap from "./pages/LakeMap";
import WaterQuality from "./pages/WaterQuality";
import AdminDashboard from "./pages/AdminDashboard";

import "./App.css";

// Check authentication
const getUser = () => {
  try {
    const user = localStorage.getItem("aquawatch_user");
    return user ? JSON.parse(user) : null;
  } catch {
    return null;
  }
};

// Citizen protection
function CitizenRoute({ children }) {
  const token = localStorage.getItem("aquawatch_token");
  const user = getUser();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role === "admin") {
    return <Navigate to="/admin" replace />;
  }

  return children;
}

// Admin protection
function AdminRoute({ children }) {
  const token = localStorage.getItem("aquawatch_token");
  const user = getUser();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function App() {
  const token = localStorage.getItem("aquawatch_token");
  const user = getUser();

  const getHomeRoute = () => {
    if (!token) return "/";
    return user?.role === "admin" ? "/admin" : "/dashboard";
  };

  return (
    <BrowserRouter>
      <Routes>

        {/* Public Pages */}
        <Route
          path="/"
          element={<Home />}
        />

        <Route
          path="/login"
          element={
            token
              ? <Navigate to={getHomeRoute()} replace />
              : <Login />
          }
        />

        <Route
          path="/register"
          element={
            token
              ? <Navigate to={getHomeRoute()} replace />
              : <Register />
          }
        />

        {/* Citizen Dashboard */}
        <Route
          path="/dashboard"
          element={
            <CitizenRoute>
              <Dashboard />
            </CitizenRoute>
          }
        />

        {/* Citizen Pollution Report */}
        <Route
          path="/report"
          element={
            <CitizenRoute>
              <ReportPollution />
            </CitizenRoute>
          }
        />

        {/* Citizen My Reports */}
        <Route
          path="/my-reports"
          element={
            <CitizenRoute>
              <MyReports />
            </CitizenRoute>
          }
        />

        {/* Lake Map */}
        <Route
          path="/map"
          element={
            <CitizenRoute>
              <LakeMap />
            </CitizenRoute>
          }
        />

        {/* Water Quality */}
        <Route
          path="/water-quality"
          element={
            <CitizenRoute>
              <WaterQuality />
            </CitizenRoute>
          }
        />

        {/* Admin Dashboard */}
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminDashboard />
            </AdminRoute>
          }
        />

        {/* Unknown Routes */}
        <Route
          path="*"
          element={<Navigate to={getHomeRoute()} replace />}
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
