import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Play, Plus, ChevronLeft, Check, Star, Film, X, Clock, Calendar, AlertCircle } from 'lucide-react';
import api from '../services/api';
import MovieCard from '../components/MovieCard';

const MovieDetails = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [inWatchlist, setInWatchlist] = useState(false);
    const [movieDetails, setMovieDetails] = useState(null);
    const [streamMessage, setStreamMessage] = useState(null);
    const [showTrailer, setShowTrailer] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);

    useEffect(() => {
        const fetchDetails = async () => {
            setLoading(true);
            setStreamMessage(null);
            setIsPlaying(false);
            try {
                const res = await api.get(`/tmdb/movies/${id}`);
                setMovieDetails(res.data);

                // Check watchlist status
                const token = localStorage.getItem('access_token') || localStorage.getItem('token');
                if (token) {
                    try {
                        const wlRes = await api.get('/watchlist');
                        if (Array.isArray(wlRes.data)) {
                            const found = wlRes.data.some(i => i.tmdb_id === parseInt(id));
                            setInWatchlist(found);
                        }
                    } catch (e) {
                        // ignore unauthenticated or silent error
                    }
                }
            } catch (err) {
                console.error("Error fetching movie details", err);
            } finally {
                setLoading(false);
            }
        };
        fetchDetails();
    }, [id]);

    const handleWatchlist = async () => {
        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            if (!token) {
                alert('Please sign in to manage your watchlist.');
                return navigate('/login');
            }

            if (!inWatchlist) {
                await api.post('/watchlist', {
                    tmdb_id: parseInt(id),
                    content_type: 'movie'
                });
                setInWatchlist(true);
            } else {
                await api.delete(`/watchlist/${id}`);
                setInWatchlist(false);
            }
        } catch (err) {
            console.error("Watchlist error", err);
        }
    };

    const handleWatchNow = async () => {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token');
        if (!token) {
            alert("Please sign in to stream content.");
            return navigate('/login');
        }

        try {
            const res = await api.post('/subscription/entitlement/check', {
                content_id: parseInt(id),
                content_type: 'movie'
            });

            if (res.data.allowed) {
                // Record history progress
                try {
                    await api.post('/history', {
                        tmdb_id: parseInt(id),
                        content_type: 'movie',
                        progress_seconds: 1,
                        duration_seconds: (movieDetails?.runtime || 120) * 60,
                        completed: false
                    });
                } catch (e) {
                    console.warn("History recording failed", e);
                }

                setStreamMessage({ type: 'success', text: `Playback Authorized (${res.data.plan}). Starting Stream...` });
                setIsPlaying(true);
            } else {
                setStreamMessage({
                    type: 'error',
                    text: res.data.message || 'StreamHub subscription required to stream this movie.'
                });
                setTimeout(() => navigate('/subscription'), 2200);
            }
        } catch (err) {
            setStreamMessage({ type: 'error', text: 'Entitlement check failed. Redirecting to subscription plans...' });
            setTimeout(() => navigate('/subscription'), 2200);
        }
    };

    if (loading) {
        return (
            <div style={{ padding: '120px 4%', color: 'var(--text-secondary)', textAlign: 'center' }}>
                <div style={{ fontSize: '18px' }}>Loading movie details...</div>
            </div>
        );
    }

    if (!movieDetails) {
        return (
            <div style={{ padding: '120px 4%', color: 'var(--text-secondary)', textAlign: 'center' }}>
                <h2>Movie Not Found</h2>
                <Link to="/movies" className="btn-primary" style={{ marginTop: '20px', display: 'inline-block' }}>
                    Browse Movies
                </Link>
            </div>
        );
    }

    // Extract cast, director, trailer, and similar
    const cast = movieDetails.credits?.cast?.slice(0, 10) || [];
    const director = movieDetails.credits?.crew?.find(c => c.job === 'Director')?.name;
    const trailer = movieDetails.videos?.results?.find(v => v.type === 'Trailer' && v.site === 'YouTube') ||
                    movieDetails.videos?.results?.find(v => v.site === 'YouTube');
    const similarMovies = movieDetails.similar?.results?.slice(0, 6) ||
                          movieDetails.recommendations?.results?.slice(0, 6) || [];

    const hours = Math.floor((movieDetails.runtime || 0) / 60);
    const minutes = (movieDetails.runtime || 0) % 60;
    const runtimeStr = movieDetails.runtime ? `${hours > 0 ? `${hours}h ` : ''}${minutes}m` : null;

    return (
        <div style={{ color: 'var(--text-primary)', paddingBottom: '100px' }}>
            {/* Hero Backdrop Banner */}
            <div style={{
                position: 'relative',
                minHeight: '65vh',
                background: 'var(--bg-secondary)',
                display: 'flex',
                alignItems: 'flex-end',
                padding: '0 4% 50px'
            }}>
                {movieDetails.backdrop_path && (
                    <div style={{
                        position: 'absolute',
                        inset: 0,
                        background: `url(https://image.tmdb.org/t/p/original${movieDetails.backdrop_path}) center/cover no-repeat`,
                        opacity: 0.35
                    }} />
                )}
                <div style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'linear-gradient(to top, var(--bg-primary) 10%, rgba(15,15,20,0.6) 60%, transparent 100%)'
                }} />

                <div style={{
                    position: 'relative',
                    zIndex: 10,
                    display: 'flex',
                    gap: '40px',
                    alignItems: 'flex-end',
                    flexWrap: 'wrap',
                    width: '100%'
                }}>
                    {/* Poster */}
                    <div style={{
                        width: '220px',
                        aspectRatio: '2/3',
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-md)',
                        boxShadow: '0 15px 35px rgba(0,0,0,0.7)',
                        overflow: 'hidden',
                        flexShrink: 0
                    }}>
                        {movieDetails.poster_path ? (
                            <img
                                src={`https://image.tmdb.org/t/p/w500${movieDetails.poster_path}`}
                                alt={movieDetails.title}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            />
                        ) : (
                            <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-muted)' }}>
                                No Poster
                            </div>
                        )}
                    </div>

                    {/* Metadata & Actions */}
                    <div style={{ maxWidth: '800px', flex: 1 }}>
                        <Link
                            to="/movies"
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                color: 'var(--accent-hover)',
                                textDecoration: 'none',
                                marginBottom: '16px',
                                fontSize: '14px'
                            }}
                        >
                            <ChevronLeft size={16} /> Back to Movies
                        </Link>

                        <h1 style={{ fontSize: '42px', margin: '0 0 12px', fontWeight: 800, letterSpacing: '-0.5px' }}>
                            {movieDetails.title}
                        </h1>

                        <div style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: '16px',
                            color: 'var(--text-secondary)',
                            marginBottom: '20px',
                            fontSize: '14px',
                            alignItems: 'center'
                        }}>
                            {movieDetails.vote_average > 0 && (
                                <span style={{ color: 'var(--accent-hover)', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <Star size={15} fill="currentColor" />
                                    {Number(movieDetails.vote_average).toFixed(1)} / 10
                                </span>
                            )}
                            {movieDetails.release_date && (
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <Calendar size={14} />
                                    {movieDetails.release_date.substring(0, 4)}
                                </span>
                            )}
                            {runtimeStr && (
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <Clock size={14} />
                                    {runtimeStr}
                                </span>
                            )}
                            {movieDetails.genres?.length > 0 && (
                                <span>{movieDetails.genres.map(g => g.name).join(', ')}</span>
                            )}
                            {director && (
                                <span>Dir: <strong style={{ color: 'var(--text-primary)' }}>{director}</strong></span>
                            )}
                        </div>

                        <p style={{
                            lineHeight: 1.65,
                            color: 'var(--text-secondary)',
                            marginBottom: '28px',
                            fontSize: '15px',
                            maxWidth: '750px'
                        }}>
                            {movieDetails.overview || "No overview available for this title."}
                        </p>

                        {/* Entitlement / Stream status notification banner */}
                        {streamMessage && (
                            <div style={{
                                padding: '12px 18px',
                                borderRadius: '8px',
                                marginBottom: '20px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px',
                                background: streamMessage.type === 'success' ? 'rgba(46, 204, 113, 0.15)' : 'rgba(231, 76, 60, 0.15)',
                                border: `1px solid ${streamMessage.type === 'success' ? '#2ecc71' : '#e74c3c'}`,
                                color: streamMessage.type === 'success' ? '#2ecc71' : '#ff6b6b',
                                fontSize: '14px'
                            }}>
                                <AlertCircle size={18} />
                                {streamMessage.text}
                            </div>
                        )}

                        {/* Primary Action Buttons */}
                        <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
                            <button
                                className="btn-primary"
                                style={{ padding: '12px 30px', display: 'flex', alignItems: 'center', gap: '8px' }}
                                onClick={handleWatchNow}
                            >
                                <Play fill="currentColor" size={18} /> Watch Now
                            </button>

                            <button
                                className="btn-secondary"
                                style={{
                                    padding: '12px 24px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    background: inWatchlist ? 'rgba(46, 204, 113, 0.2)' : undefined,
                                    borderColor: inWatchlist ? '#2ecc71' : undefined,
                                    color: inWatchlist ? '#2ecc71' : undefined
                                }}
                                onClick={handleWatchlist}
                            >
                                {inWatchlist ? <Check size={18} /> : <Plus size={18} />}
                                {inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}
                            </button>

                            {trailer && (
                                <button
                                    className="btn-secondary"
                                    style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: '8px' }}
                                    onClick={() => setShowTrailer(true)}
                                >
                                    <Film size={18} /> Trailer
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Active Streaming Player (When authorized & playing) */}
            {isPlaying && (
                <div style={{
                    margin: '30px 4%',
                    background: '#000',
                    borderRadius: '16px',
                    padding: '24px',
                    border: '1px solid var(--border)',
                    boxShadow: '0 20px 40px rgba(0,0,0,0.8)'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#2ecc71', display: 'inline-block' }} />
                            <h3 style={{ margin: 0, fontSize: '18px' }}>Now Streaming: {movieDetails.title} (4K Ultra HD)</h3>
                        </div>
                        <button
                            onClick={() => setIsPlaying(false)}
                            style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
                        >
                            <X size={20} />
                        </button>
                    </div>

                    {trailer ? (
                        <div style={{ position: 'relative', paddingTop: '56.25%', borderRadius: '8px', overflow: 'hidden' }}>
                            <iframe
                                src={`https://www.youtube.com/embed/${trailer.key}?autoplay=1&controls=1`}
                                title={movieDetails.title}
                                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowFullScreen
                            />
                        </div>
                    ) : (
                        <div style={{ height: '360px', background: 'var(--bg-secondary)', borderRadius: '8px', display: 'grid', placeItems: 'center', color: 'var(--text-secondary)' }}>
                            <div style={{ textAlign: 'center' }}>
                                <Play size={48} style={{ marginBottom: '12px', opacity: 0.8 }} />
                                <p>StreamHub Master Stream Active. Buffer ready.</p>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Trailer Modal */}
            {showTrailer && trailer && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(0,0,0,0.85)',
                    backdropFilter: 'blur(8px)',
                    zIndex: 10000,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '20px'
                }}>
                    <div style={{
                        width: '100%',
                        maxWidth: '900px',
                        background: 'var(--bg-elevated)',
                        borderRadius: '16px',
                        overflow: 'hidden',
                        boxShadow: '0 25px 60px rgba(0,0,0,0.9)',
                        border: '1px solid var(--border)'
                    }}>
                        <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ margin: 0, fontSize: '18px' }}>Official Trailer - {movieDetails.title}</h3>
                            <button
                                onClick={() => setShowTrailer(false)}
                                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex' }}
                            >
                                <X size={20} />
                            </button>
                        </div>
                        <div style={{ position: 'relative', paddingTop: '56.25%' }}>
                            <iframe
                                src={`https://www.youtube.com/embed/${trailer.key}?autoplay=1`}
                                title="Trailer"
                                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowFullScreen
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* Cast & Crew Section */}
            {cast.length > 0 && (
                <div style={{ padding: '40px 4%' }}>
                    <h3 style={{ marginBottom: '20px', fontSize: '20px', fontWeight: 700 }}>Top Cast & Crew</h3>
                    <div style={{ display: 'flex', gap: '18px', overflowX: 'auto', paddingBottom: '12px' }}>
                        {cast.map(c => (
                            <div key={c.id} style={{ width: '120px', flexShrink: 0, textAlign: 'center' }}>
                                <div style={{
                                    width: '100px',
                                    height: '100px',
                                    borderRadius: '50%',
                                    overflow: 'hidden',
                                    margin: '0 auto 10px',
                                    background: 'var(--bg-tertiary)',
                                    boxShadow: '0 4px 10px rgba(0,0,0,0.4)'
                                }}>
                                    {c.profile_path ? (
                                        <img
                                            src={`https://image.tmdb.org/t/p/w185${c.profile_path}`}
                                            alt={c.name}
                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                        />
                                    ) : (
                                        <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                                            No Image
                                        </div>
                                    )}
                                </div>
                                <p style={{ margin: '0', fontSize: '13px', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {c.name}
                                </p>
                                <p style={{ margin: '3px 0 0', fontSize: '11px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {c.character}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Similar Movies Section */}
            {similarMovies.length > 0 && (
                <div style={{ padding: '20px 4%' }}>
                    <h3 style={{ marginBottom: '20px', fontSize: '20px', fontWeight: 700 }}>More Like This</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '20px' }}>
                        {similarMovies.map(movie => (
                            <MovieCard key={movie.id} movie={movie} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default MovieDetails;
