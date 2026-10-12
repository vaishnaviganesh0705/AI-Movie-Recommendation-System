import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import {
    X, Send, Sparkles, Bot, User as UserIcon, RotateCcw,
    ExternalLink, Plus, Check, Film, Trash2, MessageSquare,
    PanelLeftClose, PanelLeft, Clock
} from 'lucide-react';
import api from '../services/api';

const QUICK_PROMPTS = [
    "Tell me about Interstellar",
    "Show Tamil comedy movies under 2 hours",
    "Movies similar to Inception",
    "Top trending movies tonight",
    "Who directed Interstellar?",
    "Recommend sci-fi thriller movies",
    "What is the plot of Leo?"
];

const INITIAL_MESSAGE = {
    text: "Hello! I am the StreamHub TMDB & Subtitle RAG Agent. I can answer questions about Interstellar from its real dialogue subtitles, search movies & TV shows, filter by verified runtimes and languages, explore cast & similar titles, and manage your watchlist. What would you like to explore?",
    sender: 'ai',
    agent: 'StreamHub Agent'
};

const ChatModal = ({ onClose }) => {
    const navigate = useNavigate();
    const [messages, setMessages] = useState([INITIAL_MESSAGE]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [conversationState, setConversationState] = useState(null);
    const [watchlistAdded, setWatchlistAdded] = useState({});

    // Conversation Memory & Sidebar State
    const [conversations, setConversations] = useState([]);
    const [activeConversationId, setActiveConversationId] = useState(() => {
        try {
            const saved = localStorage.getItem('active_conversation_id');
            return saved ? Number(saved) : null;
        } catch (e) {
            return null;
        }
    });
    const [showSidebar, setShowSidebar] = useState(true);
    const [isLoadingConversations, setIsLoadingConversations] = useState(false);
    const [isLoadingConversation, setIsLoadingConversation] = useState(false);
    const [conversationLoadError, setConversationLoadError] = useState(null);

    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading, isLoadingConversation]);

    // Fetch user conversations list
    const fetchConversations = async () => {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token');
        if (!token) return;
        setIsLoadingConversations(true);
        try {
            const res = await api.get('/chat/conversations');
            if (Array.isArray(res.data)) {
                setConversations(res.data);
            }
        } catch (err) {
            console.error("[ChatHistory] Failed to load chat conversations", err);
        } finally {
            setIsLoadingConversations(false);
        }
    };

    // Load conversation messages from backend by ID
    const loadConversation = async (convId) => {
        const numericId = Number(convId);
        if (!numericId) return;

        if (process.env.NODE_ENV === 'development' || import.meta.env?.DEV) {
            console.log(`[ChatHistory] Fetching conversation ID: ${numericId} from /chat/conversations/${numericId}`);
        }

        setIsLoadingConversation(true);
        setConversationLoadError(null);

        try {
            const res = await api.get(`/chat/conversations/${numericId}`);
            const data = res.data;
            if (!data || typeof data !== 'object') {
                throw new Error("Invalid conversation data received from server.");
            }

            setActiveConversationId(numericId);
            try {
                localStorage.setItem('active_conversation_id', String(numericId));
            } catch (e) {}

            setConversationState(null);

            if (Array.isArray(data.messages) && data.messages.length > 0) {
                setMessages(data.messages.map(m => ({
                    text: m.content || '',
                    sender: m.role === 'user' ? 'user' : 'ai',
                    agent: m.agent_name || (m.role === 'user' ? 'User' : 'StreamHub Agent'),
                    type: 'text'
                })));
            } else {
                setMessages([INITIAL_MESSAGE]);
            }
        } catch (err) {
            console.error("[ChatHistory] Failed to load conversation details:", err);
            const status = err.response?.status;
            let errMsg = "Failed to load conversation.";
            if (status === 404) {
                errMsg = "Conversation not found or has been deleted.";
                try { localStorage.removeItem('active_conversation_id'); } catch (e) {}
                setActiveConversationId(null);
            } else if (status === 403) {
                errMsg = "You are not authorized to view this conversation.";
                try { localStorage.removeItem('active_conversation_id'); } catch (e) {}
                setActiveConversationId(null);
            } else if (status === 401) {
                errMsg = "Your session expired. Please sign in again.";
            } else if (err.message) {
                errMsg = err.message;
            }
            setConversationLoadError(errMsg);
        } finally {
            setIsLoadingConversation(false);
        }
    };

    // Initialize conversations on mount and restore active conversation if persisted
    useEffect(() => {
        let isMounted = true;
        const initChat = async () => {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            if (!token) return;

            setIsLoadingConversations(true);
            try {
                const res = await api.get('/chat/conversations');
                if (!isMounted) return;

                if (Array.isArray(res.data)) {
                    setConversations(res.data);

                    // If a persisted active conversation ID exists, check if it's in the user's conversations
                    const savedId = localStorage.getItem('active_conversation_id');
                    if (savedId) {
                        const numId = Number(savedId);
                        const exists = res.data.some(c => c.id === numId);
                        if (exists) {
                            await loadConversation(numId);
                        } else {
                            try { localStorage.removeItem('active_conversation_id'); } catch (e) {}
                            if (isMounted) setActiveConversationId(null);
                        }
                    }
                }
            } catch (err) {
                console.error("[ChatHistory] Failed to initialize chat conversations", err);
            } finally {
                if (isMounted) setIsLoadingConversations(false);
            }
        };

        initChat();
        return () => { isMounted = false; };
    }, []);

    // Switch to selected conversation
    const handleSelectConversation = (convId) => {
        const numericId = Number(convId);
        if (!numericId) return;
        if (activeConversationId === numericId && !conversationLoadError) return;
        if (isLoadingConversation) return;
        loadConversation(numericId);
    };

    // Start a fresh, clean chat session
    const handleNewChat = () => {
        setActiveConversationId(null);
        try {
            localStorage.removeItem('active_conversation_id');
        } catch (e) {}
        setConversationState(null);
        setConversationLoadError(null);
        setMessages([INITIAL_MESSAGE]);
    };

    // Delete a conversation permanently with confirmation
    const handleDeleteConversation = async (convId, e) => {
        if (e && e.stopPropagation) e.stopPropagation();
        const numericId = Number(convId);
        if (!numericId) return;

        if (!window.confirm("Are you sure you want to delete this chat conversation?")) {
            return;
        }

        try {
            await api.delete(`/chat/conversations/${numericId}`);
            setConversations(prev => prev.filter(c => c.id !== numericId));
            if (activeConversationId === numericId) {
                handleNewChat();
            }
        } catch (err) {
            console.error("[ChatHistory] Failed to delete conversation", err);
            alert("Could not delete conversation. Please try again.");
        }
    };

    const handleSend = async (messageText = null) => {
        const queryText = (messageText || input).trim();
        if (!queryText) return;

        const updatedMessages = [...messages, { text: queryText, sender: 'user' }];
        setMessages(updatedMessages);
        setInput('');
        setIsLoading(true);
        setConversationLoadError(null);

        try {
            const res = await api.post('/chat', {
                prompt: queryText,
                conversation_id: activeConversationId,
                state: conversationState
            });

            // Update active conversation ID and refresh list if a new thread was created
            if (res.data.conversation_id) {
                const newId = Number(res.data.conversation_id);
                setActiveConversationId(newId);
                try {
                    localStorage.setItem('active_conversation_id', String(newId));
                } catch (e) {}
                fetchConversations();
            }

            if (res.data.state) {
                setConversationState(res.data.state);
            }

            setMessages(prev => [
                ...prev,
                {
                    text: res.data.response,
                    sender: 'ai',
                    agent: res.data.agent || 'Movie Agent',
                    type: res.data.type,
                    results: res.data.results || res.data.movies || [],
                    songs: res.data.songs || [],
                    action: res.data.action,
                    data: res.data.data
                }
            ]);
        } catch (err) {
            console.error('Chat error', err);
            let rawDetail = err.response?.data?.detail;
            let errDetail = "Network Error";
            if (typeof rawDetail === 'string') {
                errDetail = rawDetail;
            } else if (Array.isArray(rawDetail)) {
                errDetail = rawDetail.map(e => e.msg || e.loc?.join('.') || JSON.stringify(e)).join(', ');
            } else if (rawDetail && typeof rawDetail === 'object') {
                errDetail = JSON.stringify(rawDetail);
            } else if (err.message) {
                errDetail = err.message;
            }

            setMessages(prev => [
                ...prev,
                {
                    text: `Sorry, I encountered an issue communicating with the agent network: ${errDetail}`,
                    sender: 'ai',
                    agent: 'System Alert'
                }
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleResetChat = () => {
        handleNewChat();
    };

    const handleWatchlistToggle = async (movie) => {
        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            if (!token) return alert('Please sign in to manage your watchlist.');

            const id = movie.id;
            if (!watchlistAdded[id]) {
                await api.post('/watchlist', {
                    tmdb_id: id,
                    content_type: movie.content_type || 'movie'
                });
                setWatchlistAdded(prev => ({ ...prev, [id]: true }));
            } else {
                await api.delete(`/watchlist/${id}`);
                setWatchlistAdded(prev => ({ ...prev, [id]: false }));
            }
        } catch (err) {
            console.error("Watchlist action failed", err);
        }
    };

    const renderMovieCards = (results) => {
        if (!results || results.length === 0) return null;

        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
                {results.slice(0, 5).map((m, idx) => (
                    <div
                        key={m.id || idx}
                        style={{
                            display: 'flex',
                            gap: '12px',
                            background: 'rgba(255, 255, 255, 0.04)',
                            border: '1px solid rgba(255, 255, 255, 0.08)',
                            borderRadius: '12px',
                            padding: '10px',
                            alignItems: 'center',
                            transition: 'background 0.2s ease'
                        }}
                    >
                        {/* Poster */}
                        <div style={{ width: '50px', height: '75px', borderRadius: '6px', overflow: 'hidden', background: 'var(--bg-tertiary)', flexShrink: 0 }}>
                            {m.poster_path ? (
                                <img
                                    src={`https://image.tmdb.org/t/p/w200${m.poster_path}`}
                                    alt={m.title}
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                />
                            ) : (
                                <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: '10px' }}>
                                    <Film size={18} />
                                </div>
                            )}
                        </div>

                        {/* Info & Actions */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <h4 style={{
                                margin: '0 0 4px',
                                fontSize: '13.5px',
                                fontWeight: 700,
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                color: 'white'
                            }}>
                                {m.title}
                            </h4>

                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px', alignItems: 'center' }}>
                                {m.rating && (
                                    <span style={{ color: '#f1c40f', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '2px' }}>
                                        ★ {m.rating}
                                    </span>
                                )}
                                {m.release_date && <span>{m.release_date.substring(0, 4)}</span>}
                                {m.runtime && <span style={{ color: 'var(--accent-hover)' }}>{m.runtime}m</span>}
                                {m.genres?.length > 0 && <span>{m.genres.slice(0, 2).join(', ')}</span>}
                            </div>

                            <div style={{ display: 'flex', gap: '8px' }}>
                                <button
                                    onClick={() => {
                                        onClose();
                                        navigate(`/movie/${m.id}`);
                                    }}
                                    style={{
                                        padding: '5px 10px',
                                        borderRadius: '6px',
                                        background: 'var(--accent)',
                                        color: 'white',
                                        border: 'none',
                                        fontSize: '11px',
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                    }}
                                >
                                    <ExternalLink size={11} /> View Details
                                </button>

                                <button
                                    onClick={() => handleWatchlistToggle(m)}
                                    style={{
                                        padding: '5px 10px',
                                        borderRadius: '6px',
                                        background: watchlistAdded[m.id] ? 'rgba(46, 204, 113, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                                        border: `1px solid ${watchlistAdded[m.id] ? '#2ecc71' : 'rgba(255, 255, 255, 0.15)'}`,
                                        color: watchlistAdded[m.id] ? '#2ecc71' : 'white',
                                        fontSize: '11px',
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                    }}
                                >
                                    {watchlistAdded[m.id] ? <Check size={11} /> : <Plus size={11} />}
                                    {watchlistAdded[m.id] ? 'In Watchlist' : 'Watchlist'}
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    return createPortal(
        <div style={{
            position: 'fixed',
            bottom: '25px',
            right: '25px',
            width: showSidebar ? '740px' : '450px',
            maxWidth: 'calc(100vw - 32px)',
            height: '640px',
            maxHeight: 'calc(100vh - 50px)',
            background: 'var(--bg-secondary)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: '24px',
            display: 'flex',
            flexDirection: 'row',
            boxShadow: '0 25px 60px rgba(0,0,0,0.85)',
            zIndex: 99999,
            overflow: 'hidden',
            transition: 'width 0.25s ease'
        }}>
            {/* Conversation History Sidebar */}
            {showSidebar && (
                <div style={{
                    width: '240px',
                    flexShrink: 0,
                    background: '#12121a',
                    borderRight: '1px solid rgba(255,255,255,0.08)',
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '14px',
                    gap: '12px'
                }}>
                    {/* New Chat Button */}
                    <button
                        onClick={handleNewChat}
                        style={{
                            background: 'var(--accent)',
                            border: 'none',
                            color: 'white',
                            padding: '10px 14px',
                            borderRadius: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            fontSize: '13px',
                            fontWeight: 700,
                            cursor: 'pointer',
                            boxShadow: '0 4px 14px rgba(229, 9, 20, 0.35)',
                            transition: 'opacity 0.2s'
                        }}
                    >
                        <Plus size={16} /> New Chat
                    </button>

                    <div style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        color: 'var(--text-muted)',
                        letterSpacing: '0.5px',
                        padding: '4px 6px 0'
                    }}>
                        Chat History
                    </div>

                    {/* Conversations List */}
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px'
                    }}>
                        {conversations.length === 0 ? (
                            <div style={{
                                padding: '24px 10px',
                                textAlign: 'center',
                                color: 'var(--text-muted)',
                                fontSize: '12px'
                            }}>
                                {isLoadingConversations ? "Loading chats..." : (
                                    <>
                                        No past chats yet.<br />Start a conversation!
                                    </>
                                )}
                            </div>
                        ) : (
                            conversations.map(conv => {
                                const isActive = activeConversationId === conv.id;
                                const isItemLoading = isLoadingConversation && activeConversationId === conv.id;
                                return (
                                    <div
                                        key={conv.id}
                                        style={{
                                            padding: '4px 6px',
                                            borderRadius: '8px',
                                            background: isActive ? 'rgba(229, 9, 20, 0.18)' : 'rgba(255,255,255,0.03)',
                                            border: isActive ? '1px solid rgba(229, 9, 20, 0.4)' : '1px solid transparent',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            gap: '4px',
                                            transition: 'all 0.15s ease',
                                            opacity: isItemLoading ? 0.65 : 1
                                        }}
                                        onMouseEnter={e => {
                                            if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                                        }}
                                        onMouseLeave={e => {
                                            if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                                        }}
                                    >
                                        <button
                                            type="button"
                                            onClick={() => handleSelectConversation(conv.id)}
                                            disabled={isLoadingConversation}
                                            title={conv.title || 'Conversation'}
                                            style={{
                                                background: 'transparent',
                                                border: 'none',
                                                cursor: isLoadingConversation ? 'default' : 'pointer',
                                                padding: '5px 4px',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px',
                                                minWidth: 0,
                                                flex: 1,
                                                textAlign: 'left',
                                                color: isActive ? 'white' : 'var(--text-secondary)'
                                            }}
                                        >
                                            <MessageSquare size={13} style={{ flexShrink: 0, color: isActive ? 'var(--accent)' : 'var(--text-muted)' }} />
                                            <span style={{
                                                fontSize: '12px',
                                                fontWeight: isActive ? 600 : 400,
                                                whiteSpace: 'nowrap',
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                flex: 1
                                            }}>
                                                {conv.title || 'Conversation'}
                                            </span>
                                        </button>

                                        <button
                                            type="button"
                                            onClick={(e) => handleDeleteConversation(conv.id, e)}
                                            title={`Delete ${conv.title || 'chat'}`}
                                            aria-label={`Delete ${conv.title || 'chat'}`}
                                            style={{
                                                background: 'transparent',
                                                border: 'none',
                                                color: 'var(--text-muted)',
                                                cursor: 'pointer',
                                                padding: '4px',
                                                borderRadius: '4px',
                                                display: 'flex',
                                                alignItems: 'center',
                                                opacity: 0.7,
                                                flexShrink: 0
                                            }}
                                            onMouseEnter={e => {
                                                e.currentTarget.style.color = '#ff6b6b';
                                                e.currentTarget.style.opacity = 1;
                                            }}
                                            onMouseLeave={e => {
                                                e.currentTarget.style.color = 'var(--text-muted)';
                                                e.currentTarget.style.opacity = 0.7;
                                            }}
                                        >
                                            <Trash2 size={12} />
                                        </button>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}

            {/* Main Chat Panel */}
            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                minWidth: 0,
                background: 'var(--bg-secondary)'
            }}>
                {/* Header */}
                <div style={{
                    padding: '14px 18px',
                    background: 'linear-gradient(135deg, #181824, #0f0f16)',
                    borderBottom: '1px solid rgba(255,255,255,0.1)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {/* Toggle Sidebar Button */}
                        <button
                            onClick={() => setShowSidebar(prev => !prev)}
                            title={showSidebar ? "Hide Chat History" : "Show Chat History"}
                            style={{
                                background: 'rgba(255,255,255,0.08)',
                                border: 'none',
                                color: 'white',
                                cursor: 'pointer',
                                padding: '6px',
                                borderRadius: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                        >
                            {showSidebar ? <PanelLeftClose size={16} /> : <PanelLeft size={16} />}
                        </button>

                        <div style={{
                            background: 'var(--accent)',
                            padding: '7px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxShadow: '0 0 12px rgba(229, 9, 20, 0.4)'
                        }}>
                            <Sparkles size={16} color="white" />
                        </div>
                        <div>
                            <h3 style={{ margin: 0, fontSize: '14.5px', color: 'white', fontWeight: 700 }}>StreamHub TMDB Agent</h3>
                            <span style={{ fontSize: '11px', color: '#2ecc71', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#2ecc71', display: 'inline-block' }} />
                                Persistent Multi-Turn Memory
                            </span>
                        </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                            onClick={handleResetChat}
                            title="New Chat Session"
                            style={{
                                background: 'rgba(255,255,255,0.08)',
                                border: 'none',
                                color: 'var(--text-secondary)',
                                cursor: 'pointer',
                                padding: '6px',
                                borderRadius: '50%',
                                display: 'flex'
                            }}
                        >
                            <RotateCcw size={15} />
                        </button>
                        <button
                            onClick={onClose}
                            style={{
                                background: 'rgba(255,255,255,0.08)',
                                border: 'none',
                                color: 'white',
                                cursor: 'pointer',
                                padding: '6px',
                                borderRadius: '50%',
                                display: 'flex'
                            }}
                        >
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Message Area */}
                <div style={{
                    flex: 1,
                    padding: '16px',
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '14px',
                    background: 'var(--bg-primary)'
                }}>
                    {conversationLoadError && (
                        <div style={{
                            padding: '10px 14px',
                            background: 'rgba(229, 9, 20, 0.15)',
                            border: '1px solid rgba(229, 9, 20, 0.4)',
                            borderRadius: '10px',
                            color: '#ff6b6b',
                            fontSize: '12.5px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '10px'
                        }}>
                            <span>⚠️ {conversationLoadError}</span>
                            <button
                                type="button"
                                onClick={() => activeConversationId && handleSelectConversation(activeConversationId)}
                                style={{
                                    background: 'var(--accent)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    padding: '4px 10px',
                                    fontSize: '11px',
                                    fontWeight: 600,
                                    cursor: 'pointer'
                                }}
                            >
                                Retry
                            </button>
                        </div>
                    )}

                    {isLoadingConversation && (
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            padding: '12px',
                            color: 'var(--text-secondary)',
                            fontSize: '12.5px',
                            background: 'rgba(255,255,255,0.03)',
                            borderRadius: '8px'
                        }}>
                            <div style={{
                                width: '13px',
                                height: '13px',
                                border: '2px solid var(--accent)',
                                borderTopColor: 'transparent',
                                borderRadius: '50%',
                                animation: 'spin 0.8s linear infinite'
                            }} />
                            Loading conversation...
                        </div>
                    )}

                    {messages.map((m, i) => (
                        <div
                            key={i}
                            style={{
                                alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                                maxWidth: '92%',
                                display: 'flex',
                                gap: '10px',
                                alignItems: 'flex-start',
                                flexDirection: m.sender === 'user' ? 'row-reverse' : 'row'
                            }}
                        >
                            <div style={{
                                width: '28px',
                                height: '28px',
                                borderRadius: '50%',
                                flexShrink: 0,
                                background: m.sender === 'user' ? 'var(--bg-tertiary)' : 'var(--accent)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                marginTop: '2px'
                            }}>
                                {m.sender === 'user' ? <UserIcon size={14} color="white" /> : <Bot size={14} color="white" />}
                            </div>

                            <div style={{ width: '100%' }}>
                                {/* Agent Badge for AI messages */}
                                {m.sender === 'ai' && m.agent && (
                                    <div style={{
                                        fontSize: '11px',
                                        fontWeight: 700,
                                        color: m.type === 'subtitle_qa' ? '#2ecc71' : 'var(--accent-hover)',
                                        marginBottom: '4px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                    }}>
                                        <span>{m.type === 'subtitle_qa' ? '🎙️' : '🎬'}</span> {m.agent}
                                        {m.type === 'subtitle_qa' && (
                                            <span style={{
                                                fontSize: '10px',
                                                padding: '1px 6px',
                                                borderRadius: '8px',
                                                background: 'rgba(46, 204, 113, 0.15)',
                                                border: '1px solid rgba(46, 204, 113, 0.3)',
                                                color: '#2ecc71',
                                                marginLeft: '4px'
                                            }}>
                                                Subtitle RAG Grounded
                                            </span>
                                        )}
                                    </div>
                                )}

                                <div style={{
                                    background: m.sender === 'user' ? 'var(--accent)' : 'var(--bg-secondary)',
                                    color: 'white',
                                    padding: '12px 16px',
                                    borderRadius: m.sender === 'user' ? '18px 4px 18px 18px' : '4px 18px 18px 18px',
                                    fontSize: '13.5px',
                                    lineHeight: '1.55',
                                    wordBreak: 'break-word',
                                    border: '1px solid rgba(255,255,255,0.06)',
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    <div>{m.text}</div>
                                    {m.results && renderMovieCards(m.results)}
                                </div>
                            </div>
                        </div>
                    ))}

                    {isLoading && (
                        <div style={{ alignSelf: 'flex-start', display: 'flex', gap: '10px', alignItems: 'flex-start', maxWidth: '88%' }}>
                            <div style={{
                                width: '28px',
                                height: '28px',
                                borderRadius: '50%',
                                background: 'var(--accent)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                marginTop: '2px'
                            }}>
                                <Bot size={14} color="white" />
                            </div>
                            <div style={{
                                background: 'var(--bg-secondary)',
                                padding: '12px 16px',
                                borderRadius: '4px 18px 18px 18px',
                                fontSize: '13px',
                                color: 'var(--text-secondary)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                                <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-hover)', animation: 'pulse 1s infinite' }} />
                                Calling TMDB tools & verifying data...
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Quick Suggestions Chips */}
                <div style={{
                    padding: '8px 14px',
                    background: 'var(--bg-secondary)',
                    borderTop: '1px solid rgba(255,255,255,0.06)',
                    display: 'flex',
                    gap: '8px',
                    overflowX: 'auto',
                    whiteSpace: 'nowrap'
                }}>
                    {QUICK_PROMPTS.map((prompt, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleSend(prompt)}
                            disabled={isLoading}
                            style={{
                                background: 'rgba(255,255,255,0.06)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: 'var(--text-secondary)',
                                padding: '5px 12px',
                                borderRadius: '12px',
                                fontSize: '11px',
                                cursor: 'pointer',
                                flexShrink: 0
                            }}
                        >
                            {prompt}
                        </button>
                    ))}
                </div>

                {/* Input Area */}
                <div style={{
                    padding: '12px 16px',
                    background: 'var(--bg-secondary)',
                    borderTop: '1px solid rgba(255,255,255,0.08)',
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'center'
                }}>
                    <input
                        type="text"
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                        placeholder="Search, ask about movies, runtimes, or cast..."
                        disabled={isLoading}
                        style={{
                            flex: 1,
                            padding: '11px 16px',
                            borderRadius: '20px',
                            border: '1px solid rgba(255,255,255,0.15)',
                            background: 'var(--bg-primary)',
                            color: 'white',
                            outline: 'none',
                            fontSize: '13px'
                        }}
                    />
                    <button
                        onClick={() => handleSend()}
                        disabled={isLoading || !input.trim()}
                        style={{
                            background: input.trim() ? 'var(--accent)' : 'var(--bg-tertiary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '50%',
                            width: '40px',
                            height: '40px',
                            transition: 'all 0.2s ease',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: input.trim() && !isLoading ? 'pointer' : 'default',
                            flexShrink: 0
                        }}
                    >
                        <Send size={16} />
                    </button>
                </div>
            </div>
        </div>,
        document.body
    );
};

export default ChatModal;
