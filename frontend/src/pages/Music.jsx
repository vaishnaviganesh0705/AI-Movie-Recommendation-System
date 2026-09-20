import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Square, X, Heart, Music2, Disc, User, Volume2, SkipBack, SkipForward, Search } from 'lucide-react';
import api from '../services/api';
import '../styles/Music.css';

const Music = () => {
    const [activeTab, setActiveTab] = useState('songs'); // 'songs', 'artists', 'albums', 'liked'
    const [songs, setSongs] = useState([]);
    const [artists, setArtists] = useState([]);
    const [albums, setAlbums] = useState([]);
    const [likedSongIds, setLikedSongIds] = useState(new Set());
    const [genres, setGenres] = useState([]);
    const [selectedGenre, setSelectedGenre] = useState('All');
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);

    // Audio Player State
    const [currentSong, setCurrentSong] = useState(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume] = useState(0.8);

    // Ref to the single DOM audio element
    const audioRef = useRef(null);

    // Ref to avoid stale closure on audio 'ended'
    const handleNextRef = useRef(null);

    // Fetch Initial Data
    useEffect(() => {
        const fetchMusic = async () => {
            setLoading(true);
            try {
                const [songsRes, artistsRes, albumsRes, genresRes] = await Promise.all([
                    api.get('/music/songs'),
                    api.get('/music/artists'),
                    api.get('/music/albums'),
                    api.get('/music/genres')
                ]);

                setSongs(songsRes.data || []);
                setArtists(artistsRes.data || []);
                setAlbums(albumsRes.data || []);
                setGenres(genresRes.data || []);

                // Liked songs if user logged in
                const token = localStorage.getItem('access_token') || localStorage.getItem('token');
                if (token) {
                    try {
                        const likedRes = await api.get('/music/liked');
                        if (Array.isArray(likedRes.data)) {
                            setLikedSongIds(new Set(likedRes.data.map(s => s.id)));
                        }
                    } catch (e) {}
                }
            } catch (err) {
                console.error("Failed to load music data", err);
            } finally {
                setLoading(false);
            }
        };

        fetchMusic();
    }, []);

    // Filtered Songs
    useEffect(() => {
        const fetchFiltered = async () => {
            try {
                const res = await api.get('/music/songs', {
                    params: {
                        genre: selectedGenre !== 'All' ? selectedGenre : undefined,
                        search: searchQuery || undefined
                    }
                });
                setSongs(res.data || []);
            } catch (err) {
                console.error("Error filtering songs", err);
            }
        };
        const timer = setTimeout(fetchFiltered, 250);
        return () => clearTimeout(timer);
    }, [selectedGenre, searchQuery]);

    // Setup and cleanup audio element
    useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;

        window.__STREAMHUB_AUDIO__ = audio;
        audio.volume = volume;

        const onPlay = () => setIsPlaying(true);
        const onPause = () => setIsPlaying(false);
        const onTimeUpdate = () => setCurrentTime(audio.currentTime);
        const onLoadedMetadata = () => setDuration(audio.duration || 0);
        const onEnded = () => {
            setIsPlaying(false);
            if (handleNextRef.current) {
                handleNextRef.current();
            }
        };

        audio.addEventListener('play', onPlay);
        audio.addEventListener('pause', onPause);
        audio.addEventListener('timeupdate', onTimeUpdate);
        audio.addEventListener('loadedmetadata', onLoadedMetadata);
        audio.addEventListener('ended', onEnded);

        return () => {
            // STOP ALL AUDIO when navigating away from the page
            if (window.stopAllStreamHubAudio) {
                window.stopAllStreamHubAudio();
            } else {
                try {
                    audio.pause();
                    audio.currentTime = 0;
                    audio.src = '';
                } catch (e) {}
            }
            audio.removeEventListener('play', onPlay);
            audio.removeEventListener('pause', onPause);
            audio.removeEventListener('timeupdate', onTimeUpdate);
            audio.removeEventListener('loadedmetadata', onLoadedMetadata);
            audio.removeEventListener('ended', onEnded);
        };
    }, []);

    const playSong = (song) => {
        if (!song?.audio_url) return;
        const audio = audioRef.current;
        if (!audio) return;

        // If clicking the current song, toggle play/pause
        if (currentSong?.id === song.id) {
            if (!audio.paused) {
                audio.pause();
                setIsPlaying(false);
            } else {
                audio.play().catch(e => console.log("Play interrupted:", e));
                setIsPlaying(true);
            }
            return;
        }

        // Switching tracks: FIRST STOP ALL AUDIO completely
        if (window.stopAllStreamHubAudio) {
            window.stopAllStreamHubAudio();
        } else {
            audio.pause();
            audio.currentTime = 0;
        }

        setCurrentSong(song);
        audio.src = song.audio_url;
        audio.load();
        audio.play().then(() => {
            setIsPlaying(true);
        }).catch(e => {
            console.log("Audio playback error:", e);
        });
    };

    const handlePlayPause = () => {
        const audio = audioRef.current;
        if (!audio) return;

        if (!currentSong && songs.length > 0) {
            playSong(songs[0]);
            return;
        }

        if (!audio.paused) {
            audio.pause();
            setIsPlaying(false);
            if (window.__streamhub_audio_channel) {
                try {
                    window.__streamhub_audio_channel.postMessage({ action: 'PAUSE' });
                } catch (e) {}
            }
        } else {
            audio.play().catch(e => console.log("Play error:", e));
            setIsPlaying(true);
        }
    };

    const handleStop = () => {
        // Stop every single audio source in the browser
        if (window.stopAllStreamHubAudio) {
            window.stopAllStreamHubAudio();
        }

        const audio = audioRef.current;
        if (audio) {
            try {
                audio.pause();
                audio.currentTime = 0;
                audio.src = '';
            } catch (e) {}
        }

        // Notify other tabs to stop
        if (window.__streamhub_audio_channel) {
            try {
                window.__streamhub_audio_channel.postMessage({ action: 'STOP' });
            } catch (e) {}
        }

        setIsPlaying(false);
        setCurrentTime(0);
    };

    const handleClosePlayer = () => {
        handleStop();
        setCurrentSong(null);
    };

    const handleNext = () => {
        if (!currentSong || songs.length === 0) return;
        const currentIndex = songs.findIndex(s => s.id === currentSong.id);
        const nextIndex = (currentIndex + 1) % songs.length;
        playSong(songs[nextIndex]);
    };
    handleNextRef.current = handleNext;

    const handlePrev = () => {
        if (!currentSong || songs.length === 0) return;
        const currentIndex = songs.findIndex(s => s.id === currentSong.id);
        const prevIndex = (currentIndex - 1 + songs.length) % songs.length;
        playSong(songs[prevIndex]);
    };

    const handleSeek = (e) => {
        const seekTime = parseFloat(e.target.value);
        if (audioRef.current) {
            audioRef.current.currentTime = seekTime;
        }
        setCurrentTime(seekTime);
    };

    const handleVolumeChange = (e) => {
        const newVol = parseFloat(e.target.value);
        setVolume(newVol);
        if (audioRef.current) {
            audioRef.current.volume = newVol;
        }
    };

    const toggleLike = async (e, songId) => {
        e.stopPropagation();
        const token = localStorage.getItem('access_token') || localStorage.getItem('token');
        if (!token) return alert('Please log in to save your favorite songs.');

        try {
            const res = await api.post(`/music/liked/${songId}`);
            setLikedSongIds(prev => {
                const next = new Set(prev);
                if (res.data.liked) next.add(songId);
                else next.delete(songId);
                return next;
            });
        } catch (err) {
            console.error("Like toggle failed", err);
        }
    };

    const formatTime = (seconds) => {
        if (!seconds || isNaN(seconds)) return "0:00";
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    };

    const likedSongs = songs.filter(s => likedSongIds.has(s.id));

    return (
        <div className="music-page-container">
            {/* Real DOM HTML5 Audio Element */}
            <audio
                id="streamhub-master-audio"
                ref={audioRef}
                preload="metadata"
                style={{ display: 'none' }}
            />

            <div className="music-header">
                <h1 className="music-title">StreamHub Music</h1>
                <p className="music-subtitle">Stream high-fidelity film scores, charts, and exclusive original soundtracks</p>
            </div>

            {/* Navigation Tabs */}
            <div className="music-tabs">
                <button
                    onClick={() => setActiveTab('songs')}
                    className={`music-tab-btn ${activeTab === 'songs' ? 'active' : ''}`}
                >
                    <Music2 size={14} style={{ marginRight: '6px' }} /> All Tracks
                </button>
                <button
                    onClick={() => setActiveTab('artists')}
                    className={`music-tab-btn ${activeTab === 'artists' ? 'active' : ''}`}
                >
                    <User size={14} style={{ marginRight: '6px' }} /> Artists
                </button>
                <button
                    onClick={() => setActiveTab('albums')}
                    className={`music-tab-btn ${activeTab === 'albums' ? 'active' : ''}`}
                >
                    <Disc size={14} style={{ marginRight: '6px' }} /> Albums
                </button>
                <button
                    onClick={() => setActiveTab('liked')}
                    className={`music-tab-btn ${activeTab === 'liked' ? 'active' : ''}`}
                >
                    <Heart size={14} style={{ marginRight: '6px' }} /> My Favorites ({likedSongIds.size})
                </button>
            </div>

            {/* Genre Filter Pills */}
            {activeTab === 'songs' && genres.length > 0 && (
                <div className="genre-pills">
                    {genres.map(g => (
                        <button
                            key={g}
                            onClick={() => setSelectedGenre(g)}
                            className={`genre-pill ${selectedGenre === g ? 'active' : ''}`}
                        >
                            {g}
                        </button>
                    ))}
                </div>
            )}

            {/* Search Box */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                borderRadius: '8px', padding: '10px 16px', maxWidth: '450px', marginBottom: '25px'
            }}>
                <Search size={18} color="var(--text-muted)" />
                <input
                    type="text"
                    placeholder="Filter songs by title or keyword..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    style={{ background: 'transparent', border: 'none', color: 'white', outline: 'none', width: '100%', fontSize: '14px' }}
                />
            </div>

            {/* Content Tabs */}
            {activeTab === 'songs' && (
                <div className="songs-list">
                    {loading ? (
                        <p style={{ color: 'var(--text-secondary)' }}>Loading catalog...</p>
                    ) : songs.length === 0 ? (
                        <p style={{ color: 'var(--text-secondary)' }}>No songs found matching your search.</p>
                    ) : (
                        songs.map((s, idx) => (
                            <div
                                key={s.id}
                                className={`song-row ${currentSong?.id === s.id && isPlaying ? 'playing' : ''}`}
                                onClick={() => playSong(s)}
                            >
                                <div className="song-left">
                                    <span style={{ color: 'var(--text-muted)', fontSize: '13px', width: '20px' }}>
                                        {idx + 1}
                                    </span>
                                    <img src={s.cover_image || s.artist_image} alt={s.title} className="song-cover" />
                                    <div className="song-info">
                                        <div className="song-title">{s.title}</div>
                                        <div className="song-artist">{s.artist_name} • {s.album_title}</div>
                                    </div>
                                </div>

                                <div className="song-right">
                                    <span className="song-genre">{s.genre}</span>
                                    <span className="song-duration">{formatTime(s.duration_seconds)}</span>
                                    <button
                                        onClick={(e) => toggleLike(e, s.id)}
                                        style={{ color: likedSongIds.has(s.id) ? 'var(--accent-danger)' : 'var(--text-muted)', cursor: 'pointer', background: 'none', border: 'none' }}
                                        title={likedSongIds.has(s.id) ? "Unlike" : "Like"}
                                    >
                                        <Heart size={18} fill={likedSongIds.has(s.id) ? 'currentColor' : 'none'} />
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); playSong(s); }}
                                        style={{ color: currentSong?.id === s.id && isPlaying ? 'var(--accent)' : 'white', cursor: 'pointer', background: 'none', border: 'none', display: 'flex', alignItems: 'center' }}
                                        title={currentSong?.id === s.id && isPlaying ? "Pause" : "Play"}
                                    >
                                        {currentSong?.id === s.id && isPlaying ? <Pause size={18} /> : <Play size={18} fill="currentColor" />}
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}

            {activeTab === 'artists' && (
                <div className="artists-grid">
                    {artists.map(a => (
                        <div key={a.id} className="artist-card" onClick={() => { setSearchQuery(a.name); setActiveTab('songs'); }}>
                            <img src={a.image_url} alt={a.name} className="artist-avatar" />
                            <h3 style={{ fontSize: '15px', margin: '0 0 4px' }}>{a.name}</h3>
                            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)' }}>{a.songs_count} Tracks</p>
                        </div>
                    ))}
                </div>
            )}

            {activeTab === 'albums' && (
                <div className="albums-grid">
                    {albums.map(alb => (
                        <div key={alb.id} className="album-card" onClick={() => { setSearchQuery(alb.title); setActiveTab('songs'); }}>
                            <img src={alb.cover_image_url} alt={alb.title} className="album-cover" />
                            <div className="album-meta">
                                <h4 style={{ margin: '0 0 4px', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{alb.title}</h4>
                                <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)' }}>{alb.artist_name} • {alb.year}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {activeTab === 'liked' && (
                <div className="songs-list">
                    {likedSongs.length === 0 ? (
                        <p style={{ color: 'var(--text-secondary)' }}>No favorite tracks saved yet.</p>
                    ) : (
                        likedSongs.map((s, idx) => (
                            <div key={s.id} className="song-row" onClick={() => playSong(s)}>
                                <div className="song-left">
                                    <span style={{ color: 'var(--text-muted)', fontSize: '13px', width: '20px' }}>{idx + 1}</span>
                                    <img src={s.cover_image} alt={s.title} className="song-cover" />
                                    <div className="song-info">
                                        <div className="song-title">{s.title}</div>
                                        <div className="song-artist">{s.artist_name}</div>
                                    </div>
                                </div>
                                <div className="song-right">
                                    <span className="song-duration">{formatTime(s.duration_seconds)}</span>
                                    <button onClick={(e) => toggleLike(e, s.id)} style={{ color: 'var(--accent-danger)', background: 'none', border: 'none', cursor: 'pointer' }}>
                                        <Heart size={18} fill="currentColor" />
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); playSong(s); }}
                                        style={{ color: currentSong?.id === s.id && isPlaying ? 'var(--accent)' : 'white', cursor: 'pointer', background: 'none', border: 'none', display: 'flex', alignItems: 'center' }}
                                    >
                                        {currentSong?.id === s.id && isPlaying ? <Pause size={18} /> : <Play size={18} fill="currentColor" />}
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* Floating Audio Player Bar */}
            {currentSong && (
                <div className="audio-player-bar">
                    <div className="player-track-info">
                        <img src={currentSong.cover_image || currentSong.artist_image} alt={currentSong.title} style={{ width: '48px', height: '48px', borderRadius: '6px', objectFit: 'cover' }} />
                        <div style={{ minWidth: 0 }}>
                            <div style={{ fontSize: '13px', fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {currentSong.title}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {currentSong.artist_name}
                            </div>
                        </div>
                    </div>

                    <div className="player-controls">
                        <div className="player-buttons">
                            <button onClick={handlePrev} title="Previous track" style={{ color: 'var(--text-secondary)', cursor: 'pointer', background: 'none', border: 'none', display: 'flex' }}>
                                <SkipBack size={18} />
                            </button>
                            <button onClick={handlePlayPause} title={isPlaying ? "Pause" : "Play"} className="player-play-btn">
                                {isPlaying ? <Pause size={18} /> : <Play size={18} fill="currentColor" />}
                            </button>
                            <button onClick={handleStop} title="Stop playback" style={{ color: 'var(--text-secondary)', cursor: 'pointer', background: 'none', border: 'none', display: 'flex', padding: '6px' }}>
                                <Square size={16} fill="currentColor" />
                            </button>
                            <button onClick={handleNext} title="Next track" style={{ color: 'var(--text-secondary)', cursor: 'pointer', background: 'none', border: 'none', display: 'flex' }}>
                                <SkipForward size={18} />
                            </button>
                        </div>

                        <div className="progress-bar-container">
                            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{formatTime(currentTime)}</span>
                            <input
                                type="range"
                                min="0"
                                max={duration || 100}
                                value={currentTime}
                                onChange={handleSeek}
                                className="progress-slider"
                            />
                            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{formatTime(duration)}</span>
                        </div>
                    </div>

                    <div className="player-volume">
                        <Volume2 size={18} color="var(--text-secondary)" />
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.05"
                            value={volume}
                            onChange={handleVolumeChange}
                            className="volume-slider"
                        />
                        <button
                            onClick={handleClosePlayer}
                            title="Close player"
                            style={{
                                background: 'rgba(255,255,255,0.08)',
                                border: 'none',
                                color: 'var(--text-secondary)',
                                cursor: 'pointer',
                                padding: '6px',
                                borderRadius: '50%',
                                display: 'flex',
                                marginLeft: '12px'
                            }}
                        >
                            <X size={15} />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Music;
