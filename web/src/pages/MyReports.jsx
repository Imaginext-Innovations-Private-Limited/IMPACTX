
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

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
  Clock,
  CheckCircle,
  RefreshCw,
  AlertCircle,
  CalendarDays,
  Activity,
  Plus,
  Leaf
} from "lucide-react";

import { getMyReports } from "../services/reportService";


const API_BASE_URL = "http://127.0.0.1:8000";


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


function formatDate(date) {
  if (!date) return "Date unavailable";

  const parsed = new Date(date);

  if (Number.isNaN(parsed.getTime())) {
    return "Date unavailable";
  }

  return parsed.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}


function getStatusClass(status) {
  const value = (status || "submitted").toLowerCase();

  if (value === "resolved") return "mr-status-resolved";
  if (value === "rejected") return "mr-status-rejected";
  if (value === "under_review") return "mr-status-review";

  return "mr-status-submitted";
}


function MyReports() {
  const navigate = useNavigate();

  const [menuOpen, setMenuOpen] = useState(false);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");

  const user = JSON.parse(
    localStorage.getItem("aquawatch_user") || "{}"
  );


  // Fetch citizen reports
  const fetchReports = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const data = await getMyReports();

      const list = Array.isArray(data)
        ? data
        : data.reports || [];

      setReports(list);

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to load your reports. Please try again."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };


  useEffect(() => {
    fetchReports();
  }, []);


  // Report statistics
  const totalReports = reports.length;

  const resolvedReports = reports.filter(
    (report) => report.status?.toLowerCase() === "resolved"
  ).length;

  const reviewReports = reports.filter(
    (report) => report.status?.toLowerCase() === "under_review"
  ).length;

  const pendingReports = reports.filter(
    (report) =>
      !["resolved", "rejected"].includes(
        report.status?.toLowerCase()
      )
  ).length;

  const reportedLakes = new Set(
    reports.map((report) => report.lake_name).filter(Boolean)
  ).size;


  // Filter reports
  const filteredReports = useMemo(() => {
    return [...reports]
      .filter((report) => {
        if (filter === "all") return true;

        return report.status?.toLowerCase() === filter;
      })
      .sort(
        (a, b) =>
          new Date(b.created_at || 0) -
          new Date(a.created_at || 0)
      );
  }, [reports, filter]);


  const handleLogout = () => {
    localStorage.removeItem("aquawatch_token");
    localStorage.removeItem("aquawatch_user");
    navigate("/login");
  };


  const closeMenu = () => setMenuOpen(false);


  return (
    <div className="dashboard-page premium-dashboard myreports-page">

      {/* MOBILE OVERLAY */}
      {menuOpen && (
        <div
          className="mr-sidebar-overlay"
          onClick={closeMenu}
        />
      )}


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
          className="sidebar-link"
          onClick={closeMenu}
        >
          <LayoutDashboard size={19} />
          Dashboard
        </Link>


        <Link
          to="/my-reports"
          className="sidebar-link active"
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

        {/* TOPBAR */}
        <header className="premium-topbar">

          <button
            className="mobile-menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu />
          </button>

          <div className="premium-page-title">
            <h2>My Pollution Reports</h2>
            <p>Track and manage your submitted reports</p>
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


        {/* PAGE HERO */}
        <section className="mr-hero">

          <div className="mr-hero-content">

            <div className="mr-hero-tag">
              <Activity size={14} />
              CITIZEN ACTIVITY
            </div>

            <h1>
              Your Reports.
              <br />
              <span>Your Impact.</span>
            </h1>

            <p>
              Every pollution report helps identify environmental
              problems and supports cleaner lakes.
            </p>

            <Link
              to="/report"
              className="premium-primary-btn"
            >
              <Camera size={18} />
              Submit New Report
              <Plus size={17} />
            </Link>

          </div>

          <div className="mr-hero-decoration">
            <div className="mr-hero-icon">
              <FileText size={32} />
            </div>
            <strong>AquaWatch</strong>
            <small>Your environmental contribution matters</small>
          </div>

        </section>


        {/* STATISTICS */}
        <section className="premium-stats-grid mr-stats-grid">

          <div className="premium-stat-card stat-blue">
            <div className="premium-stat-icon">
              <FileText />
            </div>

            <div>
              <span>TOTAL REPORTS</span>
              <h2>{loading ? "..." : totalReports}</h2>
              <p>All submitted reports</p>
            </div>
          </div>


          <div className="premium-stat-card stat-orange">
            <div className="premium-stat-icon">
              <Clock />
            </div>

            <div>
              <span>PENDING REPORTS</span>
              <h2>{loading ? "..." : pendingReports}</h2>
              <p>Awaiting action</p>
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
          <div className="mr-error">
            <AlertCircle size={19} />
            {error}
          </div>
        )}


        {/* REPORT SECTION */}
        <section className="premium-section mr-reports-section">

          <div className="premium-section-heading">

            <div>
              <span>YOUR ACTIVITY</span>
              <h2>Submitted Reports</h2>
            </div>

            <button
              className="mr-refresh-btn"
              onClick={() => fetchReports(true)}
              disabled={refreshing}
            >
              <RefreshCw
                size={16}
                className={refreshing ? "mr-spinning" : ""}
              />
              {refreshing ? "Refreshing..." : "Refresh Reports"}
            </button>

          </div>


          {/* FILTERS */}
          <div className="mr-filter-bar">

            <button
              className={filter === "all" ? "active" : ""}
              onClick={() => setFilter("all")}
            >
              All Reports
              <span>{totalReports}</span>
            </button>

            <button
              className={filter === "submitted" ? "active" : ""}
              onClick={() => setFilter("submitted")}
            >
              Submitted
            </button>

            <button
              className={filter === "under_review" ? "active" : ""}
              onClick={() => setFilter("under_review")}
            >
              Under Review
              <span>{reviewReports}</span>
            </button>

            <button
              className={filter === "resolved" ? "active" : ""}
              onClick={() => setFilter("resolved")}
            >
              Resolved
            </button>

            <button
              className={filter === "rejected" ? "active" : ""}
              onClick={() => setFilter("rejected")}
            >
              Rejected
            </button>

          </div>


          {/* LOADING */}
          {loading && (
            <div className="mr-state">
              <RefreshCw className="mr-spinning" size={28} />
              <h3>Loading your reports</h3>
              <p>Please wait while we retrieve your activity.</p>
            </div>
          )}


          {/* EMPTY STATE */}
          {!loading && !error && filteredReports.length === 0 && (
            <div className="mr-state">

              <div className="mr-empty-icon">
                <FileText size={35} />
              </div>

              <h3>
                {reports.length === 0
                  ? "No reports submitted yet"
                  : "No reports found"}
              </h3>

              <p>
                {reports.length === 0
                  ? "Start contributing towards cleaner lakes by submitting your first report."
                  : "Try selecting another status filter."}
              </p>

              {reports.length === 0 && (
                <Link
                  to="/report"
                  className="premium-primary-btn"
                >
                  <Camera size={17} />
                  Report Pollution
                </Link>
              )}

            </div>
          )}


          {/* REPORT CARDS */}
          {!loading && filteredReports.length > 0 && (

            <div className="mr-report-grid">

              {filteredReports.map((report, index) => {

                const photoUrl = getPhotoUrl(report.photo_url);

                const status = report.status || "submitted";

                return (

                  <article
                    className="mr-report-card"
                    key={report._id || report.id || index}
                  >

                    {/* PHOTO */}
                    <div className="mr-report-image">

                      {photoUrl ? (
                        <img
                          src={photoUrl}
                          alt={`Pollution at ${report.lake_name || "lake"}`}
                          loading="lazy"
                          onError={(e) => {
                            e.currentTarget.style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="mr-no-image">
                          <Waves size={38} />
                          <span>No photo available</span>
                        </div>
                      )}

                      <span className={`mr-status ${getStatusClass(status)}`}>
                        {status.replaceAll("_", " ")}
                      </span>

                    </div>


                    {/* REPORT DETAILS */}
                    <div className="mr-report-body">

                      <div className="mr-report-title-row">
                        <div>
                          <span className="mr-card-label">
                            POLLUTION REPORT
                          </span>

                          <h3>
                            {report.lake_name || "Unnamed Lake"}
                          </h3>
                        </div>
                      </div>


                      <p className="mr-description">
                        {report.description || "No description provided."}
                      </p>


                      <div className="mr-report-details">

                        <div>
                          <MapPin size={15} />
                          <span>
                            {report.latitude != null && report.longitude != null
                              ? `${report.latitude}, ${report.longitude}`
                              : "Location not specified"}
                          </span>
                        </div>

                        <div>
                          <CalendarDays size={15} />
                          <span>{formatDate(report.created_at)}</span>
                        </div>

                        <div>
                          <Droplets size={15} />
                          <span>
                            {report.pollution_type || "Not specified"}
                          </span>
                        </div>

                        <div>
                          <Activity size={15} />
                          <span>AI analysis completed</span>
                        </div>

                      </div>


                      <div className="mr-report-footer">
                        <span>
                          Report ID: {(report._id || report.id || "N/A").toString().slice(-12)}
                        </span>
                      </div>

                    </div>

                  </article>

                );

              })}

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

export default MyReports;
