import { Link } from "react-router-dom";

function AuthLayout({ children }) {
  return (
    <div className="auth-page">

      <div className="auth-background">

        <div className="glow glow-one"></div>
        <div className="glow glow-two"></div>
        <div className="glow glow-three"></div>

      </div>

      <div className="auth-brand">
        <Link to="/login">
          Stream<span>Hub</span>
        </Link>
      </div>

      <div className="auth-container">

        <div className="auth-card">
          {children}
        </div>

      </div>

      <div className="auth-footer-text">
        © 2026 StreamHub. Entertainment powered by AI.
      </div>

    </div>
  );
}

export default AuthLayout;