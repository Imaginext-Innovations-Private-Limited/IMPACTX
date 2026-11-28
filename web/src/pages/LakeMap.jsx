
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap
} from "react-leaflet";

import {
  Waves,
  LayoutDashboard,
  FileText,
  Camera,
  MapPin,
  Droplets,
  LogOut,
  Menu,
  X,
  Bell,
  RefreshCw,
  Clock,
  CheckCircle,
  AlertCircle,
  Leaf,
  Activity
} from "lucide-react";

import { getMapReports } from "../services/reportService";

import "leaflet/dist/leaflet.css";


// -----------------------------------------
// REFRESH MAP SIZE
// -----------------------------------------

function RefreshMapSize() {
  const map = useMap();

  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 400);

    return () => clearTimeout(timer);
  }, [map]);

  return null;
}


// -----------------------------------------
// AUTOMATICALLY ZOOM TO REPORT LOCATIONS
// -----------------------------------------

function FitMapToReports({ reports }) {
  const map = useMap();

  useEffect(() => {
    if (reports.length > 0) {
      const bounds = reports.map((report) => [
        Number(report.latitude),
        Number(report.longitude)
      ]);

      map.fitBounds(bounds, {
        padding: [40, 40],
        maxZoom: 12
      });
    }
  }, [reports, map]);

  return null;
}


// -----------------------------------------
// LAKE MAP COMPONENT
// -----------------------------------------

function LakeMap() {
  const navigate = useNavigate();

  const [reports, setReports] = useState([]);
  const [filter, setFilter] = useState("all");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  const user = JSON.parse(
    localStorage.getItem("aquawatch_user") || "{}"
  );


  // -----------------------------------------
  // LOAD MAP REPORTS
  // -----------------------------------------

  const loadReports = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      // Use citizen-accessible map API
      const response = await getMapReports();

      const allReports = Array.isArray(response)
        ? response
        : response.reports || [];

      // Validate GPS coordinates
      const validReports = allReports.filter((report) => {
        if (
          report.latitude === null ||
          report.latitude === undefined ||
          report.longitude === null ||
          report.longitude === undefined ||
          report.latitude === "" ||
          report.longitude === ""
        ) {
          return false;
        }

        const lat = Number(report.latitude);
        const lng = Number(report.longitude);

        return (
          Number.isFinite(lat) &&
          Number.isFinite(lng) &&
          lat >= -90 &&
          lat <= 90 &&
          lng >= -180 &&
          lng <= 180
        );
      });

      setReports(validReports);

    } catch (err) {
      console.error("Lake map loading error:", err);

      setError(
        err.response?.data?.detail ||
        "Unable to load pollution reports. Please try again."
      );

    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };


  // -----------------------------------------
  // INITIAL DATA LOAD
  // -----------------------------------------

  useEffect(() => {
    loadReports();
  }, []);


  // -----------------------------------------
  // FILTER REPORTS
  // -----------------------------------------

  const filteredReports = useMemo(() => {
    if (filter === "all") {
      return reports;
    }

    return reports.filter(
      (report) =>
        (report.status || "submitted").toLowerCase() === filter
    );
  }, [reports, filter]);


  // -----------------------------------------
  // REPORT STATISTICS
  // -----------------------------------------

  const submittedCount = reports.filter(
    (report) =>
      (report.status || "submitted").toLowerCase() === "submitted"
  ).length;

  const reviewCount = reports.filter(
    (report) =>
      (report.status || "").toLowerCase() === "under_review"
  ).length;

  const resolvedCount = reports.filter(
    (report) =>
      (report.status || "").toLowerCase() === "resolved"
  ).length;


  // -----------------------------------------
  // LOGOUT
  // -----------------------------------------

  const handleLogout = () => {
    localStorage.removeItem("aquawatch_token");
    localStorage.removeItem("aquawatch_user");

    navigate("/login");
  };


  const closeMenu = () => {
    setMenuOpen(false);
  };


  // -----------------------------------------
  // UI
  // -----------------------------------------

  return (
    <div className="dashboard-page premium-dashboard lake-map-premium">

      {/* MOBILE OVERLAY */}

      {menuOpen && (
        <div
          className="lake-sidebar-overlay"
          onClick={closeMenu}
        />
      )}


      {/* ---------------------------------
          SIDEBAR
      --------------------------------- */}

      <aside
        className={`dashboard-sidebar premium-sidebar ${
          menuOpen ? "open" : ""
        }`}
      >

        <Link
          to="/dashboard"
          className="premium-brand"
          onClick={closeMenu}
        >
          <span className="brand-icon">
            <Waves size={28} />
          </span>

          <span>
            <strong>AquaWatch</strong>
            <small>LAKE MONITORING PLATFORM</small>
          </span>

          <button
            className="mobile-close"
            onClick={(event) => {
              event.preventDefault();
              closeMenu();
            }}
          >
            <X />
          </button>
        </Link>


        <p className="premium-nav-label">
          WORKSPACE
        </p>


        <Link
          to="/dashboard"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <LayoutDashboard size={19} />
          Dashboard
        </Link>


        <Link
          to="/my-reports"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <FileText size={19} />
          My Reports
        </Link>


        <Link
          to="/report"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <Camera size={19} />
          Report Pollution
        </Link>


        <Link
          to="/map"
          className="sidebar-link active"
          onClick={closeMenu}
        >
          <MapPin size={19} />
          Lake Map
        </Link>


        <Link
          to="/water-quality"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <Droplets size={19} />
          Water Quality
        </Link>


        <div className="sidebar-environment-card">
          <Leaf size={23} />

          <strong>Be a Lake Guardian</strong>

          <p>
            Your contribution helps protect our water resources.
          </p>
        </div>


        <button
          className="sidebar-logout"
          onClick={handleLogout}
        >
          <LogOut size={19} />
          Logout
        </button>

      </aside>


      {/* ---------------------------------
          MAIN CONTENT
      --------------------------------- */}

      <main className="dashboard-main premium-main">


        {/* TOPBAR */}

        <header className="premium-topbar">

          <button
            className="mobile-menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu />
          </button>

          <div className="premium-page-title">
            <h2>Lake Pollution Map</h2>
            <p>
              Explore pollution reports across locations
            </p>
          </div>


          <div className="premium-topbar-right">

            <div className="notification-icon">
              <Bell size={19} />
              <span></span>
            </div>


            <div className="premium-user">

              <div className="premium-avatar">
                {user.name?.charAt(0)?.toUpperCase() || "U"}
              </div>

              <div>
                <strong>
                  {user.name || "Citizen"}
                </strong>

                <small>Citizen Account</small>
              </div>

            </div>

          </div>

        </header>


        {/* ---------------------------------
            HERO SECTION
        --------------------------------- */}

        <section className="lake-premium-hero">

          <div>

            <span className="lake-hero-tag">
              <Activity size={14} />
              ENVIRONMENTAL MONITORING
            </span>

            <h1>
              Discover.
              <br />
              <span>Monitor. Protect.</span>
            </h1>

            <p>
              Explore reported pollution locations and understand
              where environmental attention is needed.
            </p>

          </div>


          <div className="lake-hero-icon">

            <MapPin size={43} />

            <strong>Pollution Report Map</strong>

            <small>
              Locations from submitted reports
            </small>

          </div>

        </section>


        {/* ---------------------------------
            STATISTICS
        --------------------------------- */}

        <section className="premium-stats-grid lake-map-stats">


          {/* TOTAL REPORTS */}

          <div className="premium-stat-card stat-blue">

            <div className="premium-stat-icon">
              <MapPin />
            </div>

            <div>
              <span>GEOLOCATED REPORTS</span>

              <h2>
                {loading ? "..." : reports.length}
              </h2>

              <p>Reports with valid GPS</p>
            </div>

          </div>


          {/* SUBMITTED */}

          <div className="premium-stat-card stat-orange">

            <div className="premium-stat-icon">
              <Clock />
            </div>

            <div>
              <span>SUBMITTED</span>

              <h2>
                {loading ? "..." : submittedCount}
              </h2>

              <p>Awaiting review</p>
            </div>

          </div>


          {/* UNDER REVIEW */}

          <div className="premium-stat-card stat-purple">

            <div className="premium-stat-icon">
              <AlertCircle />
            </div>

            <div>
              <span>UNDER REVIEW</span>

              <h2>
                {loading ? "..." : reviewCount}
              </h2>

              <p>Being investigated</p>
            </div>

          </div>


          {/* RESOLVED */}

          <div className="premium-stat-card stat-green">

            <div className="premium-stat-icon">
              <CheckCircle />
            </div>

            <div>
              <span>RESOLVED</span>

              <h2>
                {loading ? "..." : resolvedCount}
              </h2>

              <p>Resolved reports</p>
            </div>

          </div>

        </section>


        {/* ---------------------------------
            MAP SECTION
        --------------------------------- */}

        <section className="premium-section lake-map-section">


          {/* MAP HEADER */}

          <div className="premium-section-heading">

            <div>
              <span>GEOGRAPHICAL VIEW</span>

              <h2>Pollution Locations</h2>

              <p>
                Select a marker to view its pollution report.
              </p>
            </div>


            <button
              className="lake-premium-refresh"
              onClick={() => loadReports(true)}
              disabled={loading || refreshing}
            >

              <RefreshCw
                size={16}
                className={refreshing ? "lake-spin" : ""}
              />

              {refreshing
                ? "Refreshing..."
                : "Refresh Map"
              }

            </button>

          </div>


          {/* ERROR MESSAGE */}

          {error && (
            <div className="lake-premium-error">

              <AlertCircle size={18} />

              {error}

            </div>
          )}


          {/* FILTERS AND LEGEND */}

          <div className="lake-map-toolbar">

            <div className="lake-map-filter-group">

              <label htmlFor="map-status-filter">
                Filter reports
              </label>

              <select
                id="map-status-filter"
                value={filter}
                onChange={(event) =>
                  setFilter(event.target.value)
                }
              >
                <option value="all">All Reports</option>
                <option value="submitted">Submitted</option>
                <option value="under_review">Under Review</option>
                <option value="resolved">Resolved</option>
                <option value="rejected">Rejected</option>
              </select>

            </div>


            {/* MAP LEGEND */}

            <div className="lake-map-legend">

              <span>
                <i className="lake-dot lake-dot-submitted" />
                Submitted
              </span>

              <span>
                <i className="lake-dot lake-dot-review" />
                Under Review
              </span>

              <span>
                <i className="lake-dot lake-dot-resolved" />
                Resolved
              </span>

              <span>
                <i className="lake-dot lake-dot-rejected" />
                Rejected
              </span>

            </div>

          </div>


          {/* ---------------------------------
              MAP DISPLAY
          --------------------------------- */}

          {loading ? (

            <div className="lake-map-state">

              <RefreshCw
                className="lake-spin"
                size={27}
              />

              <h3>Loading pollution locations</h3>

              <p>Retrieving submitted reports...</p>

            </div>

          ) : (

            <div className="lake-premium-map-container">

              <MapContainer
                center={[20.5937, 78.9629]}
                zoom={5}
                scrollWheelZoom={true}
                className="lake-premium-map"
              >

                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />


                {/* Fix map dimensions */}

                <RefreshMapSize />


                {/* Zoom to report locations */}

                <FitMapToReports
                  reports={filteredReports}
                />


                {/* REPORT MARKERS */}

                {filteredReports.map((report) => {

                  const status = (
                    report.status || "submitted"
                  ).toLowerCase();

                  const markerColor =
                    status === "resolved"
                      ? "#22c55e"
                      : status === "under_review"
                      ? "#38bdf8"
                      : status === "rejected"
                      ? "#a78bfa"
                      : "#ef4444";


                  return (

                    <CircleMarker
                      key={report.id || report._id}
                      center={[
                        Number(report.latitude),
                        Number(report.longitude)
                      ]}
                      radius={9}
                      pathOptions={{
                        color: markerColor,
                        fillColor: markerColor,
                        fillOpacity: 0.85,
                        weight: 2
                      }}
                    >

                      <Popup>

                        <strong>
                          {report.lake_name || "Unknown Lake"}
                        </strong>

                        <br />

                        Status: {status.replace(/_/g, " ")}

                        <br />

                        {report.description || "No description"}

                        <br />

                        <small>
                          Latitude:{" "}
                          {Number(report.latitude).toFixed(5)}

                          <br />

                          Longitude:{" "}
                          {Number(report.longitude).toFixed(5)}
                        </small>

                      </Popup>

                    </CircleMarker>

                  );

                })}

              </MapContainer>

            </div>

          )}


          {/* ---------------------------------
              EMPTY STATE
          --------------------------------- */}

          {!loading && !error && filteredReports.length === 0 && (

            <div className="lake-map-state lake-map-empty">

              <MapPin size={32} />

              <h3>No reports found</h3>

              <p>
                No pollution reports match the selected filter.
              </p>

            </div>

          )}


          {/* REPORT COUNT */}

          {!loading && filteredReports.length > 0 && (

            <div className="lake-map-result-count">

              Showing {filteredReports.length} report location(s)

            </div>

          )}

        </section>


        {/* FOOTER */}

        <footer className="premium-footer">
          AquaWatch © 2026 · Protecting lakes, preserving life.
        </footer>

      </main>

    </div>
  );
}


export default LakeMap;
