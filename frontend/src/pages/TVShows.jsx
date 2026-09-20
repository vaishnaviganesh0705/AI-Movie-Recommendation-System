import React, { useState, useEffect, useCallback } from 'react';
import { Search, Tv, RefreshCw } from 'lucide-react';
import MovieCard from '../components/MovieCard';
import api from '../services/api';
import '../styles/TVShows.css';

const TVShows = () => {
    const [shows, setShows] = useState([]);
    const [genres, setGenres] = useState([]);
    const [languages, setLanguages] = useState([]);

    const [activeTab, setActiveTab] = useState('popular'); // popular, trending, top_rated, airing_today
    const [selectedGenre, setSelectedGenre] = useState('');
    const [selectedLanguage, setSelectedLanguage] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [error, setError] = useState(null);

    // Fetch genres & languages
    useEffect(() => {
        const fetchFilters = async () => {
            try {
                const [genreRes, langRes] = await Promise.all([
                    api.get('/tmdb/tv/genres'),
                    api.get('/tmdb/languages')
                ]);
                setGenres(Array.isArray(genreRes.data) ? genreRes.data : []);
                setLanguages(Array.isArray(langRes.data) ? langRes.data : []);
            } catch (err) {
                console.error("Failed to load TV genres", err);
            }
        };
        fetchFilters();
    }, []);

    // Main fetch function
    const fetchTVData = useCallback(async (pageNum = 1, append = false) => {
        if (pageNum === 1) setIsLoading(true);
        else setIsLoadingMore(true);
        setError(null);

        try {
            let res;
            if (searchQuery.trim()) {
                res = await api.get('/tmdb/tv/search', {
                    params: { query: searchQuery.trim(), page: pageNum }
                });
            } else if (selectedGenre || selectedLanguage) {
                res = await api.get('/tmdb/tv/discover', {
                    params: {
                        page: pageNum,
                        with_genres: selectedGenre || undefined,
                        with_original_language: selectedLanguage || undefined
                    }
                });
            } else {
                // Route to active tab endpoint
                const endpointMap = {
                    popular: '/tmdb/tv/popular',
                    trending: '/tmdb/tv/trending',
                    top_rated: '/tmdb/tv/top-rated',
                    airing_today: '/tmdb/tv/airing-today'
                };
                const endpoint = endpointMap[activeTab] || '/tmdb/tv/popular';
                res = await api.get(endpoint, { params: { page: pageNum } });
            }

            const results = res.data?.results || [];
            setTotalPages(res.data?.total_pages || 1);

            if (append) {
                setShows(prev => [...prev, ...results]);
            } else {
                setShows(results);
            }
        } catch (err) {
            console.error("Error loading TV shows", err);
            setError("Unable to load TV shows at this time.");
        } finally {
            setIsLoading(false);
            setIsLoadingMore(false);
        }
    }, [activeTab, searchQuery, selectedGenre, selectedLanguage]);

    useEffect(() => {
        setPage(1);
        const timer = setTimeout(() => {
            fetchTVData(1, false);
        }, 300);
        return () => clearTimeout(timer);
    }, [fetchTVData]);

    const handleLoadMore = () => {
        if (page < totalPages && !isLoadingMore) {
            const next = page + 1;
            setPage(next);
            fetchTVData(next, true);
        }
    };

    const handleTabChange = (tab) => {
        setActiveTab(tab);
        setSearchQuery('');
        setSelectedGenre('');
        setSelectedLanguage('');
    };

    return (
        <div className="tv-page-container">
            <div className="tv-header">
                <h1 className="tv-title">TV Series & Shows</h1>
                <p className="tv-subtitle">Binge-worthy drama, comedy, anime, and blockbuster streaming series</p>
            </div>

            {/* Category Tabs */}
            <div className="tv-tabs">
                {[
                    { key: 'popular', label: 'Popular Shows' },
                    { key: 'trending', label: 'Trending This Week' },
                    { key: 'top_rated', label: 'Top Rated' },
                    { key: 'airing_today', label: 'Airing Today' }
                ].map(tab => (
                    <button
                        key={tab.key}
                        onClick={() => handleTabChange(tab.key)}
                        className={`tv-tab-btn ${activeTab === tab.key && !searchQuery ? 'active' : ''}`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Filter Bar */}
            <div className="tv-filter-bar">
                <div className="tv-search-box">
                    <Search size={18} color="var(--text-muted)" />
                    <input
                        type="text"
                        placeholder="Search TV series by name..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                    />
                </div>

                <select
                    className="filter-select"
                    value={selectedGenre}
                    onChange={e => setSelectedGenre(e.target.value)}
                    disabled={!!searchQuery}
                >
                    <option value="">All Genres</option>
                    {genres.map(g => (
                        <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                </select>

                <select
                    className="filter-select"
                    value={selectedLanguage}
                    onChange={e => setSelectedLanguage(e.target.value)}
                    disabled={!!searchQuery}
                >
                    <option value="">All Languages</option>
                    {languages.map(l => (
                        <option key={l.code} value={l.code}>{l.name}</option>
                    ))}
                </select>
            </div>

            {/* Error state */}
            {error && (
                <div style={{ background: 'rgba(255, 76, 76, 0.1)', border: '1px solid var(--accent-danger)', padding: '16px', borderRadius: '8px', marginBottom: '24px', textAlign: 'center' }}>
                    <p style={{ color: 'var(--accent-danger)', margin: '0 0 10px' }}>{error}</p>
                    <button onClick={() => fetchTVData(1, false)} className="btn-primary" style={{ padding: '6px 16px', fontSize: '13px' }}>
                        Retry
                    </button>
                </div>
            )}

            {/* Shows Grid */}
            <div className="tv-grid">
                {isLoading ? (
                    Array.from({ length: 12 }).map((_, idx) => (
                        <MovieCard key={idx} isLoading={true} isTv={true} />
                    ))
                ) : shows.length === 0 ? (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '80px 20px', color: 'var(--text-secondary)' }}>
                        <Tv size={48} color="var(--text-muted)" style={{ marginBottom: '16px' }} />
                        <h3>No TV shows found</h3>
                        <p>Try searching for a different title or clearing your genre/language filters.</p>
                    </div>
                ) : (
                    shows.map((s, idx) => (
                        <MovieCard key={s.id || idx} movie={s} isTv={true} />
                    ))
                )}
            </div>

            {/* Load More Button */}
            {!isLoading && shows.length > 0 && page < totalPages && (
                <div className="load-more-container" style={{ display: 'flex', justifyContent: 'center' }}>
                    <button
                        onClick={handleLoadMore}
                        className="load-more-btn"
                        disabled={isLoadingMore}
                    >
                        {isLoadingMore ? (
                            <>
                                <RefreshCw size={16} className="spin" /> Loading more shows...
                            </>
                        ) : (
                            'Load More TV Shows'
                        )}
                    </button>
                </div>
            )}
        </div>
    );
};

export default TVShows;
