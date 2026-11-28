
import { useEffect, useState } from "react";
import axios from "axios";
import {
  HeartHandshake,
  CalendarDays,
  Clock,
  Send,
  XCircle,
  CheckCircle2,
  Hourglass,
  Info
} from "lucide-react";
import "./Counselling.css";

const API = "http://localhost:5000/api/counselling/";

function Counselling() {
  const [requests, setRequests] = useState([]);
  const [preferredDate, setPreferredDate] = useState("");
  const [preferredTime, setPreferredTime] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const fetchRequests = async () => {
    try {
      const response = await axios.get(API, {
        withCredentials: true
      });

      setRequests(response.data.requests || []);
    } catch (error) {
      console.error("Error loading counselling requests:", error);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const submitRequest = async (e) => {
    e.preventDefault();
    setMessage("");

    if (!preferredDate || !preferredTime) {
      setMessage("Please select your preferred date and time.");
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(
        API,
        {
          preferred_date: preferredDate,
          preferred_time: preferredTime,
          reason: reason
        },
        { withCredentials: true }
      );

      setMessage(response.data.message);
      setPreferredDate("");
      setPreferredTime("");
      setReason("");

      await fetchRequests();
    } catch (error) {
      setMessage(
        error.response?.data?.message ||
        "Unable to submit your request. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const cancelRequest = async (id) => {
    if (!window.confirm("Are you sure you want to cancel this request?")) {
      return;
    }

    try {
      await axios.delete(`${API}${id}`, {
        withCredentials: true
      });

      setMessage("Your counselling request has been cancelled.");
      fetchRequests();
    } catch (error) {
      setMessage(
        error.response?.data?.message ||
        "Unable to cancel the request."
      );
    }
  };

  const getStatusIcon = (status) => {
    if (status === "Approved") return <CheckCircle2 size={16} />;
    if (status === "Rejected") return <XCircle size={16} />;
    if (status === "Cancelled") return <XCircle size={16} />;
    return <Hourglass size={16} />;
  };

  return (
    <div className="counselling-page">

      <div className="counselling-hero">
        <div className="counselling-hero-icon">
          <HeartHandshake size={34} />
        </div>

        <div>
          <h1>Counselling Support</h1>
          <p>
            Taking care of your mental wellbeing is important.
            Reach out for support whenever you need it.
          </p>
        </div>
      </div>

      <div className="counselling-info">
        <Info size={21} />
        <div>
          <strong>You are not alone.</strong>
          <p>
            You can submit a counselling request by choosing
            a preferred date and time. Your request will remain
            pending until it is reviewed.
          </p>
        </div>
      </div>

      <div className="counselling-layout">

        <section className="counselling-form-card">
          <h2>Request Counselling</h2>
          <p className="counselling-subtitle">
            Share your preferred appointment details.
          </p>

          <form onSubmit={submitRequest}>

            <label>Preferred Date</label>
            <input
              type="date"
              value={preferredDate}
              min={new Date().toLocaleDateString("en-CA")}
              onChange={(e) => setPreferredDate(e.target.value)}
              required
            />

            <label>Preferred Time</label>
            <input
              type="time"
              value={preferredTime}
              onChange={(e) => setPreferredTime(e.target.value)}
              required
            />

            <label>Reason for Counselling (Optional)</label>
            <textarea
              rows="4"
              placeholder="You can briefly describe what kind of support you are looking for..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />

            <button
              type="submit"
              className="counselling-submit-btn"
              disabled={loading}
            >
              <Send size={17} />
              {loading ? "Submitting..." : "Submit Request"}
            </button>

          </form>

          {message && (
            <p className="counselling-message">{message}</p>
          )}
        </section>

        <section className="counselling-requests-card">
          <h2>My Counselling Requests</h2>
          <p className="counselling-subtitle">
            Track your submitted requests here.
          </p>

          {requests.length === 0 ? (
            <div className="counselling-empty">
              <CalendarDays size={38} />
              <h3>No requests yet</h3>
              <p>Your counselling requests will appear here.</p>
            </div>
          ) : (
            <div className="counselling-request-list">
              {requests.map((item) => (
                <div
                  className="counselling-request-item"
                  key={item.appointment_id}
                >
                  <div className="request-item-top">
                    <h3>
                      Request #{item.appointment_id}
                    </h3>

                    <span className={`request-status ${item.status.toLowerCase()}`}>
                      {getStatusIcon(item.status)}
                      {item.status}
                    </span>
                  </div>

                  <p>
                    <CalendarDays size={16} />
                    {item.preferred_date}
                  </p>

                  <p>
                    <Clock size={16} />
                    {item.preferred_time}
                  </p>

                  {item.reason && (
                    <p className="request-reason">
                      {item.reason}
                    </p>
                  )}

                  {item.status === "Pending" && (
                    <button
                      className="counselling-cancel-btn"
                      onClick={() => cancelRequest(item.appointment_id)}
                    >
                      Cancel Request
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

      </div>
    </div>
  );
}

export default Counselling;
