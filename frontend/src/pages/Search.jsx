import React, { useState, useEffect } from 'react';
import { Search as SearchIcon, X, Film, Tv, Music, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import MovieCard from '../components/MovieCard';
import api from '../services/api';

const Search = () => {
    const navigate = useNavigate();
    const [query, setQuery] = useState("");
    const [debouncedQuery, setDebouncedQuery] = useState("");
    const [isSearching, setIsSearching] = useState(false);

    const [movieResults, setMovieResults] = useState([]);
    const [tvResults, setTvResults] = useState([]);
    const [songResults, setSongResults] = useState([]);
    const [artistResults, setArtistResults] = useState([]);
    const [hasSearched, setHasSearched] = useState(false);

    // Debounce query
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedQuery(query);
        }, 350);
        return () => clearTimeout(handler);
    }, [query]);

    // Cross-category search fetch
    useEffect(() => {
        if (!debouncedQuery.trim()) {
            setMovieResults([]);
            setTvResults([]);
            setSongResults([]);
            setArtistResults([]);
            setHasSearched(false);
            return;
        }

        const performSearch = async () => {
            setIsSearching(true);
            setHasSearched(true);
            try {
                const [mRes, tvRes, sRes, artRes] = await Promise.all([
                    api.get('/tmdb/movies/search', { params: { query: debouncedQuery.trim() } }).catch(() => ({ data: { results: [] } })),
                    api.get('/tmdb/tv/search', { params: { query: debouncedQuery.trim() } }).catch(() => ({ data: { results: [] } })),
                    api.get('/music/songs', { params: { search: debouncedQuery.trim(), limit: 6 } }).catch(() => ({ data: [] })),
                    api.get('/music/artists', { params: { search: debouncedQuery.trim(), limit: 6 } }).catch(() => ({ data: [] }))
                ]);

                setMovieResults(mRes.data?.results || []);
                setTvResults(tvRes.data?.results || []);
                setSongResults(sRes.data || []);
                setArtistResults(artRes.data || []);
            } catch (err) {
                console.error("Search error", err);
            } finally {
                setIsSearching(false);
            }
        };

        performSearch();
    }, [debouncedQuery]);

    const totalResults = movieResults.length + tvResults.length + songResults.length + artistResults.length;

    return (
        <div style={{ padding: '40px 4% 100px', color: 'var(--text-primary)', minHeight: 'calc(100vh - 70px)' }}>
            {/* Search Input Bar */}
            <div style={{
                display: 'flex', alignItems: 'center', background: 'var(--bg-secondary)',
                border: '1px solid var(--border)', borderRadius: 'var(--radius-pill)',
                padding: '0 24px', height: '60px', maxWidth: '800px', margin: '0 auto 40px',
                boxShadow: 'var(--glass-shadow)', transition: '0.3s'
            }}>
                <SearchIcon size={22} color="var(--text-secondary)" />
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search movies, TV shows, songs, and artists..."
                    style={{
                        flex: 1, background: 'transparent', border: 'none', color: 'white',
                        fontSize: '17px', padding: '0 16px', outline: 'none'
                    }}
                    autoFocus
                />
                {query && (
                    <button
                        onClick={() => setQuery("")}
                        style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex' }}
                    >
                        <X size={20} />
                    </button>
                )}
            </div>

            {/* Loading State */}
            {isSearching && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '20px' }}>
                    {[1, 2, 3, 4, 5, 6].map(i => <MovieCard key={i} isLoading={true} />)}
                </div>
            )}

            {/* Empty State */}
            {!isSearching && hasSearched && totalResults === 0 && (
                <div style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: '80px' }}>
                    <h2>No results found for "{debouncedQuery}"</h2>
                    <p style={{ marginTop: '8px' }}>Try checking your spelling or searching for a different movie, show, or song.</p>
                </div>
            )}

            {/* Initial State */}
            {!hasSearched && !isSearching && (
                <div style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: '80px' }}>
                    <p style={{ fontSize: '18px' }}>Find your next favorite movie, show, or song across StreamHub.</p>
                </div>
            )}

            {/* Results Sections */}
            {!isSearching && totalResults > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '40px' }}>
                    {/* MOVIES */}
                    {movieResults.length > 0 && (
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
                                <Film size={20} color="var(--accent)" />
                                <h3 style={{ fontSize: '20px', margin: 0 }}>Movies ({movieResults.length})</h3>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '20px' }}>
                                {movieResults.slice(0, 10).map(m => (
                                    <MovieCard key={m.id} movie={m} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* TV SHOWS */}
                    {tvResults.length > 0 && (
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
                                <Tv size={20} color="var(--accent)" />
                                <h3 style={{ fontSize: '20px', margin: 0 }}>TV Shows ({tvResults.length})</h3>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '20px' }}>
                                {tvResults.slice(0, 10).map(t => (
                                    <MovieCard key={t.id} movie={t} isTv={true} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* MUSIC SONGS */}
                    {songResults.length > 0 && (
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
                                <Music size={20} color="var(--accent)" />
                                <h3 style={{ fontSize: '20px', margin: 0 }}>Tracks ({songResults.length})</h3>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {songResults.map(s => (
                                    <div
                                        key={s.id}
                                        onClick={() => navigate('/music')}
                                        style={{
                                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                            padding: '12px 18px', background: 'var(--bg-secondary)', borderRadius: '8px',
                                            border: '1px solid var(--border)', cursor: 'pointer'
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                            <img src={s.cover_image} alt={s.title} style={{ width: '40px', height: '40px', borderRadius: '4px', objectFit: 'cover' }} />
                                            <div>
                                                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{s.title}</div>
                                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{s.artist_name} • {s.genre}</div>
                                            </div>
                                        </div>
                                        <button style={{ color: 'var(--accent)', fontSize: '13px', fontWeight: 600 }}>
                                            Play on Music
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* ARTISTS */}
                    {artistResults.length > 0 && (
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
                                <User size={20} color="var(--accent)" />
                                <h3 style={{ fontSize: '20px', margin: 0 }}>Artists ({artistResults.length})</h3>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '20px' }}>
                                {artistResults.map(a => (
                                    <div
                                        key={a.id}
                                        onClick={() => navigate('/music')}
                                        style={{
                                            textAlign: 'center', padding: '16px', background: 'var(--bg-secondary)',
                                            borderRadius: '12px', border: '1px solid var(--border)', cursor: 'pointer'
                                        }}
                                    >
                                        <img src={a.image_url} alt={a.name} style={{ width: '90px', height: '90px', borderRadius: '50%', objectFit: 'cover', margin: '0 auto 10px' }} />
                                        <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{a.name}</div>
                                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Featured Artist</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default Search;
