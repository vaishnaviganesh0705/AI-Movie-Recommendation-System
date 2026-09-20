# PROJECT AUDIT

## 1. What already works
- **Frontend foundation:** React + Vite ecosystem is successfully wired with `react-router-dom` for navigation.
- **Backend foundation:** FastAPI is operational, with SQLAlchemy models and Alembic migrations targeting MySQL/Aiven.
- **Base Authentication:** Registration and Login routes exist both on the frontend (`Login.jsx`, `Register.jsx`) and backend (`auth.py`). 
- **Routes:** Distinct layouts are set up for Admin (`/admin/admindashboard`) and User (`/home`, `/`).

## 2. What is broken
- The backend to MySQL Aiven connection was suffering from connection timeouts (`OperationalError`), likely due to IP whitelisting or clustered pauses. 
- Some hardcoded CSS tokens caused stylistic collision when changing UI themes.
- Missing error boundary implementations for standard network failures.

## 3. What should be reused
- The current Authentication Flow (JWT via FastAPI to React LocalStorage). No need to rewrite completely.
- Current routing configuration (React Router setup in `App.jsx`).
- Existing `lucide-react` icons and overall glassmorphism aesthetic goal.

## 4. UI inconsistencies
- User dashboard (`dashboard.css`) and Admin Dashboard (`admindashboard.css`) used entirely different hex values for the exact same visual identity (e.g., `#080812` vs `#090a0f`). This has been unified.
- Buttons lack a centralized UI component (`Button.jsx`). Instead, they rely on ad-hoc CSS classes (`.primary-btn`, `.hero-start`).

## 5. Duplicate Components
- Styles are duplicated extensively across component CSS files instead of utilizing utility classes.
- Navigation/Hero logic is repeated between the landing page (`Dashboard.jsx`) and the user OTT app (`Home.jsx`).

## 6. Important Technical Issues
- Hard dependency on remote Aiven DB can block local development if internet fails.
- No central interceptor in Axios to attach tokens automatically, leading to potential prop-drilling or repetitive auth-header attachment.
- The `index.css` lacks standard component class encapsulation for pure React extraction (which is why CSS files are bloated).
