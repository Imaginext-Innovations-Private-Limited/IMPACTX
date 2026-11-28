
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
import Support from "./pages/Support";

import AdminDashboard from "./pages/AdminDashboard";

import "./App.css";


// Get logged-in user
const getUser = () => {
  try {
    const user = localStorage.getItem("aquawatch_user");
    return user ? JSON.parse(user) : null;
  } catch {
    return null;
  }
};


// Citizen route protection
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


// Admin route protection
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

    return user?.role === "admin"
      ? "/admin"
      : "/dashboard";
  };

  return (
    <BrowserRouter>
      <Routes>

        {/* PUBLIC PAGES */}

        <Route path="/" element={<Home />} />

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


        {/* CITIZEN PAGES */}

        <Route
          path="/dashboard"
          element={
            <CitizenRoute>
              <Dashboard />
            </CitizenRoute>
          }
        />

        <Route
          path="/report"
          element={
            <CitizenRoute>
              <ReportPollution />
            </CitizenRoute>
          }
        />

        <Route
          path="/my-reports"
          element={
            <CitizenRoute>
              <MyReports />
            </CitizenRoute>
          }
        />

        <Route
          path="/map"
          element={
            <CitizenRoute>
              <LakeMap />
            </CitizenRoute>
          }
        />

        <Route
          path="/water-quality"
          element={
            <CitizenRoute>
              <WaterQuality />
            </CitizenRoute>
          }
        />

        {/* SUPPORT & USER GUIDE */}

        <Route
          path="/support"
          element={
            <CitizenRoute>
              <Support />
            </CitizenRoute>
          }
        />


        {/* ADMIN PAGE */}

        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminDashboard />
            </AdminRoute>
          }
        />


        {/* UNKNOWN ROUTES */}

        <Route
          path="*"
          element={
            <Navigate to={getHomeRoute()} replace />
          }
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
