import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, Film, Tv, Play, Clock, CheckCircle2, RotateCcw } from 'lucide-react';
import api from '../services/api';

const History = () => {
    const navigate = useNavigate();
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // 'all' | 'movie' | 'tv' | 'completed'

    const fetchHistory = async () => {
        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            if (!token) {
                setLoading(false);
                return navigate('/login');
            }

            // 1. Fetch user's watch history from MySQL
            const res = await api.get('/history');
            const items = Array.isArray(res.data) ? res.data : [];

            // 2. Enrich with TMDB metadata for movies and TV shows
            const detailedItems = await Promise.all(items.map(async (item) => {
                try {
                    const endpoint = item.content_type === 'tv'
                        ? `/tmdb/tv/${item.tmdb_id}`
                        : `/tmdb/movies/${item.tmdb_id}`;
                    const mediaRes = await api.get(endpoint);
                    return { ...item, details: mediaRes.data };
                } catch (err) {
                    console.error('Failed to load metadata for', item.tmdb_id);
                    return item;
                }
            }));

            setHistory(detailedItems);
        } catch (err) {
            console.error("Error loading watch history", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, [navigate]);

    const handleRemove = async (tmdb_id) => {
        try {
            await api.delete(`/history/${tmdb_id}`);
            setHistory(prev => prev.filter(i => i.tmdb_id !== tmdb_id));
        } catch (err) {
            console.error("Failed to remove history item", err);
        }
    };

    const formatDate = (isoStr) => {
        if (!isoStr) return '';
        try {
            const d = new Date(isoStr);
            return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
        } catch {
            return '';
        }
    };

    const filteredList = history.filter(item => {
        if (filter === 'movie') return item.content_type === 'movie';
        if (filter === 'tv') return item.content_type === 'tv';
        if (filter === 'completed') return item.completed;
        return true;
    });

    if (loading) {
        return (
            <div style={{ padding: '120px 4%', color: 'var(--text-secondary)', textAlign: 'center' }}>
                <p>Loading your watch history...</p>
            </div>
        );
    }

    return (
        <div style={{ padding: '100px 4% 60px', color: 'var(--text-primary)', minHeight: '80vh' }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '16px',
                marginBottom: '30px'
            }}>
                <div>
                    <h1 style={{ fontSize: '32px', margin: '0 0 6px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Clock size={28} style={{ color: 'var(--accent)' }} /> Watch History
                    </h1>
                    <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '14px' }}>
                        {history.length} {history.length === 1 ? 'title' : 'titles'} watched on StreamHub
                    </p>
                </div>

                {/* Filter Tabs */}
                <div style={{ display: 'flex', gap: '8px', background: 'var(--bg-secondary)', padding: '4px', borderRadius: '10px' }}>
                    <button
                        onClick={() => setFilter('all')}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            border: 'none',
                            cursor: 'pointer',
                            background: filter === 'all' ? 'var(--accent)' : 'transparent',
                            color: 'white',
                            fontSize: '13px',
                            fontWeight: 600
                        }}
                    >
                        All ({history.length})
                    </button>
                    <button
                        onClick={() => setFilter('movie')}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            border: 'none',
                            cursor: 'pointer',
                            background: filter === 'movie' ? 'var(--accent)' : 'transparent',
                            color: 'white',
                            fontSize: '13px',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                        }}
                    >
                        <Film size={14} /> Movies ({history.filter(i => i.content_type === 'movie').length})
                    </button>
                    <button
                        onClick={() => setFilter('tv')}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            border: 'none',
                            cursor: 'pointer',
                            background: filter === 'tv' ? 'var(--accent)' : 'transparent',
                            color: 'white',
                            fontSize: '13px',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                        }}
                    >
                        <Tv size={14} /> Series ({history.filter(i => i.content_type === 'tv').length})
                    </button>
                    <button
                        onClick={() => setFilter('completed')}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            border: 'none',
                            cursor: 'pointer',
                            background: filter === 'completed' ? 'var(--accent)' : 'transparent',
                            color: 'white',
                            fontSize: '13px',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                        }}
                    >
                        <CheckCircle2 size={14} /> Completed ({history.filter(i => i.completed).length})
                    </button>
                </div>
            </div>

            {filteredList.length === 0 ? (
                <div style={{
                    padding: '80px 20px',
                    textAlign: 'center',
                    background: 'var(--bg-secondary)',
                    borderRadius: '16px',
                    border: '1px dashed var(--border)'
                }}>
                    <Clock size={48} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
                    <h3 style={{ margin: '0 0 10px', fontSize: '20px' }}>No watch history found</h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', maxWidth: '400px', margin: '0 auto 24px' }}>
                        Movies and series you stream will automatically appear here to track your progress and personalize recommendations.
                    </p>
                    <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                        <button className="btn-primary" onClick={() => navigate('/movies')}>Explore Movies</button>
                        <button className="btn-secondary" onClick={() => navigate('/tv')}>Explore TV Shows</button>
                    </div>
                </div>
            ) : (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                    gap: '24px'
                }}>
                    {filteredList.map(item => {
                        const title = item.details?.title || item.details?.name || `Title #${item.tmdb_id}`;
                        const poster = item.details?.poster_path;
                        const year = (item.details?.release_date || item.details?.first_air_date || '').substring(0, 4);
                        const rating = item.details?.vote_average ? Number(item.details.vote_average).toFixed(1) : null;
                        const isTv = item.content_type === 'tv';
                        const progressPercent = item.duration_seconds > 0
                            ? Math.min(100, Math.round((item.progress_seconds / item.duration_seconds) * 100))
                            : (item.completed ? 100 : 0);

                        return (
                            <div
                                key={item.id || item.tmdb_id}
                                onClick={() => navigate(isTv ? `/tv/${item.tmdb_id}` : `/movie/${item.tmdb_id}`)}
                                style={{
                                    position: 'relative',
                                    borderRadius: '12px',
                                    overflow: 'hidden',
                                    background: 'var(--bg-secondary)',
                                    border: '1px solid var(--border)',
                                    cursor: 'pointer',
                                    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                                    display: 'flex',
                                    flexDirection: 'column'
                                }}
                                onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-4px)'}
                                onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
                            >
                                <div style={{ position: 'relative', width: '100%', aspectRatio: '2/3', background: 'var(--bg-tertiary)' }}>
                                    {poster ? (
                                        <img
                                            src={`https://image.tmdb.org/t/p/w500${poster}`}
                                            alt={title}
                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                        />
                                    ) : (
                                        <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                                            No Poster
                                        </div>
                                    )}

                                    {/* Media Type Badge */}
                                    <div style={{
                                        position: 'absolute',
                                        top: '10px',
                                        left: '10px',
                                        background: 'rgba(0,0,0,0.75)',
                                        backdropFilter: 'blur(4px)',
                                        padding: '4px 8px',
                                        borderRadius: '6px',
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        color: isTv ? 'var(--accent-hover)' : '#fff',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                    }}>
                                        {isTv ? <Tv size={11} /> : <Film size={11} />}
                                        {isTv ? 'SERIES' : 'MOVIE'}
                                    </div>

                                    {/* Rating Badge */}
                                    {rating && (
                                        <div style={{
                                            position: 'absolute',
                                            top: '10px',
                                            right: '10px',
                                            background: 'rgba(0,0,0,0.75)',
                                            backdropFilter: 'blur(4px)',
                                            padding: '4px 8px',
                                            borderRadius: '6px',
                                            fontSize: '11px',
                                            fontWeight: 'bold',
                                            color: '#f1c40f'
                                        }}>
                                            ★ {rating}
                                        </div>
                                    )}

                                    {/* Completion / Progress Overlay */}
                                    {item.completed ? (
                                        <div style={{
                                            position: 'absolute',
                                            bottom: '8px',
                                            left: '10px',
                                            background: 'rgba(46, 204, 113, 0.9)',
                                            color: 'white',
                                            padding: '3px 8px',
                                            borderRadius: '6px',
                                            fontSize: '11px',
                                            fontWeight: 700,
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '4px'
                                        }}>
                                            <CheckCircle2 size={12} /> Watched
                                        </div>
                                    ) : (
                                        <div style={{
                                            position: 'absolute',
                                            bottom: 0,
                                            left: 0,
                                            width: '100%',
                                            height: '4px',
                                            background: 'rgba(255,255,255,0.2)'
                                        }}>
                                            <div style={{
                                                width: `${progressPercent}%`,
                                                height: '100%',
                                                background: 'var(--accent)'
                                            }} />
                                        </div>
                                    )}
                                </div>

                                <div style={{ padding: '14px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                                    <div>
                                        <h4 style={{
                                            margin: '0 0 6px',
                                            fontSize: '15px',
                                            fontWeight: 600,
                                            whiteSpace: 'nowrap',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis'
                                        }}>
                                            {title}
                                        </h4>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                            <span>{year || 'StreamHub'}</span>
                                            <span>{formatDate(item.last_watched_at)}</span>
                                        </div>
                                    </div>

                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
                                        <span style={{ fontSize: '12px', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                            <Play size={12} fill="currentColor" /> {item.completed ? 'Watch Again' : 'Resume'}
                                        </span>

                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleRemove(item.tmdb_id);
                                            }}
                                            style={{
                                                background: 'rgba(231, 76, 60, 0.15)',
                                                border: '1px solid rgba(231, 76, 60, 0.3)',
                                                color: '#ff6b6b',
                                                borderRadius: '6px',
                                                padding: '5px 10px',
                                                fontSize: '12px',
                                                cursor: 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '4px'
                                            }}
                                            title="Remove from Watch History"
                                        >
                                            <Trash2 size={13} /> Remove
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default History;
