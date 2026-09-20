import {
  ArrowRight,
  Play,
  Sparkles,
  Music2,
  Film,
  Headphones,
  Zap,
} from "lucide-react";

import { Link } from "react-router-dom";

import "../styles/Dashboard.css";

function Dashboard() {
  return (
    <div className="dashboard">

      {/* ================= NAVBAR ================= */}

      <header className="dashboard-navbar">

        <Link to="/" className="dashboard-logo">
          Stream<span>Hub</span>
        </Link>

        <nav className="dashboard-nav">
          <a href="#discover">Discover</a>
          <a href="#features">Features</a>
          <a href="#experience">Experience</a>
        </nav>

        <div className="dashboard-actions">

          <Link to="/login" className="signin-link">
            Sign In
          </Link>

          <Link to="/register" className="get-started">
            Get Started
          </Link>

        </div>

      </header>


      {/* ================= BACKGROUND ================= */}

      <div className="dashboard-background">
      </div>


      {/* ================= HERO ================= */}

      <section className="dashboard-hero">

        <div className="hero-left">

          <h1>
            One place.
            <br />

            <span>
              Every experience.
            </span>
          </h1>

          <p>
            Discover movies, series, music and podcasts
            through one intelligent entertainment platform
            designed around what you love.
          </p>

          <div className="hero-buttons">

            <Link
              to="/register"
              className="hero-start"
            >
              Start Exploring
              <ArrowRight size={18} />
            </Link>

            <Link
              to="/login"
              className="hero-demo"
            >
              <Play size={17} />
              Watch Demo
            </Link>

          </div>

          <div className="hero-stats">

            <div>
              <strong>10K+</strong>
              <span>Titles</span>
            </div>

            <div>
              <strong>24/7</strong>
              <span>Entertainment</span>
            </div>

            <div>
              <strong>AI</strong>
              <span>Personalized</span>
            </div>

          </div>

        </div>


        {/* ================= HERO VISUAL ================= */}

        <div className="hero-right">

          <div className="music-card">

            <div className="music-card-top">

              <div className="live-indicator"></div>

              <span>
                NOW DISCOVERING
              </span>

            </div>


            <div className="music-art">

              <div className="music-circle">
                <Music2 size={38} />
              </div>

              <div className="equalizer">

                <span></span>
                <span></span>
                <span></span>
                <span></span>

              </div>

            </div>


            <div className="music-info">

              <div>

                <small>
                  CURATED FOR YOU
                </small>

                <h3>
                  Midnight Frequencies
                </h3>

              </div>

              <button className="play-button">
                <Play
                  size={18}
                  fill="currentColor"
                />
              </button>

            </div>

          </div>


          {/* Floating movie card */}

          <div className="floating-card movie-card">

            <Film size={19} />

            <div>
              <small>Movies</small>
              <strong>Explore</strong>
            </div>

          </div>


          {/* Floating music card */}

          <div className="floating-card headphones-card">

            <Headphones size={19} />

            <div>
              <small>Music</small>
              <strong>Listen</strong>
            </div>

          </div>

        </div>

      </section>


      {/* ================= FEATURES ================= */}

      <section
        className="features"
        id="features"
      >

        <div className="features-heading">

          <span>BUILT DIFFERENT</span>

          <h2>
            Entertainment,
            <br />
            <em>your way.</em>
          </h2>

        </div>


        <div className="feature-grid">

          <div className="feature-card">

            <div className="feature-icon">
              <Sparkles size={22} />
            </div>

            <h3>
              Smart Discovery
            </h3>

            <p>
              Intelligent recommendations that
              understand your interests and help
              you discover something new.
            </p>

          </div>


          <div className="feature-card">

            <div className="feature-icon">
              <Film size={22} />
            </div>

            <h3>
              One Universe
            </h3>

            <p>
              Movies, series, music and podcasts
              come together inside one connected
              entertainment experience.
            </p>

          </div>


          <div className="feature-card">

            <div className="feature-icon">
              <Zap size={22} />
            </div>

            <h3>
              Personalized Flow
            </h3>

            <p>
              Your activity continuously shapes
              your experience and recommendations.
            </p>

          </div>

        </div>

      </section>


      {/* ================= FOOTER ================= */}

      <footer className="dashboard-footer">

        <strong>
          StreamHub
        </strong>

        <span>
          Entertainment, reimagined.
        </span>

      </footer>

    </div>
  );
}

export default Dashboard;