import { useState } from "react";

import {
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowLeft,
} from "lucide-react";

import {
  Link,
  useNavigate,
} from "react-router-dom";

import "../styles/Register.css";
import api from "../services/api";

function Register() {

  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const [showPassword, setShowPassword] =
    useState(false);

  const [showConfirmPassword, setShowConfirmPassword] =
    useState(false);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");


  // --------------------------------
  // INPUT CHANGE
  // --------------------------------

  const handleChange = (e) => {

    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });

    setError("");
    setSuccess("");
  };


  // --------------------------------
  // REGISTER
  // --------------------------------

  const handleSubmit = async (e) => {

    e.preventDefault();

    setError("");
    setSuccess("");


    // Check all fields

    if (
      !formData.name.trim() ||
      !formData.email.trim() ||
      !formData.password ||
      !formData.confirmPassword
    ) {

      setError(
        "Please fill in all fields."
      );

      return;
    }


    // Check password

    if (
      formData.password !==
      formData.confirmPassword
    ) {

      setError(
        "Passwords do not match."
      );

      return;
    }


    // Password minimum length

    if (formData.password.length < 6) {

      setError(
        "Password must be at least 6 characters."
      );

      return;
    }


    setLoading(true);


    try {

      // --------------------------------
      // SEND TO FASTAPI
      // --------------------------------

      const response = await api.post(
        "/auth/register",
        {
          name: formData.name.trim(),
          email: formData.email.trim(),
          password: formData.password,
          confirmPassword: formData.confirmPassword,
        }
      );


      // --------------------------------
      // SUCCESS
      // --------------------------------

      console.log(
        "Registration successful:",
        response.data
      );


      setSuccess(
        "Account created successfully! Redirecting to login..."
      );


      // Clear form

      setFormData({
        name: "",
        email: "",
        password: "",
        confirmPassword: "",
      });


      // Navigate to login

      setTimeout(() => {

        navigate("/login");

      }, 1500);


    } catch (error) {

      console.log(
        "Registration failed:",
        error.response?.data || error.message
      );


      // --------------------------------
      // BACKEND ERROR
      // --------------------------------

      if (error.response) {

        const detail =
          error.response.data?.detail;


        if (typeof detail === "string") {

          setError(detail);

        }

        else if (Array.isArray(detail)) {

          const messages =
            detail.map((item) => {

              if (typeof item === "string") {
                return item;
              }

              return item.msg || "Invalid input.";

            });


          setError(
            messages.join(", ")
          );

        }

        else {

          setError(
            "Unable to create account."
          );

        }

      }

      else {

        setError(
          "Cannot connect to the backend."
        );

      }

    } finally {

      setLoading(false);

    }

  };


  return (

    <div className="register-page">


      {/* BACKGROUND */}

      <div className="register-background">

        <div className="register-orb register-orb-one"></div>

        <div className="register-orb register-orb-two"></div>

      </div>


      {/* BACK */}

      <Link
        to="/"
        className="register-back"
      >

        <ArrowLeft size={16} />

        Back

      </Link>


      {/* CARD */}

      <div className="register-card">


        {/* LOGO */}

        <Link
          to="/"
          className="register-logo"
        >

          Stream<span>Hub</span>

        </Link>


        {/* HEADING */}

        <div className="register-heading">

          <h1>
            Create your account.
          </h1>

          <p>
            Build your own personalized
            entertainment experience.
          </p>

        </div>


        {/* ERROR */}

        {error && (

          <div className="register-error">

            {error}

          </div>

        )}


        {/* SUCCESS */}

        {success && (

          <div className="register-success">

            ✓ {success}

          </div>

        )}


        {/* FORM */}

        <form
          onSubmit={handleSubmit}
          className="register-form"
        >


          {/* NAME */}

          <div className="register-field">

            <label>
              Full name
            </label>

            <div className="register-input">

              <User size={18} />

              <input
                type="text"
                name="name"
                placeholder="Your name"
                value={formData.name}
                onChange={handleChange}
                required
              />

            </div>

          </div>


          {/* EMAIL */}

          <div className="register-field">

            <label>
              Email address
            </label>

            <div className="register-input">

              <Mail size={18} />

              <input
                type="email"
                name="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                required
              />

            </div>

          </div>


          {/* PASSWORD */}

          <div className="register-field">

            <label>
              Password
            </label>

            <div className="register-input">

              <Lock size={18} />

              <input
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                name="password"
                placeholder="Create a password"
                value={formData.password}
                onChange={handleChange}
                required
              />

              <button
                type="button"
                onClick={() =>
                  setShowPassword(
                    !showPassword
                  )
                }
                className="register-eye"
              >

                {showPassword ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}

              </button>

            </div>

          </div>


          {/* CONFIRM PASSWORD */}

          <div className="register-field">

            <label>
              Confirm password
            </label>

            <div className="register-input">

              <Lock size={18} />

              <input
                type={
                  showConfirmPassword
                    ? "text"
                    : "password"
                }
                name="confirmPassword"
                placeholder="Confirm password"
                value={
                  formData.confirmPassword
                }
                onChange={handleChange}
                required
              />

              <button
                type="button"
                onClick={() =>
                  setShowConfirmPassword(
                    !showConfirmPassword
                  )
                }
                className="register-eye"
              >

                {showConfirmPassword ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}

              </button>

            </div>

          </div>


          {/* REGISTER BUTTON */}

          <button
            type="submit"
            className="register-button"
            disabled={loading}
          >

            {loading
              ? "Creating account..."
              : "Create Account"
            }

          </button>


        </form>


        {/* LOGIN LINK */}

        <div className="register-login">

          <span>
            Already have an account?
          </span>

          <Link to="/login">
            Sign In
          </Link>

        </div>


      </div>

    </div>

  );

}

export default Register;