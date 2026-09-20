import { useState } from "react";
import api from "../services/api";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowLeft,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import "../styles/Login.css";

function Login() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Handle input changes
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });

    // Remove error when user starts typing
    setError("");
  };

  // Handle login
const handleSubmit = async (e) => {
  e.preventDefault();

  setError("");

  if (!formData.email || !formData.password) {
    setError("Please enter your email and password.");
    return;
  }

  setLoading(true);

  try {
    const response = await api.post("/auth/login", {
      email: formData.email.trim(),
      password: formData.password,
    });

    console.log("Login response:", response.data);

    const {
      access_token,
      role,
      user_id,
      name,
      email,
    } = response.data;

    if (!access_token) {
      setError("Login failed. Access token not received.");
      return;
    }

    // Save login information
    localStorage.setItem(
      "access_token",
      access_token
    );

    localStorage.setItem(
      "role",
      role
    );

    localStorage.setItem(
      "user_id",
      user_id
    );

    localStorage.setItem(
      "user_name",
      name
    );

    localStorage.setItem(
      "user_email",
      email
    );

    // ==========================
    // ADMIN
    // ==========================

    if (role === "admin") {

      console.log(
        "Admin detected → Admin Dashboard"
      );

      navigate("/admin/admindashboard", {
        replace: true,
      });

      return;
    }

    // ==========================
    // USER
    // ==========================

    if (role === "user") {

      console.log(
        "User detected → Home"
      );

      navigate("/home", {
        replace: true,
      });

      return;
    }

    setError("Invalid account role.");

  } catch (error) {

    console.error(
      "Login error:",
      error.response?.data || error.message
    );

    const detail =
      error.response?.data?.detail;

    if (typeof detail === "string") {
      setError(detail);
    } else {
      setError(
        "Invalid email or password."
      );
    }

  } finally {
    setLoading(false);
  }
};
  return (
    <div className="login-page">

      {/* ================= BACKGROUND ================= */}

      <div className="login-background">
        <div className="login-orb login-orb-one"></div>
        <div className="login-orb login-orb-two"></div>
      </div>


      {/* ================= BACK BUTTON ================= */}

      <Link
        to="/"
        className="login-back"
      >
        <ArrowLeft size={16} />
        <span>Back</span>
      </Link>


      {/* ================= LOGIN CARD ================= */}

      <div className="login-card">

        {/* Logo */}

        <Link
          to="/"
          className="login-logo"
        >
          Stream<span>Hub</span>
        </Link>


        {/* Heading */}

        <div className="login-heading">

          <h1>
            Welcome back.
          </h1>

          <p>
            Sign in to continue your
            entertainment journey.
          </p>

        </div>


        {/* Error message */}

        {error && (
          <div className="login-error">
            {error}
          </div>
        )}


        {/* ================= FORM ================= */}

        <form
          className="login-form"
          onSubmit={handleSubmit}
        >

          {/* EMAIL */}

          <div className="login-field">

            <label htmlFor="email">
              Email address
            </label>

            <div className="login-input-wrapper">

              <Mail size={18} />

              <input
                id="email"
                type="email"
                name="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                autoComplete="email"
              />

            </div>

          </div>


          {/* PASSWORD */}

          <div className="login-field">

            <div className="password-label">

              <label htmlFor="password">
                Password
              </label>

              <Link to="/forgot-password">
                Forgot password?
              </Link>

            </div>


            <div className="login-input-wrapper">

              <Lock size={18} />

              <input
                id="password"
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                name="password"
                placeholder="Enter your password"
                value={formData.password}
                onChange={handleChange}
                autoComplete="current-password"
              />


              {/* Show / Hide Password */}

              <button
                type="button"
                className="eye-button"
                onClick={() =>
                  setShowPassword(
                    !showPassword
                  )
                }
                aria-label={
                  showPassword
                    ? "Hide password"
                    : "Show password"
                }
              >

                {showPassword ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}

              </button>

            </div>

          </div>


          {/* LOGIN BUTTON */}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >

            {loading
              ? "Signing in..."
              : "Sign In"
            }

          </button>

        </form>


        {/* ================= REGISTER ================= */}

        <div className="login-register">

          <span>
            Don't have an account?
          </span>

          <Link to="/register">
            Create account
          </Link>

        </div>

      </div>

    </div>
  );
}

export default Login;

