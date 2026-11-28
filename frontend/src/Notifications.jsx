
import { useEffect, useState } from "react";
import axios from "axios";
import {
  Bell,
  CheckCheck,
  CalendarDays,
  Clock,
  RefreshCw
} from "lucide-react";
import "./Notifications.css";

const API = "http://localhost:5000/api/notifications";

function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchNotifications = async () => {
    try {
      setError("");

      const response = await axios.get(`${API}/`, {
        withCredentials: true
      });

      setNotifications(response.data.notifications || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to load notifications."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const markAsRead = async (id) => {
    try {
      await axios.put(
        `${API}/${id}/read`,
        {},
        { withCredentials: true }
      );

      await fetchNotifications();
    } catch (err) {
      alert(
        err.response?.data?.message ||
        "Unable to update notification."
      );
    }
  };

  const markAllAsRead = async () => {
    try {
      await axios.put(
        `${API}/read-all`,
        {},
        { withCredentials: true }
      );

      await fetchNotifications();
    } catch (err) {
      alert(
        err.response?.data?.message ||
        "Unable to update notifications."
      );
    }
  };

  const formatDate = (date) => {
    if (!date) return "";
    return new Date(date).toLocaleString();
  };

  return (
    <div className="notifications-page">

      <div className="notifications-header">
        <div>
          <h2>Notifications</h2>
          <p>Stay updated with your wellbeing activities.</p>
        </div>

        <button
          className="notification-refresh"
          onClick={() => {
            setLoading(true);
            fetchNotifications();
          }}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="notification-summary">
        <div className="notification-summary-icon">
          <Bell size={25} />
        </div>

        <div>
          <h3>{unreadCount} Unread Notifications</h3>
          <p>You can review your latest updates here.</p>
        </div>
      </div>

      <div className="notification-list-header">
        <h3>Recent Notifications</h3>

        {unreadCount > 0 && (
          <button
            className="mark-all-read"
            onClick={markAllAsRead}
          >
            <CheckCheck size={16} />
            Mark all as read
          </button>
        )}
      </div>

      {loading ? (
        <div className="notification-empty">
          Loading notifications...
        </div>
      ) : error ? (
        <div className="notification-error">
          {error}
          <button onClick={fetchNotifications}>
            Try Again
          </button>
        </div>
      ) : notifications.length === 0 ? (
        <div className="notification-empty">
          <Bell size={42} />
          <h3>No notifications yet</h3>
          <p>
            Your counselling updates and other important
            notifications will appear here.
          </p>
        </div>
      ) : (
        <div className="notification-items">
          {notifications.map((item) => (
            <div
              className={`notification-card ${
                item.is_read ? "read" : "unread"
              }`}
              key={item.notification_id}
            >
              <div className="notification-card-icon">
                <CalendarDays size={21} />
              </div>

              <div className="notification-card-content">
                <div className="notification-card-title">
                  <h4>{item.title}</h4>

                  {!item.is_read && (
                    <span className="unread-dot"></span>
                  )}
                </div>

                <p>{item.message}</p>

                <span className="notification-date">
                  <Clock size={13} />
                  {formatDate(item.created_at)}
                </span>

                {!item.is_read && (
                  <button
                    className="mark-read-button"
                    onClick={() =>
                      markAsRead(item.notification_id)
                    }
                  >
                    Mark as read
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}

export default Notifications;
