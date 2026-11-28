
import { useState } from "react";
import axios from "axios";
import "./Auth.css";

const API = "http://localhost:5000/api/auth";

function Auth({ onLogin, onAdminLoginClick }) {
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: ""
  });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");
    setLoading(true);

    try {
      if (isRegister) {
        const response = await axios.post(
          `${API}/register`,
          form,
          { withCredentials: true }
        );

        setMessage(response.data.message);
        setIsRegister(false);
        setForm({
          full_name: "",
          email: form.email,
          password: "",
          confirm_password: ""
        });
      } else {
        const response = await axios.post(
          `${API}/login`,
          {
            email: form.email,
            password: form.password
          },
          { withCredentials: true }
        );

        onLogin(response.data.student);
      }
    } catch (error) {
      setMessage(
        error.response?.data?.message ||
        "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Serenify</h1>

        <p className="auth-subtitle">
          Your safe space for student wellbeing
        </p>

        <h2>{isRegister ? "Create your account" : "Welcome back!"}</h2>

        <p>
          {isRegister
            ? "Start your wellbeing journey with us."
            : "Sign in to continue to your personal space."}
        </p>

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <input
              name="full_name"
              placeholder="Full name"
              value={form.full_name}
              onChange={handleChange}
              required
            />
          )}

          <input
            type="email"
            name="email"
            placeholder="Email address"
            value={form.email}
            onChange={handleChange}
            required
          />

          <input
            type="password"
            name="password"
            placeholder="Password (minimum 8 characters)"
            value={form.password}
            onChange={handleChange}
            required
            minLength={8}
          />

          {isRegister && (
            <input
              type="password"
              name="confirm_password"
              placeholder="Confirm password"
              value={form.confirm_password}
              onChange={handleChange}
              required
            />
          )}

          <button type="submit" disabled={loading}>
            {loading
              ? "Please wait..."
              : isRegister
                ? "Create Account"
                : "Login"}
          </button>
        </form>

        {message && <p className="auth-message">{message}</p>}

        <p className="auth-switch">
          {isRegister ? "Already have an account?" : "New to Serenify?"}

          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setMessage("");
            }}
          >
            {isRegister ? "Login" : "Register"}
          </button>
        </p>

        {!isRegister && (
          <div className="admin-login-option">
            <span>Are you an administrator?</span>

            <button
              type="button"
              onClick={onAdminLoginClick}
            >
              Admin Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Auth;
