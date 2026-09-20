import React, { useState, useEffect } from "react";
import "../styles/home.css";
import ContentRow from "../components/ContentRow";
import { Play, Plus, Check } from "lucide-react";
import axios from "axios";
import { fetchMovies } from "../services/tmdb";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function Home() {
  const navigate = useNavigate();
  const [trending, setTrending] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [actionMovies, setActionMovies] = useState([]);
  const [newReleases, setNewReleases] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      fetchMovies(),
      api.get("/tmdb/movies/discover?page=2"),
      api.get("/tmdb/movies/discover?with_genres=28"), // 28 is Action genre
      api.get("/tmdb/movies/discover?page=3"),
    ])
      .then(([trendingData, recRes, actionRes, newRes]) => {
        const safeArray = (data) => Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
        setTrending(safeArray(trendingData));
        setRecommended(safeArray(recRes?.data));
        setActionMovies(safeArray(actionRes?.data));
        setNewReleases(safeArray(newRes?.data));
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load TMDB movies:", err);
        setIsLoading(false);
      });
  }, []);


  const [heroAdded, setHeroAdded] = useState(false);
  const handleHeroWatchlist = async () => {
    try {
      if (!heroMovie) return;
      const token = localStorage.getItem('access_token');
      if (!token) return alert("Login first");
      if (!heroAdded) {
        await axios.post('http://localhost:8000/watchlist', {
          tmdb_id: heroMovie.id,
          content_type: heroMovie.media_type || "movie"
        }, { headers: { 'Authorization': `Bearer ${token}` } });
        setHeroAdded(true);
      }
    } catch (err) {
      if (err.response?.status === 400) setHeroAdded(true);
    }
  };

  const heroMovie = trending.length > 0 ? trending[0] : null;

  return (
    <div className="home-page-container">
      {/* Cinematic Hero */}
      <section className="unified-hero">
        <div className="hero-backdrop">
          {heroMovie && heroMovie.backdrop_path && (
            <div style={{
              position: 'absolute', inset: 0,
              backgroundImage: `url(https://image.tmdb.org/t/p/original${heroMovie.backdrop_path})`,
              backgroundSize: 'cover', backgroundPosition: 'center', opacity: 0.4
            }}></div>
          )}
          <div className="hero-gradient"></div>
        </div>

        <div className="hero-content">
          {heroMovie ? (
            <>
              <div className="hero-badge">STREAMHUB FEATURED</div>
              <h1 className="hero-title">{heroMovie.title || heroMovie.name || "Unknown"}</h1>
              <div className="hero-meta">
                <span>{heroMovie.release_date ? String(heroMovie.release_date).split('-')[0] : "2026"}</span>
                <span className="rating-badge">{(Number(heroMovie.vote_average || 0) * 10).toFixed(0)}% Match</span>
              </div>
              <p className="hero-description" style={{
                WebkitLineClamp: 3, display: '-webkit-box', WebkitBoxOrient: 'vertical', overflow: 'hidden'
              }}>
                {heroMovie.overview || "No layout description available."}
              </p>
              <div className="hero-actions">
                <button className="btn-primary hero-btn-play" onClick={() => navigate(`/movie/${heroMovie.id}`)}>
                  <Play fill="currentColor" size={20} /> Play
                </button>
                <button className="btn-secondary hero-btn-info" onClick={handleHeroWatchlist}>
                  {heroAdded ? <><Check size={20} /> Added</> : <><Plus size={20} /> Watchlist</>}
                </button>
              </div>
            </>
          ) : (
            <div style={{ paddingBottom: '50px' }}>
              {isLoading ? "Loading featured content..." : "Welcome to StreamHub"}
            </div>
          )}
        </div>
      </section>

      {/* Content Rows */}
      <section className="content-rows-container">
        <ContentRow title="Trending Now" items={trending} isLoading={isLoading} />
        <ContentRow title="Recommended for You" items={recommended} isLoading={isLoading} emptyStateMessage="Your personalized recommendations will appear here." />
        <ContentRow title="Action & Adventure" items={actionMovies} isLoading={isLoading} />
        <ContentRow title="New Releases" items={newReleases} isLoading={isLoading} />
        <ContentRow title="AI Picks" items={[]} isLoading={isLoading} emptyStateMessage="Ask StreamHub AI to generate a curated playlist." />
      </section>
    </div>
  );
}

export default Home;