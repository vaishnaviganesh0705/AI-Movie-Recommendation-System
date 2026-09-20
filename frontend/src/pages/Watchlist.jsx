import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, Film, Tv, Play, PlusCircle } from 'lucide-react';
import api from '../services/api';

const Watchlist = () => {
    const navigate = useNavigate();
    const [watchlist, setWatchlist] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // 'all' | 'movie' | 'tv'

    useEffect(() => {
        const fetchWatchlist = async () => {
            try {
                const token = localStorage.getItem('access_token') || localStorage.getItem('token');
                if (!token) {
                    setLoading(false);
                    return navigate('/login');
                }

                // 1) Fetch user's saved items from database
                const res = await api.get('/watchlist');
                const items = Array.isArray(res.data) ? res.data : [];

                // 2) Enrich with TMDB metadata for movies and TV shows
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

                setWatchlist(detailedItems);
            } catch (err) {
                console.error("Error loading watchlist", err);
            } finally {
                setLoading(false);
            }
        };

        fetchWatchlist();
    }, [navigate]);

    const handleRemove = async (tmdb_id) => {
        try {
            await api.delete(`/watchlist/${tmdb_id}`);
            setWatchlist(prev => prev.filter(i => i.tmdb_id !== tmdb_id));
        } catch (err) {
            console.error("Failed to remove item", err);
        }
    };

    const filteredList = watchlist.filter(item => {
        if (filter === 'movie') return item.content_type === 'movie';
        if (filter === 'tv') return item.content_type === 'tv';
        return true;
    });

    if (loading) {
        return (
            <div style={{ padding: '120px 4%', color: 'var(--text-secondary)', textAlign: 'center' }}>
                <p>Loading your saved watchlist...</p>
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
                    <h1 style={{ fontSize: '32px', margin: '0 0 6px', fontWeight: 800 }}>My Watchlist</h1>
                    <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '14px' }}>
                        {watchlist.length} {watchlist.length === 1 ? 'title' : 'titles'} saved to watch later
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
                        All ({watchlist.length})
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
                        <Film size={14} /> Movies ({watchlist.filter(i => i.content_type === 'movie').length})
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
                        <Tv size={14} /> Series ({watchlist.filter(i => i.content_type === 'tv').length})
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
                    <PlusCircle size={48} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
                    <h3 style={{ margin: '0 0 10px', fontSize: '20px' }}>No titles in this list</h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', maxWidth: '400px', margin: '0 auto 24px' }}>
                        Discover trending movies and popular series to add to your personal queue.
                    </p>
                    <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                        <button className="btn-primary" onClick={() => navigate('/movies')}>Explore Movies</button>
                        <button className="btn-secondary" onClick={() => navigate('/tv')}>Explore TV Shows</button>
                    </div>
                </div>
            ) : (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                    gap: '24px'
                }}>
                    {filteredList.map(item => {
                        const title = item.details?.title || item.details?.name || 'Untitled';
                        const poster = item.details?.poster_path;
                        const year = (item.details?.release_date || item.details?.first_air_date || '').substring(0, 4);
                        const rating = item.details?.vote_average ? Number(item.details.vote_average).toFixed(1) : null;
                        const isTv = item.content_type === 'tv';

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
                                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                                            {year || 'StreamHub'}
                                        </span>
                                    </div>

                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
                                        <span style={{ fontSize: '12px', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                            <Play size={12} fill="currentColor" /> Watch
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
                                            title="Remove from Watchlist"
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

export default Watchlist;
