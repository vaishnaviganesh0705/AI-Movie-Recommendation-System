import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, RefreshCw, Film } from 'lucide-react';
import MovieCard from '../components/MovieCard';
import api from '../services/api';
import '../styles/Movies.css';

const Movies = () => {
    const [movies, setMovies] = useState([]);
    const [genres, setGenres] = useState([]);
    const [languages, setLanguages] = useState([]);

    const [selectedGenre, setSelectedGenre] = useState('');
    const [selectedLanguage, setSelectedLanguage] = useState('');
    const [selectedSort, setSelectedSort] = useState('popularity.desc');
    const [selectedYear, setSelectedYear] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [error, setError] = useState(null);

    // Fetch available genres and languages on mount
    useEffect(() => {
        const fetchFilters = async () => {
            try {
                const [genreRes, langRes] = await Promise.all([
                    api.get('/tmdb/genres'),
                    api.get('/tmdb/languages')
                ]);
                setGenres(Array.isArray(genreRes.data) ? genreRes.data : []);
                setLanguages(Array.isArray(langRes.data) ? langRes.data : []);
            } catch (err) {
                console.error("Failed to fetch genres/languages", err);
            }
        };
        fetchFilters();
    }, []);

    // Main fetch movies function
    const fetchMoviesData = useCallback(async (pageNum = 1, append = false) => {
        if (pageNum === 1) setIsLoading(true);
        else setIsLoadingMore(true);
        setError(null);

        try {
            let res;
            if (searchQuery.trim()) {
                res = await api.get('/tmdb/movies/search', {
                    params: {
                        query: searchQuery.trim(),
                        page: pageNum
                    }
                });
            } else {
                res = await api.get('/tmdb/movies/discover', {
                    params: {
                        page: pageNum,
                        with_genres: selectedGenre || undefined,
                        with_original_language: selectedLanguage || undefined,
                        sort_by: selectedSort,
                        year: selectedYear || undefined
                    }
                });
            }

            const results = res.data?.results || [];
            setTotalPages(res.data?.total_pages || 1);

            if (append) {
                setMovies(prev => [...prev, ...results]);
            } else {
                setMovies(results);
            }
        } catch (err) {
            console.error("Error fetching movies", err);
            setError("Unable to load movies. Please check your connection and try again.");
        } finally {
            setIsLoading(false);
            setIsLoadingMore(false);
        }
    }, [searchQuery, selectedGenre, selectedLanguage, selectedSort, selectedYear]);

    // Re-fetch on filter change
    useEffect(() => {
        setPage(1);
        const debounceTimer = setTimeout(() => {
            fetchMoviesData(1, false);
        }, 300);
        return () => clearTimeout(debounceTimer);
    }, [fetchMoviesData]);

    const handleLoadMore = () => {
        if (page < totalPages && !isLoadingMore) {
            const nextPage = page + 1;
            setPage(nextPage);
            fetchMoviesData(nextPage, true);
        }
    };

    const handleReset = () => {
        setSelectedGenre('');
        setSelectedLanguage('');
        setSelectedSort('popularity.desc');
        setSelectedYear('');
        setSearchQuery('');
        setPage(1);
    };

    return (
        <div className="movies-page-container">
            <div className="movies-header">
                <h1 className="movies-title">Explore Movies</h1>
                <p className="movies-subtitle">Discover thousands of movies with real-time filters and curated collections</p>
            </div>

            {/* Filter Bar */}
            <div className="movies-filter-bar">
                <div className="movies-search-box">
                    <Search size={18} color="var(--text-muted)" />
                    <input
                        type="text"
                        placeholder="Search movies by title..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                    />
                </div>

                {/* Genre Filter */}
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

                {/* Language Filter */}
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

                {/* Year Filter */}
                <select
                    className="filter-select"
                    value={selectedYear}
                    onChange={e => setSelectedYear(e.target.value)}
                    disabled={!!searchQuery}
                >
                    <option value="">All Years</option>
                    {[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2015, 2010, 2000].map(yr => (
                        <option key={yr} value={yr}>{yr}</option>
                    ))}
                </select>

                {/* Sort Order */}
                <select
                    className="filter-select"
                    value={selectedSort}
                    onChange={e => setSelectedSort(e.target.value)}
                    disabled={!!searchQuery}
                >
                    <option value="popularity.desc">Most Popular</option>
                    <option value="vote_average.desc">Top Rated</option>
                    <option value="primary_release_date.desc">Newest Releases</option>
                    <option value="original_title.asc">Title (A-Z)</option>
                </select>

                {(selectedGenre || selectedLanguage || selectedYear || searchQuery || selectedSort !== 'popularity.desc') && (
                    <button onClick={handleReset} className="filter-select" style={{ color: 'var(--accent)' }}>
                        Reset Filters
                    </button>
                )}
            </div>

            {/* Error Message */}
            {error && (
                <div style={{ background: 'rgba(255, 76, 76, 0.1)', border: '1px solid var(--accent-danger)', padding: '16px', borderRadius: '8px', marginBottom: '24px', textAlign: 'center' }}>
                    <p style={{ color: 'var(--accent-danger)', margin: '0 0 10px' }}>{error}</p>
                    <button onClick={() => fetchMoviesData(1, false)} className="btn-primary" style={{ padding: '6px 16px', fontSize: '13px' }}>
                        Retry
                    </button>
                </div>
            )}

            {/* Movies Grid */}
            <div className="movies-grid">
                {isLoading ? (
                    Array.from({ length: 12 }).map((_, idx) => (
                        <MovieCard key={idx} isLoading={true} />
                    ))
                ) : movies.length === 0 ? (
                    <div className="movies-empty-state" style={{ gridColumn: '1 / -1' }}>
                        <Film size={48} color="var(--text-muted)" style={{ marginBottom: '16px' }} />
                        <h3>No movies found</h3>
                        <p>Try adjusting your search query, genre, or language filters.</p>
                        <button onClick={handleReset} className="reset-filters-btn">
                            Clear Filters
                        </button>
                    </div>
                ) : (
                    movies.map((m, idx) => (
                        <MovieCard key={m.id || idx} movie={m} />
                    ))
                )}
            </div>

            {/* Load More Button */}
            {!isLoading && movies.length > 0 && page < totalPages && (
                <div className="load-more-container">
                    <button
                        onClick={handleLoadMore}
                        className="load-more-btn"
                        disabled={isLoadingMore}
                    >
                        {isLoadingMore ? (
                            <>
                                <RefreshCw size={16} className="spin" /> Loading more movies...
                            </>
                        ) : (
                            'Load More Movies'
                        )}
                    </button>
                </div>
            )}
        </div>
    );
};

export default Movies;
