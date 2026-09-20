import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Film,
  Music,
  Mic2,
  Users,
  LogOut,
  Search,
  Plus,
  Play,
  Star,
  Calendar,
  Menu,
  X,
} from "lucide-react";
import axios from "axios";
import { fetchMovies } from "../../services/tmdb";
import { useNavigate } from "react-router-dom";
import MovieCard from "../../components/MovieCard";

import "../../styles/admin/admindashboard.css";

function AdminDashboard() {

  const navigate = useNavigate();

  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [searchMovie, setSearchMovie] = useState("");

  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  useEffect(() => {
    loadMovies(page);
  }, [page]);
  // define loadMovies function (moved out of useEffect)
  const loadMovies = async (
    page = 1,
    query = "",
    language = "",
    genre = ""
  ) => {
    try {
      setLoading(true);

      let url = "";

      if (query.trim()) {
        url = `http://127.0.0.1:8000/tmdb/movies/search?query=${encodeURIComponent(
          query
        )}&page=${page}&language=en-US`;
      } else {
        url = `http://127.0.0.1:8000/tmdb/movies/discover?page=${page}`;

        if (language) url += `&with_original_language=${language}`;

        if (genre) url += `&with_genres=${genre}`;
      }

      const res = await fetch(url);

      const data = await res.json();

      setMovies(data.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const [stats, setStats] = useState({});

  useEffect(() => {
    axios.get("http://127.0.0.1:8000/auth/stats")
      .then(res => setStats(res.data));
  }, []);

  const handleLogout = () => {

    localStorage.removeItem("access_token");
    localStorage.removeItem("role");
    localStorage.removeItem("admin_logged_in");

    navigate("/login");
  };

  const handleSearch = async () => {
    setActiveMenu("movies");
    await loadMovies(1, searchMovie);
  };
  return (
    <div className="admin-dashboard">

      {/* ================= SIDEBAR ================= */}

      <aside
        className={`admin-sidebar ${sidebarOpen ? "sidebar-open" : ""
          }`}
      >

        <div className="admin-brand">

          <div className="brand-logo">
            Stream<span>Hub</span>
          </div>

          <div className="admin-badge">
            ADMIN
          </div>

        </div>

        <nav className="admin-nav">

          <button
            className={
              activeMenu === "dashboard"
                ? "admin-nav-item active"
                : "admin-nav-item"
            }
            onClick={() => {
              setActiveMenu("dashboard");
              setSidebarOpen(false);
            }}
          >
            <LayoutDashboard size={20} />
            Dashboard
          </button>

          <button
            className={
              activeMenu === "movies"
                ? "admin-nav-item active"
                : "admin-nav-item"
            }
            onClick={() => {
              setActiveMenu("movies");
              setSidebarOpen(false);
            }}
          >
            <Film size={20} />
            Movies
          </button>

          <button
            className={
              activeMenu === "music"
                ? "admin-nav-item active"
                : "admin-nav-item"
            }
            onClick={() => {
              setActiveMenu("music");
              setSidebarOpen(false);
            }}
          >
            <Music size={20} />
            Music
          </button>

          <button
            className={
              activeMenu === "podcasts"
                ? "admin-nav-item active"
                : "admin-nav-item"
            }
            onClick={() => {
              setActiveMenu("podcasts");
              setSidebarOpen(false);
            }}
          >
            <Mic2 size={20} />
            Podcasts
          </button>

          <button
            className={
              activeMenu === "users"
                ? "admin-nav-item active"
                : "admin-nav-item"
            }
            onClick={() => {
              setActiveMenu("users");
              setSidebarOpen(false);
            }}
          >
            <Users size={20} />
            Users
          </button>

        </nav>

        <div className="admin-sidebar-bottom">

          <button
            className="admin-logout"
            onClick={handleLogout}
          >
            <LogOut size={20} />
            Logout
          </button>

        </div>

      </aside>


      {/* ================= MAIN ================= */}

      <main className="admin-main">

        {/* TOP NAVBAR */}

        <header className="admin-topbar">

          <button
            className="mobile-menu"
            onClick={() =>
              setSidebarOpen(!sidebarOpen)
            }
          >
            {sidebarOpen ? (
              <X size={24} />
            ) : (
              <Menu size={24} />
            )}
          </button>

          <div className="topbar-title">

            <h1>
              {activeMenu === "dashboard" &&
                "Dashboard"}

              {activeMenu === "movies" &&
                "Movie Management"}

              {activeMenu === "music" &&
                "Music Management"}

              {activeMenu === "podcasts" &&
                "Podcast Management"}

              {activeMenu === "users" &&
                "User Management"}
            </h1>

            <p>
              Manage your StreamHub platform
            </p>

          </div>


          <div className="admin-profile">

            <div className="admin-avatar">
              A
            </div>

            <div>
              <strong>Administrator</strong>
              <span>Admin</span>
            </div>

          </div>

        </header>


        {/* ================= CONTENT ================= */}

        <div className="admin-content">


          {/* ================= DASHBOARD ================= */}

          {activeMenu === "dashboard" && (

            <>

              {/* SEARCH */}

              <section className="admin-search-section">

                <div>

                  <h2>
                    Welcome back, Admin 👋
                  </h2>

                  <p>
                    Manage movies, music and podcasts
                    from one place.
                  </p>

                </div>

                <div className="tmdb-search">

                  <Search size={20} />

                  <input
                    type="text"
                    placeholder="Search movies from TMDB..."
                    value={searchMovie}
                    onChange={(e) =>
                      setSearchMovie(e.target.value)
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        handleSearch();
                      }
                    }}
                  />

                  <button
                    onClick={handleSearch}
                  >
                    Search
                  </button>

                </div>

              </section>


              {/* STAT CARDS */}

              <section className="admin-stat-grid">

                <div className="admin-stat-card">

                  <div className="stat-icon movie">
                    <Film size={25} />
                  </div>

                  <div>
                    <span>Total Movies</span>
                    <strong>{movies.length}</strong>
                  </div>

                </div>


                <div className="admin-stat-card">

                  <div className="stat-icon music">
                    <Music size={25} />
                  </div>

                  <div>
                    <span>Total Music</span>
                    <strong>{stats.total_music || 0}</strong>
                  </div>

                </div>


                <div className="admin-stat-card">

                  <div className="stat-icon podcast">
                    <Mic2 size={25} />
                  </div>

                  <div>
                    <span>Podcasts</span>
                    <strong>{stats.total_podcasts || 0}</strong>
                  </div>

                </div>


                <div className="admin-stat-card">

                  <div className="stat-icon users">
                    <Users size={25} />
                  </div>

                  <div>
                    <span>Users</span>
                    <strong>{stats.users}</strong>
                  </div>

                </div>

              </section>


              {/* MOVIE SECTION */}

              <section className="admin-section">

                <div className="section-heading">

                  <div>

                    <h2>
                      Movies
                    </h2>

                    <p>
                      Movies currently available
                      on StreamHub
                    </p>

                  </div>

                  <button
                    className="primary-button"
                    onClick={() =>
                      setActiveMenu("movies")
                    }
                  >
                    <Plus size={18} />
                    Add Movie
                  </button>

                </div>


                <div className="movie-grid" style={{ paddingTop: '15px' }}>
                  {loading && movies.length === 0 ? (
                    [1, 2, 3, 4, 5].map(i => <MovieCard key={i} isLoading={true} />)
                  ) : (
                    movies.map((movie) => (
                      <MovieCard key={movie.id} movie={movie} isLoading={false} />
                    ))
                  )}
                </div>
                <button
                  className="primary-button"
                  onClick={() => setPage(page + 1)}
                >
                  Load More
                </button>

              </section>

            </>

          )}


          {/* ================= MOVIES ================= */}

          {activeMenu === "movies" && (

            <section className="movie-management">

              <div className="section-heading">

                <div>

                  <h2>
                    Movie Management
                  </h2>

                  <p>
                    Search and add movies from TMDB
                  </p>

                </div>

              </div>


              <div className="tmdb-large-search">

                <Search size={22} />

                <input
                  type="text"
                  placeholder="Search for a movie..."
                  value={searchMovie}
                  onChange={(e) =>
                    setSearchMovie(e.target.value)
                  }
                />

                <button
                  onClick={handleSearch}
                >
                  Search TMDB
                </button>

              </div>


              <div className="movie-grid" style={{ paddingTop: '15px' }}>
                {loading && movies.length === 0 ? (
                  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(i => <MovieCard key={i} isLoading={true} />)
                ) : (
                  movies.map(movie => (
                    <MovieCard key={movie.id} movie={movie} isLoading={false} />
                  ))
                )}
              </div>

            </section>

          )}


          {/* ================= MUSIC ================= */}

          {activeMenu === "music" && (

            <section className="placeholder-page">

              <Music size={55} />

              <h2>
                Music Management
              </h2>

              <p>
                Music management will be added here.
              </p>

              <button className="primary-button">
                <Plus size={18} />
                Add Music
              </button>

            </section>

          )}


          {/* ================= PODCAST ================= */}

          {activeMenu === "podcasts" && (

            <section className="placeholder-page">

              <Mic2 size={55} />

              <h2>
                Podcast Management
              </h2>

              <p>
                Manage your podcasts here.
              </p>

              <button className="primary-button">
                <Plus size={18} />
                Add Podcast
              </button>

            </section>

          )}


          {/* ================= USERS ================= */}

          {activeMenu === "users" && (

            <section className="placeholder-page">

              <Users size={55} />

              <h2>
                User Management
              </h2>

              <p>
                Manage registered StreamHub users.
              </p>

            </section>

          )}

        </div>

      </main>

    </div>
  );
}

export default AdminDashboard;