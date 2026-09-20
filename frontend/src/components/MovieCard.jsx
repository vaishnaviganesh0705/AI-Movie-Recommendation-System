import React, { useState } from 'react';
import { Play, Plus, Star, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import './MovieCard.css';

const MovieCard = ({ movie, isLoading, isTv = false, onClick }) => {
    const navigate = useNavigate();
    const [added, setAdded] = useState(false);

    if (isLoading) {
        return (
            <div className="movie-card skeleton-card">
                <div className="skeleton-image pulse"></div>
                <div className="skeleton-text short pulse"></div>
                <div className="skeleton-text medium pulse"></div>
            </div>
        );
    }

    if (!movie) return null;

    const movieId = movie.id || movie.tmdb_id;
    const isTvContent = isTv || movie.media_type === "tv" || !!movie.first_air_date;

    const handleCardClick = () => {
        if (onClick) {
            onClick(movie);
            return;
        }
        if (movieId) {
            if (isTvContent) {
                navigate(`/tv/${movieId}`);
            } else {
                navigate(`/movie/${movieId}`);
            }
        }
    };

    const handleWatchlist = async (e) => {
        e.stopPropagation();
        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            if (!token) return alert('Please login first to add to your watchlist.');

            if (!added) {
                await api.post('/watchlist', {
                    tmdb_id: movieId,
                    content_type: isTvContent ? "tv" : "movie"
                });
                setAdded(true);
            }
        } catch (err) {
            if (err.response?.status === 400) setAdded(true);
        }
    };

    const handlePlayClick = (e) => {
        e.stopPropagation();
        handleCardClick();
    };

    // Fallbacks for TMDB data
    const title = movie.title || movie.name || "Unknown Title";
    const posterUrl = movie.poster_path
        ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
        : (movie.image || null);
    const rating = movie.vote_average != null ? Number(movie.vote_average).toFixed(1) : (movie.rating || "NR");
    const year = movie.release_date ? String(movie.release_date).split('-')[0] :
        (movie.first_air_date ? String(movie.first_air_date).split('-')[0] : "2026");

    return (
        <div className="movie-card" onClick={handleCardClick} style={{ cursor: 'pointer' }}>
            <div className="movie-poster-wrapper">
                {posterUrl ? (
                    <img src={posterUrl} alt={title} className="movie-poster" loading="lazy" />
                ) : (
                    <div className="movie-poster-placeholder">
                        <span>{title}</span>
                    </div>
                )}

                <div className="movie-overlay">
                    <button className="movie-play-btn" onClick={handlePlayClick} title="Play">
                        <Play size={22} fill="currentColor" />
                    </button>
                    <button className="movie-watchlist-btn" onClick={handleWatchlist} title="Add to Watchlist">
                        {added ? <Check size={22} /> : <Plus size={22} />}
                    </button>
                </div>
            </div>

            <div className="movie-metadata">
                <h3 className="movie-title">{title}</h3>
                <div className="movie-stats">
                    <span className="movie-rating"><Star size={12} fill="currentColor" /> {rating}</span>
                    <span className="movie-divider">•</span>
                    <span className="movie-year">{year}</span>
                    {movie.runtime ? (
                        <>
                            <span className="movie-divider">•</span>
                            <span className="movie-year">{movie.runtime}m</span>
                        </>
                    ) : null}
                </div>
            </div>
        </div>
    );
};

export default MovieCard;
