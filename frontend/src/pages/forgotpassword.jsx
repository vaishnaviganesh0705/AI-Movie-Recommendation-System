import { useState } from "react";

import {
  Mail,
  ArrowLeft,
  KeyRound,
} from "lucide-react";

import {
  Link,
} from "react-router-dom";

import "../styles/ForgotPassword.css";


function ForgotPassword() {

  const [email, setEmail] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [message, setMessage] =
    useState("");


  const handleSubmit = async (e) => {

    e.preventDefault();

    setLoading(true);

    setMessage("");


    try {

      /*
        Backend password reset
        will be connected here.
      */

      await new Promise(
        (resolve) =>
          setTimeout(resolve, 1000)
      );


      setMessage(
        "If this email exists, a reset link will be sent."
      );

    } finally {

      setLoading(false);

    }

  };


  return (

    <div className="forgot-page">


      {/* BACKGROUND */}

      <div className="forgot-background">

        <div className="forgot-orb forgot-orb-one"></div>

        <div className="forgot-orb forgot-orb-two"></div>

      </div>


      {/* BACK */}

      <Link
        to="/login"
        className="forgot-back"
      >

        <ArrowLeft size={16} />

        Back to login

      </Link>


      {/* CARD */}

      <div className="forgot-card">


        <Link
          to="/"
          className="forgot-logo"
        >
          Stream<span>Hub</span>
        </Link>


        <div className="forgot-icon">

          <KeyRound size={22} />

        </div>


        <div className="forgot-heading">

          <h1>
            Reset your password.
          </h1>

          <p>
            Enter your email address and
            we'll help you get back in.
          </p>

        </div>


        <form
          onSubmit={handleSubmit}
          className="forgot-form"
        >

          <label>
            Email address
          </label>


          <div className="forgot-input">

            <Mail size={18} />

            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) =>
                setEmail(e.target.value)
              }
              required
            />

          </div>


          <button
            type="submit"
            disabled={loading}
          >

            {loading
              ? "Sending..."
              : "Send Reset Link"
            }

          </button>

        </form>


        {message && (

          <div className="forgot-message">
            {message}
          </div>

        )}


      </div>

    </div>

  );
}


export default ForgotPassword;