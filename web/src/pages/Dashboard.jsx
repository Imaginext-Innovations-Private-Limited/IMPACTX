
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  Waves,
  Droplets,
  LayoutDashboard,
  FileText,
  Clock,
  CheckCircle,
  MapPin,
  Camera,
  LogOut,
  Menu,
  X,
  ArrowUpRight,
  Bell,
  ShieldCheck,
  Leaf,
  Activity
} from "lucide-react";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import { getMyReports } from "../services/reportService";

const API_BASE_URL = "http://127.0.0.1:8000";

// Convert uploaded photo path into a usable URL
function getPhotoUrl(photoUrl) {
  if (!photoUrl) return null;

  if (
    photoUrl.startsWith("http://") ||
    photoUrl.startsWith("https://")
  ) {
    return photoUrl;
  }

  return `${API_BASE_URL}/${photoUrl.replace(/^\/+/, "")}`;
}

function Dashboard() {
  const navigate = useNavigate();

  const [menuOpen, setMenuOpen] = useState(false);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const user = JSON.parse(
    localStorage.getItem("aquawatch_user") || "{}"
  );

  // Fetch reports from backend
  useEffect(() => {
    const fetchReports = async () => {
      try {
        const data = await getMyReports();

        const list = Array.isArray(data)
          ? data
          : data.reports || [];

        setReports(list);
      } catch (err) {
        setError(
          err.response?.data?.detail ||
          "Unable to load your reports."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, []);

  // Dashboard statistics
  const totalReports = reports.length;

  const resolvedReports = reports.filter(
    (r) => r.status?.toLowerCase() === "resolved"
  ).length;

  const pendingReports = totalReports - resolvedReports;

  const reportedLakes = new Set(
    reports.map((r) => r.lake_name).filter(Boolean)
  ).size;

  const resolutionRate = totalReports
    ? Math.round((resolvedReports / totalReports) * 100)
    : 0;

  // Sort and display latest three reports
  const recentReports = [...reports]
    .sort(
      (a, b) =>
        new Date(b.created_at || 0) -
        new Date(a.created_at || 0)
    )
    .slice(0, 3);

  // Keep only reports with valid GPS coordinates
  const mapReports = reports.filter((report) => {
    if (
      report.latitude === null ||
      report.latitude === undefined ||
      report.latitude === "" ||
      report.longitude === null ||
      report.longitude === undefined ||
      report.longitude === ""
    ) {
      return false;
    }

    const lat = Number(report.latitude);
    const lng = Number(report.longitude);

    return (
      Number.isFinite(lat) &&
      lat >= -90 &&
      lat <= 90 &&
      Number.isFinite(lng) &&
      lng >= -180 &&
      lng <= 180
    );
  });

  // Calculate center of reported GPS locations
  const mapCenter = mapReports.length
    ? [
        mapReports.reduce(
          (sum, report) => sum + Number(report.latitude),
          0
        ) / mapReports.length,

        mapReports.reduce(
          (sum, report) => sum + Number(report.longitude),
          0
        ) / mapReports.length
      ]
    : null;

  // Logout
  const handleLogout = () => {
    localStorage.removeItem("aquawatch_token");
    localStorage.removeItem("aquawatch_user");
    navigate("/login");
  };

  const closeMenu = () => setMenuOpen(false);

  // Format date
  const formatDate = (date) => {
    if (!date) return "Date unavailable";

    const parsed = new Date(date);

    return Number.isNaN(parsed.getTime())
      ? "Date unavailable"
      : parsed.toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric"
        });
  };

  return (
    <div className="dashboard-page premium-dashboard">

      {/* SIDEBAR */}
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
            onClick={(e) => {
              e.preventDefault();
              closeMenu();
            }}
          >
            <X />
          </button>
        </Link>

        <p className="premium-nav-label">WORKSPACE</p>

        <Link
          to="/dashboard"
          className="sidebar-link active"
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
          className="sidebar-link"
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

      {/* MAIN CONTENT */}
      <main className="dashboard-main premium-main">

        {/* TOP BAR */}
        <header className="premium-topbar">

          <button
            className="mobile-menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu />
          </button>

          <div className="premium-page-title">
            <h2>Citizen Dashboard</h2>
            <p>Monitor and protect our lakes</p>
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
                <strong>{user.name || "Citizen"}</strong>
                <small>Citizen Account</small>
              </div>
            </div>

          </div>

        </header>

        {/* LAKE HERO */}
        <section className="premium-lake-hero">

          <div className="premium-hero-overlay"></div>

          <div className="premium-hero-content">

            <div className="premium-hero-tag">
              <Activity size={14} />
              AI POWERED ENVIRONMENTAL MONITORING
            </div>

            <h1>
              Protect Our Lakes.
              <br />
              <span>Preserve Our Future.</span>
            </h1>

            <p>
              Welcome back, {user.name || "Citizen"}!
              Monitor lake pollution, explore water quality
              and contribute towards a cleaner environment.
            </p>

            <div className="premium-hero-actions">

              <Link
                to="/report"
                className="premium-primary-btn"
              >
                <Camera size={18} />
                Report Pollution
                <ArrowUpRight size={17} />
              </Link>

              <Link
                to="/map"
                className="premium-outline-btn"
              >
                <MapPin size={18} />
                Explore Lakes
              </Link>

            </div>

            <div className="premium-hero-note">
              <ShieldCheck size={17} />
              Every report makes a difference
            </div>

          </div>

          <div className="premium-monitor-card">

            <div className="monitor-icon">
              <Droplets size={23} />
            </div>

            <div>
              <strong>AquaWatch</strong>
              <small>Monitoring our lakes</small>
            </div>

            <span className="monitor-dot"></span>

          </div>

        </section>

        {/* STATISTICS */}
        <section className="premium-stats-grid">

          <div className="premium-stat-card stat-blue">
            <div className="premium-stat-icon">
              <FileText />
            </div>

            <div>
              <span>MY REPORTS</span>
              <h2>{loading ? "..." : totalReports}</h2>
              <p>Total submitted reports</p>
            </div>
          </div>

          <div className="premium-stat-card stat-orange">
            <div className="premium-stat-icon">
              <Clock />
            </div>

            <div>
              <span>PENDING REPORTS</span>
              <h2>{loading ? "..." : pendingReports}</h2>
              <p>Awaiting resolution</p>
            </div>
          </div>

          <div className="premium-stat-card stat-green">
            <div className="premium-stat-icon">
              <CheckCircle />
            </div>

            <div>
              <span>RESOLVED REPORTS</span>
              <h2>{loading ? "..." : resolvedReports}</h2>
              <p>Successfully resolved</p>
            </div>
          </div>

          <div className="premium-stat-card stat-purple">
            <div className="premium-stat-icon">
              <MapPin />
            </div>

            <div>
              <span>LAKES REPORTED</span>
              <h2>{loading ? "..." : reportedLakes}</h2>
              <p>Unique lake locations</p>
            </div>
          </div>

        </section>

        {/* ERROR */}
        {error && (
          <p className="form-message">{error}</p>
        )}

        {/* QUICK ACTIONS */}
        <section className="premium-section">

          <div className="premium-section-heading">

            <div>
              <span>GET INVOLVED</span>
              <h2>Explore AquaWatch</h2>
            </div>

            <p>
              Everything you need to monitor and protect our lakes.
            </p>

          </div>

          <div className="premium-actions-grid">

            <Link
              to="/report"
              className="premium-action-card"
            >
              <div className="premium-action-icon">
                <Camera />
              </div>

              <div>
                <h3>Report Pollution</h3>
                <p>Upload a photo and report lake pollution.</p>
              </div>

              <ArrowUpRight className="premium-action-arrow" />
            </Link>

            <Link
              to="/my-reports"
              className="premium-action-card"
            >
              <div className="premium-action-icon">
                <FileText />
              </div>

              <div>
                <h3>My Reports</h3>
                <p>View and track your submitted reports.</p>
              </div>

              <ArrowUpRight className="premium-action-arrow" />
            </Link>

            <Link
              to="/map"
              className="premium-action-card"
            >
              <div className="premium-action-icon">
                <MapPin />
              </div>

              <div>
                <h3>Explore Lake Map</h3>
                <p>Explore lake locations and pollution hotspots.</p>
              </div>

              <ArrowUpRight className="premium-action-arrow" />
            </Link>

            <Link
              to="/water-quality"
              className="premium-action-card"
            >
              <div className="premium-action-icon">
                <Droplets />
              </div>

              <div>
                <h3>Water Quality</h3>
                <p>Explore historical lake water-quality readings.</p>
              </div>

              <ArrowUpRight className="premium-action-arrow" />
            </Link>

          </div>

        </section>

        {/* LOWER DASHBOARD */}
        <section className="premium-lower-grid">

          {/* RECENT REPORTS */}
          <div className="premium-panel recent-panel">

            <div className="premium-panel-heading">

              <h3>
                <FileText size={18} />
                Recent Reports
              </h3>

              <Link to="/my-reports">
                View All
                <ArrowUpRight size={15} />
              </Link>

            </div>

            {loading ? (

              <p className="premium-empty">
                Loading your reports...
              </p>

            ) : recentReports.length === 0 ? (

              <div className="premium-empty">
                <FileText size={27} />
                <p>No reports submitted yet.</p>
                <Link to="/report">
                  Submit your first report
                </Link>
              </div>

            ) : (

              <div className="premium-report-list">

                {recentReports.map((report, index) => {

                  const photoUrl = getPhotoUrl(report.photo_url);

                  const isResolved =
                    report.status?.toLowerCase() === "resolved";

                  return (
                    <div
                      className="premium-report-row"
                      key={report._id || report.id || index}
                    >

                      <div className="report-thumbnail">

                        <Waves
                          className="report-thumbnail-fallback"
                          size={22}
                        />

                        {photoUrl && (
                          <img
                            src={photoUrl}
                            alt={`Pollution at ${report.lake_name || "lake"}`}
                            loading="lazy"
                            onError={(e) => {
                              e.currentTarget.style.display = "none";
                            }}
                          />
                        )}

                      </div>

                      <div className="report-row-info">

                        <strong>
                          {report.lake_name || "Unnamed lake"}
                        </strong>

                        <small>
                          Reported on {formatDate(report.created_at)}
                        </small>

                      </div>

                      <span
                        className={`premium-status ${
                          isResolved
                            ? "status-resolved"
                            : "status-pending"
                        }`}
                      >
                        {report.status || "Submitted"}
                      </span>

                    </div>
                  );
                })}

              </div>

            )}

          </div>

          {/* RESOLUTION PROGRESS */}
          <div className="premium-panel progress-panel">

            <div className="premium-panel-heading">
              <h3>
                <Activity size={18} />
                Resolution Progress
              </h3>
            </div>

            <div className="progress-content">

              <div
                className="progress-ring"
                style={{
                  "--progress": `${resolutionRate}%`
                }}
              >

                <div>
                  <strong>
                    {loading ? "..." : `${resolutionRate}%`}
                  </strong>
                  <small>Resolved</small>
                </div>

              </div>

              <div className="progress-legend">

                <p>
                  <span className="legend-green"></span>
                  Resolved ({loading ? "..." : resolvedReports})
                </p>

                <p>
                  <span className="legend-orange"></span>
                  Pending ({loading ? "..." : pendingReports})
                </p>

              </div>

            </div>

          </div>

          {/* INTERACTIVE REPORTED LAKES MAP */}
          <div className="premium-panel lake-summary-panel">

            <div className="premium-panel-heading">

              <h3>
                <MapPin size={18} />
                Reported Lakes
              </h3>

              <Link to="/map">
                Explore
                <ArrowUpRight size={15} />
              </Link>

            </div>

            <div className="lake-map-preview">

              {loading ? (

                <div className="map-empty-state">
                  Loading lake locations...
                </div>

              ) : mapReports.length === 0 ? (

                <div className="map-empty-state">
                  <MapPin size={30} />
                  <strong>No GPS locations available</strong>
                  <span>
                    Submit a report with a selected lake location
                    to see it here.
                  </span>
                </div>

              ) : (

                <MapContainer
                  key={`${mapCenter[0]}-${mapCenter[1]}`}
                  center={mapCenter}
                  zoom={mapReports.length > 1 ? 7 : 12}
                  scrollWheelZoom={false}
                  className="dashboard-leaflet-map"
                >

                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  {mapReports.map((report, index) => (

                    <CircleMarker
                      key={report._id || report.id || index}
                      center={[
                        Number(report.latitude),
                        Number(report.longitude)
                      ]}
                      radius={9}
                      pathOptions={{
                        color: "#a5fff0",
                        fillColor: "#00cdb7",
                        fillOpacity: 0.9,
                        weight: 3
                      }}
                    >

                      <Popup>
                        <div>
                          <strong>
                            {report.lake_name || "Unnamed lake"}
                          </strong>

                          <br />

                          Reported: {formatDate(report.created_at)}

                          <br />

                          Status: {report.status || "Submitted"}
                        </div>
                      </Popup>

                    </CircleMarker>

                  ))}

                </MapContainer>

              )}

            </div>

            <div className="lake-map-footer">

              <span>
                <span className="map-marker-dot"></span>
                {loading
                  ? "Loading..."
                  : `${mapReports.length} mapped report locations`}
              </span>

              <Link to="/map">
                Open full map →
              </Link>

            </div>

          </div>

        </section>

        {/* FOOTER */}
        <footer className="premium-footer">
          © 2026 AquaWatch · Protect Our Lakes, Preserve Our Future.
        </footer>

      </main>

      {menuOpen && (
        <div
          className="dashboard-overlay"
          onClick={closeMenu}
        ></div>
      )}

    </div>
  );
}

export default Dashboard;
