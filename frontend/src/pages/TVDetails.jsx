import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Play, Plus, ChevronLeft, Check, Star, Tv } from 'lucide-react';
import api from '../services/api';
import MovieCard from '../components/MovieCard';

const TVDetails = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [inWatchlist, setInWatchlist] = useState(false);
    const [tvDetails, setTvDetails] = useState(null);
    const [streamMessage, setStreamMessage] = useState(null);

    useEffect(() => {
        const fetchDetails = async () => {
            setLoading(true);
            try {
                const res = await api.get(`/tmdb/tv/${id}`);
                setTvDetails(res.data);

                // Watchlist check
                const token = localStorage.getItem('access_token') || localStorage.getItem('token');
                if (token) {
                    try {
                        const wlRes = await api.get('/watchlist');
                        if (Array.isArray(wlRes.data)) {
                            const found = wlRes.data.some(i => i.tmdb_id === parseInt(id));
                            setInWatchlist(found);
                        }
                    } catch (e) {}
                }
            } catch (err) {
                console.error("Error fetching TV details", err);
            } finally {
                setLoading(false);
            }
        };
        fetchDetails();
    }, [id]);

    const handleWatchlist = async () => {
        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            if (!token) return alert('Please login first to manage your watchlist.');

            if (!inWatchlist) {
                await api.post('/watchlist', {
                    tmdb_id: parseInt(id),
                    content_type: 'tv'
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
                content_type: 'tv'
            });

            if (res.data.allowed) {
                // Record history
                await api.post('/history', {
                    tmdb_id: parseInt(id),
                    content_type: 'tv',
                    progress_seconds: 1,
                    duration_seconds: 3600,
                    completed: false
                });
                setStreamMessage({ type: 'success', text: `Streaming Authorized (${res.data.plan}). Playing Episode 1...` });
            } else {
                setStreamMessage({ type: 'error', text: res.data.message || 'Subscription required to stream this show.' });
                setTimeout(() => navigate('/subscription'), 2000);
            }
        } catch (err) {
            setStreamMessage({ type: 'error', text: 'Entitlement check error. Redirecting to plans...' });
            setTimeout(() => navigate('/subscription'), 2000);
        }
    };

    if (loading) {
        return <div style={{ padding: '120px 4%', color: 'var(--text-secondary)' }}>Loading series details...</div>;
    }

    if (!tvDetails) {
        return (
            <div style={{ padding: '120px 4%', color: 'var(--text-secondary)', textAlign: 'center' }}>
                <h2>Series Not Found</h2>
                <Link to="/tv" className="btn-primary" style={{ marginTop: '20px' }}>Back to TV Shows</Link>
            </div>
        );
    }

    const title = tvDetails.name || tvDetails.original_name || "Unknown Series";
    const cast = tvDetails.credits?.cast?.slice(0, 10) || [];
    const similar = tvDetails.similar?.results?.slice(0, 6) || [];

    return (
        <div style={{ color: 'var(--text-primary)', paddingBottom: '100px' }}>
            {/* Hero Backdrop */}
            <div style={{
                position: 'relative', minHeight: '65vh',
                background: 'var(--bg-secondary)',
                display: 'flex', alignItems: 'flex-end', padding: '0 4% 50px'
            }}>
                {tvDetails.backdrop_path && (
                    <div style={{
                        position: 'absolute', inset: 0,
                        background: `url(https://image.tmdb.org/t/p/original${tvDetails.backdrop_path}) center/cover`,
                        opacity: 0.35
                    }}></div>
                )}
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, var(--bg-primary) 15%, transparent 90%)' }}></div>

                <div style={{ position: 'relative', zIndex: 10, display: 'flex', gap: '40px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    <div style={{ width: '220px', aspectRatio: '2/3', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', boxShadow: '0 10px 30px rgba(0,0,0,0.6)', overflow: 'hidden' }}>
                        {tvDetails.poster_path ? (
                            <img src={`https://image.tmdb.org/t/p/w500${tvDetails.poster_path}`}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }} alt={title} />
                        ) : (
                            <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center' }}>No Poster</div>
                        )}
                    </div>

                    <div style={{ maxWidth: '750px' }}>
                        <Link to="/tv" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: 'var(--accent-hover)', textDecoration: 'none', marginBottom: '15px' }}>
                            <ChevronLeft size={16} /> Back to TV Shows
                        </Link>
                        <h1 style={{ fontSize: '42px', margin: '0 0 12px', fontWeight: 800 }}>{title}</h1>

                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '15px', color: 'var(--text-secondary)', marginBottom: '18px', fontSize: '14px', alignItems: 'center' }}>
                            <span style={{ color: 'var(--accent-hover)', fontWeight: 'bold' }}>
                                <Star size={14} fill="currentColor" style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                                {tvDetails.vote_average ? Number(tvDetails.vote_average).toFixed(1) : 'NR'} Rating
                            </span>
                            <span>{tvDetails.first_air_date?.substring(0, 4)}</span>
                            {tvDetails.number_of_seasons && <span>{tvDetails.number_of_seasons} Season{tvDetails.number_of_seasons > 1 ? 's' : ''}</span>}
                            <span>{tvDetails.genres?.map(g => g.name).join(', ')}</span>
                        </div>

                        <p style={{ lineHeight: 1.6, color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '15px' }}>
                            {tvDetails.overview || "No overview available for this series."}
                        </p>

                        {streamMessage && (
                            <div style={{
                                padding: '10px 16px', borderRadius: '6px', marginBottom: '16px',
                                background: streamMessage.type === 'success' ? 'rgba(46, 204, 113, 0.2)' : 'rgba(231, 76, 60, 0.2)',
                                border: `1px solid ${streamMessage.type === 'success' ? '#2ecc71' : '#e74c3c'}`,
                                color: streamMessage.type === 'success' ? '#2ecc71' : '#e74c3c'
                            }}>
                                {streamMessage.text}
                            </div>
                        )}

                        <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
                            <button className="btn-primary" style={{ padding: '12px 28px' }} onClick={handleWatchNow}>
                                <Play fill="currentColor" size={18} /> Watch Now
                            </button>
                            <button className="btn-secondary" style={{ padding: '12px 22px', display: 'flex', alignItems: 'center', gap: '6px' }} onClick={handleWatchlist}>
                                {inWatchlist ? <Check size={18} /> : <Plus size={18} />}
                                {inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Cast & Characters */}
            {cast.length > 0 && (
                <div style={{ padding: '40px 4%' }}>
                    <h3 style={{ marginBottom: '20px', fontSize: '20px' }}>Cast & Characters</h3>
                    <div style={{ display: 'flex', gap: '18px', overflowX: 'auto', paddingBottom: '10px' }}>
                        {cast.map(c => (
                            <div key={c.id} style={{ width: '120px', flexShrink: 0, textAlign: 'center' }}>
                                <div style={{ width: '100px', height: '100px', borderRadius: '50%', overflow: 'hidden', margin: '0 auto 10px', background: 'var(--bg-tertiary)' }}>
                                    {c.profile_path ? (
                                        <img src={`https://image.tmdb.org/t/p/w185${c.profile_path}`} alt={c.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                    ) : (
                                        <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-muted)' }}>Photo</div>
                                    )}
                                </div>
                                <p style={{ margin: '0', fontSize: '13px', fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</p>
                                <p style={{ margin: '0', fontSize: '11px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.character}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Similar Series */}
            {similar.length > 0 && (
                <div style={{ padding: '20px 4%' }}>
                    <h3 style={{ marginBottom: '20px', fontSize: '20px' }}>More Like This</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '20px' }}>
                        {similar.map(s => (
                            <MovieCard key={s.id} movie={s} isTv={true} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TVDetails;
