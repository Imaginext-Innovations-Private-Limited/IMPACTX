
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Waves } from "lucide-react";
import { loginUser } from "../services/authService";

function Login() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setMessage("");
    setLoading(true);

    try {
      const response = await loginUser({
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
      });

      // Save authentication token
      localStorage.setItem(
        "aquawatch_token",
        response.access_token
      );

      // Save logged-in user details
      localStorage.setItem(
        "aquawatch_user",
        JSON.stringify(response.user)
      );

      setMessage("Login successful!");

      // Redirect according to user role
      const userRole = response.user?.role;

      setTimeout(() => {
        if (userRole === "admin") {
          navigate("/admin", { replace: true });
        } else {
          navigate("/dashboard", { replace: true });
        }
      }, 700);

    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
        "Login failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">

        <div className="brand">
          <Waves size={30} />
          <span>AquaWatch</span>
        </div>

        <h2>Welcome Back!</h2>

        <p>Login to your AquaWatch account</p>

        <form onSubmit={handleSubmit}>

          <label>Email Address</label>

          <input
            type="email"
            name="email"
            placeholder="Enter your email"
            value={formData.email}
            onChange={handleChange}
            required
          />

          <label>Password</label>

          <input
            type="password"
            name="password"
            placeholder="Enter your password"
            value={formData.password}
            onChange={handleChange}
            required
          />

          {message && (
            <p className="form-message">
              {message}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
          >
            {loading ? "Logging in..." : "Login"}
          </button>

        </form>

        <p className="auth-footer">
          Don't have an account?{" "}
          <Link to="/register">Register</Link>
        </p>

      </div>
    </div>
  );
}

export default Login;
