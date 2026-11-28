
import { useState } from "react";
import axios from "axios";
import { ShieldCheck, Lock, Mail } from "lucide-react";
import "./AdminLogin.css";

const API = "http://localhost:5000/api/admin";

function AdminLogin({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await axios.post(
        `${API}/login`,
        { email, password },
        { withCredentials: true }
      );

      onLogin(response.data.admin);
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to login. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-login-page">
      <div className="admin-login-card">

        <div className="admin-login-icon">
          <ShieldCheck size={35} />
        </div>

        <h1>Serenify Admin</h1>

        <p className="admin-login-subtitle">
          Sign in to manage student wellbeing support.
        </p>

        <form onSubmit={handleLogin}>

          <label>Admin Email</label>

          <div className="admin-input-wrapper">
            <Mail size={18} />
            <input
              type="email"
              placeholder="Enter admin email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <label>Password</label>

          <div className="admin-input-wrapper">
            <Lock size={18} />
            <input
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <p className="admin-login-error">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="admin-login-button"
          >
            {loading ? "Signing in..." : "Admin Login"}
          </button>

        </form>

        <p className="admin-login-footer">
          Authorized administrators only
        </p>

      </div>
    </div>
  );
}

export default AdminLogin;
