
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  Waves,
  LayoutDashboard,
  FileText,
  Users,
  Clock,
  CheckCircle,
  XCircle,
  MapPin,
  Menu,
  X,
  LogOut,
  ArrowUpRight,
  Bell,
  ShieldCheck,
  Activity,
  Camera,
  RefreshCw,
  AlertTriangle,
  Calendar,
  Droplets
} from "lucide-react";

import {
  getAllReports,
  getAdminStats,
  updateReportStatus
} from "../services/reportService";

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

  return Number.isNaN(parsed.getTime())
    ? "Date unavailable"
    : parsed.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric"
      });
}

function AdminDashboard() {
  const navigate = useNavigate();

  const [menuOpen, setMenuOpen] = useState(false);
  const [reports, setReports] = useState([]);
  const [stats, setStats] = useState({
    total_reports: 0,
    submitted: 0,
    under_review: 0,
    resolved: 0,
    rejected: 0,
    total_citizens: 0
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [updatingId, setUpdatingId] = useState(null);

  const user = JSON.parse(
    localStorage.getItem("aquawatch_user") || "{}"
  );

  const closeMenu = () => setMenuOpen(false);

  // Load Admin dashboard data
  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const [reportData, statsData] = await Promise.all([
        getAllReports(),
        getAdminStats()
      ]);

      setReports(reportData.reports || []);
      setStats(statsData);

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to load Admin dashboard."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  // Update report status
  const handleStatusChange = async (reportId, newStatus) => {
    try {
      setUpdatingId(reportId);
      setError("");

      await updateReportStatus(reportId, newStatus);

      await loadDashboard();

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to update report status."
      );
    } finally {
      setUpdatingId(null);
    }
  };

  // Logout
  const handleLogout = () => {
    localStorage.removeItem("aquawatch_token");
    localStorage.removeItem("aquawatch_user");

    navigate("/login", { replace: true });
  };

  // Filter reports
  const filteredReports = reports.filter((report) => {
    if (filter === "all") return true;
    return report.status === filter;
  });

  // Statistics
  const statCards = [
    {
      title: "TOTAL REPORTS",
      value: stats.total_reports,
      description: "All citizen submissions",
      icon: FileText,
      color: "stat-blue"
    },
    {
      title: "SUBMITTED",
      value: stats.submitted,
      description: "New pollution reports",
      icon: AlertTriangle,
      color: "stat-orange"
    },
    {
      title: "UNDER REVIEW",
      value: stats.under_review,
      description: "Currently being reviewed",
      icon: Clock,
      color: "stat-purple"
    },
    {
      title: "RESOLVED",
      value: stats.resolved,
      description: "Successfully addressed",
      icon: CheckCircle,
      color: "stat-green"
    },
    {
      title: "REJECTED",
      value: stats.rejected,
      description: "Rejected submissions",
      icon: XCircle,
      color: "stat-orange"
    },
    {
      title: "REGISTERED CITIZENS",
      value: stats.total_citizens,
      description: "Platform citizen accounts",
      icon: Users,
      color: "stat-purple"
    }
  ];

  const pendingReports =
    stats.submitted + stats.under_review;

  const resolutionRate = stats.total_reports
    ? Math.round(
        (stats.resolved / stats.total_reports) * 100
      )
    : 0;

  const recentReports = [...reports]
    .sort(
      (a, b) =>
        new Date(b.created_at || 0) -
        new Date(a.created_at || 0)
    )
    .slice(0, 5);

  return (
    <div className="dashboard-page premium-dashboard admin-dashboard">

      {/* SIDEBAR */}
      <aside
        className={`dashboard-sidebar premium-sidebar ${
          menuOpen ? "open" : ""
        }`}
      >

        <Link
          to="/admin"
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

        <p className="premium-nav-label">ADMIN WORKSPACE</p>

        <Link
          to="/admin"
          className="sidebar-link active"
          onClick={closeMenu}
        >
          <LayoutDashboard size={19} />
          Dashboard
        </Link>

        <a
          href="#admin-reports"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <FileText size={19} />
          Manage Reports
        </a>

        <a
          href="#admin-overview"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <Users size={19} />
          Citizens
        </a>

        <a
          href="#admin-activity"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <Activity size={19} />
          Activity
        </a>

        <div className="sidebar-environment-card">
          <ShieldCheck size={23} />

          <strong>Lake Authority</strong>

          <p>
            Monitor citizen reports and support lake protection activities.
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
            <h2>Admin Dashboard</h2>
            <p>Manage reports and monitor lake protection</p>
          </div>

          <div className="premium-topbar-right">

            <div className="notification-icon">
              <Bell size={19} />
              <span></span>
            </div>

            <div className="premium-user">
              <div className="premium-avatar">
                {user.name?.charAt(0)?.toUpperCase() || "A"}
              </div>

              <div>
                <strong>{user.name || "Administrator"}</strong>
                <small>Admin Account</small>
              </div>
            </div>

          </div>

        </header>

        {/* ADMIN HERO */}
        <section className="premium-lake-hero admin-hero">

          <div className="premium-hero-overlay"></div>

          <div className="premium-hero-content">

            <div className="premium-hero-tag">
              <ShieldCheck size={14} />
              AQUAWATCH ADMINISTRATION
            </div>

            <h1>
              Protect Our Lakes.
              <br />
              <span>Manage. Monitor. Act.</span>
            </h1>

            <p>
              Welcome, {user.name || "Administrator"}!
              Review citizen pollution reports, monitor
              environmental activities and track report resolution.
            </p>

            <div className="premium-hero-actions">

              <a
                href="#admin-reports"
                className="premium-primary-btn"
              >
                <FileText size={18} />
                Manage Reports
                <ArrowUpRight size={17} />
              </a>

              <button
                className="premium-outline-btn admin-refresh-btn"
                onClick={loadDashboard}
                disabled={loading}
              >
                <RefreshCw
                  size={17}
                  className={loading ? "admin-spin" : ""}
                />
                Refresh Data
              </button>

            </div>

            <div className="premium-hero-note">
              <ShieldCheck size={17} />
              Every verified report supports lake protection
            </div>

          </div>

          <div className="premium-monitor-card">

            <div className="monitor-icon">
              <Droplets size={23} />
            </div>

            <div>
              <strong>AquaWatch Authority</strong>
              <small>Environmental monitoring</small>
            </div>

            <span className="monitor-dot"></span>

          </div>

        </section>

        {/* ERROR */}
        {error && (
          <div className="admin-error-message">
            <AlertTriangle size={18} />
            <span>{error}</span>

            <button onClick={loadDashboard}>
              Retry
            </button>
          </div>
        )}

        {/* STATISTICS */}
        <section
          className="premium-stats-grid admin-stats-grid"
          id="admin-overview"
        >

          {statCards.map((card) => {
            const Icon = card.icon;

            return (
              <div
                className={`premium-stat-card ${card.color}`}
                key={card.title}
              >
                <div className="premium-stat-icon">
                  <Icon />
                </div>

                <div>
                  <span>{card.title}</span>

                  <h2>
                    {loading ? "..." : card.value ?? 0}
                  </h2>

                  <p>{card.description}</p>
                </div>
              </div>
            );
          })}

        </section>

        {/* ADMIN ACTIONS */}
        <section className="premium-section">

          <div className="premium-section-heading">
            <div>
              <span>ADMINISTRATION</span>
              <h2>Manage AquaWatch</h2>
            </div>

            <p>
              Monitor submissions and review environmental reports.
            </p>
          </div>

          <div className="premium-actions-grid">

            <a
              href="#admin-reports"
              className="premium-action-card"
            >
              <div className="premium-action-icon">
                <FileText />
              </div>

              <div>
                <h3>Review Reports</h3>
                <p>View and verify citizen pollution submissions.</p>
              </div>

              <ArrowUpRight className="premium-action-arrow" />
            </a>

            <a
              href="#admin-overview"
              className="premium-action-card"
            >
              <div className="premium-action-icon">
                <Users />
              </div>

              <div>
                <h3>Citizen Overview</h3>
                <p>Monitor registered citizen accounts and activity.</p>
              </div>

              <ArrowUpRight className="premium-action-arrow" />
            </a>

            <a
              href="#admin-activity"
              className="premium-action-card"
            >
              <div className="premium-action-icon">
                <Activity />
              </div>

              <div>
                <h3>Resolution Progress</h3>
                <p>Track submitted, pending and resolved reports.</p>
              </div>

              <ArrowUpRight className="premium-action-arrow" />
            </a>

          </div>

        </section>

        {/* REPORT MANAGEMENT */}
        <section
          className="premium-section"
          id="admin-reports"
        >

          <div className="premium-section-heading">
            <div>
              <span>REPORT MANAGEMENT</span>
              <h2>Citizen Pollution Reports</h2>
            </div>

            <p>
              Review reports and update their status.
            </p>
          </div>

          <div className="premium-panel admin-report-panel">

            <div className="premium-panel-heading">

              <h3>
                <FileText size={18} />
                All Submitted Reports
              </h3>

              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="admin-filter"
              >
                <option value="all">All Reports</option>
                <option value="submitted">Submitted</option>
                <option value="under_review">Under Review</option>
                <option value="resolved">Resolved</option>
                <option value="rejected">Rejected</option>
              </select>

            </div>

            {loading ? (

              <div className="admin-empty">
                <RefreshCw className="admin-spin" size={25} />
                <p>Loading citizen reports...</p>
              </div>

            ) : filteredReports.length === 0 ? (

              <div className="admin-empty">
                <FileText size={30} />
                <strong>No reports found</strong>
                <p>There are no reports in this category.</p>
              </div>

            ) : (

              <div className="admin-report-list">

                {filteredReports.map((report, index) => {
                  const photoUrl = getPhotoUrl(report.photo_url);

                  return (
                    <article
                      className="admin-report-item"
                      key={report.id || index}
                    >

                      <div className="admin-report-photo">

                        {photoUrl ? (
                          <img
                            src={photoUrl}
                            alt={`Pollution at ${report.lake_name || "lake"}`}
                            loading="lazy"
                          />
                        ) : (
                          <div className="admin-photo-fallback">
                            <Camera size={25} />
                            <small>No Photo</small>
                          </div>
                        )}

                      </div>

                      <div className="admin-report-information">

                        <div className="admin-report-heading">

                          <div>
                            <h3>
                              {report.lake_name || "Unnamed Lake"}
                            </h3>

                            <span
                              className={`admin-status status-${report.status || "submitted"}`}
                            >
                              {(report.status || "submitted").replace("_", " ")}
                            </span>
                          </div>

                          <small className="admin-report-date">
                            <Calendar size={14} />
                            {formatDate(report.created_at)}
                          </small>

                        </div>

                        <p className="admin-description">
                          {report.description || "No description provided."}
                        </p>

                        <div className="admin-report-meta">

                          <span>
                            <Users size={15} />
                            {report.user_name || "Unknown Citizen"}
                          </span>

                          <span>
                            <MapPin size={15} />
                            {report.latitude != null && report.longitude != null
                              ? `${report.latitude}, ${report.longitude}`
                              : "GPS unavailable"}
                          </span>

                          <span>
                            <AlertTriangle size={15} />
                            {report.pollution_type || "Unspecified"}
                          </span>

                        </div>

                        {report.detection_id && (
                          <div className="admin-ai-linked">
                            <ShieldCheck size={15} />
                            AI detection linked to this report
                          </div>
                        )}

                        <div className="admin-report-controls">

                          <label htmlFor={`status-${report.id}`}>
                            Update report status
                          </label>

                          <select
                            id={`status-${report.id}`}
                            value={report.status || "submitted"}
                            disabled={updatingId === report.id}
                            onChange={(e) =>
                              handleStatusChange(
                                report.id,
                                e.target.value
                              )
                            }
                          >
                            <option value="submitted" disabled>
                              Submitted
                            </option>

                            <option value="under_review">
                              Under Review
                            </option>

                            <option value="resolved">
                              Resolved
                            </option>

                            <option value="rejected">
                              Rejected
                            </option>
                          </select>

                          {updatingId === report.id && (
                            <small>Updating...</small>
                          )}

                        </div>

                      </div>

                    </article>
                  );
                })}

              </div>

            )}

          </div>

        </section>

        {/* ACTIVITY AND RESOLUTION */}
        <section
          className="premium-lower-grid admin-lower-grid"
          id="admin-activity"
        >

          <div className="premium-panel">

            <div className="premium-panel-heading">
              <h3>
                <Activity size={18} />
                Resolution Progress
              </h3>
            </div>

            <div className="admin-progress-content">

              <div
                className="admin-progress-ring"
                style={{
                  "--admin-progress": `${resolutionRate}%`
                }}
              >
                <div>
                  <strong>
                    {loading ? "..." : `${resolutionRate}%`}
                  </strong>
                  <small>Resolved</small>
                </div>
              </div>

              <div className="admin-progress-details">
                <p>
                  <span className="admin-dot green"></span>
                  Resolved: {loading ? "..." : stats.resolved}
                </p>

                <p>
                  <span className="admin-dot orange"></span>
                  Pending: {loading ? "..." : pendingReports}
                </p>

                <p>
                  <span className="admin-dot red"></span>
                  Rejected: {loading ? "..." : stats.rejected}
                </p>
              </div>

            </div>

          </div>

          <div className="premium-panel">

            <div className="premium-panel-heading">
              <h3>
                <Clock size={18} />
                Recent Activity
              </h3>

              <a href="#admin-reports">
                View All
                <ArrowUpRight size={15} />
              </a>
            </div>

            {loading ? (
              <div className="admin-empty">
                Loading activity...
              </div>
            ) : recentReports.length === 0 ? (
              <div className="admin-empty">
                <FileText size={25} />
                <p>No recent reports.</p>
              </div>
            ) : (
              <div className="admin-recent-list">

                {recentReports.map((report, index) => (
                  <div
                    className="admin-recent-item"
                    key={report.id || index}
                  >
                    <div className="admin-recent-icon">
                      <FileText size={17} />
                    </div>

                    <div>
                      <strong>
                        {report.lake_name || "Unnamed Lake"}
                      </strong>

                      <small>
                        {report.user_name || "Citizen"} · {formatDate(report.created_at)}
                      </small>
                    </div>

                    <span className={`admin-status status-${report.status || "submitted"}`}>
                      {(report.status || "submitted").replace("_", " ")}
                    </span>
                  </div>
                ))}

              </div>
            )}

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

export default AdminDashboard;
