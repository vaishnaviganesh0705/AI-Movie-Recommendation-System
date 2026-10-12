import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import Home from "./pages/Home";
import Movies from "./pages/Movies";
import TVShows from "./pages/TVShows";
import TVDetails from "./pages/TVDetails";
import Music from "./pages/Music";
import Subscription from "./pages/Subscription";
import Payment from "./pages/Payment";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AppLayout from "./layouts/AppLayout";
import Search from "./pages/Search";
import Profile from "./pages/Profile";
import MovieDetails from "./pages/MovieDetails";
import Watchlist from "./pages/Watchlist";
import History from "./pages/History";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* PUBLIC DASHBOARD */}
        <Route path="/" element={<Dashboard />} />

        {/* AUTH */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />

        {/* USER OTT LAYOUT */}
        <Route element={<AppLayout />}>
          <Route path="/home" element={<Home />} />
          <Route path="/movies" element={<Movies />} />
          <Route path="/tv" element={<TVShows />} />
          <Route path="/tv/:id" element={<TVDetails />} />
          <Route path="/music" element={<Music />} />
          <Route path="/subscription" element={<Subscription />} />
          <Route path="/payment" element={<Payment />} />
          <Route path="/search" element={<Search />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/history" element={<History />} />
          <Route path="/movie/:id" element={<MovieDetails />} />
        </Route>

        {/* ADMIN */}
        <Route path="/admin/admindashboard" element={<AdminDashboard />} />

        {/* INVALID URL */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;