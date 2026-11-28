
import { useEffect, useState } from "react";
import axios from "axios";
import {
  ShieldCheck,
  Users,
  CalendarDays,
  CheckCircle2,
  XCircle,
  Hourglass,
  LogOut,
  RefreshCw
} from "lucide-react";

import AdminStudents from "./AdminStudents";
import "./AdminDashboard.css";

const API = "http://localhost:5000/api/admin";

function AdminDashboard({ admin, onLogout }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [activeSection, setActiveSection] = useState("counselling");

  const fetchRequests = async () => {
    try {
      setMessage("");

      const response = await axios.get(
        `${API}/counselling`,
        { withCredentials: true }
      );

      setRequests(response.data.requests || []);
    } catch (error) {
      setMessage(
        error.response?.data?.message ||
        "Unable to load counselling requests."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const updateStatus = async (id, status) => {
    const action = status.toLowerCase();

    if (!window.confirm(`Are you sure you want to ${action} this request?`)) {
      return;
    }

    try {
      const response = await axios.put(
        `${API}/counselling/${id}`,
        { status },
        { withCredentials: true }
      );

      setMessage(response.data.message);
      await fetchRequests();
    } catch (error) {
      setMessage(
        error.response?.data?.message ||
        "Unable to update request."
      );
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(
        `${API}/logout`,
        {},
        { withCredentials: true }
      );

      onLogout();
    } catch (error) {
      setMessage("Unable to logout. Please try again.");
    }
  };

  const pending = requests.filter(
    (item) => item.status === "Pending"
  ).length;

  const approved = requests.filter(
    (item) => item.status === "Approved"
  ).length;

  const rejected = requests.filter(
    (item) => item.status === "Rejected"
  ).length;

  return (
    <div className="admin-dashboard">

      <header className="admin-dashboard-header">
        <div className="admin-brand">
          <div className="admin-brand-icon">
            <ShieldCheck size={27} />
          </div>

          <div>
            <h1>Serenify Admin</h1>
            <p>Student Wellbeing Management</p>
          </div>
        </div>

        <div className="admin-header-right">
          <div className="admin-welcome">
            <strong>{admin?.full_name || "Administrator"}</strong>
            <span>Administrator</span>
          </div>

          <button
            className="admin-logout-button"
            onClick={handleLogout}
          >
            <LogOut size={17} />
            Logout
          </button>
        </div>
      </header>

      <main className="admin-dashboard-content">

        <div className="admin-page-heading">
          <div>
            <h2>Dashboard Overview</h2>
            <p>Manage student wellbeing activities.</p>
          </div>

          {activeSection === "counselling" && (
            <button
              className="admin-refresh-button"
              onClick={() => {
                setLoading(true);
                fetchRequests();
              }}
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          )}
        </div>

        {/* Admin Navigation */}
        <div className="admin-section-navigation">
          <button
            className={activeSection === "counselling" ? "active" : ""}
            onClick={() => {
              setActiveSection("counselling");
              setMessage("");
            }}
          >
            <CalendarDays size={17} />
            Counselling Requests
          </button>

          <button
            className={activeSection === "students" ? "active" : ""}
            onClick={() => {
              setActiveSection("students");
              setMessage("");
            }}
          >
            <Users size={17} />
            Student Management
          </button>
        </div>

        {activeSection === "counselling" ? (
          <>

            <div className="admin-stats">

              <div className="admin-stat-card">
                <div className="admin-stat-icon total">
                  <Users size={23} />
                </div>
                <div>
                  <p>Total Requests</p>
                  <h2>{requests.length}</h2>
                </div>
              </div>

              <div className="admin-stat-card">
                <div className="admin-stat-icon pending">
                  <Hourglass size={23} />
                </div>
                <div>
                  <p>Pending</p>
                  <h2>{pending}</h2>
                </div>
              </div>

              <div className="admin-stat-card">
                <div className="admin-stat-icon approved">
                  <CheckCircle2 size={23} />
                </div>
                <div>
                  <p>Approved</p>
                  <h2>{approved}</h2>
                </div>
              </div>

              <div className="admin-stat-card">
                <div className="admin-stat-icon rejected">
                  <XCircle size={23} />
                </div>
                <div>
                  <p>Rejected</p>
                  <h2>{rejected}</h2>
                </div>
              </div>

            </div>

            {message && (
              <div className="admin-message">
                {message}
              </div>
            )}

            <section className="admin-requests-section">
              <div className="admin-section-heading">
                <div>
                  <h2>Counselling Requests</h2>
                  <p>Review and manage submitted requests.</p>
                </div>
              </div>

              {loading ? (
                <p className="admin-empty">Loading requests...</p>
              ) : requests.length === 0 ? (
                <div className="admin-empty">
                  <CalendarDays size={40} />
                  <h3>No counselling requests</h3>
                  <p>Student requests will appear here.</p>
                </div>
              ) : (
                <div className="admin-table-wrapper">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Preferred Date</th>
                        <th>Preferred Time</th>
                        <th>Reason</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>

                    <tbody>
                      {requests.map((item) => (
                        <tr key={item.appointment_id}>
                          <td>
                            <strong>{item.full_name}</strong>
                            <small>{item.email}</small>
                          </td>

                          <td>{item.preferred_date}</td>

                          <td>{item.preferred_time}</td>

                          <td className="admin-reason">
                            {item.reason || "Not provided"}
                          </td>

                          <td>
                            <span
                              className={`admin-status ${item.status.toLowerCase()}`}
                            >
                              {item.status}
                            </span>
                          </td>

                          <td>
                            {item.status === "Pending" ? (
                              <div className="admin-action-buttons">
                                <button
                                  className="admin-approve-button"
                                  onClick={() =>
                                    updateStatus(
                                      item.appointment_id,
                                      "Approved"
                                    )
                                  }
                                >
                                  Approve
                                </button>

                                <button
                                  className="admin-reject-button"
                                  onClick={() =>
                                    updateStatus(
                                      item.appointment_id,
                                      "Rejected"
                                    )
                                  }
                                >
                                  Reject
                                </button>
                              </div>
                            ) : (
                              <span className="admin-no-action">
                                Completed
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

          </>
        ) : (
          <AdminStudents />
        )}

      </main>
    </div>
  );
}

export default AdminDashboard;
